from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from src.experience_store.parquet_store import ParquetExperienceStore
from src.utils.hashing import content_hash, file_hash
from src.validation.confirmation import CANDIDATES, ValidationCeremony, quarantine_post_validation_observation, replication_ratio
from src.validation.multiple_testing import benjamini_hochberg, holm_bonferroni


ROOT = Path(__file__).resolve().parents[2]


class ValidationCeremonyArtifactTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads((ROOT/"reports/validation/VALIDATION_CEREMONY_MANIFEST.json").read_text())
        cls.protocol = json.loads((ROOT/"reports/validation/VALIDATION_CEREMONY_PROTOCOL.json").read_text())
        cls.result = json.loads((ROOT/"reports/validation/PROMPT_6_VALIDATION_CEREMONY.json").read_text())
        cls.state = json.loads((ROOT/"state/validation_ceremony_state.json").read_text())
        cls.registry = {x["id"]:x for x in json.loads((ROOT/"hypotheses/evidence_registry.json").read_text())}

    def test_frozen_specification_integrity(self):
        self.assertEqual(tuple(x["hypothesis_id"] for x in self.manifest["candidates"]), CANDIDATES)
        for item in self.manifest["candidates"]:
            record=self.registry[item["hypothesis_id"]]
            self.assertEqual(item["spec_hash"],record["spec_hash"])
            prereg=ROOT/item["preregistration_path"]
            self.assertEqual(file_hash(prereg),item["preregistration_file_hash"])
            self.assertEqual(file_hash(ROOT/item["dev_evidence_path"]),item["dev_evidence_hash"])
            self.assertIsInstance(item["resolved_dev_threshold"],float)

    def test_ceremony_manifest_and_protocol_hashes(self):
        for document,field in ((self.manifest,"manifest_hash"),(self.protocol,"protocol_hash")):
            payload={k:v for k,v in document.items() if k not in {field,"created_at"}}
            self.assertEqual(content_hash(payload),document[field])
        self.assertEqual(self.result["manifest_hash"],self.manifest["manifest_hash"])
        self.assertEqual(self.result["protocol_hash"],self.protocol["protocol_hash"])

    def test_one_time_validation_authorization_is_consumed_and_idempotent(self):
        self.assertEqual(self.state["status"],"CONSUMED")
        self.assertEqual(self.state["validation_authorizations"],1)
        self.assertEqual(self.state["validation_dataset_reads"],1)
        again=ValidationCeremony(ROOT).run()
        after=json.loads((ROOT/"state/validation_ceremony_state.json").read_text())
        self.assertEqual(again["result_hash"],self.result["result_hash"])
        self.assertEqual(after["validation_dataset_reads"],1)

    def test_no_discovery_or_parameter_mutation_on_validation(self):
        self.assertFalse(self.result["discovery_on_validation"])
        self.assertFalse(self.result["optimization_on_validation"])
        self.assertIn("parameter search",self.protocol["prohibitions"])
        self.assertIn("threshold mutation",self.protocol["prohibitions"])
        for item in self.manifest["candidates"]:
            self.assertEqual(item["frozen_scientific_specification"]["condition"],item["condition"])

    def test_holm_correction(self):
        self.assertEqual(holm_bonferroni([.01,.04,.03,.002]),[.03,.06,.06,.008])
        ps=[x["permutation"]["p_value"] for x in self.result["hypotheses"]]
        self.assertEqual(holm_bonferroni(ps),[x["holm_adjusted_p"] for x in self.result["hypotheses"]])

    def test_bh_fdr_is_complementary_and_persisted(self):
        ps=[x["permutation"]["p_value"] for x in self.result["hypotheses"]]
        self.assertEqual(benjamini_hochberg(ps),[x["bh_fdr_q"] for x in self.result["hypotheses"]])
        self.assertEqual(self.protocol["multiple_testing"]["primary"],"Holm family-wise correction")

    def test_replication_ratio(self):
        self.assertEqual(replication_ratio(2.0,4.0),.5)
        self.assertIsNone(replication_ratio(2.0,0.0))
        for item in self.result["hypotheses"]:
            self.assertAlmostEqual(item["replication_ratio"],item["validation_effect"]/item["dev_effect"])

    def test_predictive_and_economic_gates_are_separate(self):
        for item in self.result["hypotheses"]:
            self.assertTrue(item["predictive_replication"]["passed"])
            self.assertFalse(item["economic_gate"]["passed"])
            self.assertLess(item["economic"]["absolute_conditional_net_return"],0)

    def test_cost_stress_is_complete_and_separated_by_method(self):
        for item in self.result["hypotheses"]:
            self.assertEqual(set(item["cost_sensitivity"]),{"1.0","1.25","1.5","2.0"})
            self.assertTrue(set(item["economic"]["by_cost_method"]) <= {"REAL_TICK_COST","PROXY_COST"})
            self.assertEqual(item["economic"]["economic_confidence"],"LOW")

    def test_temporal_and_regime_stability_are_prespecified(self):
        for item in self.result["hypotheses"]:
            self.assertEqual(len(item["temporal_stability"]["effects"]),9)
            self.assertEqual(set(item["regime_stability"]["effects"]),{"RANGE","TREND_UP","TREND_DOWN"})

    def test_skeptic_and_slow_structure_controls_ran(self):
        for item in self.result["hypotheses"]:
            self.assertEqual(item["skeptic"]["attempted"],8)
            self.assertTrue(item["skeptic"]["slow_structure_control"]["passed"])

    def test_locked_oos_hard_lock(self):
        self.assertFalse(self.result["locked_oos_inspected"])
        self.assertEqual(self.state["locked_oos_reads"],0)
        with self.assertRaises(PermissionError):
            ParquetExperienceStore(ROOT).query(partitions=("LOCKED_OOS",),limit=1)

    def test_long_term_promotion_has_independent_evidence(self):
        memories=json.loads((ROOT/"memory_db/long_term/records.json").read_text())
        promoted=[x for x in memories if "independent-replication" in x.get("tags",[])]
        self.assertTrue(promoted)
        self.assertIn(self.result["result_hash"],promoted[-1]["evidence_ids"])
        self.assertTrue(set(CANDIDATES).issubset(promoted[-1]["evidence_ids"]))

    def test_post_validation_observations_are_quarantined(self):
        with tempfile.TemporaryDirectory() as directory:
            item=quarantine_post_validation_observation(directory,hypothesis_id=CANDIDATES[0],observation="possible subgroup")
            ledger=json.loads((Path(directory)/"reports/validation/POST_VALIDATION_OBSERVATIONS.json").read_text())
            self.assertEqual(item["status"],"POST_VALIDATION_OBSERVATION")
            self.assertFalse(item["tested"])
            self.assertFalse(ledger["validation_reuse_allowed"])
            self.assertFalse(ledger["discovery_feedback_allowed"])

    def test_knowledge_research_and_trade_values_are_separate(self):
        value=json.loads((ROOT/"state/value_model_state.json").read_text())["validation_values"]
        self.assertEqual(set(value)-{"interpretation"},{"knowledge_value","research_value","trade_value"})
        self.assertGreater(value["knowledge_value"],value["research_value"])
        self.assertEqual(value["trade_value"],0.0)

    def test_verdicts_are_persisted(self):
        self.assertEqual(self.result["verdict_counts"],{
            "VALIDATION_FAILED":0,"VALIDATED_PREDICTIVE_RELATIONSHIP_NO_TRADE":4,
            "VALIDATED_ECONOMIC_CANDIDATE":0})
        for item in self.result["hypotheses"]:
            self.assertEqual(self.registry[item["hypothesis_id"]]["status"],item["verdict"])

    def test_result_hash_and_validation_scope(self):
        payload={k:v for k,v in self.result.items() if k not in {"created_at","result_hash"}}
        self.assertEqual(content_hash(payload),self.result["result_hash"])
        self.assertEqual(self.result["validation_sessions"],775)
        self.assertEqual(self.result["period"],"2020-01-01/2023-01-01 exclusive")


if __name__ == "__main__":
    unittest.main()
