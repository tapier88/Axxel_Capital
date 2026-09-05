"""Symmetric scan of comparable intraday windows with FDR from the outset."""
from __future__ import annotations
from pathlib import Path
import pandas as pd
from src.experience_store.parquet_store import ParquetExperienceStore
from src.utils.serialization import atomic_write_json
from src.validation.multiple_testing import benjamini_hochberg
from src.validation.oos import PartitionGuard
from src.validation.permutation import session_permutation_test

def analyze_intraday_windows(project_root: Path | str, *, width: int = 15, permutations: int = 1000) -> dict:
    root=Path(project_root); PartitionGuard(root,"DISCOVERY").require("DEV","IntradayStructure")
    cols=["session_id","state_minute_of_session","label_realized_volatility_30m"]
    frame=ParquetExperienceStore(root).query(partitions=("DEV",),action="WAIT",columns=cols)
    windows=[]
    for start in range(0,270,width):
        mask=frame["state_minute_of_session"].between(start,start+width-1)
        work=frame.loc[frame["label_realized_volatility_30m"].notna(),["session_id","label_realized_volatility_30m"]].copy(); work["c"]=mask.loc[work.index]
        grouped=work.groupby(["session_id","c"])["label_realized_volatility_30m"].mean().unstack().dropna()
        effects=(grouped[True]-grouped[False]).to_numpy()
        test=session_permutation_test(effects,permutations=permutations,seed=20260903+start,direction="TWO_SIDED")
        windows.append({"start_minute":start,"end_minute":start+width-1,"effect":float(effects.mean()),
                        "sessions":len(effects),"p_value":test["p_value"]})
    adjusted=benjamini_hochberg([x["p_value"] for x in windows])
    for item,p in zip(windows,adjusted): item["fdr_p_value"]=p
    result={"partition":"DEV","symmetric":True,"width_minutes":width,"windows_tested":len(windows),
            "validation_inspected":False,"locked_oos_inspected":False,"windows":windows,
            "note":"18 equal 15m windows; the single 12:30 boundary minute is excluded from symmetry. Anomaly only; direction/tradability not inferred"}
    atomic_write_json(root/"reports/evidence/intraday_symmetric_windows_v1.json",result); return result
