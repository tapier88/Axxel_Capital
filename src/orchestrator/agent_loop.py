"""One complete, persistent and non-trading autonomous research iteration."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from src.execution.execution_engine import execute_dry_run
from src.experience_store.repository import JsonRepository
from src.experience_store.store import ExperienceStore
from src.experience_store.market_store import MarketExperienceStore
from src.experience_store.parquet_store import ParquetExperienceStore
from src.memory.consolidation import consolidate_memory
from src.memory.episodic_memory import EpisodicMemory
from src.memory.retrieval import retrieve_relevant
from src.memory.working_memory import WorkingMemory
from src.orchestrator.state_machine import StateStore, utc_now
from src.research.experiment_engine import ExperimentEngine
from src.research.hypothesis_engine import HypothesisEngine
from src.research.uncertainty_engine import uncertainty_score
from src.utils.ids import new_id
from src.utils.serialization import read_json
from src.validation.protocol import validate_dry_run
from src.value.information_value import information_value
from src.value.research_value import research_value


class AutonomousLoop:
    def __init__(self, project_root: Path | str):
        self.root = Path(project_root)
        self.states = StateStore(self.root / "state")
        self.hypotheses = HypothesisEngine(self.root / "hypotheses")
        self.experiments = ExperimentEngine(self.root / "experiments")
        self.experience = ExperienceStore(self.root / "experience_store")
        self.memory_root = self.root / "memory_db"

    def run_iteration(self, question: str | None = None) -> dict[str, Any]:
        policy = read_json(self.root / "config" / "runtime_policy.json", {
            "memory": {"min_evidence": 2, "long_term_threshold": 4},
            "value": {"weights": {"uncertainty": 0.35, "information": 0.40, "reproducibility": 0.25}, "dry_run_cost": 0.05},
        })
        all_states = self.states.initialize()
        agent = all_states["agent_state"]
        if agent["mode"] != "RESEARCH_ONLY" or agent["live_trading"] or agent["automatic_promotion_to_live"]:
            raise PermissionError("Unsafe state: autonomous V0 is research-only")

        iteration = int(agent["iteration"]) + 1
        run_id = f"RUN-{new_id('EXPERIMENT').split('-', 1)[1]}"
        active = self.hypotheses.latest_active()
        if question or active is None:
            query = question or "Can the research system complete a traceable dry-run?"
            active = self.hypotheses.create(
                query, tags=["system", "dry-run"],
                uncertainties=["No market dataset has been supplied", "No edge is claimed"],
            )
        else:
            query = active["question"]

        retrieved = retrieve_relevant(query, memory_root=self.memory_root, experience_root=self.root / "experience_store")
        before = uncertainty_score(active, retrieved)
        experiment = self.experiments.create(active, [item["id"] for item in retrieved])
        raw_result = execute_dry_run(experiment, mode=agent["mode"])
        validation = validate_dry_run(active, experiment, raw_result)
        result = {**raw_result, "validation": validation}
        saved_experiment = self.experiments.save_result(experiment["id"], result)

        after = round(max(0.0, before - (0.12 if validation["passed"] else 0.0)), 6)
        info = information_value(before, after, reusable_evidence=validation["passed"])
        value = research_value(
            uncertainty=before, information=info, reproducibility=1.0,
            cost=float(policy["value"]["dry_run_cost"]), weights=policy["value"]["weights"],
        )
        episode = self.experience.create_episode(
            state={"iteration": iteration, "mode": agent["mode"], "uncertainty": before},
            action={"type": "DRY_RUN", "experiment_id": experiment["id"]}, outcome=result,
            hypothesis_id=active["id"], experiment_id=experiment["id"],
            confidence=0.65 if validation["passed"] else 0.2, tags=active.get("tags", []),
        )
        episodic = EpisodicMemory(self.memory_root).remember_episode(episode)
        WorkingMemory(self.memory_root).remember(
            f"Iteration {iteration} completed for {active['id']} with value {value}",
            evidence_ids=[episode["id"]], tags=active.get("tags", []),
        )
        consolidated = consolidate_memory(
            self.memory_root, min_evidence=int(policy["memory"]["min_evidence"]),
            long_term_threshold=int(policy["memory"]["long_term_threshold"]),
        )
        counts = {
            scale: len(JsonRepository(self.memory_root / scale / "records.json").all())
            for scale in ("working", "episodic", "semantic", "long_term")
        }

        self.states.save("agent_state", {**agent, "status": "idle", "iteration": iteration, "last_run_id": run_id})
        self.states.save("research_state", {
            **all_states["research_state"], "active_hypothesis": active["id"],
            "hypothesis_count": len(self.hypotheses.repository.all()), "uncertainties": active["uncertainties"],
        })
        self.states.save("experiment_state", {
            **all_states["experiment_state"], "running": None, "last_experiment": experiment["id"],
            "experiment_count": len(self.experiments.repository.all()),
        })
        self.states.save("memory_state", {
            **all_states["memory_state"],
            "last_consolidation": utc_now() if consolidated else all_states["memory_state"]["last_consolidation"],
            "counts": counts,
        })
        value_state = all_states["value_model_state"]
        self.states.save("value_model_state", {
            **value_state, "version": "v0-heuristic",
            "model_version_id": value_state.get("model_version_id") or new_id("MODEL_VERSION"), "trained": False,
            "last_scores": {"uncertainty_before": before, "uncertainty_after": after,
                            "information_value": info, "research_value": value},
        })
        return {
            "run_id": run_id, "hypothesis": active, "experiment": saved_experiment,
            "episode": episode, "episodic_memory": episodic, "retrieved_count": len(retrieved),
            "consolidated": consolidated,
            "scores": {"uncertainty": before, "information": info, "research": value}, "safety": validation,
        }

    def run_market_iteration(self, *, symbol: str = "XAUUSD") -> dict[str, Any]:
        """Consume real counterfactual experiences without evaluating an edge."""
        all_states = self.states.initialize()
        agent = all_states["agent_state"]
        if agent["mode"] != "RESEARCH_ONLY" or agent["live_trading"] or agent["automatic_promotion_to_live"]:
            raise PermissionError("Unsafe state: market iteration is research-only")
        market_store = MarketExperienceStore(self.root / "experience_store")
        dev_records = market_store.query(symbol=symbol, allow_locked=False)
        dev_records = [item for item in dev_records if item["partition"] == "DEV"]
        if not dev_records:
            raise ValueError(f"No DEV market experiences available for {symbol}")
        seed = dev_records[len(dev_records)//2]
        similar = market_store.similar(seed["state"], symbol=symbol, limit=10, partitions=("DEV",))
        question = f"Can {symbol} market experiences be retrieved and replayed without temporal leakage?"
        matching = self.hypotheses.repository.find(
            lambda item: item.get("status") == "ACTIVE" and item.get("question") == question
        )
        hypothesis = matching[-1] if matching else self.hypotheses.create(
            question, tags=[symbol.lower(), "market-experience", "data-quality"],
            uncertainties=["No spread/bid/ask in source", "H1 cannot resolve 5m/15m/30m labels", "No edge is being evaluated"],
        )
        memories = retrieve_relevant(question, memory_root=self.memory_root, experience_root=self.root / "experience_store")
        experience_ids = [item["experience_id"] for item in similar]
        experiment = self.experiments.create(hypothesis, [item["id"] for item in memories], experience_ids)
        raw_result = execute_dry_run(experiment, mode=agent["mode"])
        raw_result["uncertainties"] = [
            "No spread/bid/ask: LONG/SHORT tradable returns are unavailable",
            "H1 source cannot resolve 5m/15m/30m outcomes",
        ]
        raw_result["analysis"] = {
            "type": "MARKET_EXPERIENCE_RETRIEVAL_REPLAY", "symbol": symbol,
            "seed_experience_id": seed["experience_id"], "experience_ids": experience_ids,
            "replayed_hash_valid": all(market_store.replay(item)["hash_valid"] for item in experience_ids),
            "partitions_accessed": sorted({item["partition"] for item in similar}),
            "locked_oos_accessed": False, "market_edge_tested": False,
        }
        validation = validate_dry_run(hypothesis, experiment, raw_result)
        validation["checks"]["replay_hashes_valid"] = raw_result["analysis"]["replayed_hash_valid"]
        validation["checks"]["locked_oos_excluded"] = not raw_result["analysis"]["locked_oos_accessed"]
        validation["passed"] = all(validation["checks"].values())
        result = {**raw_result, "validation": validation}
        saved_experiment = self.experiments.save_result(experiment["id"], result)
        iteration = int(agent["iteration"]) + 1
        episode = self.experience.create_episode(
            state={"iteration": iteration, "mode": agent["mode"], "symbol": symbol,
                   "seed_experience_id": seed["experience_id"]},
            action={"type": "ANALYZE_MARKET_EXPERIENCES", "experiment_id": experiment["id"]},
            outcome=result, hypothesis_id=hypothesis["id"], experiment_id=experiment["id"],
            confidence=0.8 if validation["passed"] else 0.2,
            tags=hypothesis["tags"], experience_ids=experience_ids,
        )
        episodic = EpisodicMemory(self.memory_root).remember_episode(episode)
        WorkingMemory(self.memory_root).remember(
            f"Real {symbol} experience retrieval/replay completed with {len(experience_ids)} DEV records",
            evidence_ids=[episode["id"], *experience_ids], tags=hypothesis["tags"],
        )
        consolidated = consolidate_memory(self.memory_root)
        counts = {scale: len(JsonRepository(self.memory_root / scale / "records.json").all())
                  for scale in ("working", "episodic", "semantic", "long_term")}
        run_id = f"RUN-{new_id('EXPERIMENT').split('-', 1)[1]}"
        self.states.save("agent_state", {**agent, "iteration": iteration, "last_run_id": run_id, "status": "idle"})
        self.states.save("research_state", {**all_states["research_state"], "active_hypothesis": hypothesis["id"],
                         "hypothesis_count": len(self.hypotheses.repository.all()), "uncertainties": hypothesis["uncertainties"]})
        self.states.save("experiment_state", {**all_states["experiment_state"], "running": None,
                         "last_experiment": experiment["id"], "experiment_count": len(self.experiments.repository.all())})
        self.states.save("memory_state", {**all_states["memory_state"], "counts": counts,
                         "last_consolidation": utc_now() if consolidated else all_states["memory_state"]["last_consolidation"]})
        return {"run_id": run_id, "hypothesis": hypothesis, "experiment": saved_experiment,
                "episode": episode, "episodic_memory": episodic, "similar_experiences": similar,
                "consolidated": consolidated, "safety": validation}

    def run_market_v2_iteration(self) -> dict[str, Any]:
        """One traceable V2 research iteration over real M1 data, never orders."""
        policy = read_json(self.root / "config/runtime_policy.json", {
            "memory": {"min_evidence": 2, "long_term_threshold": 4},
            "value": {"weights": {"uncertainty": 0.35, "information": 0.40, "reproducibility": 0.25}, "dry_run_cost": 0.05},
        })
        states = self.states.initialize()
        agent = states["agent_state"]
        if agent["mode"] != "RESEARCH_ONLY" or agent["live_trading"] or agent["automatic_promotion_to_live"]:
            raise PermissionError("Unsafe state: V2 market iteration is research-only")

        store = ParquetExperienceStore(self.root)
        seed_frame = store.query(partitions=("DEV",), action="WAIT", limit=1)
        if seed_frame.empty:
            raise ValueError("No DEV records in Experience Store V2")
        seed = seed_frame.iloc[0]
        state = {name: seed[name] for name in seed.index if name.startswith("state_") and isinstance(seed[name], (int, float))}
        similar = store.similar(state, limit=10, partition="DEV")
        experience_ids = [item["experience_id"] for item in similar]
        replay_valid = all(store.replay(item)["hash_valid"] for item in experience_ids)
        question = "Can real GOLD M1 experiences be retrieved and replayed causally from DEV without opening LOCKED_OOS?"
        matching = self.hypotheses.repository.find(
            lambda item: item.get("status") == "ACTIVE" and item.get("question") == question
        )
        hypothesis = matching[-1] if matching else self.hypotheses.create(
            question, tags=["gold", "m1", "market-experience-v2", "data-quality"],
            uncertainties=[
                "Full-history tick bid/ask is unavailable; most costs use an explicit spread proxy",
                "Slippage is unavailable and remains null",
                "No market edge is tested or claimed",
            ],
        )
        memories = retrieve_relevant(question, memory_root=self.memory_root, experience_root=self.root / "experience_store")
        before = uncertainty_score(hypothesis, memories)
        experiment = self.experiments.create(hypothesis, [x["id"] for x in memories], experience_ids)
        raw = execute_dry_run(experiment, mode=agent["mode"])
        raw["analysis"] = {
            "type": "MARKET_EXPERIENCE_V2_RETRIEVAL_REPLAY",
            "dataset_version": store.dataset_version,
            "experience_ids": experience_ids,
            "replayed_hash_valid": replay_valid,
            "partitions_accessed": ["DEV"],
            "locked_oos_accessed": False,
            "market_edge_tested": False,
            "orders_created": 0,
        }
        validation = validate_dry_run(hypothesis, experiment, raw)
        validation["checks"].update({
            "replay_hashes_valid": replay_valid,
            "locked_oos_excluded": True,
            "dataset_files_intact": all(store.verify_files().values()),
        })
        validation["passed"] = all(validation["checks"].values())
        result = {**raw, "validation": validation}
        saved_experiment = self.experiments.save_result(experiment["id"], result)

        after = round(max(0.0, before - (0.15 if validation["passed"] else 0.0)), 6)
        info = information_value(before, after, reusable_evidence=validation["passed"])
        value = research_value(
            uncertainty=before, information=info, reproducibility=1.0 if replay_valid else 0.0,
            cost=float(policy["value"]["dry_run_cost"]), weights=policy["value"]["weights"],
        )
        iteration = int(agent["iteration"]) + 1
        episode = self.experience.create_episode(
            state={"iteration": iteration, "mode": agent["mode"], "dataset_version": store.dataset_version,
                   "seed_experience_id": str(seed["experience_id"])},
            action={"type": "RETRIEVE_REPLAY_MARKET_V2", "experiment_id": experiment["id"]},
            outcome={**result, "value_v0": {"uncertainty_before": before, "uncertainty_after": after,
                                             "information_value": info, "research_value": value}},
            hypothesis_id=hypothesis["id"], experiment_id=experiment["id"],
            confidence=0.85 if validation["passed"] else 0.2,
            tags=hypothesis["tags"], experience_ids=experience_ids,
        )
        episodic = EpisodicMemory(self.memory_root).remember_episode(episode)
        WorkingMemory(self.memory_root).remember(
            f"V2 real GOLD M1 replay validated for {len(experience_ids)} DEV experiences; LOCKED_OOS remained closed",
            evidence_ids=[episode["id"], *experience_ids], tags=hypothesis["tags"],
        )
        consolidated = consolidate_memory(
            self.memory_root, min_evidence=int(policy["memory"]["min_evidence"]),
            long_term_threshold=int(policy["memory"]["long_term_threshold"]),
        )
        counts = {scale: len(JsonRepository(self.memory_root / scale / "records.json").all())
                  for scale in ("working", "episodic", "semantic", "long_term")}
        run_id = f"RUN-{new_id('EXPERIMENT').split('-', 1)[1]}"
        self.states.save("agent_state", {**agent, "iteration": iteration, "last_run_id": run_id, "status": "idle"})
        self.states.save("research_state", {**states["research_state"], "active_hypothesis": hypothesis["id"],
                         "hypothesis_count": len(self.hypotheses.repository.all()), "uncertainties": hypothesis["uncertainties"]})
        self.states.save("experiment_state", {**states["experiment_state"], "running": None,
                         "last_experiment": experiment["id"], "experiment_count": len(self.experiments.repository.all())})
        self.states.save("memory_state", {**states["memory_state"], "counts": counts,
                         "last_consolidation": utc_now() if consolidated else states["memory_state"]["last_consolidation"]})
        value_state = states["value_model_state"]
        self.states.save("value_model_state", {**value_state, "version": "v0-heuristic",
                         "model_version_id": value_state.get("model_version_id") or new_id("MODEL_VERSION"),
                         "trained": False, "last_scores": {"uncertainty_before": before,
                         "uncertainty_after": after, "information_value": info, "research_value": value}})
        return {"run_id": run_id, "dataset_version": store.dataset_version, "hypothesis": hypothesis,
                "experiment": saved_experiment, "episode": episode, "episodic_memory": episodic,
                "experience_ids": experience_ids, "consolidated": consolidated,
                "scores": {"uncertainty": before, "information": info, "research": value}, "safety": validation}
