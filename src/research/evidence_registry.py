"""Immutable hypothesis specifications, global test ledger, and validation preregistration."""
from __future__ import annotations
from pathlib import Path
from typing import Any

from src.experience_store.repository import JsonRepository
from src.orchestrator.state_machine import utc_now
from src.utils.hashing import content_hash, file_hash
from src.utils.ids import new_id
from src.utils.serialization import atomic_write_json, read_json

REQUIRED = ("question", "target_variable", "population", "temporal_window", "condition", "primary_metric",
            "secondary_metrics", "null", "expected_direction", "rejection_criterion", "survival_criterion",
            "planned_comparisons")
STATUSES = ("PROPOSED", "TESTING", "REJECTED", "RESEARCH_ONLY", "DEV_SURVIVOR", "VALIDATION_READY",
            "VALIDATION_FAILED", "VALIDATED", "VALIDATED_PREDICTIVE_RELATIONSHIP_NO_TRADE",
            "VALIDATED_ECONOMIC_CANDIDATE")
OPTIONAL_SCIENTIFIC = ("action", "effect_unit", "minimum_effect", "negative_control", "parameter_neighbors",
                       "minimum_rows", "minimum_sessions", "minimum_years", "family", "proposal_type")

class EvidenceRegistry:
    def __init__(self, project_root: Path | str):
        self.root = Path(project_root); self.repo = JsonRepository(self.root / "hypotheses/evidence_registry.json")
    def register(self, specification: dict[str, Any]) -> dict[str, Any]:
        missing = [key for key in REQUIRED if key not in specification]
        if missing: raise ValueError(f"Missing preregistration fields: {missing}")
        if int(specification["planned_comparisons"]) < 1: raise ValueError("planned_comparisons must be positive")
        spec = {**specification}; identifier = spec.get("id") or new_id("HYPOTHESIS")
        spec["id"] = identifier
        scientific_keys = ("id", *REQUIRED, *OPTIONAL_SCIENTIFIC)
        frozen = {key: spec[key] for key in scientific_keys if key in spec}
        digest = content_hash(frozen)
        existing = self.repo.find(lambda x: x["id"] == identifier)
        if existing:
            if any(existing[0].get(key) != frozen.get(key) for key in scientific_keys if key in frozen or key in existing[0]):
                raise PermissionError("Frozen hypothesis specification cannot be modified")
            return existing[0]
        return self.repo.add({**frozen, "spec_hash": digest, "created_at": utc_now(), "status": "PROPOSED",
                              "evidence_artifacts": [], "tests_executed": 0})
    def update_status(self, identifier: str, status: str, **metadata: Any) -> dict[str, Any]:
        if status not in STATUSES: raise ValueError(status)
        return self.repo.update(identifier, {"status": status, **metadata, "updated_at": utc_now()})
    def freeze_experiment_config(self, identifier: str, config: dict[str, Any], source_hash: str) -> None:
        """Freeze the complete executable recipe, not just the hypothesis prose."""
        record = self.repo.find(lambda x: x["id"] == identifier)[0]
        digest = content_hash(config)
        previous = record.get("experiment_config_hash")
        if previous and previous != digest:
            raise PermissionError("Frozen experiment configuration cannot be modified")
        for artifact in record.get("evidence_artifacts", []):
            prior = read_json(self.root / artifact, {})
            if prior.get("config_hash") and prior["config_hash"] != source_hash:
                raise PermissionError("Configuration differs from previously executed evidence")
        if not previous:
            self.repo.update(identifier, {"experiment_config_hash": digest, "frozen_experiment_config": config})
    def record_report(self, identifier: str, report: dict[str, Any]) -> Path:
        record = self.repo.find(lambda x: x["id"] == identifier)[0]
        path = self.root / "reports/evidence" / f"{identifier.lower()}_{content_hash(report)[:16]}.json"
        if not path.exists(): atomic_write_json(path, report)
        relative_path = str(path.relative_to(self.root)).replace("\\", "/")
        is_new_report = relative_path not in record.get("evidence_artifacts", [])
        artifacts = [*record.get("evidence_artifacts", []), relative_path]
        self.repo.update(identifier, {"evidence_artifacts": list(dict.fromkeys(artifacts)),
                         "tests_executed": int(record.get("tests_executed", 0))+(int(record["planned_comparisons"]) if is_new_report else 0),
                         "last_nominal_p": report["p_value"], "last_report_hash": file_hash(path), "updated_at": utc_now()})
        return path
    def preregister_validation(self, identifier: str, report_path: Path | str) -> dict[str, Any]:
        record = self.repo.find(lambda x: x["id"] == identifier)[0]
        if record["status"] != "DEV_SURVIVOR": raise PermissionError("Only DEV_SURVIVOR can become VALIDATION_READY")
        payload = {"hypothesis_id": identifier, "spec_hash": record["spec_hash"],
                   "evidence_artifact": str(Path(report_path).relative_to(self.root)).replace("\\", "/"),
                   "evidence_hash": file_hash(report_path), "partition_authorized": "VALIDATION",
                   "locked_oos_authorized": False, "created_at": utc_now()}
        path = self.root / "hypotheses/validation_preregistrations" / f"{identifier.lower()}.json"
        if path.exists():
            old = read_json(path, {}); comparable = {k: v for k, v in old.items() if k != "created_at"}
            if comparable != {k: v for k, v in payload.items() if k != "created_at"}: raise PermissionError("Validation preregistration is immutable")
        else: atomic_write_json(path, payload)
        self.update_status(identifier, "VALIDATION_READY", validation_preregistration=str(path.relative_to(self.root)).replace("\\", "/"))
        return payload
