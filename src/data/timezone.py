"""UTC and America/Bogota conversion utilities."""

from __future__ import annotations
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

COT = ZoneInfo("America/Bogota")


def parse_utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("Timestamp must include timezone")
    return parsed.astimezone(timezone.utc)


def to_utc_iso(value: datetime) -> str:
    if value.tzinfo is None:
        raise ValueError("Naive timestamps are forbidden")
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def to_cot_iso(value: datetime) -> str:
    if value.tzinfo is None:
        raise ValueError("Naive timestamps are forbidden")
    return value.astimezone(COT).isoformat()
