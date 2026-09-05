"""Persistent directed knowledge graph for hypothesis relationships."""
from __future__ import annotations
from pathlib import Path
from typing import Any
from src.orchestrator.state_machine import utc_now
from src.utils.serialization import atomic_write_json, read_json

RELATIONS = {"PARENT", "CHILD", "REFINES", "CONTRADICTS", "SUPPORTS", "REPLACES", "FALSIFIES"}

class HypothesisGraph:
    def __init__(self, project_root: Path | str): self.path = Path(project_root) / "hypotheses/graph.json"
    def load(self) -> dict[str, Any]: return read_json(self.path, {"nodes": [], "edges": []})
    def add_node(self, hypothesis: dict[str, Any]) -> None:
        graph = self.load(); node = {"id": hypothesis["id"], "family": hypothesis.get("family"),
                                   "status": hypothesis.get("status", "PROPOSED"), "updated_at": utc_now()}
        graph["nodes"] = [x for x in graph["nodes"] if x["id"] != node["id"]] + [node]
        atomic_write_json(self.path, graph)
    def add_edge(self, source: str, target: str, relation: str, evidence: str) -> None:
        if relation not in RELATIONS: raise ValueError(relation)
        graph = self.load(); edge = {"source": source, "target": target, "relation": relation,
                                     "evidence": evidence, "created_at": utc_now()}
        signature = (source, target, relation)
        if not any((x["source"], x["target"], x["relation"]) == signature for x in graph["edges"]): graph["edges"].append(edge)
        atomic_write_json(self.path, graph)
    def update_status(self, identifier: str, status: str) -> None:
        graph = self.load()
        for node in graph["nodes"]:
            if node["id"] == identifier: node["status"] = status; node["updated_at"] = utc_now()
        atomic_write_json(self.path, graph)
