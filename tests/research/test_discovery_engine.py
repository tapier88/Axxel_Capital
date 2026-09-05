from __future__ import annotations
import tempfile, unittest
from collections import Counter
from pathlib import Path

from src.research.evidence_registry import EvidenceRegistry
from src.research.hypothesis_generator import FAMILIES, HypothesisGenerator
from src.utils.hashing import content_hash
from src.utils.serialization import read_json
from src.value.research_value import research_value_v2

ROOT=Path(__file__).resolve().parents[2]
CAMPAIGN_PATH=ROOT/"reports/evidence/PROMPT_5_DISCOVERY_CAMPAIGN.json"

class GenerationTests(unittest.TestCase):
    def test_generator_is_reproducible_and_diverse(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            generator=HypothesisGenerator(Path(directory)); first=generator.generate(24); second=generator.generate(24)
            self.assertEqual(first,second); self.assertEqual(len(first),24)
            self.assertEqual(Counter(x["family"] for x in first),{family:2 for family in FAMILIES})

    def test_registry_deduplicates_destroyed_region(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); generator=HypothesisGenerator(root); proposals=generator.generate(24)
            registry=EvidenceRegistry(root); registered=registry.register(proposals[0]); registry.update_status(registered["id"],"REJECTED")
            regenerated=generator.generate(24)
            self.assertNotIn(registered["id"],{x["id"] for x in regenerated})

    def test_research_value_penalizes_complexity_and_redundancy(self) -> None:
        base=dict(expected_information_gain=.8,uncertainty_reduction=.8,novelty=.8,prior_evidence=.2,
                  contradiction_value=.5,economic_relevance=.8,data_quality=.9,estimated_compute_cost=.3,
                  family_saturation_penalty=.1)
        simple=research_value_v2(**base,redundancy_penalty=.05,complexity_penalty=.1)["score"]
        complex_duplicate=research_value_v2(**base,redundancy_penalty=.9,complexity_penalty=.9)["score"]
        self.assertGreater(simple,complex_duplicate)

@unittest.skipUnless(CAMPAIGN_PATH.exists(),"Discovery campaign not executed")
class CampaignArtifactTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.campaign=read_json(CAMPAIGN_PATH,{})

    def test_campaign_size_family_diversity_and_limits(self) -> None:
        self.assertEqual(self.campaign["proposed"],24); self.assertEqual(self.campaign["executed"],24)
        self.assertEqual(self.campaign["family_distribution"],{family:2 for family in FAMILIES})
        limits=read_json(ROOT/"config/discovery_limits_v1.json",{})
        self.assertEqual(limits["max_tests_per_iteration"],1); self.assertLessEqual(self.campaign["executed"],limits["campaign_iterations"])

    def test_scientific_campaign_hash_is_reproducible(self) -> None:
        proposals=HypothesisGenerator(ROOT).generate(24,include_existing_campaign=True)
        scientific=[{key:p[key] for key in ("id","family","target_variable","condition","action","expected_direction",
                    "minimum_effect","planned_comparisons","parameter_neighbors")} for p in proposals]
        expected=content_hash({"limits":read_json(ROOT/"config/discovery_limits_v1.json",{}),"proposals":scientific})
        self.assertEqual(expected,self.campaign["campaign_hash"])

    def test_all_reports_pass_full_evidence_and_skeptic_pipeline(self) -> None:
        required={"base_rate","effect_size","bootstrap_stability","permutation","multiple_testing_adjusted_p",
                  "temporal_stability","cost_stability","parameter_stability","negative_controls","skeptic","evidence_score"}
        for report in self.campaign["reports"]:
            self.assertTrue(required.issubset(report)); self.assertGreaterEqual(report["skeptic"]["attempted"],7)

    def test_support_minimum_is_enforced_and_reported(self) -> None:
        for report in self.campaign["reports"]:
            support=report["support"]
            self.assertGreaterEqual(support["minimum_rows"],5000)
            self.assertGreaterEqual(support["minimum_sessions"],200)
            self.assertGreaterEqual(support["minimum_years"],3)

    def test_validation_and_oos_remain_closed(self) -> None:
        self.assertFalse(self.campaign["validation_inspected"]); self.assertFalse(self.campaign["locked_oos_inspected"])
        self.assertTrue(all(x["partition"]=="DEV" for x in self.campaign["reports"]))

    def test_ready_candidates_are_frozen_without_validation_execution(self) -> None:
        ready=[x for x in self.campaign["reports"] if x["verdict"]=="VALIDATION_READY"]
        self.assertEqual(len(ready),4)
        for report in ready:
            path=ROOT/"hypotheses/validation_preregistrations"/f"{report['hypothesis_id'].lower()}.json"
            registration=read_json(path,{})
            self.assertEqual(registration["partition_authorized"],"VALIDATION")
            self.assertFalse(registration["locked_oos_authorized"])

    def test_volatility_diagnostic_confirms_rejection(self) -> None:
        diagnostic=self.campaign["volatility_diagnostic"]
        self.assertEqual(diagnostic["proposal_type"],"RETEST_WITH_NEW_EVIDENCE")
        self.assertEqual(diagnostic["conclusion"],"CONFIRMED_REJECTION")
        self.assertGreater(diagnostic["maximum_shift_to_original_ratio"],.5)
        self.assertIn("stationary_bootstrap",diagnostic)

    def test_intraday_scan_is_symmetric_and_fdr_adjusted(self) -> None:
        scan=self.campaign["intraday_structure"]
        self.assertTrue(scan["symmetric"]); self.assertEqual(scan["windows_tested"],18)
        self.assertTrue(all("fdr_p_value" in x for x in scan["windows"]))

    def test_hypothesis_graph_supports_all_relation_types(self) -> None:
        graph=read_json(ROOT/"hypotheses/graph.json",{})
        relations={x["relation"] for x in graph["edges"]}
        self.assertEqual(relations,{"PARENT","CHILD","REFINES","CONTRADICTS","SUPPORTS","REPLACES","FALSIFIES"})

    def test_family_knowledge_is_consolidated_without_raw_copy(self) -> None:
        memory=read_json(ROOT/"memory_db/semantic/records.json",[])
        tags={tag for item in memory for tag in item.get("tags",[]) if tag.startswith("family-consolidation-")}
        self.assertEqual(tags,{f"family-consolidation-{family.lower()}" for family in FAMILIES})

    def test_rejected_hypotheses_have_reasons(self) -> None:
        rejected=[x for x in self.campaign["reports"] if x["verdict"]=="REJECTED"]
        self.assertEqual(len(rejected),20); self.assertTrue(all(x["rejection_reasons"] for x in rejected))

if __name__=="__main__": unittest.main()
