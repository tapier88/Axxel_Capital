"""Dependence-aware bootstrap over sessions or chronological session blocks."""
from __future__ import annotations
import numpy as np

def _summary(distribution: np.ndarray, observed: float, direction: str) -> dict:
    favorable = distribution > 0 if direction == "GREATER" else distribution < 0 if direction == "LESS" else np.abs(distribution) > 0
    return {"observed": float(observed), "distribution_mean": float(np.mean(distribution)),
            "median": float(np.median(distribution)),
            "confidence_interval_90": [float(x) for x in np.quantile(distribution, [0.05, 0.95])],
            "confidence_interval_95": [float(x) for x in np.quantile(distribution, [0.025, 0.975])],
            "sign_stability": float(np.mean(np.sign(distribution) == np.sign(observed))),
            "favorable_resample_proportion": float(np.mean(favorable)), "resamples": int(len(distribution))}

def session_bootstrap(conditioned: np.ndarray, baseline: np.ndarray | None = None, *, paired: bool = True,
                      resamples: int = 2000, seed: int = 1729, direction: str = "GREATER") -> dict:
    rng = np.random.default_rng(seed)
    conditioned = np.asarray(conditioned, dtype=float); conditioned = conditioned[np.isfinite(conditioned)]
    if paired:
        if not len(conditioned): raise ValueError("No finite session effects")
        sampled = conditioned[rng.integers(0, len(conditioned), size=(resamples, len(conditioned)))].mean(axis=1)
        observed = conditioned.mean()
    else:
        baseline = np.asarray(baseline, dtype=float); baseline = baseline[np.isfinite(baseline)]
        if not len(conditioned) or not len(baseline): raise ValueError("Both session groups are required")
        left = conditioned[rng.integers(0, len(conditioned), size=(resamples, len(conditioned)))].mean(axis=1)
        right = baseline[rng.integers(0, len(baseline), size=(resamples, len(baseline)))].mean(axis=1)
        sampled, observed = left-right, conditioned.mean()-baseline.mean()
    return {"method": "SESSION_LEVEL_BOOTSTRAP", "seed": seed, **_summary(sampled, observed, direction)}

def block_bootstrap(ordered_effects: np.ndarray, *, block_size: int = 20, resamples: int = 2000,
                    seed: int = 2718, direction: str = "GREATER") -> dict:
    values = np.asarray(ordered_effects, dtype=float); values = values[np.isfinite(values)]
    if len(values) < block_size: raise ValueError("Not enough sessions for requested block size")
    rng = np.random.default_rng(seed); starts = np.arange(0, len(values)-block_size+1)
    blocks_needed = int(np.ceil(len(values)/block_size)); distribution = np.empty(resamples)
    for index in range(resamples):
        chosen = rng.choice(starts, size=blocks_needed, replace=True)
        distribution[index] = np.concatenate([values[s:s+block_size] for s in chosen])[:len(values)].mean()
    return {"method": "MOVING_SESSION_BLOCK_BOOTSTRAP", "block_size": block_size, "seed": seed,
            **_summary(distribution, values.mean(), direction)}

def stationary_bootstrap(ordered_effects: np.ndarray, *, mean_block_size: int = 20, resamples: int = 2000,
                         seed: int = 1618, direction: str = "GREATER") -> dict:
    values = np.asarray(ordered_effects, dtype=float); values = values[np.isfinite(values)]
    if len(values) < mean_block_size: raise ValueError("Not enough sessions")
    rng = np.random.default_rng(seed); distribution = np.empty(resamples); restart = 1/mean_block_size
    for sample_index in range(resamples):
        indices = np.empty(len(values), dtype=int); indices[0] = rng.integers(len(values))
        for i in range(1, len(values)):
            indices[i] = rng.integers(len(values)) if rng.random() < restart else (indices[i-1]+1) % len(values)
        distribution[sample_index] = values[indices].mean()
    return {"method": "STATIONARY_SESSION_BOOTSTRAP", "mean_block_size": mean_block_size, "seed": seed,
            **_summary(distribution, values.mean(), direction)}
