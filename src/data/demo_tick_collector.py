"""Bounded read-only prospective bid/ask collection; contains no trading capability."""
from __future__ import annotations
from datetime import datetime, timedelta, timezone
from pathlib import Path
import hashlib

import MetaTrader5 as mt5
import pandas as pd

from src.utils.serialization import atomic_write_json


def validate_prospective_window(start:datetime,end:datetime,*,now:datetime|None=None)->None:
    now=now or datetime.now(timezone.utc)
    if start.tzinfo is None or end.tzinfo is None:raise ValueError("UTC-aware timestamps required")
    if start < now-timedelta(minutes=5):raise PermissionError("collector is prospective only; historical/locked periods forbidden")
    if end<=start or end-start>timedelta(hours=24):raise ValueError("window must be positive and no longer than 24 hours")


def collect_demo_ticks(start:datetime,end:datetime,output_root:Path|str,*,symbol:str="GOLD")->dict:
    raise PermissionError("Tick publication awaits a Data Engine tick schema and a separately frozen prospective partition policy.")
    validate_prospective_window(start,end)
    if not mt5.initialize():raise RuntimeError(f"MT5 initialize failed: {mt5.last_error()}")
    try:
        account=mt5.account_info(); terminal=mt5.terminal_info(); info=mt5.symbol_info(symbol)
        if account is None or terminal is None or info is None:raise RuntimeError("terminal metadata unavailable")
        array=mt5.copy_ticks_range(symbol,start,end,mt5.COPY_TICKS_ALL)
        if array is None or not len(array):raise RuntimeError("no ticks returned")
        f=pd.DataFrame(array); f["timestamp_utc"]=pd.to_datetime(f.time_msc,unit="ms",utc=True)
        f["mid"]=(f.bid+f.ask)/2; f["spread"]=f.ask-f.bid
        for ms in (100,500,1000):
            target=f[["timestamp_utc","mid"]].copy(); target["timestamp_utc"]-=pd.Timedelta(milliseconds=ms)
            target=target.rename(columns={"mid":f"future_mid_{ms}ms"})
            f=pd.merge_asof(f.sort_values("timestamp_utc"),target.sort_values("timestamp_utc"),on="timestamp_utc",direction="forward")
            f[f"potential_slippage_{ms}ms"]=(f[f"future_mid_{ms}ms"]-f.mid).abs()
        keep=["timestamp_utc","bid","ask","mid","spread","volume","flags","volume_real",
              "potential_slippage_100ms","potential_slippage_500ms","potential_slippage_1000ms"]
        f=f[keep]; digest=hashlib.sha256(pd.util.hash_pandas_object(f,index=False).values.tobytes()).hexdigest()
        root=Path(output_root)/"data"/"prospective"/"demo_ticks"; root.mkdir(parents=True,exist_ok=True)
        path=root/f"demo-{symbol.lower()}-{digest[:16]}.parquet"; f.to_parquet(path,index=False,compression="zstd")
        manifest={"SOURCE_ID":f"DEMO-{account.server}-{symbol}-TICKS-V1","BROKER":account.company,"SYMBOL":symbol,
          "TIMESTAMP":{"from":start.isoformat(),"to":end.isoformat()},"BID":True,"ASK":True,"SPREAD":True,
          "PROVENANCE":"MetaTrader5 Python API COPY_TICKS_ALL, read-only prospective collection","HASH":digest,
          "digits":info.digits,"contract_size":info.trade_contract_size,"trading_hours":"broker-defined",
          "timezone":"UTC","rows":len(f),"terminal_build":mt5.version()[1],"orders_sent":0,
          "potential_slippage":"absolute mid movement after 100/500/1000ms; observation proxy, not a fill",
          "path":str(path)}
        atomic_write_json(path.with_suffix(".manifest.json"),manifest);return manifest
    finally:mt5.shutdown()
