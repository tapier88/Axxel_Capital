"""Acquire immutable public OHLCV data through the read-only MarketData MCP."""

from __future__ import annotations
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.data.mcp_client import MarketDataClient
from src.utils.hashing import content_hash
from src.utils.serialization import atomic_write_json


def main() -> int:
    raise PermissionError("Legacy acquisition disabled before network access. Use scripts/run_data_engine.py with a bounded DEV Parquet source.")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--symbol", default="XAUUSD")
    parser.add_argument("--timeframe", default="1h", choices=("1h", "4h", "1d", "1w", "1mo"))
    parser.add_argument("--from", dest="start", default="2000-01-01T00:00:00Z")
    parser.add_argument("--to", dest="end", default=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"))
    args = parser.parse_args()
    response = MarketDataClient(PROJECT_ROOT).history(args.symbol, args.timeframe, args.start, args.end)
    bars = response["bars"]
    if not bars:
        raise SystemExit("No real market bars returned; no raw artifact created")
    artifact = {
        "metadata": {
            "symbol": args.symbol.upper(), "timeframe": args.timeframe,
            "timeframe_minutes": {"1h": 60, "4h": 240, "1d": 1440, "1w": 10080, "1mo": 43200}[args.timeframe],
            "timezone": "UTC", "source": "MetaTrader MarketData MCP (public, read-only)",
            "canonical_url": response.get("url"), "resolved_symbol": response.get("resolved_symbol"),
            "requested_from": args.start, "requested_to": args.end,
            "retrieved_at": datetime.now(timezone.utc).isoformat(), "records": len(bars),
        },
        "bars": bars,
    }
    digest = content_hash(bars)
    path = PROJECT_ROOT / "data" / "raw" / args.symbol.lower() / f"{args.symbol.lower()}_{args.timeframe}_{digest[:12]}.json"
    if not path.exists():
        atomic_write_json(path, artifact)
    print(json.dumps({"path": str(path), "records": len(bars), "bars_hash": digest,
                      "first": bars[0]["time"], "last": bars[-1]["time"],
                      "canonical_url": response.get("url")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
