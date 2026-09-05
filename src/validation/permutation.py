"""Permutation tests that preserve session-level dependence."""
from __future__ import annotations
import numpy as np

def session_permutation_test(conditioned: np.ndarray, baseline: np.ndarray | None = None, *, paired: bool = True,
                             permutations: int = 4000, seed: int = 31415, direction: str = "GREATER") -> dict:
    rng = np.random.default_rng(seed)
    conditioned = np.asarray(conditioned, dtype=float); conditioned = conditioned[np.isfinite(conditioned)]
    if paired:
        observed = conditioned.mean()
        null = (conditioned * rng.choice((-1.0, 1.0), size=(permutations, len(conditioned)))).mean(axis=1)
        method = "PAIRED_SESSION_SIGN_FLIP"
    else:
        baseline = np.asarray(baseline, dtype=float); baseline = baseline[np.isfinite(baseline)]
        observed = conditioned.mean()-baseline.mean(); pooled = np.concatenate([conditioned, baseline]); size = len(conditioned)
        null = np.empty(permutations)
        for index in range(permutations):
            shuffled = rng.permutation(pooled); null[index] = shuffled[:size].mean()-shuffled[size:].mean()
        method = "SESSION_LABEL_PERMUTATION"
    extreme = null >= observed if direction == "GREATER" else null <= observed if direction == "LESS" else np.abs(null) >= abs(observed)
    return {"method": method, "seed": seed, "permutations": permutations, "observed": float(observed),
            "null_median": float(np.median(null)), "p_value": float((extreme.sum()+1)/(permutations+1))}
