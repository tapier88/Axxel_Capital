"""Minimal Track B forward tick custody owned by the existing Data Engine.

This module is intentionally acquisition-only.  It cannot place orders, expose
research data, read historical partitions, or claim that polling proves a
complete broker tick stream.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import socket
import struct
import tempfile
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable

import numpy as np
import pandas as pd

from src.utils.hashing import canonical_json, file_hash
from src.utils.serialization import atomic_write_json, read_json


CONFIG_SCHEMA = "AXXEL-TRACK-B-CAPTURE-CONFIG-1"
CAPTURE_SCHEMA = "AXXEL-TRACK-B-RAW-1"
ALLOWED_PURPOSE = "FORWARD_CAPTURE_AUDIT"
ALLOWED_TRACK = "B"


class CaptureDenied(PermissionError):
    pass


def _utc(value: datetime) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise CaptureDenied("UTC_AWARE_TIME_REQUIRED")
    return value.astimezone(timezone.utc)


def _iso(value: datetime) -> str:
    return _utc(value).isoformat().replace("+00:00", "Z")


def _sha_json(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def _exclusive_json(path: Path, value: Any) -> None:
    payload = (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n").encode()
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(dir=path.parent, prefix=".staging-")
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.link(temporary_name, path)
        except FileExistsError:
            if path.read_bytes() != payload:
                raise CaptureDenied(f"IMMUTABLE_CONFLICT:{path.name}")
    finally:
        Path(temporary_name).unlink(missing_ok=True)


def _ntp_seconds(data: bytes, offset: int) -> float:
    seconds, fraction = struct.unpack("!II", data[offset:offset + 8])
    return seconds - 2_208_988_800 + fraction / 2**32


class SntpUTCReference:
    """Small independent UTC measurement; no terminal/server clock is reused."""

    def __init__(self, config: dict[str, Any]):
        self.config = config
        self._last_result: dict[str, Any] | None = None
        self._last_monotonic: float | None = None

    def measure(self) -> dict[str, Any]:
        now_monotonic = time.monotonic()
        cadence = self.config["utc_reference"]["refresh_cadence_seconds"]
        if (self._last_result is not None and self._last_monotonic is not None and
                now_monotonic - self._last_monotonic < cadence):
            cached = dict(self._last_result)
            cached["cached"] = True
            cached["reference_age_milliseconds"] = (now_monotonic - self._last_monotonic) * 1000
            return cached
        samples, failures = [], []
        timeout = self.config["timeouts"]["utc_reference_milliseconds"] / 1000
        for server in self.config["utc_reference"]["servers"]:
            packet = bytearray(48)
            packet[0] = 0x23
            try:
                address = socket.getaddrinfo(server, 123, family=socket.AF_INET, type=socket.SOCK_DGRAM)[0][-1]
                with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as client:
                    client.settimeout(timeout)
                    wall_before = time.time()
                    mono_before = time.monotonic_ns()
                    client.sendto(packet, address)
                    data, _ = client.recvfrom(512)
                    mono_after = time.monotonic_ns()
                    wall_after = time.time()
                if len(data) < 48:
                    raise OSError("short NTP response")
                server_receive, server_transmit = _ntp_seconds(data, 32), _ntp_seconds(data, 40)
                offset = ((server_receive - wall_before) + (server_transmit - wall_after)) / 2
                delay = max(0.0, (wall_after - wall_before) - (server_transmit - server_receive))
                samples.append({
                    "server": server,
                    "offset_milliseconds": offset * 1000,
                    "round_trip_milliseconds": (mono_after - mono_before) / 1_000_000,
                    "uncertainty_milliseconds": max(1.0, delay * 500),
                    "measured_utc": _iso(datetime.fromtimestamp(wall_after + offset, timezone.utc)),
                })
            except (OSError, ValueError) as exc:
                failures.append({"server": server, "error_type": type(exc).__name__, "message": str(exc)})
        required = self.config["utc_reference"]["required_responses"]
        if len(samples) < required:
            result = {"available": False, "strategy": "SNTP", "samples": samples, "failures": failures,
                      "cached": False}
            self._last_result, self._last_monotonic = result, now_monotonic
            return dict(result)
        offsets = sorted(sample["offset_milliseconds"] for sample in samples)
        spread = offsets[-1] - offsets[0] if len(offsets) > 1 else 0.0
        uncertainty = max(sample["uncertainty_milliseconds"] for sample in samples) + spread / 2
        result = {
            "available": True,
            "strategy": "SNTP",
            "samples": samples,
            "failures": failures,
            "source_disagreement_milliseconds": spread,
            "uncertainty_milliseconds": uncertainty,
            "cached": False,
        }
        self._last_result, self._last_monotonic = result, now_monotonic
        return dict(result)


class MT5TickSource:
    """Narrow adapter: deliberately omits every trading method."""

    def __init__(self, config: dict[str, Any], module=None):
        if module is None:
            import MetaTrader5 as module
        self.mt5 = module
        self.config = config
        self.connected = False
        self.connection: dict[str, Any] | None = None

    def open(self) -> dict[str, Any]:
        timeout = self.config["timeouts"]["mt5_initialize_milliseconds"]
        if not self.mt5.initialize(timeout=timeout):
            raise RuntimeError(f"MT5_INITIALIZE:{self.mt5.last_error()}")
        account, terminal, version = self.mt5.account_info(), self.mt5.terminal_info(), self.mt5.version()
        if account is None or terminal is None or version is None:
            self.mt5.shutdown()
            raise RuntimeError(f"MT5_IDENTITY:{self.mt5.last_error()}")
        scope = self.config["scope"]
        if account.server != scope["server"]:
            self.mt5.shutdown()
            raise CaptureDenied("SERVER_IDENTITY_DENIED")
        demo_value = getattr(self.mt5, "ACCOUNT_TRADE_MODE_DEMO", 0)
        if account.trade_mode != demo_value:
            self.mt5.shutdown()
            raise CaptureDenied("NON_DEMO_ACCOUNT_DENIED")
        if scope["broker_company_contains"].casefold() not in account.company.casefold():
            self.mt5.shutdown()
            raise CaptureDenied("BROKER_IDENTITY_DENIED")
        if not self.mt5.symbol_select(scope["symbol"], True):
            self.mt5.shutdown()
            raise CaptureDenied("SYMBOL_DENIED")
        login_fingerprint = hashlib.sha256(f"{account.server}:{account.login}".encode()).hexdigest()
        self.connection = {
            "server": account.server,
            "broker": account.company,
            "account_mode": "DEMO",
            "account_fingerprint_sha256": login_fingerprint,
            "terminal_company": terminal.company,
            "terminal_build": version[1],
            "package_version": getattr(self.mt5, "__version__", "UNKNOWN"),
            "session_id": str(uuid.uuid4()),
        }
        self.connected = True
        return dict(self.connection)

    def close(self) -> None:
        if self.connected:
            self.mt5.shutdown()
        self.connected = False

    def reconnect(self) -> dict[str, Any]:
        self.close()
        return self.open()

    def symbol_specification(self) -> Any:
        value = self.mt5.symbol_info(self.config["scope"]["symbol"])
        if value is None:
            raise RuntimeError(f"MT5_SYMBOL_INFO:{self.mt5.last_error()}")
        return value

    def copy_ticks(self, start: datetime, end: datetime) -> Any:
        return self.mt5.copy_ticks_range(
            self.config["scope"]["symbol"], _utc(start), _utc(end), self.mt5.COPY_TICKS_ALL
        )

    def last_error(self) -> Any:
        return self.mt5.last_error()


@dataclass
class CaptureResult:
    status: str
    batch_id: str | None = None
    rows: int = 0
    incidents: tuple[str, ...] = ()


class TrackBForwardCapture:
    def __init__(
        self,
        project_root: Path | str,
        config_path: Path | str,
        *,
        source: Any | None = None,
        utc_reference: Any | None = None,
        utc_now: Callable[[], datetime] | None = None,
        monotonic_ns: Callable[[], int] | None = None,
        sleeper: Callable[[float], None] | None = None,
        disk_usage: Callable[[Path], Any] | None = None,
    ):
        self.root = Path(project_root).resolve()
        self.config_path = Path(config_path)
        if not self.config_path.is_absolute():
            self.config_path = self.root / self.config_path
        self.config = read_json(self.config_path, {})
        self._validate_config()
        self.config_sha256 = file_hash(self.config_path)
        self.base = self.root / "data/engine/forward/track_b_xm_forward_capture_v1"
        self.control = self.base / "control"
        self.batches = self.base / "batches"
        self.staging = self.base / "staging"
        self.derived = self.base / "derived"
        self.incidents = self.base / "incidents"
        self.source = source or MT5TickSource(self.config)
        self.utc_reference = utc_reference or SntpUTCReference(self.config)
        self.utcnow = utc_now or (lambda: datetime.now(timezone.utc))
        self.monotonic_ns = monotonic_ns or time.monotonic_ns
        self.sleep = sleeper or time.sleep
        self.disk_usage = disk_usage or shutil.disk_usage
        self.connection: dict[str, Any] | None = None

    def _validate_config(self) -> None:
        c = self.config
        if c.get("schema_version") != CONFIG_SCHEMA or c.get("config_id") != "TRACK_B_XM_FORWARD_CAPTURE_V1" or c.get("status") != "FROZEN":
            raise CaptureDenied("CONFIG_NOT_FROZEN")
        s = c.get("scope", {})
        required = {"track": "B", "partition": "FORWARD_EXECUTION", "server": "XMGlobal-MT5 6",
                    "symbol": "GOLD", "instrument": "XAUUSD", "environment": "DEMO",
                    "mode": "READ_ONLY", "orders_authorized": False, "fills_authorized": False,
                    "slippage_observed": False, "research_authorized": False}
        if any(s.get(key) != value for key, value in required.items()):
            raise CaptureDenied("SCOPE_CONFIG_DENIED")
        if c["polling"].get("claim_tick_completeness") is not False:
            raise CaptureDenied("TICK_COMPLETENESS_CLAIM_DENIED")
        if c["retention"].get("policy") != "NO_AUTOMATIC_DELETION_DURING_QUALIFICATION":
            raise CaptureDenied("RETENTION_POLICY_DENIED")
        if c["qualification"].get("g4_immediate_completion_forbidden") is not True:
            raise CaptureDenied("G4_POLICY_DENIED")

    def authorize(self, request: dict[str, Any]) -> dict[str, str]:
        expected = {
            "track": "B", "partition": "FORWARD_EXECUTION", "purpose": ALLOWED_PURPOSE,
            "environment": "DEMO", "server": "XMGlobal-MT5 6", "symbol": "GOLD",
            "operation": "READ_DERIVED_CAPTURE",
        }
        if (self.control / "REVOKED.json").exists():
            return {"decision": "DENY", "reason": "SCOPE_REVOKED"}
        if not isinstance(request, dict) or set(request) != set(expected):
            return {"decision": "DENY", "reason": "MALFORMED_OR_EXPANDED_REQUEST"}
        for key, value in expected.items():
            if request.get(key) != value:
                reason = "TRACK_A_DENIED" if key == "track" else "RESEARCH_DENIED" if key == "purpose" else f"{key.upper()}_DENIED"
                return {"decision": "DENY", "reason": reason}
        return {"decision": "ALLOW", "reason": "TRACK_B_AUDIT_SCOPE_ONLY"}

    def revoke(self, reason: str) -> None:
        atomic_write_json(self.control / "REVOKED.json", {"at_utc": _iso(self.utcnow()), "reason": reason})
        self._incident("SCOPE_REVOKED", {"reason": reason})

    def _state(self) -> dict[str, Any]:
        return read_json(self.control / "checkpoint.json", {})

    def _incident(self, classification: str, detail: dict[str, Any]) -> str:
        allowed = set(self.config["incident_classification"]["classes"])
        if classification not in allowed:
            classification = "UNKNOWN:" + classification
        incident_id = f"INC-{_iso(self.utcnow()).replace(':', '').replace('-', '')}-{uuid.uuid4().hex[:12]}"
        _exclusive_json(self.incidents / f"{incident_id}.json", {
            "schema_version": CAPTURE_SCHEMA,
            "incident_id": incident_id,
            "classification": classification,
            "observed_at_utc": _iso(self.utcnow()),
            "monotonic_ns": self.monotonic_ns(),
            "detail": detail,
            "config_sha256": self.config_sha256,
        })
        return incident_id

    def _ensure_not_revoked_or_low_disk(self) -> None:
        if (self.control / "REVOKED.json").exists():
            raise CaptureDenied("SCOPE_REVOKED")
        free = self.disk_usage(self.root).free
        minimum = self.config["backpressure"]["disk_minimum_free_bytes"]
        if free < minimum:
            self._incident("DISK_THRESHOLD", {"free_bytes": free, "minimum_free_bytes": minimum})
            raise CaptureDenied("DISK_THRESHOLD")

    def connect(self) -> dict[str, Any]:
        self._ensure_not_revoked_or_low_disk()
        self.connection = self.source.open()
        return dict(self.connection)

    def close(self) -> None:
        self.source.close()
        self.connection = None

    def _reconnect(self) -> dict[str, Any]:
        previous = self.connection
        current = self.source.reconnect()
        identity_keys = ("server", "account_fingerprint_sha256")
        if previous and any(previous.get(key) != current.get(key) for key in identity_keys):
            self._incident("SERVER_ACCOUNT_IDENTITY_CHANGE", {
                "previous": {key: previous.get(key) for key in identity_keys},
                "current": {key: current.get(key) for key in identity_keys},
                "new_session_identity": True,
            })
        self.connection = current
        self._incident("RECONNECT", {"previous_session": previous, "new_session": current})
        return dict(current)

    def _register_t0(self) -> datetime:
        path = self.control / "t0.json"
        existing = read_json(path, {})
        if existing:
            return _utc(datetime.fromisoformat(existing["t0_utc"].replace("Z", "+00:00")))
        # This is written immediately before the first quote/specification API call.
        now = _utc(self.utcnow())
        _exclusive_json(path, {
            "schema_version": CAPTURE_SCHEMA,
            "t0_utc": _iso(now),
            "monotonic_ns": self.monotonic_ns(),
            "meaning": "FIRST_AUTHORIZED_TRACK_B_CAPTURE_BOUNDARY",
            "no_requests_before_t0": True,
            "config_sha256": self.config_sha256,
        })
        return now

    @staticmethod
    def _as_original_mapping(value: Any) -> dict[str, Any]:
        if hasattr(value, "_asdict"):
            return dict(value._asdict())
        if isinstance(value, dict):
            return dict(value)
        raise TypeError("API response is not a named tuple or mapping")

    @staticmethod
    def _json_safe(value: Any) -> Any:
        if isinstance(value, dict):
            return {str(k): TrackBForwardCapture._json_safe(v) for k, v in value.items()}
        if isinstance(value, (list, tuple)):
            return [TrackBForwardCapture._json_safe(v) for v in value]
        if isinstance(value, np.generic):
            value = value.item()
        if isinstance(value, float) and not np.isfinite(value):
            return {"nonfinite_float": repr(value)}
        if value is None or isinstance(value, (str, int, float, bool)):
            return value
        return {"python_type": type(value).__name__, "repr": repr(value)}

    def _snapshot_spec(self, stage: Path, state: dict[str, Any], t0: datetime) -> tuple[dict[str, Any], list[str]]:
        observed_before, mono_before = _utc(self.utcnow()), self.monotonic_ns()
        if observed_before < t0:
            raise CaptureDenied("CLOCK_BEFORE_T0")
        response = self.source.symbol_specification()
        observed_after, mono_after = _utc(self.utcnow()), self.monotonic_ns()
        original = self._json_safe(self._as_original_mapping(response))
        spec_path = stage / "symbol_specification_original.json"
        spec_path.write_text(json.dumps(original, sort_keys=False, ensure_ascii=False, default=str, allow_nan=False) + "\n", encoding="utf-8")
        with spec_path.open("rb+") as handle:
            os.fsync(handle.fileno())
        raw_digest = file_hash(spec_path)
        contract_field_names = (
            "name", "path", "description", "currency_base", "currency_profit", "currency_margin",
            "digits", "point", "trade_contract_size", "trade_tick_size", "trade_tick_value",
            "trade_tick_value_profit", "trade_tick_value_loss", "trade_mode", "trade_calc_mode",
            "trade_exemode", "trade_stops_level", "trade_freeze_level", "volume_min", "volume_max",
            "volume_step", "volume_limit", "swap_mode", "swap_long", "swap_short",
            "swap_rollover3days", "swap_sunday", "swap_monday", "swap_tuesday", "swap_wednesday",
            "swap_thursday", "swap_friday", "swap_saturday", "start_time", "expiration_time",
            "spread_float", "option_mode", "option_right",
        )
        contract_projection = {name: original.get(name, "NOT_AVAILABLE") for name in contract_field_names}
        contract_digest = _sha_json(contract_projection)
        incidents: list[str] = []
        prior = state.get("symbol_specification_contract_sha256")
        interval_id = state.get("symbol_specification_interval_id") or f"SPEC-{contract_digest[:16]}"
        if prior and prior != contract_digest:
            interval_id = f"SPEC-{contract_digest[:16]}-{uuid.uuid4().hex[:8]}"
            incidents.append(self._incident("SYMBOL_SPECIFICATION_CHANGE", {
                "previous_contract_sha256": prior, "new_contract_sha256": contract_digest,
                "detected_at_utc": _iso(observed_after), "effective_from_known": False,
            }))
        descriptor = {
            "path": spec_path.name, "raw_response_sha256": raw_digest,
            "contract_projection": contract_projection, "contract_sha256": contract_digest,
            "observed_before_utc": _iso(observed_before), "observed_after_utc": _iso(observed_after),
            "monotonic_before_ns": mono_before, "monotonic_after_ns": mono_after,
            "interval_id": interval_id,
            "retroactive_application": False,
            "available_fields": list(original.keys()),
            "session_metadata": "NOT_AVAILABLE_IN_METATRADER5_PYTHON_5.0.5430",
        }
        return descriptor, incidents

    def _request_window(self, state: dict[str, Any], t0: datetime, now: datetime) -> tuple[datetime, datetime, bool]:
        overlap = timedelta(milliseconds=self.config["polling"]["overlap_milliseconds"])
        if state.get("request_to_utc"):
            cursor = _utc(datetime.fromisoformat(state["request_to_utc"].replace("Z", "+00:00")))
            start = max(t0, cursor - overlap)
        else:
            cursor, start = t0, t0
        maximum = timedelta(seconds=self.config["polling"]["maximum_request_span_seconds"])
        end = min(_utc(now), start + maximum)
        if end < start:
            raise CaptureDenied("CLOCK_INCONSISTENCY")
        lag = (_utc(now) - cursor).total_seconds()
        return start, end, lag > self.config["backpressure"]["maximum_tolerated_lag_seconds"]

    def capture_once(self, *, fault_after_raw: bool = False) -> CaptureResult:
        self._ensure_not_revoked_or_low_disk()
        if self.connection is None:
            self.connect()
        t0 = self._register_t0()
        state = self._state()
        request_id, batch_id = str(uuid.uuid4()), f"TB1-{uuid.uuid4().hex}"
        stage = self.staging / request_id
        stage.mkdir(parents=True, exist_ok=False)
        incidents: list[str] = []
        now = _utc(self.utcnow())
        try:
            start, end, backlog = self._request_window(state, t0, now)
        except CaptureDenied as exc:
            incidents.append(self._incident("CLOCK_INCONSISTENCY", {
                "reason": str(exc), "t0_utc": _iso(t0), "now_utc": _iso(now),
            }))
            raise
        if backlog:
            incidents.append(self._incident("BACKLOG_EXCEEDED", {
                "last_committed_to_utc": state.get("request_to_utc"), "capture_now_utc": _iso(now)
            }))
        request = {
            "request_id": request_id, "batch_id": batch_id, "api": "MetaTrader5.copy_ticks_range",
            "symbol": self.config["scope"]["symbol"], "from_utc": _iso(start), "to_utc": _iso(end),
            "flags": "COPY_TICKS_ALL", "track": "B", "environment": "DEMO",
            "orders_authorized": False, "fills_authorized": False, "research_authorized": False,
        }
        request_path = stage / "request.json"
        request_path.write_text(json.dumps(request, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        with request_path.open("rb+") as handle:
            os.fsync(handle.fileno())

        spec_due = (not state.get("symbol_specification_observed_at_utc") or
                    (_utc(now) - _utc(datetime.fromisoformat(state["symbol_specification_observed_at_utc"].replace("Z", "+00:00")))).total_seconds()
                    >= self.config["symbol_specification"]["snapshot_cadence_seconds"] or
                    state.get("session_id") != self.connection["session_id"])
        spec_descriptor = None
        if spec_due:
            spec_descriptor, spec_incidents = self._snapshot_spec(stage, state, t0)
            incidents.extend(spec_incidents)

        attempts, successful_array = [], None
        maximum_attempts = self.config["retry"]["maximum_attempts"]
        for attempt_number in range(1, maximum_attempts + 1):
            before_utc, before_mono = _utc(self.utcnow()), self.monotonic_ns()
            response, error = None, None
            try:
                response = self.source.copy_ticks(start, end)
                if response is None:
                    error = {"error_type": "MT5_NONE", "last_error": repr(self.source.last_error())}
            except Exception as exc:  # preserved and classified; no silent fallback
                error = {"error_type": type(exc).__name__, "message": str(exc), "last_error": repr(self.source.last_error())}
            after_mono, after_utc = self.monotonic_ns(), _utc(self.utcnow())
            elapsed_ms = (after_mono - before_mono) / 1_000_000
            record: dict[str, Any] = {
                "attempt": attempt_number, "request": request,
                "call_before_utc": _iso(before_utc), "call_after_utc": _iso(after_utc),
                "monotonic_before_ns": before_mono, "monotonic_after_ns": after_mono,
                "elapsed_milliseconds": elapsed_ms,
                "receipt_time_utc": _iso(after_utc), "error": error,
            }
            if elapsed_ms > self.config["timeouts"]["mt5_call_observation_threshold_milliseconds"]:
                incidents.append(self._incident("API_TIMEOUT_THRESHOLD_EXCEEDED", {"request_id": request_id, "elapsed_milliseconds": elapsed_ms}))
            if error is None:
                array = np.asarray(response)
                response_path = stage / f"attempt-{attempt_number:03d}-response.npy"
                with response_path.open("wb") as handle:
                    np.save(handle, array, allow_pickle=False)
                    handle.flush(); os.fsync(handle.fileno())
                record.update({
                    "response_kind": "NUMPY_NDARRAY_AT_API_BOUNDARY", "response_path": response_path.name,
                    "response_sha256": file_hash(response_path), "dtype": array.dtype.descr,
                    "dtype_string": array.dtype.str, "shape": list(array.shape), "strides": list(array.strides),
                    "itemsize": array.dtype.itemsize, "nbytes": array.nbytes,
                    "c_contiguous": bool(array.flags.c_contiguous), "row_count": int(len(array)),
                })
                successful_array = array
                if len(array) == 0:
                    incidents.append(self._incident("EMPTY_RESPONSE", {"request_id": request_id, "attempt": attempt_number}))
                break
            error_path = stage / f"attempt-{attempt_number:03d}-response.json"
            error_path.write_text(json.dumps({"response": None, "error": error}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            with error_path.open("rb+") as handle:
                os.fsync(handle.fileno())
            record.update({"response_kind": "NONE_OR_EXCEPTION_AT_API_BOUNDARY", "response_path": error_path.name,
                           "response_sha256": file_hash(error_path), "row_count": 0})
            incidents.append(self._incident("API_ERROR", {"request_id": request_id, "attempt": attempt_number, "error": error}))
            attempts.append(record)
            if attempt_number < maximum_attempts:
                self.sleep(self.config["retry"]["backoff_seconds"][attempt_number - 1])
            continue
        if error is None:
            attempts.append(record)
        if fault_after_raw:
            raise RuntimeError("INJECTED_CRASH_AFTER_RAW_BEFORE_COMMIT")

        reference = self.utc_reference.measure()
        if not reference.get("available"):
            incidents.append(self._incident("UTC_REFERENCE_UNAVAILABLE", {"request_id": request_id, "reference": reference}))
        else:
            uncertainty = reference["uncertainty_milliseconds"]
            disagreement = reference["source_disagreement_milliseconds"]
            if uncertainty > self.config["utc_reference"]["maximum_uncertainty_milliseconds"]:
                incidents.append(self._incident("UTC_UNCERTAINTY_EXCEEDED", {"request_id": request_id, "uncertainty_milliseconds": uncertainty}))
            if disagreement > self.config["utc_reference"]["maximum_source_disagreement_milliseconds"]:
                incidents.append(self._incident("UTC_SOURCE_DISAGREEMENT", {"request_id": request_id, "source_disagreement_milliseconds": disagreement}))

        rows = 0 if successful_array is None else int(len(successful_array))
        if rows > self.config["batch"]["maximum_records"]:
            incidents.append(self._incident("BATCH_RECORD_LIMIT_EXCEEDED", {"request_id": request_id, "rows": rows}))
        successful_digest = next((a["response_sha256"] for a in reversed(attempts) if a["response_kind"] == "NUMPY_NDARRAY_AT_API_BOUNDARY"), None)
        if successful_digest and successful_digest == state.get("last_response_sha256"):
            incidents.append(self._incident("DUPLICATE_RESPONSE", {"request_id": request_id, "response_sha256": successful_digest}))

        recovery_control = read_json(self.control / "recovery_pending.json", {})
        recovered = bool(state.get("gap_open") or recovery_control.get("status") == "PENDING")
        if recovered and rows:
            incidents.append(self._incident("RECOVERED_AFTER_GAP", {"request_id": request_id, "from_utc": _iso(start), "to_utc": _iso(end)}))
        gap_open = successful_array is None
        descriptor = {
            "schema_version": CAPTURE_SCHEMA, "config_id": self.config["config_id"],
            "config_sha256": self.config_sha256, "request": request, "connection": self.connection,
            "t0_utc": _iso(t0), "attempts": attempts, "utc_reference": reference,
            "symbol_specification": spec_descriptor, "incidents": incidents,
            "fields_not_available": ["current_server_time", "current_terminal_time", "quotation_session_windows", "trading_session_windows"],
            "claims": {"tick_completeness": False, "orders": False, "fills": False, "slippage": "NOT_OBSERVED", "research": False},
            "recovered_after_gap": recovered,
        }
        descriptor_path = stage / "descriptor.json"
        descriptor_path.write_text(json.dumps(descriptor, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")
        with descriptor_path.open("rb+") as handle:
            os.fsync(handle.fileno())
        artifacts = {p.name: file_hash(p) for p in sorted(stage.iterdir()) if p.is_file()}
        manifest = {
            "schema_version": CAPTURE_SCHEMA, "batch_id": batch_id, "sequence": int(state.get("sequence", 0)) + 1,
            "previous_commit_sha256": state.get("commit_sha256"), "artifacts": artifacts,
            "descriptor_sha256": artifacts["descriptor.json"], "rows": rows,
            "status": "CAPTURED_AWAITING_QUALIFICATION", "eligible_for_research": False,
            "tick_completeness_claimed": False, "durable_commit_required": True,
        }
        manifest_path = stage / "manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        with manifest_path.open("rb+") as handle:
            os.fsync(handle.fileno())
        commit = {"batch_id": batch_id, "manifest_sha256": file_hash(manifest_path), "committed_at_utc": _iso(self.utcnow())}
        commit["commit_sha256"] = _sha_json(commit)
        commit_path = stage / "COMMIT.json"
        commit_path.write_text(json.dumps(commit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        with commit_path.open("rb+") as handle:
            os.fsync(handle.fileno())
        final = self.batches / batch_id
        final.parent.mkdir(parents=True, exist_ok=True)
        os.rename(stage, final)

        checkpoint = {
            "schema_version": CAPTURE_SCHEMA, "sequence": manifest["sequence"], "batch_id": batch_id,
            "commit_sha256": commit["commit_sha256"],
            "request_to_utc": _iso(end) if successful_array is not None else state.get("request_to_utc", _iso(t0)),
            "t0_utc": _iso(t0),
            "last_response_sha256": successful_digest, "gap_open": gap_open,
            "session_id": self.connection["session_id"],
            "symbol_specification_raw_sha256": spec_descriptor["raw_response_sha256"] if spec_descriptor else state.get("symbol_specification_raw_sha256"),
            "symbol_specification_contract_sha256": spec_descriptor["contract_sha256"] if spec_descriptor else state.get("symbol_specification_contract_sha256"),
            "symbol_specification_interval_id": spec_descriptor["interval_id"] if spec_descriptor else state.get("symbol_specification_interval_id"),
            "symbol_specification_observed_at_utc": spec_descriptor["observed_after_utc"] if spec_descriptor else state.get("symbol_specification_observed_at_utc"),
        }
        atomic_write_json(self.control / "checkpoint.json", checkpoint)
        if recovered and successful_array is not None and recovery_control.get("status") == "PENDING":
            atomic_write_json(self.control / "recovery_pending.json", {
                **recovery_control, "status": "RESOLVED_BY_COMMITTED_RECAPTURE",
                "resolved_batch_id": batch_id, "resolved_at_utc": _iso(self.utcnow()),
            })
        self._write_derived(final, descriptor, successful_array)
        if successful_array is None:
            status = "ERROR_COMMITTED_RECONNECT_REQUIRED"
        elif backlog or rows > self.config["backpressure"]["maximum_tolerated_backlog_records"]:
            status = "BACKPRESSURE_STOP_REQUIRED"
        else:
            status = "CAPTURED_AWAITING_QUALIFICATION"
        return CaptureResult(status, batch_id, rows, tuple(incidents))

    def _write_derived(self, batch: Path, descriptor: dict[str, Any], array: np.ndarray | None) -> None:
        if array is None:
            frame = pd.DataFrame()
        else:
            # No sorting/deduplication: response order and multiplicity are explicit.
            frame = pd.DataFrame.from_records(array)
            frame.insert(0, "response_index", np.arange(len(frame), dtype="int64"))
            frame.insert(0, "batch_id", descriptor["request"]["batch_id"])
            frame["receipt_time_utc"] = descriptor["attempts"][-1]["receipt_time_utc"]
            frame["receipt_monotonic_ns"] = descriptor["attempts"][-1]["monotonic_after_ns"]
            frame["recovered_after_gap"] = descriptor["recovered_after_gap"]
            if "bid" in frame and "ask" in frame:
                frame["spread_price"] = frame["ask"] - frame["bid"]
        target = self.derived / f"{descriptor['request']['batch_id']}.parquet"
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            return
        fd, temporary_name = tempfile.mkstemp(dir=target.parent, prefix=".staging-", suffix=".parquet")
        os.close(fd)
        temporary = Path(temporary_name)
        try:
            frame.to_parquet(temporary, index=False, compression="zstd")
            with temporary.open("rb+") as handle:
                os.fsync(handle.fileno())
            os.link(temporary, target)
        finally:
            temporary.unlink(missing_ok=True)

    def read_derived(self, batch_id: str, request: dict[str, Any]) -> pd.DataFrame:
        decision = self.authorize(request)
        if decision["decision"] != "ALLOW":
            raise CaptureDenied(decision["reason"])
        if not isinstance(batch_id, str) or not batch_id.startswith("TB1-") or any(x in batch_id for x in ("/", "\\", "..")):
            raise CaptureDenied("BATCH_ID_DENIED")
        batch = self.batches / batch_id
        commit_path, manifest_path = batch / "COMMIT.json", batch / "manifest.json"
        if not commit_path.exists() or not manifest_path.exists():
            raise CaptureDenied("BATCH_NOT_DURABLY_COMMITTED")
        commit = read_json(commit_path, {})
        if file_hash(manifest_path) != commit.get("manifest_sha256"):
            raise CaptureDenied("BATCH_INTEGRITY_FAILURE")
        path = self.derived / f"{batch_id}.parquet"
        if not path.exists():
            raise CaptureDenied("DERIVED_VIEW_UNAVAILABLE")
        return pd.read_parquet(path)

    def recover_partial_staging(self) -> list[str]:
        recovered = []
        if not self.staging.exists():
            return recovered
        for path in sorted(p for p in self.staging.iterdir() if p.is_dir()):
            incident = self._incident("PARTIAL_STAGING_RECOVERED", {
                "staging_id": path.name, "files": sorted(p.name for p in path.iterdir()),
                "action": "PRESERVED_UNCOMMITTED_NO_CHECKPOINT_ADVANCE",
            })
            recovered.append(incident)
        if recovered:
            existing = read_json(self.control / "recovery_pending.json", {})
            atomic_write_json(self.control / "recovery_pending.json", {
                "schema_version": CAPTURE_SCHEMA, "status": "PENDING",
                "incident_ids": sorted(set(existing.get("incident_ids", []) + recovered)),
                "reason": "UNCOMMITTED_RESPONSE_BOUNDARY_REQUIRES_RECAPTURE",
                "never_request_before_t0": True,
            })
        return recovered

    def run(self, duration_seconds: int | None = None) -> None:
        started = time.monotonic()
        self.recover_partial_staging()
        try:
            self.connect()
            while duration_seconds is None or time.monotonic() - started < duration_seconds:
                try:
                    result = self.capture_once()
                    if result.status == "ERROR_COMMITTED_RECONNECT_REQUIRED":
                        self._reconnect()
                    elif result.status == "BACKPRESSURE_STOP_REQUIRED":
                        raise CaptureDenied("BACKPRESSURE_STOP_REQUIRED")
                except CaptureDenied:
                    raise
                except Exception as exc:
                    self._incident("GAP_OR_INTERRUPTION", {"error_type": type(exc).__name__, "message": str(exc)})
                    try:
                        self._reconnect()
                    except Exception as reconnect_error:
                        self._incident("API_ERROR", {"during": "reconnect", "message": str(reconnect_error)})
                        raise
                self.sleep(self.config["polling"]["cadence_seconds"])
        finally:
            self.close()


def audit_request(**overrides: Any) -> dict[str, Any]:
    request = {
        "track": "B", "partition": "FORWARD_EXECUTION", "purpose": ALLOWED_PURPOSE,
        "environment": "DEMO", "server": "XMGlobal-MT5 6", "symbol": "GOLD",
        "operation": "READ_DERIVED_CAPTURE",
    }
    request.update(overrides)
    return request
