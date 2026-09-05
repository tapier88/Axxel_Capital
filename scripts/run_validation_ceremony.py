from pathlib import Path
import json
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from src.validation.confirmation import run_validation_ceremony

if __name__ == "__main__":
    result=run_validation_ceremony(ROOT)
    print(json.dumps({"ceremony_id":result["ceremony_id"],"verdict_counts":result["verdict_counts"],
                      "validation_sessions":result["validation_sessions"],"locked_oos_inspected":result["locked_oos_inspected"]},indent=2))
