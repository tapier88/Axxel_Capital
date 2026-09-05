"""Read-only bulk acquisition from the connected MetaTrader 5 terminal."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

import MetaTrader5 as mt5
import pandas as pd

from src.utils.hashing import file_hash
from src.utils.serialization import atomic_write_json


def _months(start: datetime, end: datetime) -> Iterator[tuple[datetime, datetime]]:
    cursor = start
    while cursor < end:
        if cursor.month == 12:
            next_month = cursor.replace(year=cursor.year + 1, month=1, day=1)
        else:
            next_month = cursor.replace(month=cursor.month + 1, day=1)
        yield cursor, min(next_month, end)
        cursor = next_month


def frame_content_hash(frame: pd.DataFrame) -> str:
    digest = hashlib.sha256()
    digest.update("|".join(map(str, frame.columns)).encode("utf-8"))
    digest.update(pd.util.hash_pandas_object(frame, index=False, categorize=False).values.tobytes())
    return digest.hexdigest()


class MT5ReadOnlyAcquirer:
    def __init__(self, symbol: str = "GOLD"):
        self.symbol = symbol

    def __enter__(self) -> "MT5ReadOnlyAcquirer":
        if not mt5.initialize():
            raise RuntimeError(f"MT5 initialize failed: {mt5.last_error()}")
        if not mt5.symbol_select(self.symbol, True):
            mt5.shutdown()
            raise RuntimeError(f"Symbol unavailable: {self.symbol}; {mt5.last_error()}")
        return self

    def __exit__(self, *_: object) -> None:
        mt5.shutdown()

    def source_metadata(self) -> dict[str, Any]:
        symbol = mt5.symbol_info(self.symbol)
        account = mt5.account_info()
        terminal = mt5.terminal_info()
        if symbol is None or account is None or terminal is None:
            raise RuntimeError(f"MT5 metadata unavailable: {mt5.last_error()}")
        return {
            "source_id": "MT5-XMGLOBAL-GOLD-M1-V1",
            "source": "Connected MetaTrader 5 terminal via official Python API (read-only acquisition)",
            "broker": account.company,
            "server": account.server,
            "terminal_company": terminal.company,
            "terminal_build": mt5.version()[1],
            "symbol_exact": symbol.name,
            "symbol_international": "XAUUSD",
            "digits": symbol.digits,
            "point": symbol.point,
            "spread_float": bool(symbol.spread_float),
            "timezone": "UTC (POSIX timestamps returned by MetaTrader5 Python API)",
        }

    def rates_m1(self, start: datetime, end: datetime) -> pd.DataFrame:
        frames = []
        for chunk_start, chunk_end in _months(start, end):
            array = mt5.copy_rates_range(self.symbol, mt5.TIMEFRAME_M1, chunk_start, chunk_end)
            if array is None:
                raise RuntimeError(f"M1 acquisition failed {chunk_start}..{chunk_end}: {mt5.last_error()}")
            if len(array):
                frames.append(pd.DataFrame(array))
        if not frames:
            raise RuntimeError("MT5 returned no M1 bars")
        frame = pd.concat(frames, ignore_index=True)
        before = len(frame)
        frame = frame.drop_duplicates(subset=["time"], keep="last").sort_values("time").reset_index(drop=True)
        frame["timestamp_utc"] = pd.to_datetime(frame.pop("time"), unit="s", utc=True)
        frame.insert(0, "symbol", self.symbol)
        frame.attrs["boundary_duplicates_removed"] = before - len(frame)
        return frame[["symbol", "timestamp_utc", "open", "high", "low", "close",
                      "tick_volume", "spread", "real_volume"]]

    def ticks(self, start: datetime, end: datetime) -> pd.DataFrame:
        array = mt5.copy_ticks_range(self.symbol, start, end, mt5.COPY_TICKS_ALL)
        if array is None:
            raise RuntimeError(f"Tick acquisition failed: {mt5.last_error()}")
        frame = pd.DataFrame(array)
        if frame.empty:
            raise RuntimeError("MT5 returned no ticks")
        frame["timestamp_utc"] = pd.to_datetime(frame["time_msc"], unit="ms", utc=True)
        info = mt5.symbol_info(self.symbol)
        frame["mid"] = (frame["bid"] + frame["ask"]) / 2.0
        frame["spread_price"] = frame["ask"] - frame["bid"]
        frame["spread_points"] = frame["spread_price"] / info.point
        frame["source_id"] = "MT5-XMGLOBAL-GOLD-TICKS-SAMPLE-V1"
        return frame[["timestamp_utc", "bid", "ask", "mid", "spread_price", "spread_points",
                      "last", "volume", "flags", "volume_real", "source_id"]].sort_values("timestamp_utc").reset_index(drop=True)


def persist_parquet_dataset(
    frame: pd.DataFrame, *, project_root: Path, category: str, source_id: str,
    metadata: dict[str, Any], transformations: list[str],
) -> dict[str, Any]:
    raise PermissionError("Legacy RAW publication retired; use immutable Data Engine ingestion.")
