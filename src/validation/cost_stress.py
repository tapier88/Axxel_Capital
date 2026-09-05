"""Transaction-cost stress without inventing unavailable slippage."""
from __future__ import annotations
import pandas as pd

def stressed_return(frame: pd.DataFrame, horizon: int, multiplier: float) -> pd.Series:
    gross = frame[f"outcome_gross_return_{horizon}m"]
    observed_net = frame[f"outcome_tradable_return_{horizon}m"]
    return gross-multiplier*(gross-observed_net)

def cost_stability(results: dict[float, float], direction: str) -> dict:
    favorable = {str(k): (v > 0 if direction == "GREATER" else v < 0) for k, v in results.items()}
    return {"multipliers": {str(k): float(v) for k, v in results.items()}, "favorable": favorable,
            "favorable_proportion": sum(favorable.values())/len(favorable), "survives_2x": favorable.get("2.0", False)}
