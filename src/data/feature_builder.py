"""Strictly causal state features and future-only labels."""

from __future__ import annotations
import math
import statistics
from typing import Any


def _returns(bars: list[dict[str, Any]], index: int, lookback: int) -> float | None:
    if index < lookback or bars[index-lookback]["close"] == 0:
        return None
    return (bars[index]["close"] / bars[index-lookback]["close"]) - 1.0


def build_state(bars: list[dict[str, Any]], point: dict[str, Any], session_id: str) -> dict[str, Any]:
    index = point["bar_index"]
    current = bars[index]
    start14 = max(0, index-13)
    true_ranges = []
    for offset in range(start14, index+1):
        previous_close = bars[offset-1]["close"] if offset else bars[offset]["open"]
        true_ranges.append(max(
            bars[offset]["high"]-bars[offset]["low"],
            abs(bars[offset]["high"]-previous_close), abs(bars[offset]["low"]-previous_close),
        ))
    recent_returns = [_returns(bars, offset, 1) for offset in range(max(1,index-5), index+1)]
    recent_returns = [value for value in recent_returns if value is not None]
    start12 = max(0, index-11)
    recent_high = max(bar["high"] for bar in bars[start12:index+1])
    recent_low = min(bar["low"] for bar in bars[start12:index+1])
    volatility = statistics.pstdev(recent_returns) if len(recent_returns) >= 2 else None
    momentum = _returns(bars, index, 3)
    if volatility is None or momentum is None:
        regime = "UNKNOWN"
    elif momentum > volatility:
        regime = "TREND_UP"
    elif momentum < -volatility:
        regime = "TREND_DOWN"
    else:
        regime = "RANGE"
    return {
        "information_boundary": "FEATURES_AVAILABLE_AT_DECISION_TIME",
        "symbol": current["symbol"], "session_id": session_id,
        "timestamp_utc": point["timestamp_utc"], "timestamp_cot": point["timestamp_cot"],
        "minute_of_session": point["minute_of_session"],
        "recent_ohlc": {key: current[key] for key in ("open","high","low","close")},
        "return_1h": _returns(bars,index,1), "return_3h": _returns(bars,index,3), "return_6h": _returns(bars,index,6),
        "bar_range": current["high"]-current["low"], "atr_14_causal": sum(true_ranges)/len(true_ranges),
        "realized_volatility_6h_causal": volatility, "spread": current["spread"],
        "tick_volume": current["tick_volume"], "real_volume": current["real_volume"],
        "distance_to_recent_high": (recent_high-current["close"])/current["close"],
        "distance_to_recent_low": (current["close"]-recent_low)/current["close"],
        "momentum_3h_causal": momentum, "regime_v0": regime,
        "data_quality": {"spread_available": current["spread"] is not None, "real_volume_available": current["real_volume"] is not None},
        "max_source_bar_index": index,
    }


def build_future_outcome(bars: list[dict[str, Any]], index: int) -> dict[str, Any] | None:
    if index + 1 >= len(bars):
        return None
    current, future = bars[index], bars[index+1]
    base = current["close"]
    future_return = (future["close"] / base) - 1.0
    return {
        "information_boundary": "FUTURE INFORMATION — LABEL ONLY",
        "future_return_5m": None, "future_return_15m": None, "future_return_30m": None,
        "future_return_60m": future_return,
        "mfe_60m_long": (future["high"]-base)/base, "mae_60m_long": (future["low"]-base)/base,
        "up_excursion_60m": (future["high"]-base)/base,
        "down_excursion_60m": (future["low"]-base)/base,
        "realized_volatility_60m": abs(future_return),
        "unavailable_horizons_reason": "Source timeframe is H1; 5m/15m/30m cannot be derived",
        "source_future_bar_index": index+1,
    }


def assert_no_temporal_leakage(state: dict[str, Any], outcome: dict[str, Any]) -> None:
    if state["information_boundary"] != "FEATURES_AVAILABLE_AT_DECISION_TIME":
        raise ValueError("Invalid state information boundary")
    if outcome["information_boundary"] != "FUTURE INFORMATION — LABEL ONLY":
        raise ValueError("Invalid outcome information boundary")
    if state["max_source_bar_index"] >= outcome["source_future_bar_index"]:
        raise ValueError("Temporal leakage detected")
    if any(key.startswith("future_") for key in state):
        raise ValueError("Future label leaked into state")
