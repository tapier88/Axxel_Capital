"""Fail-closed partition capabilities with a persistent access-attempt log."""
from __future__ import annotations
from pathlib import Path
from src.orchestrator.state_machine import utc_now
from src.utils.serialization import atomic_write_json, read_json

class PartitionGuard:
    def __init__(self, project_root: Path | str, phase: str = "DISCOVERY"):
        self.root = Path(project_root); self.phase = phase.upper()
        self.log_path = self.root / "reports/partition_access_log.json"
    def require(self, partition: str, component: str) -> None:
        partition = partition.upper()
        allowed = (self.phase == "DISCOVERY" and partition == "DEV") or (self.phase == "VALIDATION" and partition == "VALIDATION")
        log = read_json(self.log_path, [])
        log.append({"timestamp": utc_now(), "phase": self.phase, "partition": partition,
                    "component": component, "allowed": allowed})
        atomic_write_json(self.log_path, log)
        if not allowed: raise PermissionError(f"{component} cannot access {partition} during {self.phase}")
