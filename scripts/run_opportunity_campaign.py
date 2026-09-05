"""Run Prompt #8's bounded DEV opportunity campaign."""
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from src.research.opportunity_campaign import OpportunityCampaign
if __name__=="__main__":
    x=OpportunityCampaign(ROOT).run()
    print(json.dumps({k:x[k] for k in ("campaign_id","proposed","executed","status_counts","opportunity_survivors","direction_survivors","dev_economic_survivors","validation_reads","locked_oos_reads")},indent=2))
