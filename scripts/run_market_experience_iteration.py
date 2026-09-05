"""Run one safe autonomous iteration over real stored market experiences."""

from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
from src.orchestrator.agent_loop import AutonomousLoop

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--symbol", default="XAUUSD")
    args = parser.parse_args()
    result = AutonomousLoop(PROJECT_ROOT).run_market_iteration(symbol=args.symbol)
    summary = {key: result[key] for key in ("run_id", "hypothesis", "experiment", "episode", "consolidated", "safety")}
    summary["similar_experience_ids"] = [item["experience_id"] for item in result["similar_experiences"]]
    print(json.dumps(summary, indent=2, ensure_ascii=False))
