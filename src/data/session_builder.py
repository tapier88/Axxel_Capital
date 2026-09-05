"""Build COT research sessions while retaining full raw context."""

from __future__ import annotations
from collections import defaultdict
from datetime import timedelta
from typing import Any
from src.data.timezone import COT, parse_utc, to_cot_iso, to_utc_iso


def build_sessions(
    bars: list[dict[str, Any]], *, timeframe_minutes: int = 60,
    window_start_minutes: int = 8 * 60, window_end_minutes: int = 12 * 60 + 30,
) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for index, bar in enumerate(bars):
        decision = parse_utc(bar["timestamp_open_utc"]) + timedelta(minutes=timeframe_minutes)
        cot = decision.astimezone(COT)
        minute = cot.hour * 60 + cot.minute
        if window_start_minutes <= minute <= window_end_minutes:
            date = cot.date().isoformat()
            grouped[date].append({
                "bar_index": index, "timestamp_utc": to_utc_iso(decision),
                "timestamp_cot": to_cot_iso(decision), "minute_of_session": minute-window_start_minutes,
            })
    return [
        {"session_id": f"SESSION-{bars[0]['symbol']}-{date}-COT", "symbol": bars[0]["symbol"],
         "date_cot": date, "decision_points": points}
        for date, points in sorted(grouped.items())
    ] if bars else []
