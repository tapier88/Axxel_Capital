"""AXXEL's sole certified market-data boundary (local, CPU-only, fail-closed).

OS owners can edit files: certificates provide integrity, not an OS sandbox.
Uncertified legacy histories are never silently grandfathered into research.
"""
from __future__ import annotations

import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import re
import shutil
import sys
import tempfile
from copy import deepcopy

import duckdb
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from src.data.quality import normalize_and_validate
from src.utils.hashing import file_hash
from src.utils.serialization import read_json


def identity(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                    ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def _publish(path: Path, writer):
    """Atomic, exclusive, content-checked publication; never replace existing data."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(dir=path.parent, prefix=".staging-")
    os.close(fd)
    temporary = Path(name)
    try:
        writer(temporary)
        with temporary.open("rb+") as handle:
            os.fsync(handle.fileno())
        try:
            os.link(temporary, path)
        except FileExistsError:
            if file_hash(path) != file_hash(temporary):
                raise PermissionError(f"Immutable artifact conflict: {path.name}")
    finally:
        temporary.unlink(missing_ok=True)


def _json(path, value):
    payload = json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n"
    _publish(path, lambda target: target.write_text(payload, encoding="utf-8"))


def _parquet(path, frame):
    _publish(path, lambda target: frame.to_parquet(target, index=False, compression="zstd", row_group_size=100_000))


class DataEngine:
    def __init__(self, root: Path | str):
        self.root = Path(root).resolve()
        self.base = self.root / "data/engine"
        self.policy_path = self.root / "config/partitions_gold_m1_v2.json"
        self.policy = read_json(self.policy_path, {})
        if not self.policy.get("frozen") or not self.policy.get("created_before_outcome_analysis"):
            raise PermissionError("A pre-frozen chronological partition policy is mandatory")
        self._scope_shadow = None

    def track_b_forward_capture(self, config_path="config/track_b_xm_forward_capture_v1.json", **dependencies):
        """Construct the bounded Track B worker without broker I/O or T0."""
        from src.data.track_b_forward_capture import TrackBForwardCapture
        return TrackBForwardCapture(self.root, config_path, **dependencies)

    def track_b_forward_capture_v2(self, config_path="config/track_b_xm_forward_capture_v2.json", **dependencies):
        """Versioned custody implementation; real activation is denied before source I/O."""
        from src.data.track_b_forward_capture_v2 import TrackBForwardCaptureV2
        return TrackBForwardCaptureV2(self.root, config_path, **dependencies)

    def configure_scope_shadow(self, manifests, *, consumer, environment, clock=None):
        """Trusted host bootstrap with resident synthetic metadata, never a consumer API.

        One configuration per engine lifetime. V1 certificates are not migrated.
        Missing sealed-partition metadata disables Track B, rather than guessing.
        """
        from src.data.scope import ScopeShadow, deny
        if self._scope_shadow is not None:
            deny('SHADOW_ALREADY_CONFIGURED')
        try:
            self._scope_shadow = ScopeShadow(
                manifests, consumer=consumer, environment=environment,
                dev_period=self.policy['DEV'],
                forward_floor=self.policy.get('LOCKED_OOS', {}).get('to_exclusive'), clock=clock)
        except (TypeError, ValueError, KeyError, AttributeError):
            deny('MALFORMED_CONTROL_METADATA')

    def authorize_scope_shadow(self, request):
        """No artifact I/O; the result is diagnostic, never a reusable read token."""
        from src.data.scope import POLICY as SCOPE_POLICY
        if self._scope_shadow is None:
            return dict(decision='DENY', reason='SHADOW_NOT_CONFIGURED',
                        policy_version=SCOPE_POLICY, mode='SHADOW')
        return self._scope_shadow.authorize(deepcopy(request), physical=True)

    def read_scope_shadow(self, request):
        """Authorize the entire ancestry BEFORE path resolution, hashing or cache use."""
        from src.data.scope import ScopeDenied, deny
        context = self._scope_shadow
        if context is None:
            deny('SHADOW_NOT_CONFIGURED')
        request = deepcopy(request)
        with context.lock:
            decision = context.authorize(request, physical=True)
            if decision['decision'] != 'ALLOW':
                deny(decision['reason'])
            manifest = context._authorize(request, physical=True)
            artifact = manifest['artifact']
            key = (manifest['certificate_id'], artifact['sha256'], tuple(request['fields']))
            if key in context._cache:
                return context._cache[key].copy(deep=True)
            # Authorization above includes the full physical fragment's scope.
            path = self._path(artifact['path'])
            expected = self.root / artifact['path']  # lexical: do not resolve this too
            if path != expected:
                deny('ARTIFACT_REDIRECTION_DENIED')
            try:
                if file_hash(path) != artifact['sha256']:
                    deny('ARTIFACT_INTEGRITY_FAILURE')
                frame = pq.read_table(path, columns=request['fields']).to_pandas()
                if file_hash(path) != artifact['sha256']:
                    deny('ARTIFACT_CHANGED_DURING_READ')
            except ScopeDenied:
                raise
            except (OSError, pa.ArrowException) as exc:
                raise ScopeDenied('ARTIFACT_UNAVAILABLE_OR_INVALID') from exc
            context._cache[key] = frame.copy(deep=True)
            return frame

    def derive_scope_shadow(self, certificate_id, parents, operation, artifact):
        from src.data.scope import deny
        if self._scope_shadow is None:
            deny('SHADOW_NOT_CONFIGURED')
        try:
            return self._scope_shadow.derive(certificate_id, parents, operation, artifact)
        except (TypeError, ValueError, KeyError, AttributeError):
            deny('MALFORMED_DERIVATION')

    def revoke_scope_shadow(self, certificate_id):
        from src.data.scope import deny
        if self._scope_shadow is None:
            deny('SHADOW_NOT_CONFIGURED')
        self._scope_shadow.revoke(certificate_id)

    def _bounds(self, partition="DEV", phase="DISCOVERY"):
        # V1 deliberately does not expose a validation capability; prior authorization was consumed.
        if partition != "DEV" or phase != "DISCOVERY":
            raise PermissionError("Data Engine V1 only admits DEV; VALIDATION and LOCKED_OOS are sealed")
        entry = self.policy[partition]
        return pd.Timestamp(entry["from"]), pd.Timestamp(entry["to_exclusive"])

    def _path(self, relative):
        path = (self.root / relative).resolve()
        if not path.is_relative_to(self.base.resolve()):
            raise PermissionError("Artifact escaped the Data Engine directory")
        return path

    def _relative(self, path):
        return path.relative_to(self.root).as_posix()

    def ingest_parquet(self, source: Path | str, metadata: dict, *, partition="DEV",
                       legacy_dev_rowgroups=False):
        start, end = self._bounds(partition)
        metadata = dict(metadata)
        required = ("source_id", "broker", "symbol_exact", "symbol_international", "timeframe", "timezone", "point", "digits", "timestamp_semantics")
        if any(key not in metadata for key in required):
            raise ValueError(f"Required provenance: {required}")
        if metadata["timeframe"] not in ("M1", "M5") or metadata["point"] <= 0:
            raise ValueError("Only positive-point M1/M5 contracts are supported")
        if metadata["timestamp_semantics"] != "BAR_OPEN":
            raise ValueError("An explicit BAR_OPEN timestamp contract is required")
        source = Path(source).resolve()
        # Footer only. No whole-file checksum of a mixed/protected legacy source.
        parquet = pq.ParquetFile(source)
        column = parquet.schema_arrow.get_field_index("timestamp_utc")
        if column < 0:
            raise ValueError("Source needs explicit timestamp_utc with timezone")
        approved = []
        for index in range(parquet.num_row_groups):
            stats = parquet.metadata.row_group(index).column(column).statistics
            if stats is None or not stats.has_min_max:
                raise PermissionError("Cannot establish partition from footer; provide a bounded source extract")
            low, high = pd.Timestamp(stats.min), pd.Timestamp(stats.max)
            if low.tzinfo is None or high.tzinfo is None:
                raise PermissionError("Naive source timestamps require a separate explicit timezone normalization adapter")
            if low >= start and high + pd.Timedelta(minutes=int(metadata["timeframe"][1:])) < end:
                approved.append(index)
            elif not legacy_dev_rowgroups:
                raise PermissionError("Source intersects a protected partition; no filtered full scan is allowed")
        if not approved:
            raise PermissionError("No wholly DEV row group")
        if sum(parquet.metadata.row_group(i).num_rows for i in approved) > 2_000_000:
            raise ValueError("V1 bounded ingestion limit is 2,000,000 rows; supply smaller source chunks")
        if legacy_dev_rowgroups:
            metadata["legacy_transformed"] = True
            metadata["legacy_parent_path"] = str(source)
            metadata["legacy_selected_row_groups"] = approved
            metadata["legacy_excluded_row_groups"] = parquet.num_row_groups - len(approved)
            metadata["parent_file_hash_verified"] = False
            metadata["raw_semantics"] = "Immutable selected-rowgroup export; NOT original MT5 response"
            frame = parquet.read_row_groups(approved).to_pandas()
            # Preserve source values/order; this newly acquired extract is the RAW object.
            fd, temp = tempfile.mkstemp(suffix=".parquet")
            os.close(fd)
            snapshot = Path(temp)
            try:
                frame.to_parquet(snapshot, index=False, compression="zstd", row_group_size=100_000)
                result = self._freeze(snapshot, metadata, partition)
            finally:
                snapshot.unlink(missing_ok=True)
            return result
        return self._freeze(source, metadata, partition)

    def _freeze(self, source, metadata, partition):
        source_hash = file_hash(source)
        raw = self.base / "raw" / partition / f"{source_hash}.parquet"
        _publish(raw, lambda temporary: shutil.copyfile(source, temporary))
        if file_hash(raw) != source_hash:
            raise PermissionError("Source changed during RAW capture")
        dependencies = {name: importlib.metadata.version(name) for name in ("pandas", "numpy", "pyarrow", "pandera", "duckdb")}
        code = {name: file_hash(Path(__file__).parent / name) for name in ("engine.py", "quality.py", "pipeline_v2.py")}
        recipe = {"engine": "AXXEL-DATA-V1", "raw_sha256": source_hash, "metadata": metadata,
                  "partition": partition, "partition_policy": self.policy, "dependencies": dependencies,
                  "python_version": sys.version.split()[0],
                  "code_sha256": code, "quality_policy": "market-quality-v1-fixed-thresholds-no-imputation"}
        dataset_id = "DE1-" + identity(recipe)
        directory = self.base / "datasets" / dataset_id
        certificate = directory / "manifest.json"
        if certificate.exists():
            return self.manifest(dataset_id, research=False)
        frame = pq.read_table(raw).to_pandas()
        bronze, silver, flags, quality = normalize_and_validate(frame, metadata, int(metadata["timeframe"][1:]))
        start, end = self._bounds(partition)
        duration = pd.Timedelta(minutes=int(metadata["timeframe"][1:]))
        if not ((bronze.timestamp_utc >= start) & (bronze.timestamp_utc + duration < end)).all():
            raise PermissionError("Observed timestamps contradict DEV source declaration")
        artifacts = {"raw": raw}
        for name in code:
            snapshot = directory / "code" / name
            _publish(snapshot, lambda target, name=name: shutil.copyfile(Path(__file__).parent / name, target))
            if file_hash(snapshot) != code[name]:
                raise PermissionError("Transformation source changed during freeze")
            artifacts["code_" + name] = snapshot
        for name, table in (("bronze", bronze), ("silver", silver), ("findings", flags)):
            path = directory / f"{name}.parquet"
            _parquet(path, table)
            artifacts[name] = path
        report = directory / "quality.json"
        _json(report, quality)
        artifacts["quality"] = report
        # A canonical logical hash of an Arrow stream; version explicitly fixed in recipe.
        clean_table = pa.Table.from_pandas(silver, preserve_index=False).replace_schema_metadata(None)
        sink = pa.BufferOutputStream()
        with pa.ipc.new_stream(sink, clean_table.schema) as writer:
            writer.write_table(clean_table, max_chunksize=100_000)
        logical_hash = hashlib.sha256(sink.getvalue()).hexdigest()
        manifest = {"dataset_id": dataset_id, "recipe": recipe, "partition": partition,
                    "raw_schema": str(pq.read_schema(raw)), "raw_rows": len(frame),
                    "status": quality["status"], "quality": quality, "rows": len(silver),
                    "from": silver.timestamp_utc.min().isoformat(), "to": silver.timestamp_utc.max().isoformat(),
                    "schema": str(clean_table.schema), "logical_sha256": logical_hash,
                    "transformations": ["numeric float64 conversion", "explicit timezone to UTC",
                                        "source row identity", "exact duplicate removal in silver only", "stable temporal sort"],
                    "artifacts": {name: {"path": self._relative(path), "sha256": file_hash(path)} for name, path in artifacts.items()},
                    "lineage": {"parent_raw_sha256": source_hash, "legacy": bool(metadata.get("legacy_transformed"))},
                    "validation_opened": False, "locked_oos_opened": False}
        manifest["certificate_sha256"] = identity(manifest)
        _json(certificate, manifest)  # Last publication is the commit marker.
        return manifest

    def manifest(self, dataset_id, *, research=True, partition="DEV"):
        self._bounds(partition)
        if not re.fullmatch(r"DE1-[0-9a-f]{64}", str(dataset_id)):
            raise PermissionError("A registered Data Engine dataset ID is required")
        path = self._path(f"data/engine/datasets/{dataset_id}/manifest.json")
        result = read_json(path, {})
        if not result:
            raise PermissionError("No committed certificate")
        payload = {key: value for key, value in result.items() if key != "certificate_sha256"}
        if identity(payload) != result.get("certificate_sha256") or "DE1-" + identity(result["recipe"]) != dataset_id:
            raise PermissionError("Certificate identity mismatch")
        if (result.get("dataset_id") != dataset_id or result["partition"] != partition or
                result["recipe"]["partition_policy"] != self.policy):
            raise PermissionError("Partition or frozen policy mismatch")
        if research and result["status"] not in ("RESEARCH_GRADE", "USABLE_WITH_LIMITATIONS"):
            raise PermissionError(f"Dataset cannot enter research: {result['status']}")
        expected = {"raw": self.base / "raw" / "DEV" / f"{result['recipe']['raw_sha256']}.parquet",
                    **{name: path.parent / f"{name}.parquet" for name in ("bronze", "silver", "findings")},
                    **{"code_" + name: path.parent / "code" / name for name in ("engine.py", "quality.py", "pipeline_v2.py")},
                    "quality": path.parent / "quality.json"}
        if set(result["artifacts"]) != set(expected):
            raise PermissionError("Unexpected artifact set")
        # Check all locations before hashing any payload; even a rehashed manifest
        # may not redirect reads toward protected or unrelated files.
        for name, item in result["artifacts"].items():
            if self._path(item["path"]) != expected[name].resolve():
                raise PermissionError("Certificate redirected an artifact")
        for item in result["artifacts"].values():
            if file_hash(self._path(item["path"])) != item["sha256"]:
                raise PermissionError("RAW or derived artifact integrity violation")
        return result

    def query(self, dataset_id, *, columns=None, partition="DEV", limit=None):
        manifest = self.manifest(dataset_id, partition=partition)
        path = self._path(manifest["artifacts"]["silver"]["path"])
        schema = pq.read_schema(path).names
        columns = schema if columns is None else list(columns)
        if not columns or not set(columns) <= set(schema):
            raise ValueError("Unknown projection columns")
        if limit is not None and (not isinstance(limit, int) or limit < 0):
            raise ValueError("Invalid limit")
        projection = ",".join('"' + name.replace('"', '""') + '"' for name in columns)
        sql = f"SELECT {projection} FROM read_parquet(?)"
        if limit is not None:
            sql += f" LIMIT {limit}"
        with duckdb.connect(config={"threads": 2, "memory_limit": "1GB"}) as connection:
            return connection.execute(sql, [str(path)]).fetchdf()

    def require_experience(self, manifest, partition="DEV"):
        """Compatibility stores may only consume a gold artifact bound to its parent certificate."""
        self._bounds(partition)
        parent = self.manifest(manifest.get("data_engine_dataset_id"), partition=partition)
        registration = read_json(self._path(f"data/engine/datasets/{parent['dataset_id']}/gold.json"), {})
        if registration.get("experience_manifest") != manifest:
            raise PermissionError("Experience dataset lacks a matching Data Engine gold registration")
        item = registration["artifact"]
        expected = self.base / "datasets" / parent["dataset_id"] / "dev.parquet"
        if (self._path(item["path"]) != expected.resolve() or
                manifest.get("files") != {"DEV": self._relative(expected)} or
                manifest.get("file_hashes") != {"DEV": item["sha256"]}):
            raise PermissionError("Gold registration redirected its DEV artifact")
        if file_hash(self._path(item["path"])) != item["sha256"]:
            raise PermissionError("Gold checksum mismatch")
        return self._path(item["path"])

    def build_experiences(self, dataset_id):
        """Reuse the existing causal/counterfactual engine, only after certification.

        No ticks are silently taken from a different source/partition. V1's gold
        adapter supports M1 and marks all execution costs as proxies.
        """
        from src.data.pipeline_v2 import (build_feature_label_frame, _add_action_outcomes,
                                          _record_hashes, SCHEMA_VERSION)
        parent = self.manifest(dataset_id)
        if any(file_hash(Path(__file__).parent / name) != digest
               for name, digest in parent["recipe"]["code_sha256"].items()):
            raise PermissionError("Gold must use the parent's frozen transformation code; re-freeze under a new recipe")
        metadata = parent["recipe"]["metadata"]
        if metadata["timeframe"] != "M1":
            raise ValueError("M5 is certifiable as bars; the existing experience adapter is M1-only")
        registration_path = self.base / "datasets" / dataset_id / "gold.json"
        if registration_path.exists():
            existing = read_json(registration_path, {})["experience_manifest"]
            self.require_experience(existing)
            return existing
        bars = self.query(dataset_id)
        featured = build_feature_label_frame(bars, float(metadata["point"]))
        featured["partition"] = "DEV"
        featured["session_id"] = "SESSION-" + metadata["symbol_exact"] + "-" + featured.timestamp_cot.dt.strftime("%Y-%m-%d") + "-COT"
        ticks = pd.DataFrame({"timestamp_utc": pd.Series([], dtype="datetime64[ns, UTC]"),
                              "bid": pd.Series([], dtype=float), "ask": pd.Series([], dtype=float)})
        experiences = pd.concat([_add_action_outcomes(featured, action, ticks, metadata["point"])
                                 for action in ("WAIT", "LONG", "SHORT")], ignore_index=True)
        version = "DATASET-DE1-" + dataset_id[4:]
        experiences["dataset_version"] = version
        experiences["schema_version"] = SCHEMA_VERSION
        experiences["source_id"] = metadata["source_id"]
        keys = experiences[["dataset_version", "session_id", "decision_timestamp_utc", "action"]]
        fingerprint = pd.util.hash_pandas_object(keys, index=False, categorize=False)
        experiences.insert(0, "experience_id", [f"EXPERIENCE-DE1-{int(value):016x}" for value in fingerprint])
        if experiences.experience_id.duplicated().any():
            raise ValueError("Duplicate experience identity")
        experiences["record_hash"] = _record_hashes(experiences, version)
        directory = self.base / "datasets" / dataset_id
        target = directory / "dev.parquet"
        _parquet(target, experiences)
        manifest = {"dataset_version": version, "schema_version": SCHEMA_VERSION,
                    "data_engine_dataset_id": dataset_id, "partition_policy": self._relative(self.policy_path),
                    "symbol_international": metadata["symbol_international"], "symbol_exact": metadata["symbol_exact"],
                    "source_id": metadata["source_id"], "timeframe": "M1",
                    "files": {"DEV": self._relative(target)}, "file_hashes": {"DEV": file_hash(target)},
                    "experience_counts": {"DEV": len(experiences)}, "total_experiences": len(experiences),
                    "session_counts": {"DEV": int(experiences.session_id.nunique())},
                    "slippage": "UNAVAILABLE_NOT_ASSUMED_ZERO", "proxy_cost": "Declared point times bar spread",
                    "locked_oos_policy": "SEALED", "quality_status": parent["status"]}
        _json(directory / "experience_manifest.json", manifest)
        _json(registration_path, {"experience_manifest": manifest,
                                  "artifact": {"path": self._relative(target), "sha256": file_hash(target)}})
        # Reuse the Experience Store index; never overwrite historical entries.
        from src.utils.serialization import atomic_write_json
        index_path = self.root / "experience_store/v2/index.json"
        index = read_json(index_path, {"datasets": []})
        entry = {"dataset_version": version, "manifest": self._relative(directory / "experience_manifest.json")}
        if entry not in index["datasets"]:
            index["datasets"].append(entry)
            atomic_write_json(index_path, index)
        return manifest
