"""Consolidated, evidence-linked semantic memory."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from src.experience_store.repository import JsonRepository
from src.orchestrator.state_machine import utc_now
from src.utils.ids import new_id


class SemanticMemory:
    def __init__(self, root: Path | str):
        self.repository = JsonRepository(Path(root) / "semantic" / "records.json")

    def add_knowledge(
        self, content: str, *, evidence_ids: list[str], confidence: float, tags: list[str],
        experience_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        return self.repository.add(
            {
                "id": new_id("MEMORY"),
                "type": "semantic",
                "content": content,
                "evidence_ids": sorted(set(evidence_ids)),
                "experience_ids": sorted(set(experience_ids or [])),
                "tags": sorted(set(tags)),
                "confidence": max(0.0, min(1.0, float(confidence))),
                "created_at": utc_now(),
                "status": "active",
            }
        )

    def all(self) -> list[dict[str, Any]]:
        return self.repository.all()
