"""Replay one stored counterfactual experience and verify its content hash."""

from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
from src.experience_store.market_store import MarketExperienceStore

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("experience_id")
    args = parser.parse_args()
    print(json.dumps(MarketExperienceStore(PROJECT_ROOT / "experience_store").replay(args.experience_id), indent=2, ensure_ascii=False))
