"""Long-term memory for semantic records with stronger evidence."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from src.experience_store.repository import JsonRepository
from src.orchestrator.state_machine import utc_now
from src.utils.ids import new_id


class LongTermMemory:
    def __init__(self, root: Path | str):
        self.repository = JsonRepository(Path(root) / "long_term" / "records.json")

    def promote(self, semantic: dict[str, Any]) -> dict[str, Any]:
        return self.repository.add(
            {
                **semantic,
                "id": new_id("MEMORY"),
                "type": "long_term",
                "source_memory_id": semantic["id"],
                "promoted_at": utc_now(),
            }
        )

    def all(self) -> list[dict[str, Any]]:
        return self.repository.all()
