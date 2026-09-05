"""Canonical bar normalization with no forward filling."""

from __future__ import annotations
from typing import Any
from src.data.timezone import parse_utc, to_utc_iso


def normalize_bars(bars: list[dict[str, Any]], symbol: str) -> list[dict[str, Any]]:
    normalized = []
    for bar in bars:
        normalized.append({
            "symbol": symbol.upper(), "timestamp_open_utc": to_utc_iso(parse_utc(str(bar["time"]))),
            "open": float(bar["open"]), "high": float(bar["high"]), "low": float(bar["low"]),
            "close": float(bar["close"]), "tick_volume": int(bar["volume"]),
            "real_volume": None, "spread": None,
        })
    return sorted(normalized, key=lambda item: item["timestamp_open_utc"])
