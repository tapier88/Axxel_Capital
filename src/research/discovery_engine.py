"""Autonomous, bounded DEV discovery campaign orchestrator."""
from __future__ import annotations
from collections import Counter
from pathlib import Path
from typing import Any

from src.memory.semantic_memory import SemanticMemory
from src.experience_store.repository import JsonRepository
from src.orchestrator.state_machine import StateStore
from src.research.evidence_registry import EvidenceRegistry
from src.research.hypothesis_generator import HypothesisGenerator
from src.research.hypothesis_graph import HypothesisGraph
from src.research.intraday_structure import analyze_intraday_windows
from src.research.volatility_diagnostic import diagnose_volatility_persistence
from src.utils.hashing import content_hash
from src.utils.serialization import atomic_write_json, read_json
from src.validation.evidence_engine import EvidenceEngine
from src.validation.multiple_testing import benjamini_hochberg
from src.value.research_value import research_value_v2

class DiscoveryEngine:
    def __init__(self, project_root: Path | str):
        self.root=Path(project_root); self.limits=read_json(self.root/"config/discovery_limits_v1.json",{})
        self.generator=HypothesisGenerator(self.root); self.graph=HypothesisGraph(self.root)
        self.registry=EvidenceRegistry(self.root); self.memory=SemanticMemory(self.root/"memory_db")

    def run_ml_candidate(self, config_path: Path | str) -> dict[str, Any]:
        """Evaluate a preregistered candidate through the same evidence and memory system."""
        from src.ml.experiment import run_ml_experiment
        return run_ml_experiment(self.root, config_path)

    def run_campaign(self) -> dict[str, Any]:
        volatility=diagnose_volatility_persistence(self.root,seed=int(self.limits["seed"]))
        intraday=analyze_intraday_windows(self.root,permutations=min(1000,int(self.limits["permutations"])))
        proposals=self.generator.generate(limit=int(self.limits["proposals"]),include_existing_campaign=True); initial_ranking=[]
        for proposal in proposals:
            related=proposal["family"] in {"VOLATILITY","TEMPORAL"}; complexity=.5 if proposal["condition"]["type"]=="all" else .2
            frozen_initial=research_value_v2(expected_information_gain=.8,uncertainty_reduction=.75,
                novelty=.55 if related else .85,prior_evidence=.45 if related else .15,
                contradiction_value=1.0 if related else .3,economic_relevance=1.0 if proposal["action"]!="WAIT" else .65,
                data_quality=.9,estimated_compute_cost=.35+complexity*.2,redundancy_penalty=.05,
                family_saturation_penalty=0,complexity_penalty=complexity)
            initial_ranking.append({"id":proposal["id"],"family":proposal["family"],
                                    "score":frozen_initial["score"],
                                    "proposal_type":proposal["proposal_type"]})
            self.graph.add_node(proposal)
            family_node=f"FAMILY-{proposal['family']}"
            self.graph.add_node({"id":family_node,"family":proposal["family"],"status":"ACTIVE"})
            self.graph.add_edge(family_node,proposal["id"],"PARENT","Taxonomy membership")
            self.graph.add_edge(proposal["id"],family_node,"CHILD","Taxonomy membership")
            if proposal["family"] == "VOLATILITY":
                self.graph.add_edge(proposal["id"],"HYPOTHESIS-CAL-VOL-PERSISTENCE-V1","REFINES",
                                    "New horizon/threshold after slow-structure falsification")
                self.graph.add_edge(proposal["id"],"HYPOTHESIS-CAL-VOL-PERSISTENCE-V1","REPLACES",
                                    "New specification replaces reuse of rejected candidate")
            if proposal["family"] == "TEMPORAL":
                self.graph.add_edge(proposal["id"],"HYPOTHESIS-CAL-0830-EXPANSION-V1","REFINES",
                                    "Symmetric non-privileged temporal window")
        initial_ranking.sort(key=lambda x:(-x["score"],x["id"]))
        reports=[]; completed_ids=set()
        for record in self.registry.repo.all():
            if record["id"].startswith("HYPOTHESIS-DISC-") and record.get("last_evidence_artifact"):
                reports.append(read_json(self.root/record["last_evidence_artifact"],{})); completed_ids.add(record["id"])
        engine=EvidenceEngine(self.root,bootstrap_resamples=int(self.limits["bootstrap_resamples"]),
                                          permutations=int(self.limits["permutations"]),seed=int(self.limits["seed"]))
        queue=[x for x in proposals if x["id"] not in completed_ids]
        for _iteration in range(min(max(0,int(self.limits["campaign_iterations"])-len(reports)),len(queue))):
            # One highest-value hypothesis per iteration; priorities are recalculated after every result.
            queue.sort(key=lambda x:(-x["initial_research_value"]["score"],x["id"])); hypothesis=queue.pop(0)
            report=engine.evaluate_hypothesis(hypothesis); reports.append(report)
            self.graph.update_status(hypothesis["id"],report["verdict"])
            self.graph.add_node({"id":report["evidence_report_id"],"family":"EVIDENCE","status":"COMPLETED"})
            relation="SUPPORTS" if report["verdict"]=="DEV_SURVIVOR" else "FALSIFIES"
            self.graph.add_edge(report["evidence_report_id"],hypothesis["id"],relation,"Evidence Engine V1 verdict")
            if not any(report["evidence_report_id"] in x.get("evidence_ids",[]) for x in self.memory.all()):
                self.memory.add_knowledge(
                    f"Discovery {hypothesis['family']} {hypothesis['id']} -> {report['verdict']}; {report['rejection_reasons'] or ['passed DEV gates']}",
                    evidence_ids=[report["evidence_report_id"]],confidence=report["evidence_score"]["value"],
                    tags=["discovery-v1",hypothesis["family"].lower(),report["verdict"].lower()])
            for candidate in queue:
                # A resolved family becomes less valuable; contradictory/refinement families retain information value.
                same_family=sum(x["hypothesis_id"].startswith("HYPOTHESIS-DISC") and
                                next((p["family"] for p in proposals if p["id"]==x["hypothesis_id"]),None)==candidate["family"] for x in reports)
                old=candidate["initial_research_value"]["components"]
                candidate["initial_research_value"]=research_value_v2(
                    expected_information_gain=max(.15,old["expected_information_gain"]-.08*same_family),
                    uncertainty_reduction=old["uncertainty_reduction"],novelty=old["novelty"],
                    prior_evidence=min(1,old["prior_evidence"]+.12*same_family),
                    contradiction_value=old["contradiction_value"],economic_relevance=old["economic_relevance"],
                    data_quality=old["data_quality"],estimated_compute_cost=old["estimated_compute_cost"],
                    redundancy_penalty=old["redundancy_penalty"],
                    family_saturation_penalty=min(1,old["family_saturation_penalty"]+.2*same_family),
                    complexity_penalty=old["complexity_penalty"])
        adjusted=benjamini_hochberg([min(1,r["within_hypothesis_adjusted_p"]) for r in reports])
        for report,fdr in zip(reports,adjusted):
            report["campaign_fdr_p_value"]=fdr
            if report["verdict"]=="DEV_SURVIVOR" and fdr>.05:
                report["verdict"]="REJECTED"; report["rejection_reasons"].append("campaign_fdr_failed")
            self.registry.update_status(report["hypothesis_id"],report["verdict"],campaign_fdr_p_value=fdr)
            if report["verdict"]=="DEV_SURVIVOR" and report["evidence_score"]["value"]>=.75:
                record=self.registry.repo.find(lambda x:x["id"]==report["hypothesis_id"])[0]
                artifact=self.root/record["last_evidence_artifact"]
                self.registry.preregister_validation(report["hypothesis_id"],artifact)
                report["verdict"]="VALIDATION_READY"
            self.graph.update_status(report["hypothesis_id"],report["verdict"])
        self.graph.add_node({"id":volatility["diagnostic_id"],"family":"EVIDENCE","status":volatility["conclusion"]})
        self.graph.add_edge(volatility["diagnostic_id"],"HYPOTHESIS-CAL-VOL-PERSISTENCE-V1","FALSIFIES",
                            "Shifted outcomes retained slow structure")
        self.graph.add_edge("HYPOTHESIS-DISC-13-NEAR_HIGH_BREAKS-V1","HYPOTHESIS-DISC-15-NEAR_HIGH_REVERTS-V1",
                            "CONTRADICTS","Same state, opposite action interpretation")
        self.graph.add_edge("HYPOTHESIS-DISC-14-NEAR_LOW_BREAKS-V1","HYPOTHESIS-DISC-16-NEAR_LOW_REVERTS-V1",
                            "CONTRADICTS","Same state, opposite action interpretation")
        report_map={r["hypothesis_id"]:r for r in reports}; family_rejected=Counter(
            next(p["family"] for p in proposals if p["id"]==r["hypothesis_id"]) for r in reports if r["verdict"]=="REJECTED")
        post_ranking=[]
        for proposal in proposals:
            report=report_map[proposal["id"]]; evidence=report["evidence_score"]["value"]
            score=research_value_v2(expected_information_gain=max(.05,1-evidence),uncertainty_reduction=.5,
                novelty=.15,prior_evidence=evidence,contradiction_value=.8 if report["verdict"]=="VALIDATION_READY" else .2,
                economic_relevance=1.0 if proposal["action"]!="WAIT" else .65,data_quality=.9,
                estimated_compute_cost=.35,redundancy_penalty=.9 if report["verdict"]=="REJECTED" else .4,
                family_saturation_penalty=min(1,family_rejected[proposal["family"]]/2),
                complexity_penalty=.5 if proposal["condition"]["type"]=="all" else .2)
            post_ranking.append({"id":proposal["id"],"family":proposal["family"],"score":score["score"],
                                 "status":report["verdict"]})
        post_ranking.sort(key=lambda x:(-x["score"],x["id"]))
        for family in sorted(set(p["family"] for p in proposals)):
            family_reports=[r for r in reports if next(p["family"] for p in proposals if p["id"]==r["hypothesis_id"])==family]
            tag=f"family-consolidation-{family.lower()}"
            if not any(tag in item.get("tags",[]) for item in self.memory.all()):
                rejected=sum(r["verdict"]=="REJECTED" for r in family_reports)
                ready=sum(r["verdict"]=="VALIDATION_READY" for r in family_reports)
                conclusion="NO_PREDICTIVE_INFORMATION_IN_TESTED_REGION" if rejected==len(family_reports) else "DEV_STATISTICAL_CANDIDATE_NOT_VALIDATED"
                self.memory.add_knowledge(f"{family}: {conclusion}; rejected={rejected}, validation_ready={ready}",
                    evidence_ids=[r["evidence_report_id"] for r in family_reports],confidence=.8,
                    tags=["discovery-consolidated",tag,conclusion.lower()])
        for report in reports:
            if report["verdict"]=="VALIDATION_READY" and report["base_rate"]["conditioned"]<=0:
                tag=f"no-trade-{report['hypothesis_id'].lower()}"
                if not any(tag in item.get("tags",[]) for item in self.memory.all()):
                    self.memory.add_knowledge(
                        f"NO_TRADE: {report['hypothesis_id']} improves relative to a worse base rate but conditioned net return remains {report['base_rate']['conditioned']:.10f} <= 0.",
                        evidence_ids=[report["evidence_report_id"]],confidence=.95,
                        tags=["no-trade","relative-predictive-information",tag])
        knowledge={"known":[f"{r['hypothesis_id']} rejected: {', '.join(r['rejection_reasons'])}" for r in reports if r["verdict"]=="REJECTED"],
                   "no_trade":[r["hypothesis_id"] for r in reports if r["verdict"]=="VALIDATION_READY" and r["base_rate"]["conditioned"]<=0],
                   "unknown":["Whether effects rejected by shifted controls reflect slow structure or causal information",
                              "Cross-broker generalization","Full-history tick execution costs"],
                   "open_contradictions":["Raw significance can coexist with failed shifted-outcome controls"],
                   "most_valuable_next_data":"Independent broker M1/ticks or a DEV-only slow-volatility causal control"}
        scientific_proposals=[{key:p[key] for key in ("id","family","target_variable","condition","action","expected_direction",
                              "minimum_effect","planned_comparisons","parameter_neighbors")} for p in proposals]
        summary={"campaign_id":self.limits["campaign_id"],"campaign_hash":content_hash({"limits":self.limits,"proposals":scientific_proposals}),
                 "seed":self.limits["seed"],"partition":"DEV","validation_inspected":False,"locked_oos_inspected":False,
                 "proposed":len(proposals),"executed":len(reports),"family_distribution":dict(Counter(x["family"] for x in proposals)),
                 "initial_ranking":initial_ranking,"post_campaign_ranking":post_ranking,"reports":reports,
                 "volatility_diagnostic":{**volatility,"proposal_type":"RETEST_WITH_NEW_EVIDENCE"},"intraday_structure":intraday,"knowledge_update":knowledge,
                 "status_counts":dict(Counter(x["verdict"] for x in reports)),"hypothesis_graph":"hypotheses/graph.json"}
        atomic_write_json(self.root/"reports/evidence/PROMPT_5_DISCOVERY_CAMPAIGN.json",summary)
        states=StateStore(self.root/"state"); current=states.load_all()
        counts={scale:len(JsonRepository(self.root/"memory_db"/scale/"records.json").all()) for scale in ("working","episodic","semantic","long_term")}
        states.save("memory_state",{**current["memory_state"],"counts":counts})
        states.save("research_state",{**current["research_state"],"discovery_campaign":summary["campaign_id"],
                    "discovery_status_counts":summary["status_counts"],"validation_inspected":False,"locked_oos_inspected":False})
        states.save("value_model_state",{**current["value_model_state"],"version":"v2-discovery-research-priority",
                    "trained":False,"post_campaign_priorities":post_ranking})
        return summary
