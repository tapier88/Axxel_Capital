"""Scalable quality audits for canonical M1 bars and bid/ask ticks."""

from __future__ import annotations
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from src.utils.serialization import atomic_write_json


def audit_m1(frame: pd.DataFrame) -> dict[str, Any]:
    timestamps = frame["timestamp_utc"]
    delta_minutes = timestamps.diff().dt.total_seconds().div(60)
    gaps = delta_minutes[delta_minutes > 1]
    gap_rows = frame.loc[gaps.index, ["timestamp_utc"]].copy()
    gap_rows["previous_timestamp_utc"] = timestamps.shift(1).loc[gaps.index]
    gap_rows["minutes"] = gaps
    weekend_gap = (gap_rows["minutes"] >= 24 * 60) | (
        (gap_rows["previous_timestamp_utc"].dt.dayofweek >= 4)
        & (gap_rows["timestamp_utc"].dt.dayofweek <= 1)
        & (gap_rows["minutes"] >= 12 * 60)
    )
    daily_pause = gap_rows["minutes"].between(30, 180)
    gap_durations = Counter(int(value) for value in gaps.tolist())
    returns = frame["close"].pct_change(fill_method=None).abs()
    median = float(returns.median())
    mad = float((returns - median).abs().median())
    jump_threshold = median + 20 * mad if mad > 0 else 0.05
    price_columns = ["open", "high", "low", "close"]
    invalid_ohlc = ~(
        frame["low"].le(frame[price_columns].min(axis=1))
        & frame["high"].ge(frame[price_columns].max(axis=1))
    )
    cot = timestamps.dt.tz_convert("America/Bogota")
    decision_minutes = (cot + pd.Timedelta(minutes=1)).dt.hour * 60 + (cot + pd.Timedelta(minutes=1)).dt.minute
    session_mask = decision_minutes.between(8 * 60, 12 * 60 + 30)
    session_counts = frame.loc[session_mask].groupby(cot[session_mask].dt.date).size()
    incomplete = session_counts[session_counts < 271]
    scaled = frame[price_columns].to_numpy(dtype=float) * 100
    digit_violations = int((np.abs(scaled - np.round(scaled)) > 1e-7).any(axis=1).sum())
    return {
        "rows": int(len(frame)), "duplicate_timestamps": int(timestamps.duplicated().sum()),
        "timestamps_out_of_order": int((timestamps.diff().dt.total_seconds() < 0).sum()),
        "nulls": {column: int(frame[column].isna().sum()) for column in frame.columns},
        "invalid_ohlc": int(invalid_ohlc.sum()),
        "nonpositive_prices": int((frame[price_columns] <= 0).any(axis=1).sum()),
        "negative_spread": int((frame["spread"] < 0).sum()), "zero_spread": int((frame["spread"] == 0).sum()),
        "negative_tick_volume": int((frame["tick_volume"] < 0).sum()),
        "real_volume_nonzero": int((frame["real_volume"] > 0).sum()),
        "gaps_over_one_minute": int(len(gaps)),
        "gap_duration_minutes_top": [{"minutes": key, "count": value} for key, value in gap_durations.most_common(15)],
        "largest_gap_minutes": int(gaps.max()) if len(gaps) else 0,
        "weekend_or_multiday_gap_candidates": int(weekend_gap.sum()),
        "daily_broker_pause_candidates_30_to_180m": int(daily_pause.sum()),
        "unexplained_short_gap_candidates_2_to_29m": int(gaps.between(2, 29).sum()),
        "anomalous_jump_threshold_abs_return": jump_threshold,
        "anomalous_jump_count": int((returns > jump_threshold).sum()),
        "two_decimal_digit_violations": digit_violations,
        "research_sessions_observed": int(len(session_counts)),
        "incomplete_research_sessions": int(len(incomplete)),
        "incomplete_session_examples": [{"date": str(date), "minutes": int(count)} for date, count in incomplete.head(20).items()],
        "synthetic_bar_candidates": int(((frame["open"] == frame["high"]) & (frame["high"] == frame["low"])
                                           & (frame["low"] == frame["close"]) & (frame["tick_volume"] <= 1)).sum()),
        "timezone": "UTC POSIX; America/Bogota has no DST",
        "blocking_errors": bool(timestamps.duplicated().any() or (timestamps.diff().dt.total_seconds() < 0).any()
                                or invalid_ohlc.any() or (frame[price_columns] <= 0).any(axis=1).any()
                                or (frame["spread"] < 0).any()),
    }


def audit_ticks(frame: pd.DataFrame) -> dict[str, Any]:
    timestamps = frame["timestamp_utc"]
    return {
        "rows": int(len(frame)),
        "nulls": {column: int(frame[column].isna().sum()) for column in frame.columns},
        "duplicate_exact_ticks": int(frame.duplicated(subset=["timestamp_utc", "bid", "ask"]).sum()),
        "timestamps_out_of_order": int((timestamps.diff().dt.total_seconds() < 0).sum()),
        "nonpositive_bid_or_ask": int(((frame["bid"] <= 0) | (frame["ask"] <= 0)).sum()),
        "bid_greater_than_ask": int((frame["bid"] > frame["ask"]).sum()),
        "negative_spread": int((frame["spread_price"] < 0).sum()),
        "zero_spread": int((frame["spread_price"] == 0).sum()),
        "spread_points": {
            "min": float(frame["spread_points"].min()), "median": float(frame["spread_points"].median()),
            "p95": float(frame["spread_points"].quantile(0.95)), "max": float(frame["spread_points"].max()),
        },
        "blocking_errors": bool((timestamps.diff().dt.total_seconds() < 0).any()
                                or ((frame["bid"] <= 0) | (frame["ask"] <= 0)).any()
                                or (frame["bid"] > frame["ask"]).any()),
    }


def audit_parquet(m1_path: Path | str, tick_path: Path | str, output: Path | str) -> dict[str, Any]:
    raise PermissionError("Unbounded legacy audit retired; use Data Engine on a bounded DEV source.")
