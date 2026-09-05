"""V0 validation gate for system safety and traceability.

This protocol intentionally does not validate market performance.
"""

from __future__ import annotations
from typing import Any


def validate_dry_run(hypothesis: dict[str, Any], experiment: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    checks = {
        "hypothesis_linked": experiment.get("hypothesis_id") == hypothesis.get("id"),
        "experiment_linked": result.get("experiment_id") == experiment.get("id"),
        "research_only": result.get("execution_mode") == "RESEARCH_ONLY",
        "no_broker_connection": result.get("broker_connected") is False,
        "no_real_orders": result.get("orders_created") == 0,
        "no_real_capital": result.get("real_capital_at_risk") is False,
    }
    return {"passed": all(checks.values()), "checks": checks, "scope": "SYSTEM_FLOW_ONLY", "edge_validated": False, "promotion_allowed": False}
