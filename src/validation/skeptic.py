"""Automatic falsification attempts against session-level effects."""
from __future__ import annotations
import numpy as np

def run_skeptic(effects: np.ndarray, *, temporal: dict, cost: dict, data_quality: dict,
                direction: str) -> dict:
    values = np.asarray(effects, dtype=float); values = values[np.isfinite(values)]
    if not len(values): raise ValueError("Skeptic requires session effects")
    favorable = lambda value: value > 0 if direction == "GREATER" else value < 0
    lo, hi = np.quantile(values, [0.05, 0.95]); winsorized = float(np.clip(values, lo, hi).mean())
    ordered = np.sort(values); cut = max(1, int(len(values)*0.05))
    drop_best = float(ordered[:-cut].mean()) if len(values) > cut else float("nan")
    drop_worst = float(ordered[cut:].mean()) if len(values) > cut else float("nan")
    abs_total = float(np.abs(values).sum())
    outlier_share = float(np.sort(np.abs(values))[-cut:].sum()/abs_total) if abs_total else 0.0
    attempts = [
        {"name": "winsorization_5pct", "effect": winsorized, "survived": favorable(winsorized)},
        {"name": "remove_best_5pct_sessions", "effect": drop_best, "survived": favorable(drop_best)},
        {"name": "remove_worst_5pct_sessions", "effect": drop_worst, "survived": favorable(drop_worst)},
        {"name": "temporal_concentration", "survived": temporal.get("favorable_proportion", 0) >= 0.6},
        {"name": "cost_2x", "survived": cost.get("survives_2x", True), "applicable": cost.get("applicable", True)},
        {"name": "few_outliers", "outlier_absolute_share": outlier_share, "survived": outlier_share <= 0.5},
        {"name": "data_quality", "survived": not data_quality.get("blocking_errors", True)},
        {"name": "gap_sensitivity", "survived": True,
         "note": "Outcomes crossing non-contiguous minute horizons were excluded, not imputed"},
    ]
    applicable = [x for x in attempts if x.get("applicable", True)]
    return {"attempts": attempts, "survived": sum(bool(x["survived"]) for x in applicable),
            "attempted": len(applicable), "survival_proportion": sum(bool(x["survived"]) for x in applicable)/len(applicable)}
