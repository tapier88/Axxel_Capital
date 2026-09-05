"""Audit canonical GOLD M1 and tick Parquet datasets."""

from __future__ import annotations
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
from src.data.quality_v2 import audit_parquet

if __name__ == "__main__":
    m1 = next((PROJECT_ROOT / "data/raw/gold_m1").rglob("*.parquet"))
    ticks = next((PROJECT_ROOT / "data/raw/gold_ticks").rglob("*.parquet"))
    result = audit_parquet(m1, ticks, PROJECT_ROOT / "reports/gold_m1_ticks_quality_v2.json")
    print(json.dumps(result, indent=2, ensure_ascii=False))
