"""Economic materiality metrics before directional prediction."""
from __future__ import annotations
import numpy as np


def edge_to_cost_ratio(expected_gross_opportunity: float, expected_cost: float) -> float:
    if expected_cost <= 0: raise ValueError("expected_cost must be positive")
    return float(expected_gross_opportunity/expected_cost)


def opportunity_labels(up_excursion, down_excursion, cost, *, k: float, horizon: int,
                       shorter_excursions: dict[int, np.ndarray] | None = None) -> dict:
    up=np.asarray(up_excursion,dtype=float); down=np.asarray(down_excursion,dtype=float); c=np.asarray(cost,dtype=float)
    max_abs=np.maximum(np.abs(up),np.abs(down)); large=max_abs >= float(k)*c
    time=np.full(len(max_abs),np.nan)
    for minutes,values in sorted((shorter_excursions or {}).items()):
        hit=(np.asarray(values,dtype=float)>=float(k)*c)&np.isnan(time); time[hit]=minutes
    time[large & np.isnan(time)]=horizon
    return {"max_absolute_excursion":max_abs,"large_future_excursion":large,
            "opportunity_surplus":max_abs-float(k)*c,"time_to_excursion_minutes":time}


def opportunity_value(expected_move: float, expected_cost: float, frequency: float,
                      uncertainty: float, *, complexity: int) -> float:
    ratio=edge_to_cost_ratio(expected_move,expected_cost)
    materiality=min(1.0,ratio/3.0); freq=min(1.0,max(0.0,frequency)/.10)
    precision=max(0.0,1.0-min(1.0,uncertainty/.25))
    return float(max(0.0,.45*materiality+.25*freq+.2*precision-.08*complexity))
