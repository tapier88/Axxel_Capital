from __future__ import annotations

import unittest
from pathlib import Path

import pandas as pd

from src.data.pipeline_v2 import HORIZONS, build_feature_label_frame
from src.experience_store.parquet_store import ParquetExperienceStore
from src.utils.hashing import file_hash
from src.utils.serialization import read_json


PROJECT_ROOT = Path(__file__).resolve().parents[2]


class MarketV2MechanicsTests(unittest.TestCase):
    def test_features_are_causal_and_labels_have_exact_horizons(self) -> None:
        timestamps = pd.date_range("2024-01-02T12:00:00Z", periods=200, freq="min")
        close = pd.Series(range(200), dtype=float) / 100 + 2000
        bars = pd.DataFrame({
            "symbol": "GOLD", "timestamp_utc": timestamps, "open": close,
            "high": close + 0.2, "low": close - 0.2, "close": close,
            "tick_volume": 10, "spread": 30, "real_volume": 0,
        })
        featured = build_feature_label_frame(bars, 0.01)
        row = featured.iloc[0]
        self.assertLess(row["state_max_source_timestamp_utc"], row["decision_timestamp_utc"])
        for horizon in HORIZONS:
            self.assertEqual(
                row[f"label_source_timestamp_{horizon}m"] - row["state_max_source_timestamp_utc"],
                pd.Timedelta(minutes=horizon),
            )
        self.assertEqual(row["state_information_boundary"], "FEATURES_AVAILABLE_AT_DECISION_TIME")
        self.assertEqual(row["outcome_information_boundary"], "FUTURE INFORMATION — LABEL ONLY")


class MarketV2ArtifactTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        import tempfile
        from tests.data_quality.test_data_engine import certify
        cls.temporary = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temporary.name)
        engine, parent = certify(cls.root)
        engine.build_experiences(parent["dataset_id"])
        cls.store = ParquetExperienceStore(cls.root)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temporary.cleanup()

    def test_manifest_counts_and_three_separate_partitions(self) -> None:
        manifest = self.store.manifest
        self.assertGreater(manifest["total_experiences"], 0)
        self.assertEqual(set(manifest["files"]), {"DEV"})
        self.assertEqual(sum(manifest["experience_counts"].values()), manifest["total_experiences"])

    def test_source_and_dataset_files_are_content_addressed(self) -> None:
        self.assertTrue(all(self.store.verify_files().values()))
        self.assertEqual(set(self.store.verify_files()), {"DEV"})
        parent = self.store.data_engine.manifest(self.store.manifest["data_engine_dataset_id"])
        self.assertEqual(parent["partition"], "DEV")
        self.assertFalse(parent["locked_oos_opened"])

    def test_locked_oos_requires_explicit_capability(self) -> None:
        with self.assertRaises(PermissionError):
            self.store.query(partitions=("LOCKED_OOS",), limit=1)
        with self.assertRaises(PermissionError):
            self.store.query(partitions=("LOCKED_OOS",), limit=1, allow_locked=True)
        with self.assertRaises(PermissionError):
            self.store.verify_files(include_locked=True)

    def test_replay_reconstructs_and_validates_record_hash(self) -> None:
        record = self.store.query(partitions=("DEV",), action="WAIT", limit=1).iloc[0]
        replay = self.store.replay(record["experience_id"])
        self.assertTrue(replay["hash_valid"])
        self.assertEqual(replay["experience"]["experience_id"], record["experience_id"])

    def test_actions_costs_and_horizons_are_explicit(self) -> None:
        wait = self.store.query(partitions=("DEV",), action="WAIT", limit=1).iloc[0]
        long = self.store.query(partitions=("DEV",), action="LONG", limit=1).iloc[0]
        self.assertTrue(wait["counterfactual"] and not wait["execution_real"])
        self.assertEqual(wait["cost_method_5m"], "NO_POSITION")
        self.assertIn(long["cost_method_5m"], {"PROXY_COST", "REAL_TICK_COST"})
        self.assertEqual(long["cost_slippage_status"], "UNAVAILABLE_NOT_ASSUMED_ZERO")
        for horizon in HORIZONS:
            self.assertIn(f"outcome_tradable_return_{horizon}m", long.index)

    def test_research_window_is_preserved_without_prefiltering_states(self) -> None:
        rows = self.store.query(
            partitions=("DEV",), action="WAIT",
            columns=["state_minute_of_session", "timestamp_cot", "state_regime_v0"],
        )
        self.assertEqual(int(rows["state_minute_of_session"].min()), 0)
        self.assertEqual(int(rows["state_minute_of_session"].max()), 140)
        self.assertGreater(rows["state_regime_v0"].nunique(), 1)


if __name__ == "__main__":
    unittest.main()
