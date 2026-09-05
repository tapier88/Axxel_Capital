"""Explicit entry point for the authorized read-only Track B worker."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.data.track_b_forward_capture import TrackBForwardCapture


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config/track_b_xm_forward_capture_v1.json")
    parser.add_argument("--start-authorized-capture", action="store_true")
    parser.add_argument("--duration-seconds", type=int)
    args = parser.parse_args()
    worker = TrackBForwardCapture(ROOT, args.config)
    if not args.start_authorized_capture:
        print(json.dumps({
            "status": "READY_NOT_STARTED", "config_sha256": worker.config_sha256,
            "t0_registered": (worker.control / "t0.json").exists(),
            "orders_authorized": False, "fills_authorized": False,
            "research_authorized": False, "g4_fulfilled": False,
        }, indent=2))
        return 0
    worker.run(args.duration_seconds)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
