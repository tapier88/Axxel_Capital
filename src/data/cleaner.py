"""Market-bar quality checks that report rather than invent repairs."""

from __future__ import annotations
from datetime import timedelta
from typing import Any
from src.data.timezone import parse_utc


def validate_bars(bars: list[dict[str, Any]], timeframe_minutes: int) -> dict[str, Any]:
    timestamps = [parse_utc(str(bar["time"])) for bar in bars]
    duplicates = len(timestamps) - len(set(timestamps))
    unordered = sum(left >= right for left, right in zip(timestamps, timestamps[1:]))
    nan_fields = 0
    invalid_ohlc = 0
    negative_volume = 0
    required = ("open", "high", "low", "close", "volume")
    for bar in bars:
        nan_fields += sum(bar.get(field) is None for field in required)
        if all(bar.get(field) is not None for field in ("open", "high", "low", "close")):
            invalid_ohlc += not (
                float(bar["low"]) <= min(float(bar["open"]), float(bar["close"]))
                and float(bar["high"]) >= max(float(bar["open"]), float(bar["close"]))
                and float(bar["low"]) <= float(bar["high"])
            )
        if bar.get("volume") is not None:
            negative_volume += float(bar["volume"]) < 0
    expected = timedelta(minutes=timeframe_minutes)
    gaps = [
        {"after": left.isoformat(), "before": right.isoformat(), "minutes": int((right-left).total_seconds()/60)}
        for left, right in zip(timestamps, timestamps[1:]) if right-left > expected
    ]
    blocking = duplicates > 0 or unordered > 0 or nan_fields > 0 or invalid_ohlc > 0 or negative_volume > 0
    return {
        "records": len(bars), "duplicate_timestamps": duplicates, "unordered_pairs": unordered,
        "nan_required_fields": nan_fields, "invalid_ohlc": int(invalid_ohlc),
        "negative_volume": int(negative_volume), "gaps": gaps, "gap_count": len(gaps),
        "blocking_errors": bool(blocking),
    }
