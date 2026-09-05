"""Run one research-only retrieval/replay iteration against Experience Store V2."""

from __future__ import annotations

import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.orchestrator.agent_loop import AutonomousLoop


if __name__ == "__main__":
    result = AutonomousLoop(PROJECT_ROOT).run_market_v2_iteration()
    print(json.dumps({
        "run_id": result["run_id"],
        "dataset_version": result["dataset_version"],
        "hypothesis_id": result["hypothesis"]["id"],
        "experiment_id": result["experiment"]["id"],
        "episode_id": result["episode"]["id"],
        "experience_ids": result["experience_ids"],
        "scores": result["scores"],
        "safety": result["safety"],
    }, indent=2, ensure_ascii=False))
