"""Reproducible raw-bars to counterfactual experience pipeline."""

from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.data.cleaner import validate_bars
from src.data.cost_model import evaluate_cost
from src.data.feature_builder import assert_no_temporal_leakage, build_future_outcome, build_state
from src.data.normalizer import normalize_bars
from src.data.session_builder import build_sessions
from src.experience_store.market_store import MarketExperienceStore
from src.utils.hashing import content_hash, file_hash
from src.utils.ids import stable_id
from src.utils.serialization import atomic_write_json, read_json

SCHEMA_VERSION = "market-experience-v1"
ACTIONS = ("WAIT", "LONG", "SHORT")


def _partitions(session_ids: list[str]) -> dict[str, list[str]]:
    count = len(session_ids)
    if count < 3:
        raise ValueError("At least three sessions are required for DEV/VALIDATION/LOCKED_OOS")
    dev_end = max(1, int(count * 0.60))
    validation_end = max(dev_end + 1, int(count * 0.80))
    validation_end = min(validation_end, count - 1)
    return {"DEV": session_ids[:dev_end], "VALIDATION": session_ids[dev_end:validation_end],
            "LOCKED_OOS": session_ids[validation_end:]}


def _partition_for(session_id: str, partitions: dict[str, list[str]]) -> str:
    return next(name for name, values in partitions.items() if session_id in values)


def build_experience_dataset(project_root: Path | str, raw_path: Path | str) -> dict[str, Any]:
    raise PermissionError("Uncertified JSON builder retired. Import a bounded source through Data Engine.")
