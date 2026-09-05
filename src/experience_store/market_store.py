"""Queryable store for non-executed market counterfactual experiences."""

from __future__ import annotations
import math
from pathlib import Path
from typing import Any
from src.utils.hashing import content_hash
from src.utils.serialization import atomic_write_json, read_json

SIMILARITY_FIELDS = (
    "return_1h", "return_3h", "return_6h", "bar_range", "atr_14_causal",
    "realized_volatility_6h_causal", "distance_to_recent_high",
    "distance_to_recent_low", "momentum_3h_causal", "minute_of_session",
)


class MarketExperienceStore:
    def __init__(self, root: Path | str):
        self.root = Path(root) / "market"
        self.index_path = self.root / "index.json"

    def publish(self, symbol: str, dataset_id: str, experiences: list[dict[str, Any]], metadata: dict[str, Any]) -> Path:
        path = self.root / symbol.lower() / f"{dataset_id.lower()}.json"
        atomic_write_json(path, experiences)
        index = read_json(self.index_path, {"datasets": []})
        entry = {**metadata, "symbol": symbol, "dataset_id": dataset_id,
                 "path": str(path.relative_to(self.root.parent)).replace("\\", "/"), "records": len(experiences)}
        existing = next((position for position, item in enumerate(index["datasets"])
                         if item["dataset_id"] == dataset_id), None)
        if existing is None:
            index["datasets"].append(entry)
        else:
            index["datasets"][existing] = entry
        atomic_write_json(self.index_path, index)
        return path

    def _datasets(self, symbol: str | None = None) -> list[dict[str, Any]]:
        entries = read_json(self.index_path, {"datasets": []})["datasets"]
        return [item for item in entries if symbol is None or item["symbol"] == symbol]

    def all(self, symbol: str | None = None, *, allow_locked: bool = False) -> list[dict[str, Any]]:
        raise PermissionError("Mixed-partition JSON reader retired. Use certified Data Engine experiences.")

    def query(self, *, symbol: str | None = None, session_id: str | None = None,
              date_cot: str | None = None, timestamp_utc: str | None = None, regime: str | None = None,
              action: str | None = None, outcome_status: str | None = None,
              hypothesis_id: str | None = None, experiment_id: str | None = None,
              allow_locked: bool = False) -> list[dict[str, Any]]:
        result = self.all(symbol, allow_locked=allow_locked)
        filters = {
            "session_id": session_id, "timestamp_utc": timestamp_utc, "action": action,
            "outcome_status": outcome_status, "hypothesis_id": hypothesis_id, "experiment_id": experiment_id,
        }
        for key, value in filters.items():
            if value is not None:
                result = [item for item in result if item.get(key) == value]
        if date_cot is not None:
            result = [item for item in result if f"-{date_cot}-COT" in item["session_id"]]
        if regime is not None:
            result = [item for item in result if item["state"].get("regime_v0") == regime]
        return result

    def similar(
        self, state: dict[str, Any], *, symbol: str, limit: int = 10,
        partitions: tuple[str, ...] = ("DEV",),
    ) -> list[dict[str, Any]]:
        candidates = [item for item in self.all(symbol) if item["partition"] in partitions]
        scales: dict[str, float] = {}
        for field in SIMILARITY_FIELDS:
            values = [float(item["state"][field]) for item in candidates if item["state"].get(field) is not None]
            scales[field] = max(values)-min(values) if values and max(values) != min(values) else 1.0
        scored = []
        for item in candidates:
            distances = []
            for field in SIMILARITY_FIELDS:
                left, right = state.get(field), item["state"].get(field)
                if left is not None and right is not None:
                    distances.append(abs(float(left)-float(right))/scales[field])
            distance = sum(distances)/len(distances) if distances else math.inf
            scored.append({**item, "similarity_distance": round(distance, 8)})
        return sorted(scored, key=lambda item: item["similarity_distance"])[:limit]

    def replay(self, experience_id: str) -> dict[str, Any]:
        matches = [item for item in self.all(allow_locked=True) if item["experience_id"] == experience_id]
        if len(matches) != 1:
            raise KeyError(experience_id)
        record = matches[0]
        payload = {key: value for key, value in record.items() if key != "hash"}
        return {"experience": record, "hash_valid": content_hash(payload) == record["hash"]}
