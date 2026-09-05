"""Deterministic expanding-window DEV walk-forward splits."""
from __future__ import annotations

import pandas as pd


def expanding_year_splits(timestamps, *, first_test_year: int = 2016,
                          horizon_minutes: int = 30, embargo_minutes: int = 30):
    ts = pd.to_datetime(timestamps, utc=True)
    years_array = ts.dt.year if isinstance(ts, pd.Series) else ts.year
    years = sorted(set(years_array))
    splits = []
    for year in [y for y in years if y >= first_test_year]:
        boundary = pd.Timestamp(f"{year}-01-01", tz="UTC")
        train_end = boundary - pd.Timedelta(minutes=horizon_minutes)
        test_start = boundary + pd.Timedelta(minutes=embargo_minutes)
        train = ts < train_end
        test = (ts >= test_start) & (ts < pd.Timestamp(f"{year+1}-01-01", tz="UTC"))
        if train.any() and test.any():
            splits.append({"test_year": year, "train_mask": train, "test_mask": test,
                           "purge_minutes": horizon_minutes, "embargo_minutes": embargo_minutes})
    return splits


def assert_no_overlap(timestamps, split, horizon_minutes: int) -> None:
    ts = pd.to_datetime(timestamps, utc=True)
    last_train = ts[split["train_mask"]].max()
    first_test = ts[split["test_mask"]].min()
    if last_train + pd.Timedelta(minutes=horizon_minutes) >= first_test:
        raise AssertionError("purging/embargo failed")
