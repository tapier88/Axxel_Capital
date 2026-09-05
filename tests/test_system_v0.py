from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from src.execution.execution_engine import execute_dry_run
from src.experience_store.store import ExperienceStore
from src.memory.consolidation import consolidate_memory
from src.memory.episodic_memory import EpisodicMemory
from src.memory.retrieval import retrieve_relevant
from src.orchestrator.agent_loop import AutonomousLoop
from src.orchestrator.state_machine import StateStore
from src.research.experiment_engine import ExperimentEngine
from src.research.hypothesis_engine import HypothesisEngine
from src.utils.ids import new_id
from src.value.information_value import information_value
from src.value.research_value import research_value


class SystemV0Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_state_persistence_and_safe_defaults(self) -> None:
        store = StateStore(self.root / "state")
        state = store.initialize()["agent_state"]
        self.assertEqual(state["mode"], "RESEARCH_ONLY")
        state["iteration"] = 7
        store.save("agent_state", state)
        self.assertEqual(StateStore(self.root / "state").load("agent_state")["iteration"], 7)

    def test_unique_traceable_ids(self) -> None:
        for kind in ("HYPOTHESIS", "EXPERIMENT", "EPISODE", "MEMORY", "MODEL_VERSION", "EXPERIENCE", "SESSION", "DATASET"):
            first, second = new_id(kind), new_id(kind)
            self.assertTrue(first.startswith(kind + "-"))
            self.assertNotEqual(first, second)

    def test_hypothesis_experiment_episode_creation(self) -> None:
        hypothesis = HypothesisEngine(self.root / "hypotheses").create("Does X explain Y?")
        experiment_engine = ExperimentEngine(self.root / "experiments")
        experiment = experiment_engine.create(hypothesis, [])
        episode = ExperienceStore(self.root / "experience_store").create_episode(
            state={"mode": "RESEARCH_ONLY"}, action={"type": "DRY_RUN"},
            outcome={"status": "DONE"}, hypothesis_id=hypothesis["id"],
            experiment_id=experiment["id"], confidence=0.5,
        )
        self.assertEqual(experiment["hypothesis_id"], hypothesis["id"])
        self.assertEqual(episode["experiment_id"], experiment["id"])

    def test_retrieval_finds_relevant_memory(self) -> None:
        hypothesis = HypothesisEngine(self.root / "hypotheses").create("gold london volatility", tags=["gold"])
        experiment = ExperimentEngine(self.root / "experiments").create(hypothesis, [])
        episode = ExperienceStore(self.root / "experience_store").create_episode(
            state={}, action={}, outcome={"summary": "gold volatility in london"},
            hypothesis_id=hypothesis["id"], experiment_id=experiment["id"], confidence=0.8, tags=["gold", "london"],
        )
        EpisodicMemory(self.root / "memory_db").remember_episode(episode)
        results = retrieve_relevant("gold london", memory_root=self.root / "memory_db", experience_root=self.root / "experience_store")
        self.assertTrue(results)
        self.assertGreater(results[0]["relevance"], 0)

    def test_consolidation_requires_multiple_episodes(self) -> None:
        episodic = EpisodicMemory(self.root / "memory_db")
        for index in range(2):
            episodic.remember_episode({
                "id": new_id("EPISODE"), "hypothesis_id": "HYPOTHESIS-shared",
                "experiment_id": f"EXPERIMENT-{index}", "outcome": {"summary": "consistent dry result"},
                "confidence": 0.8, "tags": ["shared"],
            })
        created = consolidate_memory(self.root / "memory_db", min_evidence=2)
        self.assertEqual(len(created), 1)
        self.assertEqual(len(created[0]["evidence_ids"]), 2)

    def test_value_v0_is_bounded(self) -> None:
        info = information_value(0.8, 0.5, reusable_evidence=True)
        value = research_value(uncertainty=0.8, information=info, reproducibility=1.0, cost=0.1)
        self.assertGreater(info, 0)
        self.assertGreaterEqual(value, 0)
        self.assertLessEqual(value, 1)

    def test_execution_rejects_non_research_mode(self) -> None:
        with self.assertRaises(PermissionError):
            execute_dry_run({"id": "EXPERIMENT-test"}, mode="LIVE")

    def test_complete_autonomous_iteration(self) -> None:
        result = AutonomousLoop(self.root).run_iteration("Can persistence be traced?")
        self.assertTrue(result["safety"]["passed"])
        self.assertFalse(result["safety"]["edge_validated"])
        self.assertEqual(result["experiment"]["status"], "COMPLETED")
        self.assertEqual(StateStore(self.root / "state").load("agent_state")["iteration"], 1)
        self.assertEqual(json.loads((self.root / "experience_store" / "episodes.json").read_text())[0]["id"], result["episode"]["id"])


if __name__ == "__main__":
    unittest.main()
