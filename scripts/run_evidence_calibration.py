"""Run the small preregistered DEV calibration battery; never opens validation/OOS."""
from __future__ import annotations
import json, sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(PROJECT_ROOT))
from src.memory.semantic_memory import SemanticMemory
from src.experience_store.repository import JsonRepository
from src.orchestrator.state_machine import StateStore
from src.research.evidence_registry import EvidenceRegistry
from src.utils.hashing import content_hash
from src.utils.serialization import atomic_write_json, read_json
from src.validation.evidence_engine import EvidenceEngine
from src.validation.multiple_testing import benjamini_hochberg
from src.value.research_value import research_value_v1

if __name__ == "__main__":
    battery = read_json(PROJECT_ROOT / "config/calibration_hypotheses_v1.json", {})
    engine = EvidenceEngine(PROJECT_ROOT); reports = [engine.evaluate_hypothesis(spec) for spec in battery["hypotheses"]]
    adjusted = benjamini_hochberg([r["within_hypothesis_adjusted_p"] for r in reports])
    registry = EvidenceRegistry(PROJECT_ROOT); memory = SemanticMemory(PROJECT_ROOT / "memory_db")
    for report, fdr in zip(reports, adjusted):
        report["multiple_testing_adjusted_p"] = fdr
        if report["verdict"] == "DEV_SURVIVOR" and fdr > 0.05:
            report["verdict"] = "REJECTED"; report["rejection_reasons"].append("global_fdr_failed")
        registry.update_status(report["hypothesis_id"], report["verdict"], last_adjusted_p=fdr,
                               evidence_score=report["evidence_score"]["value"], rejection_reasons=report["rejection_reasons"])
        if not any(report["evidence_report_id"] in x.get("evidence_ids", []) and report["verdict"] in x.get("content", "")
                   for x in memory.all()):
            memory.add_knowledge(
                f"{report['hypothesis_id']} terminó {report['verdict']}; razones: {report['rejection_reasons'] or ['passed DEV gates']}",
                evidence_ids=[report["evidence_report_id"]], confidence=report["evidence_score"]["value"],
                tags=["evidence-v1", report["verdict"].lower(), report["hypothesis_id"].lower()])
    # VALIDATION_READY is possible only after the final global correction and immutable preregistration.
    for report in reports:
        if report["verdict"] == "DEV_SURVIVOR" and report["evidence_score"]["value"] >= 0.75:
            path = PROJECT_ROOT / registry.repo.find(lambda x: x["id"] == report["hypothesis_id"])[0]["last_evidence_artifact"]
            registry.preregister_validation(report["hypothesis_id"], path); report["verdict"] = "VALIDATION_READY"
    priorities = {r["hypothesis_id"]: research_value_v1(
        expected_information_gain=max(0.0, 1-r["evidence_score"]["value"]), uncertainty_reduction=.7,
        novelty=.3 if "0830" in r["hypothesis_id"] else .7, cost=.25, relevance=.8,
        previous_evidence=r["evidence_score"]["value"]) for r in reports}
    summary = {"battery_version": battery["version"], "battery_hash": content_hash(battery),
               "partition": "DEV", "validation_inspected": False, "locked_oos_inspected": False,
               "reports": reports, "research_value_v1": priorities,
               "counts": {status: sum(r["verdict"] == status for r in reports)
                          for status in ("REJECTED", "DEV_SURVIVOR", "VALIDATION_READY")}}
    output = PROJECT_ROOT / "reports/evidence/PROMPT_4_CALIBRATION_BATTERY.json"; atomic_write_json(output, summary)
    states = StateStore(PROJECT_ROOT / "state"); current = states.load_all()
    counts = {scale: len(JsonRepository(PROJECT_ROOT / "memory_db" / scale / "records.json").all())
              for scale in ("working", "episodic", "semantic", "long_term")}
    states.save("memory_state", {**current["memory_state"], "counts": counts})
    states.save("research_state", {**current["research_state"], "evidence_registry_count": len(reports),
                "evidence_status_counts": summary["counts"], "validation_inspected": False,
                "locked_oos_inspected": False})
    states.save("value_model_state", {**current["value_model_state"], "version": "v1-interpretable-research-priority",
                "trained": False, "last_research_priorities": priorities})
    print(json.dumps({"output": str(output), "counts": summary["counts"],
                      "results": [{"id": r["hypothesis_id"], "p": r["p_value"],
                                   "fdr": r["multiple_testing_adjusted_p"], "score": r["evidence_score"]["value"],
                                   "verdict": r["verdict"]} for r in reports]}, indent=2))
