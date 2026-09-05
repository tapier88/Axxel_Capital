"""Partition-aware retrieval and deterministic replay for Experience Store V2."""

from __future__ import annotations

from pathlib import Path
import re
from typing import Any, Iterable

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

from src.data.pipeline_v2 import STATE_NUMERIC, _record_hashes
from src.utils.hashing import file_hash
from src.utils.serialization import read_json


class ParquetExperienceStore:
    def __init__(self, project_root: Path | str, dataset_version: str | None = None):
        self.root = Path(project_root)
        index = read_json(self.root / "experience_store/v2/index.json", {"datasets": []})
        entries = index.get("datasets", [])
        if not entries:
            raise FileNotFoundError("Experience Store V2 index is empty")
        selected = next((x for x in entries if x["dataset_version"] == dataset_version), None) if dataset_version else entries[-1]
        if selected is None:
            raise KeyError(dataset_version)
        version = selected["dataset_version"]
        if re.fullmatch(r"DATASET-DE1-[0-9a-f]{64}", version):
            expected = self.root / "data/engine/datasets" / ("DE1-" + version.removeprefix("DATASET-DE1-")) / "experience_manifest.json"
        elif re.fullmatch(r"DATASET-V2-[0-9a-f]{24}", version):
            expected = self.root / "experience_store/v2" / version.lower() / "manifest.json"
        else:
            raise PermissionError("Unknown Experience Store version format")
        self.manifest_path = self.root / selected["manifest"]
        if self.manifest_path.resolve() != expected.resolve():
            raise PermissionError("Index cannot redirect a metadata read")
        self.manifest = read_json(self.manifest_path, {})
        self.dataset_version = self.manifest["dataset_version"]
        from src.data.engine import DataEngine
        self.data_engine = DataEngine(self.root)

    def _partitions(self, partitions: Iterable[str], allow_locked: bool) -> tuple[str, ...]:
        names = tuple(dict.fromkeys(str(x).upper() for x in partitions))
        unknown = set(names) - {"DEV", "VALIDATION", "LOCKED_OOS"}
        if unknown:
            raise ValueError(f"Unknown partitions: {sorted(unknown)}")
        if "LOCKED_OOS" in names:
            raise PermissionError("LOCKED_OOS is sealed; allow_locked cannot bypass the research hard lock")
        if set(names) - {"DEV"}:
            raise PermissionError("Only certified DEV is available through the research store")
        return names

    def verify_files(self, *, include_locked: bool = False) -> dict[str, bool]:
        if include_locked:
            raise PermissionError("LOCKED_OOS cannot be opened even for checksum verification")
        names = ("DEV",)
        self.data_engine.require_experience(self.manifest)
        return {
            name: file_hash(self.root / self.manifest["files"][name]) == self.manifest["file_hashes"][name]
            for name in names
        }

    def query(
        self, *, partitions: tuple[str, ...] = ("DEV",), action: str | None = None,
        session_id: str | None = None, regime: str | None = None,
        experience_ids: list[str] | None = None, columns: list[str] | None = None,
        limit: int | None = None, allow_locked: bool = False,
    ) -> pd.DataFrame:
        names = self._partitions(partitions, allow_locked)
        filters: list[tuple[str, str, Any]] = []
        if action is not None:
            filters.append(("action", "=", action))
        if session_id is not None:
            filters.append(("session_id", "=", session_id))
        if regime is not None:
            filters.append(("state_regime_v0", "=", regime))
        if experience_ids:
            filters.append(("experience_id", "in", experience_ids))
        frames = []
        for name in names:
            certified_path = self.data_engine.require_experience(self.manifest, name)
            table = pq.read_table(certified_path, columns=columns, filters=filters or None)
            frame = table.to_pandas()
            if limit is not None:
                remaining = max(0, limit - sum(len(x) for x in frames))
                frame = frame.head(remaining)
            frames.append(frame)
            if limit is not None and sum(len(x) for x in frames) >= limit:
                break
        return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=columns)

    def similar(self, state: dict[str, Any], *, limit: int = 10, partition: str = "DEV") -> list[dict[str, Any]]:
        columns = ["experience_id", "partition", "session_id", "decision_timestamp_utc", "action", *STATE_NUMERIC]
        candidates = self.query(partitions=(partition,), action="WAIT", columns=columns)
        if candidates.empty:
            return []
        usable = [field for field in STATE_NUMERIC if field in state and state[field] is not None]
        if not usable:
            raise ValueError("At least one numeric state field is required")
        matrix = candidates[usable].astype(float)
        scale = (matrix.max()-matrix.min()).replace(0, 1.0)
        target = pd.Series({field: float(state[field]) for field in usable})
        distances = ((matrix-target).abs()/scale).mean(axis=1, skipna=True).replace(np.nan, np.inf)
        selected = candidates.loc[distances.nsmallest(limit).index].copy()
        selected["similarity_distance"] = distances.loc[selected.index]
        return selected.sort_values("similarity_distance").to_dict("records")

    def replay(self, experience_id: str, *, allow_locked: bool = False) -> dict[str, Any]:
        if allow_locked:
            raise PermissionError("Replay cannot bypass the LOCKED_OOS hard lock")
        partitions = ("DEV",)
        frame = self.query(partitions=partitions, experience_ids=[experience_id], allow_locked=allow_locked)
        if len(frame) != 1:
            raise KeyError(experience_id)
        stored = str(frame.iloc[0]["record_hash"])
        payload = frame.drop(columns=["record_hash"])
        recomputed = str(_record_hashes(payload, self.dataset_version).iloc[0])
        return {"experience": frame.iloc[0].to_dict(), "hash_valid": stored == recomputed}
