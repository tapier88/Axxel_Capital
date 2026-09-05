"""Traceable experiment specifications and result recording."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from src.experience_store.repository import JsonRepository
from src.orchestrator.state_machine import utc_now
from src.utils.ids import new_id


class ExperimentEngine:
    def __init__(self, root: Path | str):
        self.repository = JsonRepository(Path(root) / "records.json")

    def create(
        self, hypothesis: dict[str, Any], retrieved_ids: list[str],
        experience_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        return self.repository.add({
            "id": new_id("EXPERIMENT"), "hypothesis_id": hypothesis["id"], "created_at": utc_now(),
            "objective": f"Dry-run feasibility check: {hypothesis['question']}",
            "method": "RESEARCH_ONLY deterministic dry-run; no broker connection",
            "retrieved_evidence_ids": retrieved_ids, "experience_ids": experience_ids or [],
            "status": "PENDING", "result": None,
        })

    def save_result(self, experiment_id: str, result: dict[str, Any]) -> dict[str, Any]:
        return self.repository.update(experiment_id, {"status": "COMPLETED", "completed_at": utc_now(), "result": result})
