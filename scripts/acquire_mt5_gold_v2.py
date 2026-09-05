"""Acquire GOLD M1 2015-2024 and a bounded real-tick sample without trading."""

from __future__ import annotations
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.data.mt5_acquisition import MT5ReadOnlyAcquirer, persist_parquet_dataset


if __name__ == "__main__":
    raise PermissionError("Mixed-history acquisition disabled before MT5 access. Use a bounded Data Engine source.")
    with MT5ReadOnlyAcquirer("GOLD") as source:
        metadata = source.source_metadata()
        rates = source.rates_m1(
            datetime(2015, 1, 1, tzinfo=timezone.utc),
            datetime(2025, 1, 1, tzinfo=timezone.utc),
        )
        rates_manifest = persist_parquet_dataset(
            rates, project_root=PROJECT_ROOT, category="gold_m1",
            source_id=metadata["source_id"], metadata=metadata,
            transformations=["monthly range concatenation", "duplicate chunk boundaries removed", "POSIX seconds converted to UTC"],
        )
        ticks = source.ticks(
            datetime(2024, 1, 2, 13, 0, tzinfo=timezone.utc),
            datetime(2024, 1, 2, 18, 30, tzinfo=timezone.utc),
        )
        tick_metadata = {**metadata, "source_id": "MT5-XMGLOBAL-GOLD-TICKS-SAMPLE-V1",
                         "sample_scope": "One bounded session plus 60-minute outcome buffer; not full-history ticks"}
        ticks_manifest = persist_parquet_dataset(
            ticks, project_root=PROJECT_ROOT, category="gold_ticks",
            source_id=tick_metadata["source_id"], metadata=tick_metadata,
            transformations=["POSIX milliseconds converted to UTC", "mid/spread_price/spread_points derived from bid/ask"],
        )
    print(json.dumps({"m1": rates_manifest, "ticks": ticks_manifest}, indent=2, ensure_ascii=False))
