"""Shared causal and temporal isolation assertions for research and ML."""
from __future__ import annotations

import pandas as pd


def assert_causal_sources(frame: pd.DataFrame) -> None:
    source = pd.to_datetime(frame["state_max_source_timestamp_utc"], utc=True)
    decision = pd.to_datetime(frame["decision_timestamp_utc"], utc=True)
    if not (source < decision).all():
        raise AssertionError("A feature source reaches or crosses the decision boundary")


def assert_purged_segments(timestamps, *segments, horizon_minutes: int) -> None:
    ts = pd.Series(pd.to_datetime(timestamps, utc=True)).reset_index(drop=True)
    if not ts.is_monotonic_increasing or ts.duplicated().any():
        raise AssertionError("Temporal training requires unique ordered decisions")
    for left, right in zip(segments[:-1], segments[1:]):
        if not len(left) or not len(right):
            raise AssertionError("Empty temporal segment")
        if ts.iloc[left].max() + pd.Timedelta(minutes=horizon_minutes) >= ts.iloc[right].min():
            raise AssertionError("Label interval overlaps the following temporal segment")
