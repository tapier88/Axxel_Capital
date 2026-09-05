"""Multiple-testing corrections with stable input/output ordering."""
from __future__ import annotations
import numpy as np

def benjamini_hochberg(p_values: list[float]) -> list[float]:
    if any(not 0 <= float(p) <= 1 for p in p_values): raise ValueError("p-values must be in [0,1]")
    if not p_values: return []
    values = np.asarray(p_values, dtype=float); order = np.argsort(values); ranked = values[order]
    adjusted = ranked * len(values) / np.arange(1, len(values)+1)
    adjusted = np.minimum.accumulate(adjusted[::-1])[::-1].clip(0, 1)
    result = np.empty_like(adjusted); result[order] = adjusted
    return [float(x) for x in result]

def holm_bonferroni(p_values: list[float]) -> list[float]:
    """Return Holm step-down family-wise adjusted p-values."""
    if any(not 0 <= float(p) <= 1 for p in p_values): raise ValueError("p-values must be in [0,1]")
    if not p_values: return []
    values = np.asarray(p_values, dtype=float); order = np.argsort(values); ranked = values[order]
    adjusted = np.maximum.accumulate(ranked * (len(values)-np.arange(len(values)))).clip(0, 1)
    result = np.empty_like(adjusted); result[order] = adjusted
    return [float(x) for x in result]
