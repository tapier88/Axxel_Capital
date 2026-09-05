"""Heuristic uncertainty V0."""

from __future__ import annotations
from typing import Any


def uncertainty_score(hypothesis: dict[str, Any], retrieved: list[dict[str, Any]]) -> float:
    missing = len(hypothesis.get("uncertainties", []))
    evidence_strength = sum(float(item.get("relevance", 0.0)) for item in retrieved[:5]) / 5.0
    score = 0.45 + min(0.35, missing * 0.12) + (0.20 * (1.0 - evidence_strength))
    return round(max(0.0, min(1.0, score)), 6)
