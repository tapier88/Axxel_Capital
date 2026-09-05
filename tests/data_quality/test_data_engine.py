"""Synthetic, isolated data only. No live broker or historical holdout I/O."""
import json
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest

from src.data.engine import DataEngine
from src.data.pipeline_v2 import build_feature_label_frame
from src.data.quality import normalize_and_validate
from src.experience_store.parquet_store import ParquetExperienceStore
from src.ml.data import DevOnlyMLData
from src.utils.serialization import atomic_write_json


META = dict(source_id="SYNTHETIC", broker="TEST", symbol_exact="GOLD", symbol_international="XAUUSD",
            timeframe="M1", timezone="UTC", point=.01, digits=2, timestamp_semantics="BAR_OPEN")
POLICY = {"frozen": True, "created_before_outcome_analysis": True, "DEV":
          {"from": "2015-01-01T00:00:00Z", "to_exclusive": "2020-01-01T00:00:00Z"}}


def bars():
    price = 2000 + np.arange(200) * .01
    return pd.DataFrame(dict(timestamp_utc=pd.date_range("2016-01-04T12:00:00Z", periods=200, freq="min"),
                             symbol="GOLD", open=price, high=price+.1, low=price-.1, close=price,
                             spread=20, tick_volume=100, real_volume=0))


def certify(root, frame=None, metadata=None):
    root.mkdir(parents=True, exist_ok=True)
    atomic_write_json(root / "config/partitions_gold_m1_v2.json", POLICY)
    source = root / "source.parquet"
    (bars() if frame is None else frame).to_parquet(source, index=False, row_group_size=100)
    engine = DataEngine(root)
    manifest = engine.ingest_parquet(source, metadata or META)
    return engine, manifest


def test_reproducible_idempotent_bytes_and_logical_hash(tmp_path):
    engine, first = certify(tmp_path / "one")
    second = engine.ingest_parquet(tmp_path / "one/source.parquet", META)
    _, third = certify(tmp_path / "two")
    assert first == second == third
    assert len(engine.query(first["dataset_id"])) == 200
    assert engine.query(first["dataset_id"], columns=["close"], limit=3).shape == (3, 1)


@pytest.mark.parametrize("artifact", ["raw", "silver", "bronze", "findings", "quality"])
def test_artifact_tampering_fails_closed(tmp_path, artifact):
    engine, manifest = certify(tmp_path)
    path = tmp_path / manifest["artifacts"][artifact]["path"]
    with path.open("ab") as handle:
        handle.write(b"corruption")
    with pytest.raises(PermissionError):
        engine.query(manifest["dataset_id"])


def test_raw_snapshot_is_exact_and_independent_of_source(tmp_path):
    engine, result = certify(tmp_path)
    raw = tmp_path / result["artifacts"]["raw"]["path"]
    assert raw.read_bytes() == (tmp_path / "source.parquet").read_bytes()
    (tmp_path / "source.parquet").write_bytes(b"source changed")
    assert len(engine.query(result["dataset_id"])) == 200


@pytest.mark.parametrize("partition", ["VALIDATION", "LOCKED_OOS", "../DEV"])
def test_denial_precedes_any_parquet_open(tmp_path, partition):
    atomic_write_json(tmp_path / "config/partitions_gold_m1_v2.json", POLICY)
    engine = DataEngine(tmp_path)
    with patch("src.data.engine.pq.ParquetFile", side_effect=AssertionError("No open permitted")):
        with pytest.raises(PermissionError):
            engine.ingest_parquet("not-opened", META, partition=partition)


def test_mixed_rowgroup_cannot_be_filtered_into_dev(tmp_path):
    frame = bars()
    frame.loc[199, "timestamp_utc"] = pd.Timestamp("2023-01-01T00:00Z")
    atomic_write_json(tmp_path / "config/partitions_gold_m1_v2.json", POLICY)
    path = tmp_path / "mixed.parquet"
    frame.to_parquet(path, index=False)  # One mixed rowgroup, no payload reads allowed.
    with patch("pyarrow.parquet.ParquetFile.read_row_groups", side_effect=AssertionError("No payload read")):
        with pytest.raises(PermissionError):
            DataEngine(tmp_path).ingest_parquet(path, META, legacy_dev_rowgroups=True)


@pytest.mark.parametrize("column,value,code", [
    ("high", 1., "INVALID_OHLC"), ("close", -1., "NONPOSITIVE_PRICE"),
    ("spread", -1., "NEGATIVE_SPREAD"), ("close", np.inf, "NONFINITE_OR_NULL"),
    ("tick_volume", -1., "NEGATIVE_VOLUME"), ("symbol", "EURUSD", "SYMBOL_CHANGE")])
def test_reject_anomalies_are_retained_in_raw(tmp_path, column, value, code):
    frame = bars()
    frame[column] = frame[column].astype("object") if column == "symbol" else frame[column].astype(float)
    frame.loc[80, column] = value
    engine, manifest = certify(tmp_path, frame)
    assert manifest["status"] == "REJECTED"
    assert manifest["quality"]["counts"][code] > 0
    assert manifest["rows"] == 200
    with pytest.raises(PermissionError):
        engine.query(manifest["dataset_id"])


def test_exact_duplicates_fix_conflicts_reject_and_gaps_review():
    frame = pd.concat([bars(), bars().iloc[[0]]], ignore_index=True)
    _, silver, _, quality = normalize_and_validate(frame, META, 1)
    assert len(silver) == 200 and quality["counts"]["EXACT_DUPLICATE"] == 1
    frame.loc[200, "spread"] = 22
    assert normalize_and_validate(frame, META, 1)[3]["counts"]["CONFLICTING_TIMESTAMP"] == 2
    quality = normalize_and_validate(bars().drop(index=50), META, 1)[3]
    assert quality["status"] == "EXPLORATORY_ONLY" and quality["counts"]["GAP"] == 1


def test_jumps_and_stale_prices_are_flagged_not_clipped():
    frame = bars()
    frame.loc[80:90, ["open", "high", "low", "close"]] = 2200.
    _, silver, flags, quality = normalize_and_validate(frame, META, 1)
    assert silver.loc[80, "close"] == 2200.
    assert {"PRICE_JUMP", "STALE_RUN"} <= set(flags.code)


def test_dst_ambiguity_is_not_guessed():
    frame = bars().iloc[:1].copy()
    frame["timestamp_utc"] = pd.to_datetime(["2024-11-03 01:30:00"])
    with pytest.raises(Exception, match="[Aa]mbiguous|infer dst"):
        normalize_and_validate(frame, {**META, "timezone": "America/New_York"}, 1)


def test_feature_prefix_does_not_depend_on_future_and_gap_warmup_is_masked():
    frame = bars()
    before = build_feature_label_frame(frame, .01)
    frame.loc[180:, ["open", "high", "low", "close"]] *= 2
    after = build_feature_label_frame(frame, .01)
    columns = [c for c in before if c.startswith("state_")]
    pd.testing.assert_frame_equal(before.loc[:100, columns], after.loc[:100, columns])
    gap = bars().drop(index=70)
    after = build_feature_label_frame(gap, .01)
    assert after.loc[after.timestamp_utc == bars().timestamp_utc.iloc[80], "state_atr_14_causal"].isna().all()


def test_gold_reuses_store_ml_and_no_boundary_labels(tmp_path):
    engine, parent = certify(tmp_path)
    manifest = engine.build_experiences(parent["dataset_id"])
    assert manifest == engine.build_experiences(parent["dataset_id"])
    store = ParquetExperienceStore(tmp_path)
    assert store.verify_files() == {"DEV": True}
    first = store.query(action="WAIT", limit=1).iloc[0]
    assert store.replay(first.experience_id)["hash_valid"]
    dataset = DevOnlyMLData(tmp_path).load_0830(horizon=30, atr_multiple=.25)
    assert len(dataset.frame) == 1 and set(dataset.frame.partition) == {"DEV"}
    frame = store.query(action="WAIT")
    assert frame.label_future_return_60m.iloc[-60:].isna().all()
    for name in ("VALIDATION", "LOCKED_OOS"):
        with pytest.raises(PermissionError):
            store.query(partitions=(name,), allow_locked=True)


def test_uncertified_discovery_ml_and_economic_backtest_fail_before_payload(tmp_path):
    from src.data.pipeline import build_experience_dataset
    from src.data.pipeline_v2 import build_experience_store_v2
    from src.data.loader import load_raw_dataset
    from src.experience_store.market_store import MarketExperienceStore
    from src.data.quality_v2 import audit_parquet
    operations = [lambda: build_experience_dataset(tmp_path, "missing"),
                  lambda: build_experience_store_v2(tmp_path, "missing", "missing"),
                  lambda: load_raw_dataset("missing"),
                  lambda: MarketExperienceStore(tmp_path).all(allow_locked=True),
                  lambda: audit_parquet("missing", "missing", "missing")]
    for operation in operations:
        with pytest.raises(PermissionError):
            operation()
    engine, parent = certify(tmp_path)
    engine.build_experiences(parent["dataset_id"])
    store = ParquetExperienceStore(tmp_path)
    store.manifest.pop("data_engine_dataset_id")
    with patch("src.experience_store.parquet_store.pq.read_table", side_effect=AssertionError("No read")):
        with pytest.raises(PermissionError):
            store.query()


def test_certificate_tamper_unknown_id_and_path_escape(tmp_path):
    engine, result = certify(tmp_path)
    for bad in ("legacy", "../../locked_oos", "DE1-" + "0"*64):
        with pytest.raises(PermissionError):
            engine.query(bad)
    path = tmp_path / "data/engine/datasets" / result["dataset_id"] / "manifest.json"
    content = json.loads(path.read_text())
    content["artifacts"]["silver"]["path"] = "outside.parquet"
    atomic_write_json(path, content)
    with pytest.raises(PermissionError):
        engine.query(result["dataset_id"])


def test_even_rehashed_manifest_cannot_redirect_to_locked_before_hash(tmp_path):
    from src.data.engine import identity
    engine, result = certify(tmp_path)
    result["artifacts"]["silver"]["path"] = "data/engine/raw/LOCKED_OOS/protected.parquet"
    result["certificate_sha256"] = identity({k: v for k, v in result.items() if k != "certificate_sha256"})
    atomic_write_json(tmp_path / "data/engine/datasets" / result["dataset_id"] / "manifest.json", result)
    with patch("src.data.engine.file_hash", side_effect=AssertionError("No payload hash permitted")):
        with pytest.raises(PermissionError, match="redirected"):
            engine.query(result["dataset_id"])


def test_scientific_consumers_have_no_direct_parquet_readers():
    import ast
    root = Path(__file__).resolve().parents[2]
    for folder in ("research", "ml", "validation", "execution", "orchestrator"):
        for path in (root / "src" / folder).glob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            forbidden = [node.func.attr for node in ast.walk(tree) if isinstance(node, ast.Call)
                         and isinstance(node.func, ast.Attribute)
                         and node.func.attr in ("read_parquet", "read_table", "read_csv", "ParquetFile")]
            assert not forbidden, str(path)


def test_discovery_ml_economic_actual_entrypoints_require_certificate(tmp_path):
    from src.research.economic_campaign import EconomicCampaign
    from src.validation.evidence_engine import EvidenceEngine
    engine, parent = certify(tmp_path)
    engine.build_experiences(parent["dataset_id"])
    store = ParquetExperienceStore(tmp_path)
    store.manifest.pop("data_engine_dataset_id")
    campaign = EconomicCampaign.__new__(EconomicCampaign)
    campaign.store = store
    campaign.config = {"signals": [{"action": "ENTER_LONG", "horizon": 30}]}
    with pytest.raises(PermissionError):
        campaign._load("ENTER_LONG")
    ml = DevOnlyMLData(tmp_path)
    ml.store = store
    with pytest.raises(PermissionError):
        ml.load_0830(horizon=30, atr_multiple=.25)
    evidence = EvidenceEngine(tmp_path)
    evidence.store = store
    with pytest.raises(PermissionError):
        evidence._data("WAIT")


def test_index_cannot_redirect_metadata_read(tmp_path):
    version = "DATASET-DE1-" + "a" * 64
    atomic_write_json(tmp_path / "experience_store/v2/index.json", {"datasets": [
        {"dataset_version": version, "manifest": "protected.json"}]})
    with pytest.raises(PermissionError, match="redirect"):
        ParquetExperienceStore(tmp_path)
