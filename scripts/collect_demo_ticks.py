"""Prepare/read-only prospective tick collection. Does not place or simulate orders."""
from __future__ import annotations
import argparse,json,sys
from datetime import datetime
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from src.data.demo_tick_collector import collect_demo_ticks,validate_prospective_window

def parse(value):return datetime.fromisoformat(value.replace("Z","+00:00"))
if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--from-utc",required=True);p.add_argument("--to-utc",required=True)
    p.add_argument("--symbol",default="GOLD");p.add_argument("--dry-run",action="store_true");a=p.parse_args()
    start,end=parse(a.from_utc),parse(a.to_utc);validate_prospective_window(start,end)
    print(json.dumps({"status":"READY_NOT_EXECUTED","orders_enabled":False,"from":start.isoformat(),"to":end.isoformat()}) if a.dry_run
          else json.dumps(collect_demo_ticks(start,end,ROOT,symbol=a.symbol),indent=2))
