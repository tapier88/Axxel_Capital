"""Certify an explicitly bounded DEV source, or import safe legacy DEV rowgroups."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.data.engine import DataEngine
from src.utils.serialization import read_json


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config/data_engine_xauusd_m1_v1.json")
    parser.add_argument("--build-experiences", action="store_true")
    args = parser.parse_args()
    config = read_json(ROOT / args.config, {})
    engine = DataEngine(ROOT)
    result = engine.ingest_parquet(ROOT / config["source"], config["metadata"],
                                   legacy_dev_rowgroups=config.get("legacy_dev_rowgroups", False))
    if args.build_experiences:
        engine.build_experiences(result["dataset_id"])
    print(json.dumps({key: result[key] for key in ("dataset_id", "status", "rows", "from", "to", "quality")}, indent=2))


if __name__ == "__main__":
    main()
