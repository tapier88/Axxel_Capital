"""Traceable, collision-resistant identifiers for persisted entities."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4
from src.utils.hashing import content_hash

VALID_KINDS = {
    "HYPOTHESIS", "EXPERIMENT", "EPISODE", "MEMORY", "MODEL_VERSION",
    "EXPERIENCE", "SESSION", "DATASET",
}


def new_id(kind: str) -> str:
    normalized = kind.upper()
    if normalized not in VALID_KINDS:
        raise ValueError(f"Unsupported identifier kind: {kind}")
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    return f"{normalized}-{timestamp}-{uuid4().hex[:10]}"


def stable_id(kind: str, value: object) -> str:
    normalized = kind.upper()
    if normalized not in VALID_KINDS:
        raise ValueError(f"Unsupported identifier kind: {kind}")
    return f"{normalized}-{content_hash(value)[:24]}"
