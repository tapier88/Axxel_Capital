from __future__ import annotations

import inspect

import numpy as np
import pandas as pd
import pytest

from src.ml.data import CLASSES, FEATURES, DevOnlyMLData, assert_feature_contract
from src.ml.experiment import _economic, _metrics, _temporal_train_parts, _skeptic
from src.ml.models import classifier, regressor, fit_with_early_stopping, save_native


def test_dev_gateway_has_no_partition_or_locked_escape_hatch():
    signature = inspect.signature(DevOnlyMLData.load_0830)
    assert "partition" not in signature.parameters
    assert "allow_locked" not in signature.parameters


def test_feature_contract_rejects_future_and_cost_fields():
    assert_feature_contract(list(FEATURES))
    with pytest.raises(AssertionError):
        assert_feature_contract([*FEATURES, "label_future_return_30m"])
    with pytest.raises(AssertionError):
        assert_feature_contract([*FEATURES, "cost_spread_return_30m"])


def test_certified_dev_0830_dataset_is_causal_unique_and_dev_only(tmp_path):
    from tests.data_quality.test_data_engine import certify
    engine, parent = certify(tmp_path)
    engine.build_experiences(parent["dataset_id"])
    dataset = DevOnlyMLData(tmp_path).load_0830(horizon=30, atr_multiple=.25)
    assert len(dataset.frame) == dataset.frame.index.nunique() == 1
    assert tuple(dataset.features.columns) == FEATURES
    assert set(dataset.frame["partition"]) == {"DEV"}
    assert dataset.manifest["validation_inspected"] is False
    assert dataset.manifest["locked_oos_inspected"] is False
    assert set(dataset.manifest["class_counts"]) <= set(CLASSES)
    assert set(dataset.barrier_targets) == {"long_atr_reached", "short_atr_reached"}
    assert all(set(np.unique(values)) <= {0, 1} for values in dataset.barrier_targets.values())


def test_temporal_parts_are_strictly_ordered():
    fit, stop, calibration = _temporal_train_parts(np.arange(100))
    assert fit.max() < stop.min() <= stop.max() < calibration.min()


def test_economic_gate_abstains_below_frozen_probability():
    frame = pd.DataFrame({
        "decision_timestamp_utc": pd.to_datetime(["2019-01-01", "2019-01-02"], utc=True),
        "long_outcome_gross_return_30m": [.01, .01], "short_outcome_gross_return_30m": [-.01, -.01],
        "long_cost_spread_return_30m": [.001, .001], "short_cost_spread_return_30m": [.001, .001],
    })
    probabilities = np.array([[.34, .33, .33], [.33, .34, .33]])
    result = _economic(frame, probabilities, .50)
    assert result["trades"] == 0 and result["cumulative_net_return"] == 0


def test_all_three_cpu_adapters_construct_for_classification_and_regression():
    config = {
        "models": {name: {"iterations": 5, "depth": 2, "learning_rate": .1}
                   for name in ("xgboost", "lightgbm", "catboost")}
    }
    for name in config["models"]:
        assert classifier(name, 7, 1, config) is not None
        assert regressor(name, 7, 1, config) is not None


def test_metrics_are_multiclass_probability_metrics():
    y = np.array([0, 1, 2])
    perfect = np.eye(3) * .98 + .02 / 3
    result = _metrics(y, perfect)
    assert result["balanced_accuracy"] == 1.0
    assert result["log_loss"] < .1


@pytest.mark.parametrize("name", ["xgboost", "lightgbm", "catboost"])
def test_fit_and_native_serialization_roundtrip(name, tmp_path):
    rng = np.random.default_rng(7)
    x = rng.normal(size=(120, 4)); y = np.tile([0, 1, 2], 40)
    config = {"models": {name: {"iterations": 8, "depth": 2, "learning_rate": .1}}}
    model = classifier(name, 7, 1, config)
    fit_with_early_stopping(model, name, x[:90], y[:90], x[90:], y[90:], 3)
    extension = {"xgboost": "json", "lightgbm": "txt", "catboost": "cbm"}[name]
    path = tmp_path / f"model.{extension}"
    save_native(model, name, path)
    if name == "lightgbm":
        from lightgbm import Booster
        restored = Booster(model_file=str(path)).predict(x[90:])
    else:
        loaded = classifier(name, 7, 1, config); loaded.load_model(str(path))
        restored = loaded.predict_proba(x[90:])
    np.testing.assert_allclose(model.predict_proba(x[90:]), restored, rtol=1e-6, atol=1e-7)


def test_skeptic_returns_evidence_for_no_trades():
    n = 40
    frame = pd.DataFrame({"decision_timestamp_utc": pd.date_range("2018-01-01", periods=n, tz="UTC"),
                          **{f"{side}_{field}_30m": np.zeros(n) for side in ("long", "short")
                             for field in ("outcome_gross_return", "cost_spread_return")}})
    probabilities = np.tile([.3, .4, .3], (n, 1))
    economic = _economic(frame, probabilities, .5)
    result = _skeptic(frame, np.arange(n) % 3, probabilities, economic,
                      {"seed": 1, "decision": {"minimum_probability": .5, "maximum_probability_std": .1}}, np.zeros((n, 3)))
    assert result["survived"] is False
    assert result["no_trade_note"]


def test_complete_recipe_is_immutable(tmp_path):
    import json
    from src.research.evidence_registry import EvidenceRegistry
    config = json.loads(open("config/ml_xauusd_0830_v1.json", encoding="utf-8").read())
    registry = EvidenceRegistry(tmp_path); record = registry.register(config["hypothesis"])
    registry.freeze_experiment_config(record["id"], config, "hash")
    config["decision"]["minimum_probability"] = .1
    with pytest.raises(PermissionError):
        registry.freeze_experiment_config(record["id"], config, "changed")


def test_causal_source_and_temporal_leakage_are_blocked():
    from src.validation.leakage import assert_causal_sources, assert_purged_segments
    timestamps = pd.date_range("2019-01-01", periods=4, freq="10min", tz="UTC")
    frame = pd.DataFrame({"decision_timestamp_utc": timestamps, "state_max_source_timestamp_utc": timestamps})
    with pytest.raises(AssertionError): assert_causal_sources(frame)
    with pytest.raises(AssertionError):
        assert_purged_segments(timestamps, np.array([0]), np.array([1, 2]), horizon_minutes=30)


def test_identical_report_is_not_counted_as_another_experiment(tmp_path):
    import json
    from src.research.evidence_registry import EvidenceRegistry
    config = json.loads(open("config/ml_xauusd_0830_v1.json", encoding="utf-8").read())
    registry = EvidenceRegistry(tmp_path); record = registry.register(config["hypothesis"])
    report = {"p_value": 1.0, "verdict": "REJECTED"}
    registry.record_report(record["id"], report); registry.record_report(record["id"], report)
    assert registry.repo.all()[0]["tests_executed"] == config["hypothesis"]["planned_comparisons"]
