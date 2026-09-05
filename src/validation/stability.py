"""Transparent summaries for temporal and parameter stability."""
from __future__ import annotations
from typing import Mapping

def stability_summary(effects: Mapping[str, float], direction: str) -> dict:
    finite = {str(k): float(v) for k, v in effects.items()}
    favorable = {k: (v > 0 if direction == "GREATER" else v < 0) for k, v in finite.items()}
    return {"effects": finite, "favorable": favorable,
            "favorable_proportion": sum(favorable.values())/len(favorable) if favorable else 0.0,
            "periods": len(finite)}
