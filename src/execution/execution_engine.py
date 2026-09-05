"""Fail-closed dry-run execution boundary. V0 cannot emit real orders."""

from __future__ import annotations
from typing import Any

ALLOWED_MODE = "RESEARCH_ONLY"


def execute_dry_run(experiment: dict[str, Any], *, mode: str) -> dict[str, Any]:
    if mode != ALLOWED_MODE:
        raise PermissionError("V0 only permits RESEARCH_ONLY")
    return {
        "status": "DRY_RUN_COMPLETED", "summary": "Control-flow dry-run completed; no market claim was tested",
        "experiment_id": experiment["id"], "execution_mode": ALLOWED_MODE,
        "broker_connected": False, "orders_created": 0, "real_capital_at_risk": False,
        "evidence_quality": "STRUCTURAL_ONLY",
        "uncertainties": ["Market data and statistical validation are not part of Prompt #1"],
    }
