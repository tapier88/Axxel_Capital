"""Cost models that refuse to invent unavailable execution inputs."""

from __future__ import annotations
from typing import Any


def evaluate_cost(state: dict[str, Any], action: str) -> dict[str, Any]:
    if action == "WAIT":
        return {"method": "NO_POSITION", "spread_price": 0.0, "round_trip_return": 0.0, "quality": "EXACT"}
    spread = state.get("spread")
    close = state["recent_ohlc"]["close"]
    if spread is None:
        return {"method": "UNAVAILABLE", "spread_price": None, "round_trip_return": None,
                "quality": "NOT_COMPUTABLE_WITHOUT_BID_ASK_OR_BAR_SPREAD"}
    return {"method": "BAR_SPREAD_APPROXIMATION", "spread_price": spread,
            "round_trip_return": float(spread)/float(close), "quality": "APPROXIMATION"}


def cost_model_v2(*, spread_price: float | None, close: float, source_id: str,
                  broker: str, timestamp: Any, real_tick_cost: float | None = None,
                  estimated_slippage: float | None = None) -> dict[str, Any]:
    """Return explicit provenance and uncertainty for a pre-entry round-trip cost.

    A real bid/ask observation wins.  Otherwise the broker's M1 spread field is
    retained as a labelled proxy.  Missing slippage is never converted to zero.
    """
    if close <= 0:
        raise ValueError("close must be positive")
    if real_tick_cost is not None:
        method, value, confidence = "REAL_TICK_COST", float(real_tick_cost), "HIGH"
    elif spread_price is not None:
        method, value, confidence = "PROXY_COST", float(spread_price) / float(close), "MEDIUM"
    else:
        method, value, confidence = "UNAVAILABLE", None, "LOW"
    return {
        "SOURCE_ID": source_id, "broker": broker, "timestamp": str(timestamp),
        "REAL_TICK_COST": float(real_tick_cost) if real_tick_cost is not None else None,
        "PROXY_COST": value if method == "PROXY_COST" else None,
        "method": method, "round_trip_return": value, "confidence": confidence,
        "estimated_slippage": estimated_slippage,
        "slippage_status": "AVAILABLE" if estimated_slippage is not None else "UNAVAILABLE_NOT_ASSUMED_ZERO",
    }
