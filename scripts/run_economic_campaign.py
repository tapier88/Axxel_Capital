"""Run the bounded Prompt #7 DEV-only economic campaign."""
from __future__ import annotations
import json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
from src.research.economic_campaign import EconomicCampaign

if __name__ == "__main__":
    result=EconomicCampaign(ROOT).run()
    print(json.dumps({k:result[k] for k in ("campaign_id","proposed","executed","status_counts",
        "dev_economic_survivors","validation_reads","locked_oos_reads")},indent=2))
