"""Preregistered DEV-only temporal experiment and native AXXEL persistence."""
from __future__ import annotations

import importlib.metadata
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.metrics import balanced_accuracy_score, log_loss, mean_absolute_error

from src.ml.data import CLASSES, DevOnlyMLData, assert_feature_contract
from src.ml.models import (aligned_probabilities, classifier, feature_importance,
                           fit_probability_calibrator, fit_with_early_stopping, regressor, save_native)
from src.research.evidence_registry import EvidenceRegistry
from src.research.hypothesis_graph import HypothesisGraph
from src.utils.hashing import content_hash, file_hash
from src.utils.serialization import atomic_write_json, read_json
from src.validation.walk_forward import assert_no_overlap, expanding_year_splits
from src.validation.leakage import assert_purged_segments
from src.validation.bootstrap import block_bootstrap
from src.validation.skeptic import run_skeptic
from src.value.research_value import research_value_v2
from src.memory.semantic_memory import SemanticMemory

MODEL_NAMES = ("xgboost", "lightgbm", "catboost")


def _temporal_train_parts(indices: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    n = len(indices)
    first = max(1, int(n * 0.70)); second = max(first + 1, int(n * 0.85))
    if n < 30 or second >= n:
        raise ValueError("Insufficient history for fit/early-stop/calibration separation")
    return indices[:first], indices[first:second], indices[second:]


def _median_transform(train: pd.DataFrame, *others: pd.DataFrame):
    medians = train.median(axis=0).fillna(0.0)
    arrays = [part.fillna(medians).to_numpy(dtype=float) for part in (train, *others)]
    return arrays, medians


def _ece(y: np.ndarray, probabilities: np.ndarray, bins: int = 10) -> float:
    confidence = probabilities.max(axis=1); predicted = probabilities.argmax(axis=1)
    result = 0.0
    for low, high in zip(np.linspace(0, 1, bins + 1)[:-1], np.linspace(0, 1, bins + 1)[1:]):
        mask = (confidence >= low) & (confidence < high if high < 1 else confidence <= high)
        if mask.any():
            result += mask.mean() * abs((predicted[mask] == y[mask]).mean() - confidence[mask].mean())
    return float(result)


def _economic(frame: pd.DataFrame, probabilities: np.ndarray, threshold: float,
              disagreement: np.ndarray | None = None, max_disagreement: float | None = None,
              cost_multiplier: float = 1.0) -> dict[str, Any]:
    predicted = probabilities.argmax(axis=1)
    confidence = probabilities.max(axis=1)
    trade = (predicted != 1) & (confidence >= threshold)
    if disagreement is not None and max_disagreement is not None:
        trade &= disagreement[np.arange(len(predicted)), predicted] <= max_disagreement
    direction = np.where(predicted == 2, "long", "short")
    horizon = 30
    gross = np.where(direction == "long", frame[f"long_outcome_gross_return_{horizon}m"],
                     frame[f"short_outcome_gross_return_{horizon}m"])
    cost = np.where(direction == "long", frame[f"long_cost_spread_return_{horizon}m"],
                    frame[f"short_cost_spread_return_{horizon}m"])
    net = np.where(trade, gross - cost_multiplier * cost, 0.0)
    traded = net[trade]
    years = pd.to_datetime(frame["decision_timestamp_utc"], utc=True).dt.year.to_numpy()
    yearly = {str(int(year)): float(net[years == year].sum()) for year in sorted(set(years))}
    return {
        "trades": int(trade.sum()), "coverage": float(trade.mean()),
        "mean_net_return_per_trade": float(traded.mean()) if len(traded) else 0.0,
        "cumulative_net_return": float(traded.sum()),
        "win_rate": float((traded > 0).mean()) if len(traded) else 0.0,
        "positive_year_fraction": float(np.mean([x > 0 for x in yearly.values()])), "by_year": yearly,
        "trade_mask": trade, "net_returns": net,
    }


def _metrics(y: np.ndarray, probabilities: np.ndarray) -> dict[str, float]:
    one_hot = np.eye(3)[y]
    return {
        "balanced_accuracy": float(balanced_accuracy_score(y, probabilities.argmax(axis=1))),
        "log_loss": float(log_loss(y, probabilities, labels=[0, 1, 2])),
        "brier_multiclass": float(np.mean(np.sum((probabilities - one_hot) ** 2, axis=1))),
        "expected_calibration_error": _ece(y, probabilities),
    }


def _classifier_diagnostics(features: pd.DataFrame, y: np.ndarray, frame: pd.DataFrame,
                            splits: list, config: dict[str, Any]) -> dict[str, Any]:
    """Fixed adversarial checks; never select a model or alter the primary recipe."""
    controls = {"permuted_training_blocks": 0, "features_lagged_7_sessions": 0,
                "seed_plus_101": 101, "seed_plus_202": 202}
    results = {}
    for control, seed_delta in controls.items():
        matrix = features.shift(7) if control == "features_lagged_7_sessions" else features
        parts = []; indices = []
        for fold in splits:
            train = np.flatnonzero(np.asarray(fold["train_mask"]))
            test = np.flatnonzero(np.asarray(fold["test_mask"]))
            fit, stop, cal = _temporal_train_parts(train)
            assert_purged_segments(frame["decision_timestamp_utc"], fit, stop, cal, test, horizon_minutes=30)
            arrays, _ = _median_transform(matrix.iloc[fit], matrix.iloc[stop], matrix.iloc[cal], matrix.iloc[test])
            x_fit, x_stop, x_cal, x_test = arrays
            labels = [y[index].copy() for index in (fit, stop, cal)]
            if control == "permuted_training_blocks":
                # Shuffle ten-session blocks independently inside each historical segment.
                rng = np.random.default_rng(config["seed"] + int(fold["test_year"]))
                for i, values in enumerate(labels):
                    blocks = [values[start:start + 10] for start in range(0, len(values), 10)]
                    labels[i] = np.concatenate([blocks[j] for j in rng.permutation(len(blocks))])
            model_probabilities = []
            for offset, name in enumerate(MODEL_NAMES):
                seed = config["seed"] + offset + seed_delta
                model = classifier(name, seed, config["cpu_threads_per_model"], config)
                fit_with_early_stopping(model, name, x_fit, labels[0], x_stop, labels[1], config["early_stopping_rounds"])
                calibration = fit_probability_calibrator(aligned_probabilities(model, x_cal), labels[2], seed)
                model_probabilities.append(calibration.predict_proba(aligned_probabilities(model, x_test)))
            parts.append(np.stack(model_probabilities)); indices.extend(test.tolist())
        stacked = np.concatenate(parts, axis=1)
        probabilities = stacked.mean(axis=0)
        economics = _economic(frame.iloc[indices], probabilities, config["decision"]["minimum_probability"],
                              stacked.std(axis=0), config["decision"]["maximum_probability_std"])
        results[control] = {**_metrics(y[indices], probabilities),
                            "trades": economics["trades"], "cumulative_net_return": economics["cumulative_net_return"]}
    return {"purpose": "adversarial diagnostics only; no model/threshold selection", "controls": results}


def _barrier_probabilities(dataset, splits: list, config: dict[str, Any]) -> dict[str, Any]:
    """Marginal ATR-excursion probabilities, auxiliary and excluded from trade selection."""
    report = {}
    for target_name, values in dataset.barrier_targets.items():
        probabilities = {name: [] for name in MODEL_NAMES}; indices = []
        for fold in splits:
            train = np.flatnonzero(np.asarray(fold["train_mask"])); test = np.flatnonzero(np.asarray(fold["test_mask"]))
            fit, stop, cal = _temporal_train_parts(train)
            arrays, _ = _median_transform(dataset.features.iloc[fit], dataset.features.iloc[stop], dataset.features.iloc[cal], dataset.features.iloc[test])
            x_fit, x_stop, x_cal, x_test = arrays
            indices.extend(test.tolist())
            for offset, name in enumerate(MODEL_NAMES):
                seed = config["seed"] + offset
                model = classifier(name, seed, config["cpu_threads_per_model"], config, num_classes=2)
                fit_with_early_stopping(model, name, x_fit, values[fit], x_stop, values[stop], config["early_stopping_rounds"])
                calibration = fit_probability_calibrator(model.predict_proba(x_cal), values[cal], seed, num_classes=2)
                probabilities[name].append(calibration.predict_proba(model.predict_proba(x_test))[:, 1])
        predictions = {name: np.concatenate(parts) for name, parts in probabilities.items()}
        predictions["ensemble"] = np.stack(list(predictions.values())).mean(axis=0)
        actual = values[indices]
        report[target_name] = {name: {"brier": float(np.mean((prob - actual) ** 2)),
                                     "log_loss": float(log_loss(actual, np.column_stack([1 - prob, prob]), labels=[0, 1])),
                                     "observed_rate": float(actual.mean()), "mean_probability": float(prob.mean())}
                               for name, prob in predictions.items()}
    return {"purpose": "auxiliary only; not used to change the frozen primary trade decision", "tasks": report}


def _skeptic(frame: pd.DataFrame, y: np.ndarray, probabilities: np.ndarray, economics: dict[str, Any],
             config: dict[str, Any], disagreement: np.ndarray) -> dict[str, Any]:
    net = economics["net_returns"]; traded = net[economics["trade_mask"]]
    rng = np.random.default_rng(config["seed"] + 991)
    means = np.array([rng.choice(traded, len(traded), replace=True).mean() for _ in range(2000)]) if len(traded) else np.array([0.0])
    shifted_y = np.roll(y, 7)
    shifted_ba = balanced_accuracy_score(shifted_y[7:], probabilities.argmax(axis=1)[7:])
    stressed = _economic(frame, probabilities, config["decision"]["minimum_probability"], disagreement,
                         config["decision"]["maximum_probability_std"], cost_multiplier=2.0)
    if len(traded):
        keep = np.ones(len(traded), dtype=bool); keep[np.argsort(traded)[-max(1, int(np.ceil(len(traded) * .05))):]] = False
        after_best = float(traded[keep].mean()) if keep.any() else 0.0
    else: after_best = 0.0
    tests = {
        "bootstrap_ci_lower_positive": bool(np.quantile(means, .025) > 0),
        "positive_in_at_least_75pct_years": economics["positive_year_fraction"] >= .75,
        "survives_cost_2x": stressed["mean_net_return_per_trade"] > 0,
        "survives_remove_best_5pct": after_best > 0,
        "beats_seven_session_label_shift": _metrics(y, probabilities)["balanced_accuracy"] > shifted_ba + .02,
        "calibration_ece_at_most_10pct": _ece(y, probabilities) <= .10,
        "mean_model_probability_std_at_most_limit": float(disagreement.mean()) <= config["decision"]["maximum_probability_std"],
    }
    block = block_bootstrap(net, block_size=20, resamples=2000, seed=config["seed"] + 992)
    existing = run_skeptic(net, temporal={"favorable_proportion": economics["positive_year_fraction"]},
                          cost={"survives_2x": stressed["mean_net_return_per_trade"] > 0},
                          data_quality={"blocking_errors": False}, direction="GREATER")
    return {
        "tests": tests, "passed": sum(tests.values()), "attempted": len(tests),
        "survived": all(tests.values()) and existing["survived"] == existing["attempted"] and block["confidence_interval_95"][0] > 0,
        "bootstrap_mean_ci_95": [float(np.quantile(means, .025)), float(np.quantile(means, .975))],
        "block_bootstrap_all_sessions": block, "existing_skeptic": existing,
        "shifted_balanced_accuracy": float(shifted_ba),
        "cost_2x": {k: v for k, v in stressed.items() if k not in ("trade_mask", "net_returns")},
        "mean_after_remove_best_5pct": after_best,
        "no_trade_note": "Economic attacks cannot demonstrate survival when no trades occur" if not len(traded) else None,
    }


def _serialize_final_models(root: Path, dataset, config: dict[str, Any]) -> dict[str, Any]:
    """Fit the frozen specification on all DEV history and persist native artifacts."""
    indices = np.arange(len(dataset.target)); fit_idx, stop_idx, cal_idx = _temporal_train_parts(indices)
    assert_purged_segments(dataset.frame["decision_timestamp_utc"], fit_idx, stop_idx, cal_idx, horizon_minutes=30)
    arrays, medians = _median_transform(dataset.features.iloc[fit_idx], dataset.features.iloc[stop_idx], dataset.features.iloc[cal_idx])
    x_fit, x_stop, x_cal = arrays
    artifact_root = root / "models" / config["experiment_id"].lower()
    artifacts: dict[str, Any] = {}
    extensions = {"xgboost": "json", "lightgbm": "txt", "catboost": "cbm"}
    for offset, name in enumerate(MODEL_NAMES):
        seed = config["seed"] + offset
        clf = classifier(name, seed, config["cpu_threads_per_model"], config)
        fit_with_early_stopping(clf, name, x_fit, dataset.target[fit_idx], x_stop, dataset.target[stop_idx], config["early_stopping_rounds"])
        calibrator = fit_probability_calibrator(aligned_probabilities(clf, x_cal), dataset.target[cal_idx], seed)
        classifier_path = artifact_root / f"{name}_classifier.{extensions[name]}"
        save_native(clf, name, classifier_path)
        model_artifacts = {"classifier": str(classifier_path.relative_to(root)).replace("\\", "/")}
        for target_name, values in dataset.regression_targets.items():
            reg = regressor(name, seed, config["cpu_threads_per_model"], config)
            fit_with_early_stopping(reg, name, x_fit, values[fit_idx], x_stop, values[stop_idx], config["early_stopping_rounds"])
            path = artifact_root / f"{name}_{target_name}.{extensions[name]}"
            save_native(reg, name, path); model_artifacts[target_name] = str(path.relative_to(root)).replace("\\", "/")
        for target_name, values in dataset.barrier_targets.items():
            binary = classifier(name, seed, config["cpu_threads_per_model"], config, num_classes=2)
            fit_with_early_stopping(binary, name, x_fit, values[fit_idx], x_stop, values[stop_idx], config["early_stopping_rounds"])
            calibration = fit_probability_calibrator(binary.predict_proba(x_cal), values[cal_idx], seed, num_classes=2)
            path = artifact_root / f"{name}_{target_name}.{extensions[name]}"
            save_native(binary, name, path)
            model_artifacts[target_name] = {"model": str(path.relative_to(root)).replace("\\", "/"),
                                            "calibrator": {"classes": calibration.classes_.tolist(),
                                                           "coef": calibration.coef_.tolist(), "intercept": calibration.intercept_.tolist()}}
        model_artifacts["calibrator"] = {
            "type": "multinomial_logistic_on_temporal_holdout",
            "classes": calibrator.classes_.tolist(), "coef": calibrator.coef_.tolist(), "intercept": calibrator.intercept_.tolist(),
        }
        artifacts[name] = model_artifacts
    manifest = {
        "experiment_id": config["experiment_id"], "dataset_version": dataset.manifest["dataset_version"],
        "partition": "DEV", "feature_names": list(dataset.features.columns), "feature_medians": medians.to_dict(),
        "classes": list(CLASSES), "fit_rows": len(fit_idx), "early_stop_rows": len(stop_idx), "calibration_rows": len(cal_idx),
        "versions": {name: importlib.metadata.version(name) for name in MODEL_NAMES}, "artifacts": artifacts,
        "validation_inspected": False, "locked_oos_inspected": False,
    }
    manifest_path = artifact_root / "manifest.json"; atomic_write_json(manifest_path, manifest)
    return {"path": str(manifest_path.relative_to(root)).replace("\\", "/"), "hash": file_hash(manifest_path)}


def run_ml_experiment(project_root: Path | str, config_path: Path | str) -> dict[str, Any]:
    root = Path(project_root); config_path = Path(config_path)
    config = read_json(config_path, {})
    if not config.get("frozen_before_execution") or config.get("partition") != "DEV":
        raise PermissionError("ML experiment must be frozen and DEV-only")
    if config["horizon_minutes"] != 30 or config["decision_time_cot"] != "08:30":
        raise ValueError("This frozen experiment runner supports the 08:30 / 30-minute protocol only")
    registry = EvidenceRegistry(root); registered = registry.register(config["hypothesis"])
    registry.freeze_experiment_config(registered["id"], config, file_hash(config_path))
    registry.update_status(registered["id"], "TESTING")
    dataset = DevOnlyMLData(root, config.get("dataset_version")).load_0830(
        horizon=config["horizon_minutes"], atr_multiple=config["label"]["atr_multiple"], expected_symbol=config["symbol"])
    assert_feature_contract(list(dataset.features.columns))
    timestamps = pd.to_datetime(dataset.frame["decision_timestamp_utc"], utc=True).reset_index(drop=True)
    frame = dataset.frame.reset_index(); features = dataset.features.reset_index(drop=True); y = dataset.target
    splits = expanding_year_splits(timestamps, first_test_year=config["walk_forward"]["first_test_year"],
                                   horizon_minutes=config["horizon_minutes"], embargo_minutes=config["walk_forward"]["embargo_minutes"])
    if len(splits) < 3: raise ValueError("At least three temporal folds are required")
    oof_indices: list[int] = []; probability_parts = {name: [] for name in MODEL_NAMES}
    regression_predictions = {name: {target: [] for target in dataset.regression_targets} for name in MODEL_NAMES}
    importance = {name: [] for name in MODEL_NAMES}; fold_records = []
    for fold in splits:
        assert_no_overlap(timestamps, fold, config["horizon_minutes"])
        train_idx = np.flatnonzero(np.asarray(fold["train_mask"])); test_idx = np.flatnonzero(np.asarray(fold["test_mask"]))
        fit_idx, stop_idx, cal_idx = _temporal_train_parts(train_idx)
        assert_purged_segments(timestamps, fit_idx, stop_idx, cal_idx, test_idx, horizon_minutes=config["horizon_minutes"])
        arrays, _ = _median_transform(features.iloc[fit_idx], features.iloc[stop_idx], features.iloc[cal_idx], features.iloc[test_idx])
        x_fit, x_stop, x_cal, x_test = arrays; oof_indices.extend(test_idx.tolist())
        fold_records.append({"test_year": fold["test_year"], "fit_rows": len(fit_idx), "early_stop_rows": len(stop_idx),
                             "calibration_rows": len(cal_idx), "test_rows": len(test_idx), "purge_minutes": fold["purge_minutes"],
                             "embargo_minutes": fold["embargo_minutes"]})
        for offset, name in enumerate(MODEL_NAMES):
            seed = config["seed"] + offset
            clf = classifier(name, seed, config["cpu_threads_per_model"], config)
            fit_with_early_stopping(clf, name, x_fit, y[fit_idx], x_stop, y[stop_idx], config["early_stopping_rounds"])
            raw_cal = aligned_probabilities(clf, x_cal); calibrator = fit_probability_calibrator(raw_cal, y[cal_idx], seed)
            calibrated = calibrator.predict_proba(aligned_probabilities(clf, x_test))
            probability_parts[name].append(calibrated); importance[name].append(feature_importance(clf))
            for target_name, values in dataset.regression_targets.items():
                reg = regressor(name, seed, config["cpu_threads_per_model"], config)
                fit_with_early_stopping(reg, name, x_fit, values[fit_idx], x_stop, values[stop_idx], config["early_stopping_rounds"])
                regression_predictions[name][target_name].append(np.asarray(reg.predict(x_test), dtype=float))
    order = np.argsort(oof_indices); oof_indices_array = np.asarray(oof_indices)[order]
    oof_frame = frame.iloc[oof_indices_array].reset_index(drop=True); oof_y = y[oof_indices_array]
    probabilities = {name: np.vstack(parts)[order] for name, parts in probability_parts.items()}
    stacked = np.stack([probabilities[name] for name in MODEL_NAMES], axis=0)
    ensemble = stacked.mean(axis=0); disagreement = stacked.std(axis=0)
    class_rate = np.bincount(y[np.asarray(splits[0]["train_mask"])], minlength=3).astype(float); class_rate /= class_rate.sum()
    baseline_prob = np.tile(class_rate, (len(oof_y), 1)); baseline = _metrics(oof_y, baseline_prob)
    model_results = {}
    for name in MODEL_NAMES:
        economic = _economic(oof_frame, probabilities[name], config["decision"]["minimum_probability"])
        regressions = {}
        for target_name, parts in regression_predictions[name].items():
            predicted = np.concatenate(parts)[order]
            actual = dataset.regression_targets[target_name][oof_indices_array]
            regressions[target_name] = {"mae": float(mean_absolute_error(actual, predicted))}
        model_results[name] = {**_metrics(oof_y, probabilities[name]),
                               "economic": {k: v for k, v in economic.items() if k not in ("trade_mask", "net_returns")},
                               "regression": regressions,
                               "top_feature_importance": sorted(zip(dataset.features.columns, np.mean(importance[name], axis=0)), key=lambda x: x[1], reverse=True)[:8]}
        rank_correlations = []
        for a, b in zip(importance[name][:-1], importance[name][1:]):
            correlation = pd.Series(a).rank().corr(pd.Series(b).rank())
            if np.isfinite(correlation): rank_correlations.append(float(correlation))
        model_results[name]["importance_rank_stability"] = float(np.mean(rank_correlations)) if rank_correlations else None
    ensemble_regression = {}
    for target_name, actual_values in dataset.regression_targets.items():
        predictions = np.stack([np.concatenate(regression_predictions[name][target_name])[order] for name in MODEL_NAMES]).mean(axis=0)
        ensemble_regression[target_name] = {"mae": float(mean_absolute_error(actual_values[oof_indices_array], predictions))}
    ensemble_economic = _economic(oof_frame, ensemble, config["decision"]["minimum_probability"], disagreement,
                                  config["decision"]["maximum_probability_std"])
    ensemble_metrics = _metrics(oof_y, ensemble)
    skeptic = _skeptic(oof_frame, oof_y, ensemble, ensemble_economic, config, disagreement)
    predictive = ensemble_metrics["balanced_accuracy"] >= config["promotion"]["minimum_balanced_accuracy"] and ensemble_metrics["log_loss"] < baseline["log_loss"]
    economic_positive = ensemble_economic["mean_net_return_per_trade"] > 0 and ensemble_economic["trades"] >= config["promotion"]["minimum_trades"]
    real_costs = dataset.manifest["cost_methods"] == ["REAL_TICK_COST"] and dataset.manifest["slippage_status"] == ["AVAILABLE"]
    incident_path = root / "reports/ML_PARTITION_ACCESS_INCIDENT.json"
    incident = read_json(incident_path, {})
    integrity_cleared = not incident or incident.get("status") == "RESOLVED_REVIEWED"
    if not predictive or not economic_positive: verdict = "REJECTED"
    elif not skeptic["survived"] or not real_costs or not integrity_cleared: verdict = "RESEARCH_ONLY"
    else: verdict = "VALIDATION_READY"
    traded = ensemble_economic["net_returns"][ensemble_economic["trade_mask"]]
    rng = np.random.default_rng(config["seed"] + 404)
    p_value = float((1 + sum((traded * rng.choice([-1, 1], len(traded))).mean() >= traded.mean() for _ in range(4000))) / 4001) if len(traded) else 1.0
    serialized_models = _serialize_final_models(root, dataset, config)
    diagnostics = _classifier_diagnostics(features, y, frame, splits, config)
    barrier_results = _barrier_probabilities(dataset, splits, config)
    report = {
        "report_id": "ML-XAUUSD-0830-V1", "hypothesis_id": registered["id"], "spec_hash": registered["spec_hash"],
        "config_hash": file_hash(config_path), "dataset": dataset.manifest, "serialized_models": serialized_models, "models": model_results,
        "ensemble": {**ensemble_metrics, "economic": {k: v for k, v in ensemble_economic.items() if k not in ("trade_mask", "net_returns")},
                     "regression": ensemble_regression,
                     "mean_probability_std": float(disagreement.mean()), "maximum_probability_std": float(disagreement.max())},
        "baseline": baseline, "walk_forward_folds": fold_records, "skeptic": skeptic, "p_value": p_value,
        "adversarial_diagnostics": diagnostics,
        "auxiliary_barrier_probabilities": barrier_results,
        "cost_reality": {"real_costs_complete": real_costs, "spread": "PROXY_COST", "slippage": "UNAVAILABLE_NOT_ASSUMED_ZERO",
                         "promotion_ceiling": "RESEARCH_ONLY"},
        "gates": {"predictive": predictive, "economic_positive": economic_positive, "skeptic": skeptic["survived"], "real_costs": real_costs,
                  "research_integrity_review_cleared": integrity_cleared},
        "verdict": verdict, "validation_inspected": False, "locked_oos_inspected": False,
        "partition_flag_scope": "The false inspection flags describe this ML runner only, not legacy tests executed during integration",
        "legacy_test_partition_incident": str(incident_path.relative_to(root)).replace("\\", "/") if incident else None,
        "locked_oos_opened_by_legacy_integration_test": bool(incident),
    }
    report["prediction_hash"] = content_hash({name: values.tolist() for name, values in probabilities.items()})
    report["runtime"] = {"python": __import__("platform").python_version(), "device": "CPU",
                         "threads_per_model": config["cpu_threads_per_model"], "seed": config["seed"],
                         "versions": {name: importlib.metadata.version(name) for name in
                                      (*MODEL_NAMES, "numpy", "pandas", "scipy", "pyarrow", "scikit-learn")}}
    report["source_hashes"] = {str(path.relative_to(root)).replace("\\", "/"): file_hash(path)
                               for path in sorted((root / "src/ml").glob("*.py"))}
    resolved = float(not predictive or not economic_positive)
    report["research_value"] = research_value_v2(
        expected_information_gain=1 - resolved, uncertainty_reduction=resolved, novelty=0,
        prior_evidence=resolved, contradiction_value=resolved, economic_relevance=1,
        data_quality=1 if real_costs else .5, estimated_compute_cost=.5,
        redundancy_penalty=resolved, family_saturation_penalty=resolved, complexity_penalty=.3)
    report["research_value"]["interpretation"] = "Heuristic priority for repeating the same hypothesis, not statistical confidence"
    prediction_frame = oof_frame[["session_id", "decision_timestamp_utc"]].copy()
    prediction_frame["actual_class"] = oof_y
    for name, values in {**probabilities, "ensemble": ensemble}.items():
        for index, label in enumerate(CLASSES): prediction_frame[f"{name}_{label}"] = values[:, index]
    prediction_path = root / "reports/evidence" / f"{config['experiment_id'].lower()}_predictions.parquet"
    prediction_frame.to_parquet(prediction_path, index=False)
    report["predictions_path"] = str(prediction_path.relative_to(root)).replace("\\", "/")
    report_path = registry.record_report(registered["id"], report)
    if verdict == "VALIDATION_READY":
        registry.update_status(registered["id"], "DEV_SURVIVOR")
        registry.preregister_validation(registered["id"], report_path)
    else:
        registry.update_status(registered["id"], verdict, ml_report=str(report_path.relative_to(root)).replace("\\", "/"))
    graph = HypothesisGraph(root); graph.add_node({"id": registered["id"], "family": "ML_0830", "status": verdict})
    graph.add_edge(registered["id"], "HYPOTHESIS-CAL-0830-EXPANSION-V1", "REFINES", str(report_path.relative_to(root)).replace("\\", "/"))
    graph.add_node({"id": report["report_id"], "family": "ML_EVIDENCE", "status": "COMPLETED"})
    graph.add_edge(report["report_id"], registered["id"], "FALSIFIES" if verdict == "REJECTED" else "SUPPORTS", str(report_path.relative_to(root)))
    memory = SemanticMemory(root / "memory_db")
    if not any(report["report_id"] in item.get("evidence_ids", []) for item in memory.all()):
        memory.add_knowledge(f"{report['report_id']}: {verdict}; balanced accuracy={ensemble_metrics['balanced_accuracy']:.6f}; trades={ensemble_economic['trades']}. No post-hoc tuning; proxy costs cannot justify promotion.",
                             evidence_ids=[report["report_id"]], confidence=.7, tags=["ml", "xauusd", "0830", verdict.lower()])
    output_path = root / config["output_report"]
    atomic_write_json(output_path, report)
    return {**report, "report_path": str(output_path), "evidence_path": str(report_path)}
