from __future__ import annotations
import tempfile, unittest
from pathlib import Path
import numpy as np

from src.research.evidence_registry import EvidenceRegistry
from src.utils.serialization import atomic_write_json, read_json
from src.validation.bootstrap import block_bootstrap, session_bootstrap
from src.validation.multiple_testing import benjamini_hochberg
from src.validation.oos import PartitionGuard
from src.validation.permutation import session_permutation_test
from src.validation.skeptic import run_skeptic
from src.value.research_value import research_value_v1

ROOT = Path(__file__).resolve().parents[2]
BATTERY = ROOT / "reports/evidence/PROMPT_4_CALIBRATION_BATTERY.json"

def spec(identifier: str = "HYPOTHESIS-TEST-V1") -> dict:
    return {"id": identifier, "question": "test", "target_variable": "x", "population": "DEV",
            "temporal_window": "fixed", "condition": {"type": "test"}, "primary_metric": "mean",
            "secondary_metrics": [], "null": "zero", "expected_direction": "GREATER",
            "rejection_criterion": "fail", "survival_criterion": "pass", "planned_comparisons": 1}

class StatisticalPrimitiveTests(unittest.TestCase):
    def test_session_and_block_bootstrap_are_reproducible(self) -> None:
        values = np.linspace(-.01, .03, 100)
        self.assertEqual(session_bootstrap(values, resamples=200, seed=7), session_bootstrap(values, resamples=200, seed=7))
        self.assertEqual(block_bootstrap(values, block_size=10, resamples=100, seed=9),
                         block_bootstrap(values, block_size=10, resamples=100, seed=9))

    def test_permutation_is_reproducible(self) -> None:
        values = np.linspace(-.01, .03, 100)
        first = session_permutation_test(values, permutations=500, seed=11)
        self.assertEqual(first, session_permutation_test(values, permutations=500, seed=11))
        self.assertLess(first["p_value"], .05)

    def test_benjamini_hochberg(self) -> None:
        self.assertEqual(benjamini_hochberg([.01, .04, .03]), [.03, .04, .04])

    def test_skeptic_executes_falsifications(self) -> None:
        result = run_skeptic(np.linspace(.01, .03, 100), temporal={"favorable_proportion": 1},
                             cost={"survives_2x": True, "applicable": True},
                             data_quality={"blocking_errors": False}, direction="GREATER")
        self.assertGreaterEqual(result["attempted"], 7)
        self.assertTrue(any(x["name"] == "remove_best_5pct_sessions" for x in result["attempts"]))

    def test_research_value_discounts_resolved_questions(self) -> None:
        common = dict(expected_information_gain=.5, uncertainty_reduction=.5, novelty=.5, cost=.2, relevance=.8)
        unresolved = research_value_v1(**common, previous_evidence=.1)["score"]
        resolved = research_value_v1(**common, previous_evidence=.95)["score"]
        self.assertGreater(unresolved, resolved)

class RegistryAndIsolationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(); self.root = Path(self.tmp.name)
    def tearDown(self) -> None: self.tmp.cleanup()

    def test_hypothesis_specification_is_immutable(self) -> None:
        registry = EvidenceRegistry(self.root); registry.register(spec())
        changed = spec(); changed["primary_metric"] = "median"
        with self.assertRaises(PermissionError): registry.register(changed)

    def test_preregistration_hash_is_persistent(self) -> None:
        registry = EvidenceRegistry(self.root); registry.register(spec()); registry.update_status("HYPOTHESIS-TEST-V1", "DEV_SURVIVOR")
        report = self.root / "reports/evidence/report.json"; atomic_write_json(report, {"evidence": 1})
        frozen = registry.preregister_validation("HYPOTHESIS-TEST-V1", report)
        self.assertEqual(frozen["partition_authorized"], "VALIDATION")
        self.assertFalse(frozen["locked_oos_authorized"])

    def test_discovery_rejects_and_logs_validation_and_oos(self) -> None:
        guard = PartitionGuard(self.root, "DISCOVERY"); guard.require("DEV", "test")
        with self.assertRaises(PermissionError): guard.require("VALIDATION", "test")
        with self.assertRaises(PermissionError): guard.require("LOCKED_OOS", "test")
        log = read_json(self.root / "reports/partition_access_log.json", [])
        self.assertEqual([x["allowed"] for x in log], [True, False, False])

@unittest.skipUnless(BATTERY.exists(), "Calibration battery not executed")
class CalibrationArtifactTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.battery = read_json(BATTERY, {}); cls.reports = cls.battery["reports"]

    def test_base_rates_temporal_splits_and_scores_exist(self) -> None:
        for report in self.reports:
            self.assertIn("baseline", report["base_rate"])
            self.assertGreaterEqual(report["temporal_stability"]["periods"], 5)
            self.assertTrue(0 <= report["evidence_score"]["value"] <= 1)

    def test_cost_multipliers_and_parameter_neighbors(self) -> None:
        negative = next(x for x in self.reports if "NEGATIVE" in x["hypothesis_id"])
        self.assertEqual(set(negative["cost_stability"]["multipliers"]), {"1.0", "1.25", "1.5", "2.0"})
        perturbed = [x for x in self.reports if x["parameter_stability"]["periods"] > 1]
        self.assertEqual(len(perturbed), 3)

    def test_negative_control_is_rejected(self) -> None:
        negative = next(x for x in self.reports if "NEGATIVE" in x["hypothesis_id"])
        self.assertEqual(negative["verdict"], "REJECTED")
        self.assertGreater(negative["multiple_testing_adjusted_p"], .05)

    def test_significant_result_is_rejected_when_negative_control_fails(self) -> None:
        volatility = next(x for x in self.reports if "VOL-PERSISTENCE" in x["hypothesis_id"])
        self.assertLess(volatility["multiple_testing_adjusted_p"], .05)
        self.assertFalse(volatility["negative_controls"]["passed"])
        self.assertEqual(volatility["verdict"], "REJECTED")
        self.assertIn("negative_control_failed", volatility["rejection_reasons"])

    def test_only_dev_was_inspected(self) -> None:
        self.assertEqual(self.battery["partition"], "DEV")
        self.assertFalse(self.battery["validation_inspected"])
        self.assertFalse(self.battery["locked_oos_inspected"])
        self.assertTrue(all(x["partition"] == "DEV" for x in self.reports))

    def test_memory_persists_rejections_and_survivors(self) -> None:
        memory = read_json(ROOT / "memory_db/semantic/records.json", [])
        evidence_ids = {eid for item in memory for eid in item.get("evidence_ids", [])}
        self.assertTrue({x["evidence_report_id"] for x in self.reports}.issubset(evidence_ids))

if __name__ == "__main__": unittest.main()
