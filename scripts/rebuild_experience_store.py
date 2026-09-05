"""Rebuild and verify a market Experience Store from an immutable raw file."""

from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
from src.data.pipeline import build_experience_dataset

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("raw_path", type=Path)
    args = parser.parse_args()
    print(json.dumps(build_experience_dataset(PROJECT_ROOT, args.raw_path.resolve()), indent=2, ensure_ascii=False))
