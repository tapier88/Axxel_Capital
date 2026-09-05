"""Vectorized GOLD M1 -> Parquet Experience Store V2 pipeline."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from pandas.api.indexers import FixedForwardWindowIndexer

from src.utils.hashing import content_hash, file_hash
from src.utils.serialization import atomic_write_json, read_json

SCHEMA_VERSION = "market-experience-v2"
HORIZONS = (5, 15, 30, 60)
STATE_NUMERIC = (
    "state_return_1m", "state_return_5m", "state_return_15m", "state_return_30m",
    "state_return_60m", "state_bar_range", "state_atr_14_causal",
    "state_volatility_15m_causal", "state_volatility_60m_causal",
    "state_distance_recent_high", "state_distance_recent_low", "state_momentum_15m_causal",
    "state_spread_points", "state_tick_volume", "state_minute_of_session",
)


def _future_window(series: pd.Series, horizon: int, operation: str) -> pd.Series:
    indexer = FixedForwardWindowIndexer(window_size=horizon)
    shifted = series.shift(-1)
    rolling = shifted.rolling(indexer, min_periods=horizon)
    return getattr(rolling, operation)()


def build_feature_label_frame(bars: pd.DataFrame, point: float) -> pd.DataFrame:
    frame = bars.copy()
    ts = frame["timestamp_utc"]
    close = frame["close"]
    returns_1m = close.pct_change(fill_method=None)
    frame["decision_timestamp_utc"] = ts + pd.Timedelta(minutes=1)
    cot = frame["decision_timestamp_utc"].dt.tz_convert("America/Bogota")
    frame["timestamp_cot"] = cot
    frame["state_minute_of_session"] = cot.dt.hour * 60 + cot.dt.minute - 8 * 60
    for horizon in (1, 5, 15, 30, 60):
        frame[f"state_return_{horizon}m"] = close.pct_change(horizon, fill_method=None)
    previous_close = close.shift(1)
    true_range = pd.concat([
        frame["high"] - frame["low"],
        (frame["high"] - previous_close).abs(),
        (frame["low"] - previous_close).abs(),
    ], axis=1).max(axis=1)
    frame["state_bar_range"] = frame["high"] - frame["low"]
    frame["state_atr_14_causal"] = true_range.rolling(14, min_periods=14).mean()
    frame["state_volatility_15m_causal"] = returns_1m.rolling(15, min_periods=15).std(ddof=0)
    frame["state_volatility_60m_causal"] = returns_1m.rolling(60, min_periods=60).std(ddof=0)
    recent_high = frame["high"].rolling(60, min_periods=60).max()
    recent_low = frame["low"].rolling(60, min_periods=60).min()
    frame["state_distance_recent_high"] = (recent_high-close)/close
    frame["state_distance_recent_low"] = (close-recent_low)/close
    frame["state_momentum_15m_causal"] = frame["state_return_15m"]
    vol = frame["state_volatility_15m_causal"]
    momentum = frame["state_momentum_15m_causal"]
    frame["state_regime_v0"] = np.select(
        [momentum > vol, momentum < -vol], ["TREND_UP", "TREND_DOWN"], default="RANGE"
    )
    frame["state_spread_points"] = frame["spread"].astype(float)
    frame["state_spread_price"] = frame["state_spread_points"] * point
    frame["state_tick_volume"] = frame["tick_volume"]
    frame["state_real_volume"] = frame["real_volume"]
    frame["state_information_boundary"] = "FEATURES_AVAILABLE_AT_DECISION_TIME"
    frame["state_max_source_timestamp_utc"] = ts

    # A nominal N-minute feature requires N elapsed minutes, not just N rows.
    # A gap cannot create a fabricated contiguous history or cross-boundary warmup.
    for horizon in (1, 5, 15, 30, 60):
        contiguous_past = (ts - ts.shift(horizon)) == pd.Timedelta(minutes=horizon)
        frame[f"state_return_{horizon}m"] = frame[f"state_return_{horizon}m"].where(contiguous_past)
    warmup = (ts - ts.shift(60)) == pd.Timedelta(minutes=60)
    rolling_fields = ["state_atr_14_causal", "state_volatility_15m_causal", "state_volatility_60m_causal",
                      "state_distance_recent_high", "state_distance_recent_low", "state_momentum_15m_causal"]
    frame.loc[~warmup, rolling_fields] = np.nan
    frame.loc[~warmup, "state_regime_v0"] = "UNAVAILABLE"

    for horizon in HORIZONS:
        future_close = close.shift(-horizon)
        future_time = ts.shift(-horizon)
        contiguous = (future_time-ts) == pd.Timedelta(minutes=horizon)
        future_return = (future_close/close)-1.0
        future_high = _future_window(frame["high"], horizon, "max")
        future_low = _future_window(frame["low"], horizon, "min")
        future_vol = _future_window(returns_1m, horizon, "std")
        frame[f"label_future_return_{horizon}m"] = future_return.where(contiguous)
        frame[f"label_up_excursion_{horizon}m"] = ((future_high-close)/close).where(contiguous)
        frame[f"label_down_excursion_{horizon}m"] = ((future_low-close)/close).where(contiguous)
        frame[f"label_realized_volatility_{horizon}m"] = future_vol.where(contiguous)
        frame[f"label_future_spread_points_{horizon}m"] = frame["spread"].shift(-horizon).where(contiguous)
        frame[f"label_source_timestamp_{horizon}m"] = future_time.where(contiguous)
    frame["outcome_information_boundary"] = "FUTURE INFORMATION — LABEL ONLY"
    mask = frame["state_minute_of_session"].between(0, 270)
    return frame.loc[mask].reset_index(drop=True)


def _forward_tick_quotes(ticks: pd.DataFrame, targets: pd.Series) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    if ticks.empty:
        return np.full(len(targets), np.nan), np.full(len(targets), np.nan), np.zeros(len(targets), dtype=bool)
    tick_ns = ticks["timestamp_utc"].astype("int64").to_numpy()
    target_ns = targets.astype("int64").to_numpy()
    positions = np.searchsorted(tick_ns, target_ns, side="left")
    safe = np.minimum(positions, len(ticks)-1)
    delta = tick_ns[safe]-target_ns
    valid = (positions < len(ticks)) & (delta >= 0) & (delta <= 60_000_000_000)
    bid = np.where(valid, ticks["bid"].to_numpy()[safe], np.nan)
    ask = np.where(valid, ticks["ask"].to_numpy()[safe], np.nan)
    return bid, ask, valid


def _assign_partition(timestamps: pd.Series, policy: dict[str, Any]) -> pd.Series:
    result = pd.Series("OUTSIDE", index=timestamps.index, dtype="object")
    for name in ("DEV", "VALIDATION", "LOCKED_OOS"):
        start = pd.Timestamp(policy[name]["from"])
        end = pd.Timestamp(policy[name]["to_exclusive"])
        result.loc[timestamps.between(start, end, inclusive="left")] = name
    return result


def _add_action_outcomes(frame: pd.DataFrame, action: str, ticks: pd.DataFrame, point: float) -> pd.DataFrame:
    result = frame.copy()
    result["action"] = action
    result["counterfactual"] = True
    result["execution_real"] = False
    entry_bid, entry_ask, entry_valid = _forward_tick_quotes(ticks, result["decision_timestamp_utc"])
    for horizon in HORIZONS:
        gross = result[f"label_future_return_{horizon}m"]
        future_spread = result[f"label_future_spread_points_{horizon}m"] * point
        proxy_long = (result["close"].shift(0) * (1+gross) - (result["close"]+result["state_spread_price"])) / (result["close"]+result["state_spread_price"])
        proxy_short = (result["close"] - (result["close"]*(1+gross)+future_spread)) / result["close"]
        exit_bid, exit_ask, exit_valid = _forward_tick_quotes(
            ticks, result["decision_timestamp_utc"] + pd.Timedelta(minutes=horizon)
        )
        real = entry_valid & exit_valid
        if action == "LONG":
            action_gross = gross
            net_real = (exit_bid-entry_ask)/entry_ask
            net_proxy = proxy_long
            mfe = result[f"label_up_excursion_{horizon}m"]
            mae = result[f"label_down_excursion_{horizon}m"]
        elif action == "SHORT":
            action_gross = -gross
            net_real = (entry_bid-exit_ask)/entry_bid
            net_proxy = proxy_short
            mfe = -result[f"label_down_excursion_{horizon}m"]
            mae = -result[f"label_up_excursion_{horizon}m"]
        else:
            action_gross = pd.Series(0.0, index=result.index).where(gross.notna())
            net_real = net_proxy = np.zeros(len(result))
            mfe = mae = pd.Series(0.0, index=result.index).where(gross.notna())
        net = np.where(real & (action != "WAIT"), net_real, net_proxy)
        net = pd.Series(net, index=result.index).where(gross.notna())
        result[f"outcome_gross_return_{horizon}m"] = action_gross
        result[f"outcome_tradable_return_{horizon}m"] = net
        result[f"outcome_mfe_{horizon}m"] = mfe
        result[f"outcome_mae_{horizon}m"] = mae
        result[f"cost_spread_return_{horizon}m"] = action_gross-net
        result[f"cost_method_{horizon}m"] = np.where(
            action == "WAIT", "NO_POSITION", np.where(real, "REAL_TICK_COST", "PROXY_COST")
        )
    result["cost_estimated_slippage"] = np.nan
    result["cost_slippage_status"] = "UNAVAILABLE_NOT_ASSUMED_ZERO"
    result["tick_source_id"] = np.where(entry_valid, "MT5-XMGLOBAL-GOLD-TICKS-SAMPLE-V1", None)
    return result


def _record_hashes(frame: pd.DataFrame, dataset_version: str) -> pd.Series:
    fingerprint = pd.util.hash_pandas_object(frame, index=False, categorize=False).to_numpy()
    return pd.Series([
        hashlib.sha256(f"{dataset_version}:{int(value):016x}".encode()).hexdigest()
        for value in fingerprint
    ], index=frame.index)


def build_experience_store_v2(project_root: Path | str, m1_manifest_path: Path | str,
                              tick_manifest_path: Path | str) -> dict[str, Any]:
    raise PermissionError("Legacy mixed-partition builder retired. Use DataEngine.build_experiences(certified_id).")
