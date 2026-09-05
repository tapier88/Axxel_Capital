"""Fail-closed DEV data access, causal features, and monetizable labels."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from src.data.pipeline_v2 import STATE_NUMERIC
from src.experience_store.parquet_store import ParquetExperienceStore
from src.utils.hashing import content_hash, file_hash
from src.utils.serialization import read_json
from src.validation.oos import PartitionGuard
from src.validation.leakage import assert_causal_sources

CLASSES = ("DOWN", "NO_TRADE", "UP")
CLASS_TO_INT = {name: index for index, name in enumerate(CLASSES)}
FEATURES = tuple(x for x in STATE_NUMERIC if x != "state_minute_of_session") + (
    "state_regime_v0_RANGE", "state_regime_v0_TREND_DOWN", "state_regime_v0_TREND_UP",
)


@dataclass(frozen=True)
class MLDataset:
    frame: pd.DataFrame
    features: pd.DataFrame
    target: np.ndarray
    regression_targets: dict[str, np.ndarray]
    barrier_targets: dict[str, np.ndarray]
    manifest: dict[str, Any]


class DevOnlyMLData:
    """A deliberately narrow gateway: callers cannot name another partition."""

    def __init__(self, project_root: Path | str, dataset_version: str | None = None):
        self.root = Path(project_root)
        self.store = ParquetExperienceStore(self.root, dataset_version)
        self.guard = PartitionGuard(self.root, phase="DISCOVERY")

    def load_0830(self, *, horizon: int, atr_multiple: float, expected_symbol: str = "XAUUSD") -> MLDataset:
        self.store.data_engine.require_experience(self.store.manifest)
        if horizon not in (5, 15, 30, 60):
            raise ValueError("Unsupported horizon")
        if self.store.manifest.get("symbol_international") != expected_symbol:
            raise ValueError("Configured symbol does not match the selected dataset manifest")
        self.guard.require("DEV", "ML_DATA_GATEWAY")
        dev_path = self.root / self.store.manifest["files"]["DEV"]
        resolved = dev_path.resolve()
        if resolved.name != "dev.parquet" or resolved.parent != self.store.manifest_path.resolve().parent:
            raise PermissionError("DEV manifest path cannot redirect ML to another partition")
        if file_hash(dev_path) != self.store.manifest["file_hashes"]["DEV"]:
            raise PermissionError("DEV file checksum differs from its immutable manifest")
        columns = [
            "partition", "action", "session_id", "decision_timestamp_utc",
            "state_max_source_timestamp_utc", "state_minute_of_session", "close",
            "state_regime_v0", *[x for x in STATE_NUMERIC if x != "state_minute_of_session"],
            f"label_future_return_{horizon}m", f"label_up_excursion_{horizon}m",
            f"label_down_excursion_{horizon}m", f"outcome_gross_return_{horizon}m",
            f"outcome_tradable_return_{horizon}m", f"outcome_mfe_{horizon}m",
            f"outcome_mae_{horizon}m", f"cost_spread_return_{horizon}m",
            f"cost_method_{horizon}m", "cost_slippage_status",
        ]
        raw = self.store.query(partitions=("DEV",), columns=list(dict.fromkeys(columns)))
        raw = raw.loc[raw["state_minute_of_session"] == 30].copy()
        if raw.empty or set(raw["partition"].unique()) != {"DEV"}:
            raise PermissionError("ML dataset is not exclusively DEV")
        policy = read_json(self.root / self.store.manifest["partition_policy"], {})["DEV"]
        decisions = pd.to_datetime(raw["decision_timestamp_utc"], utc=True)
        if not ((decisions >= pd.Timestamp(policy["from"])) &
                (decisions + pd.Timedelta(minutes=horizon) < pd.Timestamp(policy["to_exclusive"]))).all():
            raise PermissionError("ML decision or label interval crosses the DEV calendar boundary")
        assert_causal_sources(raw)

        states = raw.loc[raw["action"] == "WAIT"].copy()
        if states["session_id"].duplicated().any():
            raise AssertionError("Expected one 08:30 state per session")
        states = states.set_index("session_id")
        actions: dict[str, pd.DataFrame] = {}
        outcome_columns = [
            f"outcome_gross_return_{horizon}m", f"outcome_tradable_return_{horizon}m",
            f"outcome_mfe_{horizon}m", f"outcome_mae_{horizon}m",
            f"cost_spread_return_{horizon}m", f"cost_method_{horizon}m",
        ]
        for action in ("LONG", "SHORT"):
            part = raw.loc[raw["action"] == action, ["session_id", *outcome_columns]].set_index("session_id")
            if part.index.duplicated().any():
                raise AssertionError("Duplicate action would inflate the scientific sample")
            actions[action] = part.rename(columns={x: f"{action.lower()}_{x}" for x in outcome_columns})
            states = states.join(actions[action], how="inner")

        barrier = atr_multiple * states["state_atr_14_causal"] / states["close"]
        long_net = states[f"long_outcome_tradable_return_{horizon}m"]
        short_net = states[f"short_outcome_tradable_return_{horizon}m"]
        target_name = np.where(long_net > barrier, "UP", np.where(short_net > barrier, "DOWN", "NO_TRADE"))
        states["ml_target"] = target_name
        states["ml_atr_barrier_return"] = barrier

        numeric = states[[x for x in STATE_NUMERIC if x != "state_minute_of_session"]].astype(float)
        regime = pd.get_dummies(states["state_regime_v0"], prefix="state_regime_v0", dtype=float)
        features = numeric.join(regime).reindex(columns=FEATURES, fill_value=0.0)
        required_state = ["ml_target", f"label_future_return_{horizon}m", "close", "state_atr_14_causal"]
        required_state += [f"{side}_{column}" for side in ("long", "short")
                           for column in outcome_columns if not column.startswith("cost_method")]
        valid = states[required_state].notna().all(axis=1) & np.isfinite(features.to_numpy()).all(axis=1)
        states = states.loc[valid].sort_values("decision_timestamp_utc")
        features = features.loc[states.index]
        target = states["ml_target"].map(CLASS_TO_INT).to_numpy(dtype=int)
        regression_targets = {
            f"{direction.lower()}_{measure.lower()}": states[f"{direction.lower()}_outcome_{measure.lower()}_{horizon}m"].to_numpy(float)
            for direction in ("LONG", "SHORT") for measure in ("MFE", "MAE")
        }
        barrier_targets = {
            f"{side}_atr_reached": (
                states[f"{side}_outcome_mfe_{horizon}m"] >
                states["ml_atr_barrier_return"] + states[f"{side}_cost_spread_return_{horizon}m"]
            ).to_numpy(dtype=int) for side in ("long", "short")
        }
        dev_path = self.root / self.store.manifest["files"]["DEV"]
        manifest = {
            "dataset_version": self.store.dataset_version, "partition": "DEV",
            "dev_file_hash": file_hash(dev_path), "rows": len(states), "sessions": states.index.nunique(),
            "candidate_sessions": int(raw["session_id"].nunique()),
            "excluded_incomplete_sessions": int(raw["session_id"].nunique() - len(states)),
            "horizon_minutes": horizon, "atr_multiple": atr_multiple, "classes": list(CLASSES),
            "class_counts": states["ml_target"].value_counts().sort_index().to_dict(),
            "features": list(FEATURES), "feature_contract_hash": content_hash(list(FEATURES)),
            "validation_inspected": False, "locked_oos_inspected": False,
            "cost_methods": sorted(set(states[f"long_cost_method_{horizon}m"])),
            "slippage_status": sorted(set(states["cost_slippage_status"])),
        }
        manifest["auxiliary_barriers"] = "Marginal excursion above 0.25 causal ATR plus proxy spread; not first touch or executable bracket PnL"
        return MLDataset(states, features, target, regression_targets, barrier_targets, manifest)


def assert_feature_contract(columns: list[str] | tuple[str, ...]) -> None:
    forbidden = [x for x in columns if x.startswith(("label_", "outcome_", "cost_"))]
    if forbidden:
        raise AssertionError(f"Future/cost columns in feature matrix: {forbidden}")
    if tuple(columns) != FEATURES:
        raise AssertionError("Feature order differs from frozen ML contract")
