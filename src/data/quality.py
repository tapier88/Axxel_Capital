"""Deterministic market checks. Findings never silently rewrite market prices."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pandera.pandas as pa

BAR_COLUMNS = ("symbol", "timestamp_utc", "open", "high", "low", "close",
               "tick_volume", "spread", "real_volume")
NUMERIC = BAR_COLUMNS[2:]


def normalize_and_validate(frame: pd.DataFrame, metadata: dict, minutes: int):
    """Return normalized bronze, cleaned silver, row-level findings and quality.

    Thresholds are fixed by policy, not estimated from future or other partitions.
    Only exact duplicate removal and stable sorting are automatic fixes.
    """
    missing = set(BAR_COLUMNS) - set(frame.columns)
    if missing:
        raise ValueError(f"Missing OHLCV columns: {sorted(missing)}")
    bronze = frame.copy().reset_index(drop=True)
    bronze.insert(0, "source_row", np.arange(len(bronze), dtype=np.int64))
    ts = pd.to_datetime(bronze.timestamp_utc, errors="raise")
    if ts.dt.tz is None:
        # Do not guess local DST folds or nonexistent clock readings.
        ts = ts.dt.tz_localize(metadata["timezone"], ambiguous="raise", nonexistent="raise")
    bronze["timestamp_utc"] = ts.dt.tz_convert("UTC")
    for col in NUMERIC:
        bronze[col] = pd.to_numeric(bronze[col], errors="raise").astype("float64")
    bronze["symbol"] = bronze.symbol.astype("string")
    findings = []

    def flag(mask, code, decision, detail):
        selected = bronze.loc[np.asarray(mask), ["source_row", "timestamp_utc"]].copy()
        selected["code"], selected["decision"], selected["detail"] = code, decision, detail
        findings.append(selected)

    # Strict normalized schema: coercions above are explicit lineage operations.
    schema = pa.DataFrameSchema({
        "symbol": pa.Column(pd.StringDtype(), nullable=False),
        "timestamp_utc": pa.Column(pd.DatetimeTZDtype(unit="ns", tz="UTC"), nullable=False),
        **{col: pa.Column(float, nullable=False) for col in NUMERIC},
    }, strict=False, coerce=False)
    schema_errors = []
    try:
        schema.validate(bronze, lazy=True)
    except pa.errors.SchemaErrors as exc:
        schema_errors = exc.failure_cases.astype(str).to_dict("records")
    finite = np.isfinite(bronze[list(NUMERIC)]).all(axis=1)
    flag(~finite, "NONFINITE_OR_NULL", "REJECT", "Nonfinite numeric observation")
    flag(bronze.timestamp_utc.isna(), "INVALID_TIME", "REJECT", "Missing timestamp")
    flag((bronze[["open", "high", "low", "close"]] <= 0).any(axis=1),
         "NONPOSITIVE_PRICE", "REJECT", "Prices must be positive")
    flag((bronze.high < bronze[["open", "close", "low"]].max(axis=1)) |
         (bronze.low > bronze[["open", "close", "high"]].min(axis=1)),
         "INVALID_OHLC", "REJECT", "OHLC bounds violated; no price replacement")
    flag(bronze.spread < 0, "NEGATIVE_SPREAD", "REJECT", "Negative spread")
    flag(bronze.spread == 0, "ZERO_SPREAD", "KEEP_FLAGGED", "Not proof of zero transaction cost")
    flag((bronze.tick_volume < 0) | (bronze.real_volume < 0),
         "NEGATIVE_VOLUME", "REJECT", "Negative volume")
    flag(bronze.tick_volume == 0, "NO_TICK_VOLUME", "KEEP_FLAGGED", "Tick coverage absent")
    flag(bronze.symbol != metadata["symbol_exact"], "SYMBOL_CHANGE", "REJECT", "Mixed instrument")
    for field in ("broker", "source_id", "point"):
        if field in bronze:
            flag(bronze[field] != metadata[field], "BROKER_OR_CONTRACT_CHANGE", "REVIEW", field)
    duplicate = frame.reset_index(drop=True).duplicated(keep="first")
    flag(duplicate, "EXACT_DUPLICATE", "FIX", "Removed from silver; retained in RAW and bronze")
    unique = bronze.loc[~duplicate]
    conflict_ids = unique.loc[unique.timestamp_utc.duplicated(keep=False), "source_row"]
    flag(bronze.source_row.isin(conflict_ids), "CONFLICTING_TIMESTAMP", "REJECT", "No keep-last arbitration")
    flag(bronze.timestamp_utc.diff() < pd.Timedelta(0), "OUT_OF_ORDER", "FIX", "Stable chronological sort")
    silver = unique.sort_values(["timestamp_utc", "source_row"], kind="stable").copy()
    delta = silver.timestamp_utc.diff()
    gap_ids = silver.loc[delta > pd.Timedelta(minutes=minutes), "source_row"]
    flag(bronze.source_row.isin(gap_ids), "GAP", "REVIEW", "Unverified session closure or missing bars; no filling")
    irregular_ids = silver.loc[(delta > pd.Timedelta(0)) & (delta < pd.Timedelta(minutes=minutes)), "source_row"]
    flag(bronze.source_row.isin(irregular_ids), "IRREGULAR_INTERVAL", "REJECT", "Interval shorter than timeframe")
    flag((bronze.timestamp_utc.astype("int64") % (minutes * 60_000_000_000)) != 0,
         "OFF_GRID_TIME", "REVIEW", "Bar clock not aligned to declared timeframe")
    jumps = silver.close.pct_change(fill_method=None).abs() > 0.02
    flag(bronze.source_row.isin(silver.loc[jumps, "source_row"]), "PRICE_JUMP", "KEEP_FLAGGED", "Fixed 2% alert, not clipping")
    stale = (silver.close == silver.close.shift()).rolling(5, min_periods=5).sum() == 5
    flag(bronze.source_row.isin(silver.loc[stale, "source_row"]), "STALE_RUN", "KEEP_FLAGGED", "Five unchanged closes; retain")
    flag(bronze.spread * metadata["point"] / bronze.close > 0.01,
         "WIDE_SPREAD", "KEEP_FLAGGED", "Spread exceeds fixed 1% of price")
    flags = pd.concat(findings, ignore_index=True)
    counts = {str(k): int(v) for k, v in flags.code.value_counts().items()}
    decisions = {str(k): int(v) for k, v in flags.decision.value_counts().items()}
    limitations = ["Broker historical calendar and contract continuity not independently verified",
                   "Bar spread is a proxy; executed slippage and historical ticks not certified"]
    if metadata.get("legacy_transformed"):
        limitations.append("Legacy source was deduplicated before preservation; original discarded observations unrecoverable")
    # Score is descriptive, not a probability; hard gates override the average.
    affected = int(flags.source_row.nunique())
    score = round(max(0.0, 100 * (1 - affected / max(1, len(bronze))) - 10), 4)
    status = "USABLE_WITH_LIMITATIONS"
    if decisions.get("REVIEW") or metadata.get("legacy_transformed"):
        status = "EXPLORATORY_ONLY"
    if decisions.get("REJECT") or schema_errors or bronze.empty:
        status = "REJECTED"
    silver["quality_flagged"] = silver.source_row.isin(flags.source_row)
    quality = {"status": status, "quality_score": score, "score_formula":
               "max(0, 100*(1-unique_flagged_rows/input_rows)-10 provenance/cost limitation points)",
               "input_rows": len(bronze), "clean_rows": len(silver), "counts": counts,
               "decisions": decisions, "limitations": limitations, "schema_errors": schema_errors,
               "tick_volume_positive_fraction": float((bronze.tick_volume > 0).mean()),
               "real_volume_positive_fraction": float((bronze.real_volume > 0).mean()),
               "zero_spread_fraction": float((bronze.spread == 0).mean()),
               "policy": "market-quality-v1-fixed-thresholds-no-imputation"}
    return bronze, silver.reset_index(drop=True), flags, quality
