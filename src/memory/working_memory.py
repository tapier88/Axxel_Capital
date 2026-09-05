"""Working-memory persistence with an explicit bounded capacity."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from src.experience_store.repository import JsonRepository
from src.orchestrator.state_machine import utc_now
from src.utils.ids import new_id
from src.utils.serialization import atomic_write_json


class WorkingMemory:
    def __init__(self, root: Path | str, capacity: int = 50):
        self.repository = JsonRepository(Path(root) / "working" / "records.json")
        self.capacity = capacity

    def remember(self, content: str, *, evidence_ids: list[str], tags: list[str]) -> dict[str, Any]:
        record = {
            "id": new_id("MEMORY"),
            "type": "working",
            "content": content,
            "evidence_ids": evidence_ids,
            "tags": sorted(set(tags)),
            "confidence": 0.5,
            "created_at": utc_now(),
            "status": "active",
        }
        records = self.repository.all() + [record]
        atomic_write_json(self.repository.path, records[-self.capacity :])
        return record

    def all(self) -> list[dict[str, Any]]:
        return self.repository.all()
