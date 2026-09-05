"""Retrieve relevant experience and memory without external embeddings."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from src.experience_store.repository import JsonRepository
from src.memory.memory_scoring import relevance_score


def retrieve_relevant(
    query: str,
    *,
    memory_root: Path | str,
    experience_root: Path | str,
    limit: int = 10,
) -> list[dict[str, Any]]:
    memory_root = Path(memory_root)
    candidates: list[dict[str, Any]] = []
    for scale in ("working", "episodic", "semantic", "long_term"):
        for record in JsonRepository(memory_root / scale / "records.json").all():
            candidates.append({**record, "source": f"memory:{scale}"})
    for episode in JsonRepository(Path(experience_root) / "episodes.json").all():
        searchable = {
            **episode,
            "content": " ".join(
                [
                    str(episode.get("state", "")),
                    str(episode.get("action", "")),
                    str(episode.get("outcome", "")),
                ]
            ),
            "source": "experience:episode",
        }
        candidates.append(searchable)
    scored = [({**item, "relevance": relevance_score(query, item)}) for item in candidates]
    scored.sort(key=lambda item: (item["relevance"], item.get("created_at", "")), reverse=True)
    return scored[: max(0, limit)]
