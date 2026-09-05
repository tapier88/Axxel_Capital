"""Episode-derived memory records."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from src.experience_store.repository import JsonRepository
from src.orchestrator.state_machine import utc_now
from src.utils.ids import new_id


class EpisodicMemory:
    def __init__(self, root: Path | str):
        self.repository = JsonRepository(Path(root) / "episodic" / "records.json")

    def remember_episode(self, episode: dict[str, Any]) -> dict[str, Any]:
        result = episode.get("outcome", {})
        content = (
            f"Experiment {episode['experiment_id']} for {episode['hypothesis_id']}: "
            f"{result.get('summary', result.get('status', 'unknown outcome'))}"
        )
        memory = {
            "id": new_id("MEMORY"),
            "type": "episodic",
            "content": content,
            "evidence_ids": [episode["id"]],
            "hypothesis_id": episode["hypothesis_id"],
            "experiment_id": episode["experiment_id"],
            "experience_ids": episode.get("experience_ids", []),
            "tags": episode.get("tags", []),
            "confidence": episode.get("confidence", 0.5),
            "created_at": utc_now(),
            "status": "active",
        }
        return self.repository.add(memory)

    def all(self) -> list[dict[str, Any]]:
        return self.repository.all()
