"""Synthetic proof for Track B custody; no terminal, network, or holdout access."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from src.data.engine import DataEngine
from src.data.track_b_forward_capture import CaptureDenied, MT5TickSource, TrackBForwardCapture, audit_request


DTYPE = np.dtype([
    ("time", "<i8"), ("bid", "<f8"), ("ask", "<f8"), ("last", "<f8"),
    ("volume", "<u8"), ("time_msc", "<i8"), ("flags", "<u4"), ("volume_real", "<f8"),
])


def ticks(rows=None):
    rows = rows or [
        (1_788_520_000, 2400.1, 2400.3, 0.0, 0, 1_788_520_000_123, 130, 0.0),
        (1_788_520_000, 2400.2, 2400.4, 0.0, 0, 1_788_520_000_123, 134, 0.0),
        (1_788_520_001, 2400.0, 2400.2, 0.0, 0, 1_788_520_001_005, 130, 0.0),
    ]
    return np.array(rows, dtype=DTYPE)


class Clock:
    def __init__(self, start=datetime(2026, 9, 4, 12, 0, tzinfo=timezone.utc)):
        self.value = start
        self.mono = 1_000_000_000

    def now(self):
        result = self.value
        self.value += timedelta(milliseconds=1)
        return result

    def monotonic_ns(self):
        self.mono += 1_000_000
        return self.mono

    def advance(self, seconds):
        self.value += timedelta(seconds=seconds)


class Reference:
    def __init__(self, available=True, uncertainty=5.0, disagreement=2.0):
        self.available, self.uncertainty, self.disagreement = available, uncertainty, disagreement

    def measure(self):
        if not self.available:
            return {"available": False, "strategy": "FIXTURE", "samples": [], "failures": [{"error": "fixture"}]}
        return {"available": True, "strategy": "FIXTURE", "samples": [{"server": "fixture"}], "failures": [],
                "uncertainty_milliseconds": self.uncertainty,
                "source_disagreement_milliseconds": self.disagreement}


class Source:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []
        self.session = 0
        self.account_fingerprint = "a" * 64
        self.spec = {"name": "GOLD", "digits": 2, "point": 0.01, "trade_contract_size": 100.0,
                     "trade_tick_size": 0.01, "trade_tick_value": 1.0, "swap_mode": 1,
                     "swap_long": -10.0, "swap_short": 4.0, "swap_rollover3days": 3,
                     "bid": 2400.1, "ask": 2400.3, "time": 1_788_520_000}

    def open(self):
        self.session += 1
        return {"server": "XMGlobal-MT5 6", "broker": "XM Global", "account_mode": "DEMO",
                "account_fingerprint_sha256": self.account_fingerprint, "terminal_company": "MetaQuotes",
                "terminal_build": 5000, "package_version": "fixture", "session_id": f"session-{self.session}"}

    def close(self):
        pass

    def reconnect(self):
        self.calls.append(("reconnect",))
        return self.open()

    def symbol_specification(self):
        self.calls.append(("symbol_specification",))
        return dict(self.spec)

    def copy_ticks(self, start, end):
        self.calls.append(("copy_ticks", start, end))
        value = self.responses.pop(0)
        if isinstance(value, BaseException):
            raise value
        return value

    def last_error(self):
        return (1, "fixture error")


def worker(tmp_path, responses, *, reference=None, disk_free=20 * 1024**3, clock=None):
    clock = clock or Clock()
    source = Source(responses)
    config_path = Path(__file__).parents[2] / "config/track_b_xm_forward_capture_v1.json"
    w = TrackBForwardCapture(
        tmp_path, config_path, source=source, utc_reference=reference or Reference(), utc_now=clock.now,
        monotonic_ns=clock.monotonic_ns, sleeper=lambda _: None,
        disk_usage=lambda _: SimpleNamespace(free=disk_free),
    )
    return w, source, clock


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def load_raw(w, batch_id):
    descriptor = read_json(w.batches / batch_id / "descriptor.json")
    attempt = descriptor["attempts"][-1]
    return np.load(w.batches / batch_id / attempt["response_path"], allow_pickle=False)


def incident_text(w):
    return "\n".join(p.read_text(encoding="utf-8") for p in w.incidents.glob("*.json"))


def test_preserves_dtype_order_multiplicity_and_identical_milliseconds(tmp_path):
    original = ticks()
    w, _, _ = worker(tmp_path, [original])
    result = w.capture_once()
    raw = load_raw(w, result.batch_id)
    assert raw.dtype == original.dtype
    assert raw.dtype.descr == original.dtype.descr
    assert np.array_equal(raw, original)
    assert raw[0]["time_msc"] == raw[1]["time_msc"]
    assert w.source.calls[-1][1] >= datetime.fromisoformat(read_json(w.control / "t0.json")["t0_utc"].replace("Z", "+00:00"))
    derived = w.read_derived(result.batch_id, audit_request())
    assert derived["response_index"].tolist() == [0, 1, 2]
    assert derived["time_msc"].tolist()[:2] == [1_788_520_000_123] * 2


def test_crash_after_raw_never_advances_checkpoint_and_partial_is_preserved(tmp_path):
    w, _, _ = worker(tmp_path, [ticks(), ticks()])
    with pytest.raises(RuntimeError, match="INJECTED_CRASH"):
        w.capture_once(fault_after_raw=True)
    assert not (w.control / "checkpoint.json").exists()
    partials = list(w.staging.iterdir())
    assert len(partials) == 1 and any(p.name.endswith(".npy") for p in partials[0].iterdir())
    assert w.recover_partial_staging()
    result = w.capture_once()
    assert result.rows == 3
    assert (w.batches / result.batch_id / "COMMIT.json").exists()
    assert (w.control / "checkpoint.json").exists()
    descriptor = read_json(w.batches / result.batch_id / "descriptor.json")
    assert descriptor["recovered_after_gap"] is True
    assert read_json(w.control / "recovery_pending.json")["status"] == "RESOLVED_BY_COMMITTED_RECAPTURE"


def test_retry_preserves_error_attempt_then_success(tmp_path):
    w, _, _ = worker(tmp_path, [RuntimeError("temporary"), ticks()])
    result = w.capture_once()
    descriptor = read_json(w.batches / result.batch_id / "descriptor.json")
    assert len(descriptor["attempts"]) == 2
    assert descriptor["attempts"][0]["error"]["message"] == "temporary"
    assert (w.batches / result.batch_id / "attempt-001-response.json").exists()


def test_duplicate_response_preserved_and_flagged_not_deduplicated(tmp_path):
    original = ticks()
    w, _, clock = worker(tmp_path, [original, original])
    first = w.capture_once(); clock.advance(30)
    second = w.capture_once()
    assert second.rows == first.rows == 3
    assert "DUPLICATE_RESPONSE" in incident_text(w)
    assert len(load_raw(w, second.batch_id)) == 3


def test_exhausted_retry_commits_error_without_cursor_advance_then_reconnects(tmp_path):
    w, source, _ = worker(tmp_path, [None, None, None, ticks()])
    result = w.capture_once()
    assert result.status == "ERROR_COMMITTED_RECONNECT_REQUIRED"
    checkpoint = read_json(w.control / "checkpoint.json")
    assert checkpoint["request_to_utc"] == checkpoint["t0_utc"]
    old = w.connection["session_id"]
    w._reconnect()
    assert w.connection["session_id"] != old
    assert ("reconnect",) in source.calls
    recovered = w.capture_once()
    descriptor = read_json(w.batches / recovered.batch_id / "descriptor.json")
    assert descriptor["recovered_after_gap"] is True
    assert "RECOVERED_AFTER_GAP" in incident_text(w)


def test_account_change_on_reconnect_creates_new_identity_incident(tmp_path):
    w, source, _ = worker(tmp_path, [ticks()])
    w.connect()
    previous_session = w.connection["session_id"]
    source.account_fingerprint = "b" * 64
    w._reconnect()
    assert w.connection["session_id"] != previous_session
    assert "SERVER_ACCOUNT_IDENTITY_CHANGE" in incident_text(w)


def test_disk_backpressure_denies_before_source_io(tmp_path):
    w, source, _ = worker(tmp_path, [ticks()], disk_free=1)
    with pytest.raises(CaptureDenied, match="DISK_THRESHOLD"):
        w.capture_once()
    assert source.calls == []
    assert "DISK_THRESHOLD" in incident_text(w)


def test_empty_response_is_durable_and_not_called_complete(tmp_path):
    w, _, _ = worker(tmp_path, [np.array([], dtype=DTYPE)])
    result = w.capture_once()
    assert result.rows == 0
    assert (w.batches / result.batch_id / "COMMIT.json").exists()
    assert "EMPTY_RESPONSE" in incident_text(w)


def test_clock_inconsistency_records_incident(tmp_path):
    clock = Clock()
    w, _, _ = worker(tmp_path, [ticks()], clock=clock)
    w._register_t0()
    clock.value -= timedelta(seconds=10)
    with pytest.raises(CaptureDenied, match="CLOCK_INCONSISTENCY"):
        w.capture_once()
    assert "CLOCK_INCONSISTENCY" in incident_text(w)


def test_symbol_spec_change_creates_new_interval_without_retroactive_fill(tmp_path):
    w, source, clock = worker(tmp_path, [ticks(), ticks()])
    w.capture_once(); first_state = read_json(w.control / "checkpoint.json")
    source.spec["trade_contract_size"] = 10.0
    source.spec["bid"] = 9999.0
    clock.advance(901)
    second = w.capture_once(); second_state = read_json(w.control / "checkpoint.json")
    assert first_state["symbol_specification_interval_id"] != second_state["symbol_specification_interval_id"]
    descriptor = read_json(w.batches / second.batch_id / "descriptor.json")
    assert descriptor["symbol_specification"]["retroactive_application"] is False
    assert "SYMBOL_SPECIFICATION_CHANGE" in incident_text(w)


def test_dynamic_quote_change_does_not_create_contract_interval(tmp_path):
    w, source, clock = worker(tmp_path, [ticks(), ticks()])
    w.capture_once(); first = read_json(w.control / "checkpoint.json")
    source.spec["bid"] = 2500.0; source.spec["ask"] = 2500.2; source.spec["time"] += 900
    clock.advance(901); w.capture_once(); second = read_json(w.control / "checkpoint.json")
    assert first["symbol_specification_interval_id"] == second["symbol_specification_interval_id"]


def test_utc_failure_and_uncertainty_are_preserved_as_incidents(tmp_path):
    w, _, _ = worker(tmp_path, [ticks()], reference=Reference(available=False))
    result = w.capture_once()
    assert result.rows == 3 and "UTC_REFERENCE_UNAVAILABLE" in incident_text(w)
    w2, _, _ = worker(tmp_path / "uncertain", [ticks()], reference=Reference(uncertainty=999, disagreement=500))
    w2.capture_once()
    assert "UTC_UNCERTAINTY_EXCEEDED" in incident_text(w2)
    assert "UTC_SOURCE_DISAGREEMENT" in incident_text(w2)


@pytest.mark.parametrize("requested_scope,reason", [
    (audit_request(track="A"), "TRACK_A_DENIED"),
    (audit_request(purpose="DISCOVERY"), "RESEARCH_DENIED"),
    (audit_request(partition="VALIDATION"), "PARTITION_DENIED"),
    (audit_request(partition="LOCKED_OOS"), "PARTITION_DENIED"),
])
def test_track_a_research_and_holdouts_denied_before_read(tmp_path, requested_scope, reason):
    w, _, _ = worker(tmp_path, [ticks()])
    assert w.authorize(requested_scope) == {"decision": "DENY", "reason": reason}
    with pytest.raises(CaptureDenied, match=reason):
        w.read_derived("TB1-not-read", requested_scope)


def test_revoked_scope_denies_capture_and_reads(tmp_path):
    w, source, _ = worker(tmp_path, [ticks()])
    result = w.capture_once()
    w.revoke("human stop")
    before = list(source.calls)
    with pytest.raises(CaptureDenied, match="SCOPE_REVOKED"):
        w.capture_once()
    with pytest.raises(CaptureDenied, match="SCOPE_REVOKED"):
        w.read_derived(result.batch_id, audit_request())
    assert source.calls == before


def test_data_engine_constructs_worker_without_io_or_t0(tmp_path):
    (tmp_path / "config").mkdir()
    (tmp_path / "config/partitions_gold_m1_v2.json").write_text(
        '{"frozen":true,"created_before_outcome_analysis":true,"DEV":{"from":"2015-01-01T00:00:00Z","to_exclusive":"2020-01-01T00:00:00Z"},"LOCKED_OOS":{"from":"2023-01-01T00:00:00Z","to_exclusive":"2025-01-01T00:00:00Z"}}',
        encoding="utf-8")
    source = Source([ticks()]); clock = Clock()
    engine = DataEngine(tmp_path)
    config_path = Path(__file__).parents[2] / "config/track_b_xm_forward_capture_v1.json"
    w = engine.track_b_forward_capture(config_path, source=source, utc_reference=Reference(),
        utc_now=clock.now, monotonic_ns=clock.monotonic_ns,
        disk_usage=lambda _: SimpleNamespace(free=20 * 1024**3))
    assert source.calls == []
    assert not (w.control / "t0.json").exists()


def test_adapter_exposes_no_trading_method_and_config_forbids_trading(tmp_path):
    w, _, _ = worker(tmp_path, [ticks()])
    assert not hasattr(MT5TickSource, "order_send")
    assert w.config["scope"]["orders_authorized"] is False
    assert w.config["scope"]["fills_authorized"] is False
    assert w.config["scope"]["slippage_observed"] is False
