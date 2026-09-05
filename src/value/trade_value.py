"""Interpretable economic value estimates for ENTER versus WAIT."""
from __future__ import annotations

from math import sqrt
from statistics import NormalDist
from typing import Iterable

import numpy as np


def trade_value_v1(gross_returns: Iterable[float], costs: Iterable[float], *,
                   action: str, minimum_support: int = 100) -> dict:
    gross = np.asarray(list(gross_returns), dtype=float)
    cost = np.asarray(list(costs), dtype=float)
    valid = np.isfinite(gross) & np.isfinite(cost)
    gross, cost = gross[valid], cost[valid]
    net = gross - cost
    support = int(len(net))
    mean = float(net.mean()) if support else float("nan")
    se = float(net.std(ddof=1) / sqrt(support)) if support > 1 else float("inf")
    ci = [mean - 1.96 * se, mean + 1.96 * se] if np.isfinite(se) else [None, None]
    downside = float(np.quantile(net, .05)) if support else None
    decision = action if support >= minimum_support and ci[0] is not None and ci[0] > 0 else "WAIT"
    return {"expected_gross_return": float(gross.mean()) if support else None,
            "expected_costs": float(cost.mean()) if support else None,
            "expected_net_return": mean if support else None, "uncertainty": se,
            "confidence_interval_95": ci, "support": support, "downside_p05": downside,
            "decision": decision}


def abstention_value(value_enter: float | None, value_wait: float = 0.0) -> dict:
    enter = float(value_enter) if value_enter is not None and np.isfinite(value_enter) else float("-inf")
    gain = float(value_wait - enter)
    return {"value_enter": None if enter == float("-inf") else enter,
            "value_wait": float(value_wait), "ABSTENTION_VALUE": gain,
            "optimal_action": "WAIT" if gain >= 0 else "ENTER"}


def one_sided_positive_p(values: Iterable[float]) -> float:
    x = np.asarray(list(values), dtype=float)
    x = x[np.isfinite(x)]
    if len(x) < 2 or x.std(ddof=1) == 0:
        return 1.0 if not len(x) or x.mean() <= 0 else 0.0
    z = float(x.mean() / (x.std(ddof=1) / sqrt(len(x))))
    return float(1.0 - NormalDist().cdf(z))
