"""Evidence-threshold consolidation from episodic to semantic memory."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any

from src.memory.long_term_memory import LongTermMemory
from src.memory.semantic_memory import SemanticMemory


def consolidate_memory(
    memory_root: Path | str, *, min_evidence: int = 2, long_term_threshold: int = 4
) -> list[dict[str, Any]]:
    root = Path(memory_root)
    from src.memory.episodic_memory import EpisodicMemory

    episodic = EpisodicMemory(root).all()
    semantic_store = SemanticMemory(root)
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in episodic:
        groups[item.get("hypothesis_id", "unlinked")].append(item)

    created: list[dict[str, Any]] = []
    for hypothesis_id, records in groups.items():
        if len(records) < min_evidence:
            continue
        evidence_ids = [eid for record in records for eid in record.get("evidence_ids", [])]
        previous = [
            item for item in semantic_store.all()
            if hypothesis_id.lower() in item.get("tags", [])
        ]
        if previous and set(evidence_ids).issubset(set(previous[-1].get("evidence_ids", []))):
            continue
        confidence = sum(float(r.get("confidence", 0.5)) for r in records) / len(records)
        semantic = semantic_store.add_knowledge(
            f"{len(records)} episodios aportan evidencia sobre {hypothesis_id}. "
            "Conclusión V0: evidencia acumulada; requiere validación estadística posterior.",
            evidence_ids=evidence_ids,
            confidence=confidence,
            tags=["consolidated", hypothesis_id.lower()],
            experience_ids=[eid for record in records for eid in record.get("experience_ids", [])],
        )
        created.append(semantic)
        if len(records) >= long_term_threshold and confidence >= 0.75:
            long_term = LongTermMemory(root)
            if not any(item.get("source_memory_id") == semantic["id"] for item in long_term.all()):
                long_term.promote(semantic)
    return created
