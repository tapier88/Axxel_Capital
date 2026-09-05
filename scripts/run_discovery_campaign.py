"""Execute the bounded, reproducible DEV-only discovery campaign."""
from __future__ import annotations
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
from src.research.discovery_engine import DiscoveryEngine
if __name__=="__main__":
    result=DiscoveryEngine(ROOT).run_campaign()
    print(json.dumps({"campaign_id":result["campaign_id"],"proposed":result["proposed"],
      "executed":result["executed"],"families":result["family_distribution"],
      "statuses":result["status_counts"],"validation_inspected":result["validation_inspected"],
      "locked_oos_inspected":result["locked_oos_inspected"],
      "volatility_diagnostic":result["volatility_diagnostic"]["conclusion"]},indent=2))
