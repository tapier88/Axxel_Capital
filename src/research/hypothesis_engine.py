"""Create traceable research hypotheses without asserting an unobserved edge."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from src.experience_store.repository import JsonRepository
from src.orchestrator.state_machine import utc_now
from src.utils.ids import new_id


class HypothesisEngine:
    def __init__(self, root: Path | str):
        self.repository = JsonRepository(Path(root) / "records.json")

    def create(
        self,
        question: str,
        *,
        statement: str | None = None,
        rationale: str = "Pending empirical evidence",
        falsification: str = "Dry-run evidence fails the declared acceptance criteria",
        tags: list[str] | None = None,
        uncertainties: list[str] | None = None,
    ) -> dict[str, Any]:
        hypothesis = {
            "id": new_id("HYPOTHESIS"), "created_at": utc_now(), "question": question,
            "statement": statement or f"Investigate whether: {question}", "rationale": rationale,
            "falsification": falsification, "tags": sorted(set(tags or [])),
            "uncertainties": uncertainties or ["No market dataset has been supplied"], "status": "ACTIVE",
        }
        return self.repository.add(hypothesis)

    def latest_active(self) -> dict[str, Any] | None:
        active = self.repository.find(lambda item: item.get("status") == "ACTIVE")
        return active[-1] if active else None
