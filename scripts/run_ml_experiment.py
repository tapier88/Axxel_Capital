"""Run the frozen first native AXXEL ML experiment."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.research.discovery_engine import DiscoveryEngine


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config/ml_xauusd_0830_v1.json")
    args = parser.parse_args()
    result = DiscoveryEngine(ROOT).run_ml_candidate(ROOT / args.config)
    print(json.dumps({"verdict": result["verdict"], "report_path": result["report_path"],
                      "models": {k: {"balanced_accuracy": v["balanced_accuracy"], "log_loss": v["log_loss"]}
                                 for k, v in result["models"].items()},
                      "ensemble": result["ensemble"], "skeptic": result["skeptic"]}, indent=2))


if __name__ == "__main__":
    main()
