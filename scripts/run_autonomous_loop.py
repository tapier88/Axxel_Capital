"""Run exactly one safe autonomous research iteration."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.orchestrator.agent_loop import AutonomousLoop


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--question", help="Research question; creates a new hypothesis")
    parser.add_argument("--root", type=Path, default=PROJECT_ROOT, help="Persistence root")
    args = parser.parse_args()
    result = AutonomousLoop(args.root).run_iteration(args.question)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
