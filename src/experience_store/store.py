"""STATE -> ACTION -> OUTCOME episode persistence."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from src.experience_store.repository import JsonRepository
from src.orchestrator.state_machine import utc_now
from src.utils.ids import new_id


class ExperienceStore:
    def __init__(self, root: Path | str):
        self.root = Path(root)
        self.episodes = JsonRepository(self.root / "episodes.json")

    def create_episode(
        self,
        *,
        state: dict[str, Any],
        action: dict[str, Any],
        outcome: dict[str, Any],
        hypothesis_id: str,
        experiment_id: str,
        confidence: float,
        tags: list[str] | None = None,
        experience_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        episode = {
            "id": new_id("EPISODE"),
            "created_at": utc_now(),
            "hypothesis_id": hypothesis_id,
            "experiment_id": experiment_id,
            "state": state,
            "action": action,
            "outcome": outcome,
            "confidence": max(0.0, min(1.0, float(confidence))),
            "tags": sorted(set(tags or [])),
            "experience_ids": sorted(set(experience_ids or [])),
        }
        return self.episodes.add(episode)
