"""DEV-only diagnosis of slow-structure confounding in volatility persistence."""
from __future__ import annotations
from pathlib import Path
import numpy as np
import pandas as pd
from src.experience_store.parquet_store import ParquetExperienceStore
from src.utils.serialization import atomic_write_json
from src.validation.bootstrap import stationary_bootstrap
from src.validation.oos import PartitionGuard

def _paired_effect(frame: pd.DataFrame, mask: pd.Series, target: str) -> tuple[float, np.ndarray]:
    work = frame.loc[frame[target].notna(), ["session_id", target]].copy(); work["c"] = mask.loc[work.index]
    grouped = work.groupby(["session_id", "c"])[target].mean().unstack().dropna()
    effects = (grouped[True]-grouped[False]).to_numpy(dtype=float)
    return float(effects.mean()), effects

def diagnose_volatility_persistence(project_root: Path | str, *, seed: int = 20260903) -> dict:
    root = Path(project_root); PartitionGuard(root, "DISCOVERY").require("DEV", "VolatilityDiagnostic")
    columns = ["session_id","decision_timestamp_utc","state_minute_of_session","state_regime_v0",
               "state_volatility_15m_causal","state_volatility_60m_causal",
               "label_realized_volatility_15m","label_realized_volatility_30m","label_realized_volatility_60m"]
    frame = ParquetExperienceStore(root).query(partitions=("DEV",), action="WAIT", columns=columns)
    mask = frame["state_volatility_15m_causal"].ge(frame["state_volatility_15m_causal"].quantile(.75))
    original, effects = _paired_effect(frame, mask, "label_realized_volatility_30m")
    shifts = {}
    for lag in (1, 5, 10, 20, 60):
        shifted = frame.copy(); shifted["shifted"] = shifted.groupby("state_minute_of_session")["label_realized_volatility_30m"].shift(lag)
        shifts[str(lag)] = _paired_effect(shifted, mask, "shifted")[0]
    purged = []
    for offset in (0, 10, 20):
        sparse = frame[frame["state_minute_of_session"].mod(30).eq(offset)]
        try: purged.append(_paired_effect(sparse, mask.loc[sparse.index], "label_realized_volatility_30m")[0])
        except (ValueError, KeyError): pass
    detrended = {}
    for name, groups in {"year":[frame["decision_timestamp_utc"].dt.year],
                         "month":[frame["decision_timestamp_utc"].dt.year, frame["decision_timestamp_utc"].dt.month],
                         "regime":[frame["state_regime_v0"]]}.items():
        adjusted = frame.copy(); adjusted["residual"] = adjusted["label_realized_volatility_30m"]-adjusted.groupby(groups)["label_realized_volatility_30m"].transform("mean")
        detrended[name] = _paired_effect(adjusted, mask, "residual")[0]
    valid = frame[["state_volatility_15m_causal","state_volatility_60m_causal","label_realized_volatility_30m"]].dropna()
    x = np.c_[np.ones(len(valid)), valid["state_volatility_60m_causal"].to_numpy()]
    beta_feature = np.linalg.lstsq(x, valid["state_volatility_15m_causal"].to_numpy(), rcond=None)[0]
    beta_target = np.linalg.lstsq(x, valid["label_realized_volatility_30m"].to_numpy(), rcond=None)[0]
    controlled = frame.loc[valid.index].copy(); controlled["feature_residual"] = valid["state_volatility_15m_causal"]-x@beta_feature
    controlled["target_residual"] = valid["label_realized_volatility_30m"]-x@beta_target
    controlled_mask = controlled["feature_residual"].ge(controlled["feature_residual"].quantile(.75))
    slow_control = _paired_effect(controlled, controlled_mask, "target_residual")[0]
    horizons = {str(h): _paired_effect(frame, mask, f"label_realized_volatility_{h}m")[0] for h in (15,30,60)}
    stationary = stationary_bootstrap(effects, mean_block_size=20, resamples=1000, seed=seed)
    max_shift_ratio = max(abs(v) for v in shifts.values())/abs(original)
    conclusion = "CONFIRMED_REJECTION" if max_shift_ratio > .5 else "NEW_CAUSAL_HYPOTHESIS"
    result = {"diagnostic_id":"VOLATILITY-SLOW-STRUCTURE-DIAGNOSTIC-V1", "partition":"DEV",
              "validation_inspected":False,"locked_oos_inspected":False,"original_effect":original,
              "temporal_shifts_sessions":shifts,"maximum_shift_to_original_ratio":max_shift_ratio,
              "purging_embargo_nonoverlap_offsets":purged,"detrended_effects":detrended,
              "prior_slow_volatility_controlled_effect":slow_control,"horizon_effects":horizons,
              "stationary_bootstrap":stationary,"conclusion":conclusion,
              "interpretation":"Statistical volatility structure only; not a directional signal or tradable edge"}
    atomic_write_json(root/"reports/evidence/volatility_slow_structure_diagnostic_v1.json", result)
    return result
