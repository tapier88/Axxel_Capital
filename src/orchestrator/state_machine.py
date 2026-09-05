"""Persistent state boundary for the autonomous research system."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.utils.serialization import atomic_write_json, read_json

STATE_DEFAULTS: dict[str, dict[str, Any]] = {
    "agent_state": {
        "status": "idle",
        "iteration": 0,
        "mode": "RESEARCH_ONLY",
        "live_trading": False,
        "automatic_promotion_to_live": False,
        "last_run_id": None,
        "updated_at": None,
    },
    "research_state": {
        "active_hypothesis": None,
        "hypothesis_count": 0,
        "uncertainties": [],
        "updated_at": None,
    },
    "experiment_state": {
        "running": None,
        "last_experiment": None,
        "experiment_count": 0,
        "updated_at": None,
    },
    "memory_state": {
        "last_consolidation": None,
        "counts": {"working": 0, "episodic": 0, "semantic": 0, "long_term": 0},
        "updated_at": None,
    },
    "value_model_state": {
        "version": "v0",
        "model_version_id": None,
        "trained": False,
        "last_scores": None,
        "updated_at": None,
    },
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _merge(default: dict[str, Any], saved: dict[str, Any]) -> dict[str, Any]:
    result = deepcopy(default)
    for key, value in saved.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _merge(result[key], value)
        else:
            result[key] = value
    return result


class StateStore:
    def __init__(self, root: Path | str):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def load(self, name: str) -> dict[str, Any]:
        if name not in STATE_DEFAULTS:
            raise KeyError(f"Unknown state: {name}")
        saved = read_json(self.root / f"{name}.json", {})
        if not isinstance(saved, dict):
            raise ValueError(f"State {name} must contain a JSON object")
        return _merge(STATE_DEFAULTS[name], saved)

    def save(self, name: str, state: dict[str, Any]) -> dict[str, Any]:
        if name not in STATE_DEFAULTS:
            raise KeyError(f"Unknown state: {name}")
        normalized = _merge(STATE_DEFAULTS[name], state)
        normalized["updated_at"] = utc_now()
        atomic_write_json(self.root / f"{name}.json", normalized)
        return normalized

    def load_all(self) -> dict[str, dict[str, Any]]:
        return {name: self.load(name) for name in STATE_DEFAULTS}

    def initialize(self) -> dict[str, dict[str, Any]]:
        states = self.load_all()
        return {name: self.save(name, value) for name, value in states.items()}
