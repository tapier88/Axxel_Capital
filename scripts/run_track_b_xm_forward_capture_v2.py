"""Readiness entry point. No market start authorization or quote API calls."""
import argparse
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from src.data.engine import DataEngine


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--config',default='config/track_b_xm_forward_capture_v2.json')
    p.add_argument('--start-authorized-capture',action='store_true')
    args=p.parse_args()
    worker=DataEngine(ROOT).track_b_forward_capture_v2(args.config)
    if args.start_authorized_capture:
        worker.start_market_capture()  # always DENY in this implementation approval
    print(json.dumps({'implementation':'TRACK_B_XM_FORWARD_CAPTURE_V2',
        'config_sha256':worker.config_hash,'activation':False,'t0':None,
        'market_capture':'NOT_AUTHORIZED','g4':False,'storage_root':None}))


if __name__=='__main__':main()
