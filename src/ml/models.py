"""Small common CPU adapter for XGBoost, LightGBM, and CatBoost."""
from __future__ import annotations

from pathlib import Path
from typing import Any
import os
import sys

import numpy as np
from sklearn.linear_model import LogisticRegression


def _prepare_windows_openmp() -> None:
    """Make the OpenMP runtime bundled with scikit-learn visible to LightGBM."""
    if sys.platform != "win32" or not hasattr(os, "add_dll_directory"):
        return
    import sklearn
    runtime = Path(sklearn.__file__).resolve().parent / ".libs"
    if runtime.exists():
        # The handle must stay alive for the process lifetime.
        global _DLL_HANDLE
        _DLL_HANDLE = os.add_dll_directory(str(runtime))


def classifier(name: str, seed: int, threads: int, config: dict[str, Any], num_classes: int = 3):
    common = config["models"][name]
    if name == "xgboost":
        from xgboost import XGBClassifier
        return XGBClassifier(
            n_estimators=common["iterations"], max_depth=common["depth"], learning_rate=common["learning_rate"],
            subsample=1.0, colsample_bytree=1.0,
            objective="multi:softprob" if num_classes == 3 else "binary:logistic",
            eval_metric="mlogloss" if num_classes == 3 else "logloss", tree_method="hist", device="cpu", n_jobs=threads,
            random_state=seed, verbosity=0,
        )
    if name == "lightgbm":
        _prepare_windows_openmp()
        from lightgbm import LGBMClassifier
        return LGBMClassifier(
            n_estimators=common["iterations"], max_depth=common["depth"], num_leaves=2 ** common["depth"] - 1,
            learning_rate=common["learning_rate"], objective="multiclass" if num_classes == 3 else "binary", device_type="cpu",
            deterministic=True, force_col_wise=True, n_jobs=threads, random_state=seed,
            verbosity=-1, importance_type="gain",
        )
    if name == "catboost":
        from catboost import CatBoostClassifier
        return CatBoostClassifier(
            iterations=common["iterations"], depth=common["depth"], learning_rate=common["learning_rate"],
            loss_function="MultiClass" if num_classes == 3 else "Logloss",
            eval_metric="MultiClass" if num_classes == 3 else "Logloss", task_type="CPU", thread_count=threads,
            random_seed=seed, has_time=True, verbose=False, allow_writing_files=False,
        )
    raise ValueError(name)


def regressor(name: str, seed: int, threads: int, config: dict[str, Any]):
    common = config["models"][name]
    if name == "xgboost":
        from xgboost import XGBRegressor
        return XGBRegressor(
            n_estimators=common["iterations"], max_depth=common["depth"], learning_rate=common["learning_rate"],
            objective="reg:squarederror", eval_metric="rmse", tree_method="hist", device="cpu",
            n_jobs=threads, random_state=seed, verbosity=0,
        )
    if name == "lightgbm":
        _prepare_windows_openmp()
        from lightgbm import LGBMRegressor
        return LGBMRegressor(
            n_estimators=common["iterations"], max_depth=common["depth"], num_leaves=2 ** common["depth"] - 1,
            learning_rate=common["learning_rate"], objective="regression", device_type="cpu",
            deterministic=True, force_col_wise=True, n_jobs=threads, random_state=seed,
            verbosity=-1, importance_type="gain",
        )
    if name == "catboost":
        from catboost import CatBoostRegressor
        return CatBoostRegressor(
            iterations=common["iterations"], depth=common["depth"], learning_rate=common["learning_rate"],
            loss_function="RMSE", task_type="CPU", thread_count=threads, random_seed=seed,
            has_time=True, verbose=False, allow_writing_files=False,
        )
    raise ValueError(name)


def fit_with_early_stopping(model, name: str, x_train, y_train, x_eval, y_eval, rounds: int):
    if name == "xgboost":
        model.set_params(early_stopping_rounds=rounds)
        model.fit(x_train, y_train, eval_set=[(x_eval, y_eval)], verbose=False)
    elif name == "lightgbm":
        import lightgbm as lgb
        model.fit(x_train, y_train, eval_X=x_eval, eval_y=y_eval, callbacks=[lgb.early_stopping(rounds, verbose=False)])
    else:
        model.set_params(early_stopping_rounds=rounds)
        model.fit(x_train, y_train, eval_set=(x_eval, y_eval), verbose=False)
    return model


def fit_probability_calibrator(raw_probabilities: np.ndarray, y: np.ndarray, seed: int, num_classes: int = 3):
    if set(np.unique(y)) != set(range(num_classes)):
        raise ValueError("Temporal calibration segment must contain all frozen classes")
    return LogisticRegression(max_iter=1000, random_state=seed).fit(raw_probabilities, y)


def aligned_probabilities(model, x, classes=(0, 1, 2)) -> np.ndarray:
    raw = np.asarray(model.predict_proba(x), dtype=float)
    result = np.zeros((len(raw), len(classes)), dtype=float)
    for source, label in enumerate(np.asarray(model.classes_, dtype=int)):
        result[:, int(label)] = raw[:, source]
    return result


def feature_importance(model) -> np.ndarray:
    values = getattr(model, "feature_importances_", None)
    if values is None and hasattr(model, "get_feature_importance"):
        values = model.get_feature_importance()
    values = np.asarray(values, dtype=float)
    total = values.sum()
    return values / total if total > 0 else values


def save_native(model, name: str, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if name == "lightgbm":
        model.booster_.save_model(str(path))
    else:
        model.save_model(str(path))
