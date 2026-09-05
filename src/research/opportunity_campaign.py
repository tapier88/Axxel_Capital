"""DEV-only large-move opportunity discovery followed by frozen-condition direction tests."""
from __future__ import annotations
from collections import Counter
from pathlib import Path
from statistics import NormalDist
from typing import Any
import hashlib, math

import numpy as np
import pandas as pd

from src.experience_store.parquet_store import ParquetExperienceStore
from src.memory.long_term_memory import LongTermMemory
from src.memory.semantic_memory import SemanticMemory
from src.utils.hashing import file_hash
from src.utils.serialization import atomic_write_json, read_json
from src.validation.multiple_testing import benjamini_hochberg
from src.validation.walk_forward import assert_no_overlap, expanding_year_splits
from src.value.opportunity_value import edge_to_cost_ratio, opportunity_labels, opportunity_value


def _num(x):
    try:
        y=float(x); return y if math.isfinite(y) else None
    except (TypeError,ValueError): return None


def _cluster_mean_ci(frame:pd.DataFrame,col:str)->tuple[float|None,float|None,list]:
    x=frame[["session_id",col]].dropna()
    if len(x)<2:return _num(x[col].mean()),None,[None,None]
    mean=float(x[col].mean()); g=x.groupby("session_id")[col].agg(["sum","count"]); n=len(g)
    infl=g["sum"]-mean*g["count"]
    se=float(np.sqrt(infl.pow(2).sum()*n/max(1,n-1))/len(x)) if n>1 else None
    return mean,se,[mean-1.96*se,mean+1.96*se] if se is not None else [None,None]


def _p_positive(mean,se):
    if mean is None or se in (None,0): return 1.0 if mean is None or mean<=0 else 0.0
    return float(1-NormalDist().cdf(mean/se))


def _derive(frame:pd.DataFrame)->pd.DataFrame:
    f=frame.copy()
    f["state_abs_return_1m"]=f.state_return_1m.abs(); f["state_abs_return_5m"]=f.state_return_5m.abs()
    f["state_abs_return_15m"]=f.state_return_15m.abs(); f["state_abs_momentum_15m"]=f.state_momentum_15m_causal.abs()
    f["state_min_distance_extreme"]=f[["state_distance_recent_high","state_distance_recent_low"]].min(axis=1)
    f["state_vol_ratio"]=f.state_volatility_15m_causal/f.state_volatility_60m_causal.replace(0,np.nan)
    f["state_atr_range_ratio"]=f.state_atr_14_causal/f.state_bar_range.replace(0,np.nan)
    return f


def _condition_mask(train:pd.DataFrame,test:pd.DataFrame,condition:dict,neighbor:float=0)->tuple[pd.Series,dict]:
    kind=condition["type"]
    if kind=="all":
        mask=pd.Series(True,index=test.index); learned={}
        for i,c in enumerate(condition["clauses"]):
            m,l=_condition_mask(train,test,c,neighbor); mask&=m; learned[f"clause_{i+1}"]=l
        return mask,learned
    if kind=="minute":
        shift=int(neighbor*15); start=max(0,condition["start"]+shift); end=min(270,condition["end"]+shift)
        return test.state_minute_of_session.between(start,end),{"start":start,"end":end}
    q=min(.99,max(.01,float(condition["q"])+neighbor*.05)); value=float(train[condition["field"]].quantile(q))
    mask=test[condition["field"]].ge(value) if kind=="qgte" else test[condition["field"]].le(value)
    return mask,{"field":condition["field"],"quantile":q,"threshold":value,"operator":kind}


def _attach_labels(frame:pd.DataFrame,h:int,k:float)->pd.DataFrame:
    f=frame.copy(); shorter={}
    for x in (5,15,30,60):
        if x<=h:
            shorter[x]=np.maximum(f[f"label_up_excursion_{x}m"].abs(),f[f"label_down_excursion_{x}m"].abs()).to_numpy()
    labels=opportunity_labels(f[f"label_up_excursion_{h}m"],f[f"label_down_excursion_{h}m"],
                              f[f"cost_spread_return_{h}m"],k=k,horizon=h,shorter_excursions=shorter)
    for name,value in labels.items():f[name]=value
    f["cost"]=f[f"cost_spread_return_{h}m"]
    f["future_return"]=f[f"label_future_return_{h}m"]
    return f


def _paired_rate_effect(selected:pd.DataFrame,baseline:pd.DataFrame)->tuple[float|None,float|None,list,float]:
    a=selected.groupby("session_id").large_future_excursion.mean(); b=baseline.groupby("session_id").large_future_excursion.mean()
    x=(a-b.reindex(a.index)).dropna()
    if len(x)<2:return _num(x.mean()),None,[None,None],1.0
    mean=float(x.mean()); se=float(x.std(ddof=1)/np.sqrt(len(x))); ci=[mean-1.96*se,mean+1.96*se]
    return mean,se,ci,_p_positive(mean,se)


def _opportunity_skeptic(entries:pd.DataFrame,baseline:pd.DataFrame,condition:dict,train:pd.DataFrame,h:int,k:float)->dict:
    if entries.empty:return {"passed":False,"failures":["no_entries"],"attacks":{}}
    session=entries.groupby("session_id").opportunity_surplus.mean().sort_values(ascending=False)
    without5=entries[entries.max_absolute_excursion<entries.max_absolute_excursion.quantile(.95)]
    without10=entries[~entries.session_id.isin(session.head(10).index)]
    weak,_=_condition_mask(train,baseline,condition,-1); strong,_=_condition_mask(train,baseline,condition,1)
    year=entries.groupby(entries.decision_timestamp_utc.dt.year).opportunity_surplus.mean()
    regime=entries.groupby("state_regime_v0").opportunity_surplus.mean()
    rng=np.random.default_rng(20260908); random_mask=pd.Series(rng.random(len(baseline))<len(entries)/max(1,len(baseline)),index=baseline.index)
    attacks={"remove_best_5pct":_num(without5.opportunity_surplus.mean()),
      "remove_top_10_sessions":_num(without10.opportunity_surplus.mean()),
      "winsorization":_num(entries.opportunity_surplus.clip(entries.opportunity_surplus.quantile(.01),entries.opportunity_surplus.quantile(.99)).mean()),
      "cost_1_5x":_num((entries.max_absolute_excursion-1.5*k*entries.cost).mean()),
      "cost_2x":_num((entries.max_absolute_excursion-2*k*entries.cost).mean()),
      "neighbor_weaker_surplus":_num(baseline.loc[weak,"opportunity_surplus"].mean()),
      "neighbor_stronger_surplus":_num(baseline.loc[strong,"opportunity_surplus"].mean()),
      "neighbor_time_window": "APPLIED" if condition["type"]=="minute" else "NOT_APPLICABLE",
      "year_means":{str(a):_num(b) for a,b in year.items()},"regime_means":{str(a):_num(b) for a,b in regime.items()},
      "gap_null_fraction":float(entries.max_absolute_excursion.isna().mean()),"synthetic_bar_flags":"NONE_PRESENT_GAPS_NOT_IMPUTED",
      "random_condition_rate":_num(baseline.loc[random_mask,"large_future_excursion"].mean()),
      "selected_rate":_num(entries.large_future_excursion.mean())}
    required=["remove_best_5pct","remove_top_10_sessions","winsorization","cost_1_5x","neighbor_weaker_surplus","neighbor_stronger_surplus"]
    failures=[x for x in required if attacks[x] is None or attacks[x]<=0]
    if sum(v is not None and v>0 for v in attacks["year_means"].values())<max(2,len(year)-1):failures.append("year_concentration")
    if attacks["gap_null_fraction"]>0.01:failures.append("gaps")
    return {"passed":not failures,"failures":failures,"attacks":attacks}


def _direction(entries:pd.DataFrame,action:str)->dict:
    f=entries.copy(); f["gross"]=f.future_return if action=="ENTER_LONG" else -f.future_return
    f["net"]=f.gross-f.cost; mean,se,ci=_cluster_mean_ci(f,"net")
    years=f.groupby(f.decision_timestamp_utc.dt.year).net.mean(); regimes=f.groupby("state_regime_v0").net.mean()
    sess=f.groupby("session_id").net.mean().sort_values(ascending=False)
    without10=f[~f.session_id.isin(sess.head(10).index)]
    attacks={"remove_best_5pct":_num(f.loc[f.net<f.net.quantile(.95),"net"].mean()),
             "remove_top_10_sessions":_num(without10.net.mean()),
             "winsorization":_num(f.net.clip(f.net.quantile(.01),f.net.quantile(.99)).mean()),
             "cost_1_5x":_num((f.gross-1.5*f.cost).mean()),"cost_2x":_num((f.gross-2*f.cost).mean())}
    skeptic=all(v is not None and v>0 for v in attacks.values())
    stable=len(years)>=3 and sum(years>0)>=max(2,len(years)-1)
    return {"action":action,"expected_gross_return":_num(f.gross.mean()),"expected_cost":_num(f.cost.mean()),
      "expected_net_return":mean,"confidence_interval_95":ci,"uncertainty":se,"raw_p_value":_p_positive(mean,se),
      "break_even_cost":_num(f.gross.mean()),"edge_to_cost_ratio_final":_num(f.gross.mean()/f.cost.mean()),
      "cost_stress":{str(x):_num((f.gross-x*f.cost).mean()) for x in (.75,1,1.25,1.5,2)},
      "temporal":{str(a):_num(b) for a,b in years.items()},"regime":{str(a):_num(b) for a,b in regimes.items()},
      "skeptic":{"passed":skeptic,"attacks":attacks},"stability_passed":stable,"support":len(f)}


class OpportunityCampaign:
    def __init__(self,root:Path|str):
        self.root=Path(root); self.config_path=self.root/"config/opportunity_campaign_v1.json"; self.config=read_json(self.config_path,{})
        if self.config.get("partition")!="DEV" or self.config.get("validation_access") or self.config.get("locked_oos_access"):
            raise PermissionError("Opportunity campaign must remain DEV-only")
        if len(self.config.get("hypotheses",[]))!=30:raise ValueError("Campaign must contain exactly 30 hypotheses")
        self.store=ParquetExperienceStore(self.root)

    def _load(self):
        state=["state_return_1m","state_return_5m","state_return_15m","state_bar_range","state_atr_14_causal",
          "state_volatility_15m_causal","state_volatility_60m_causal","state_distance_recent_high","state_distance_recent_low",
          "state_momentum_15m_causal","state_spread_points","state_tick_volume","state_minute_of_session","state_regime_v0"]
        labels=[]
        for h in (5,15,30,60):labels += [f"label_future_return_{h}m",f"label_up_excursion_{h}m",f"label_down_excursion_{h}m",f"cost_spread_return_{h}m",f"cost_method_{h}m"]
        f=self.store.query(partitions=("DEV",),action="LONG",columns=["decision_timestamp_utc","session_id",*state,*labels])
        f["decision_timestamp_utc"]=pd.to_datetime(f.decision_timestamp_utc,utc=True); return _derive(f)

    def _evaluate(self,frame,hyp):
        h=int(hyp["horizon"]); k=float(hyp["K"]); folds=[]; entry_frames=[]; train_for_skeptic=None; baseline_for_skeptic=[]
        for split in expanding_year_splits(frame.decision_timestamp_utc,first_test_year=self.config["first_test_year"],horizon_minutes=h,embargo_minutes=h):
            assert_no_overlap(frame.decision_timestamp_utc,split,h)
            train=_attach_labels(frame[split["train_mask"]],h,k); test=_attach_labels(frame[split["test_mask"]],h,k)
            mask,learned=_condition_mask(train,test,hyp["condition"]); selected=test[mask].copy()
            effect,se,ci,p=_paired_rate_effect(selected,test); initial_ratio=_num(train.loc[_condition_mask(train,train,hyp["condition"])[0],"max_absolute_excursion"].mean()/train.loc[_condition_mask(train,train,hyp["condition"])[0],"cost"].mean())
            selected["fold_year"]=split["test_year"]; entry_frames.append(selected); baseline_for_skeptic.append(test); train_for_skeptic=train
            folds.append({"test_year":split["test_year"],"eligible":len(selected),"baseline":len(test),"opportunity_rate":_num(selected.large_future_excursion.mean()),
              "baseline_rate":_num(test.large_future_excursion.mean()),"rate_lift":effect,"initial_edge_to_cost":initial_ratio,
              "learned_from_past":learned,"purge_minutes":h,"embargo_minutes":h})
        entries=pd.concat(entry_frames,ignore_index=True); baseline=pd.concat(baseline_for_skeptic,ignore_index=True)
        move=_num(entries.max_absolute_excursion.mean()); cost=_num(entries.cost.mean()); ratio=edge_to_cost_ratio(move,cost) if move and cost else None
        effect,se,ci,p=_paired_rate_effect(entries,baseline); sessions=entries.session_id.nunique(); years=entries.decision_timestamp_utc.dt.year.nunique()
        year_lifts={str(x["test_year"]):x["rate_lift"] for x in folds}; stable=years>=self.config["minimum_years"] and sum(v is not None and v>0 for v in year_lifts.values())>=max(2,years-1)
        skeptic=_opportunity_skeptic(entries,baseline,hyp["condition"],train_for_skeptic,h,k)
        support=len(entries)>=self.config["minimum_rows"] and sessions>=self.config["minimum_sessions"] and years>=self.config["minimum_years"]
        reasons=[]
        if ratio is None or ratio<=k:reasons.append("gross_edge_to_cost_below_predeclared_K")
        if ci[0] is None or ci[0]<=0:reasons.append("opportunity_rate_lift_ci_failed")
        if not support:reasons.append("minimum_support_failed")
        if not stable:reasons.append("temporal_stability_failed")
        if not skeptic["passed"]:reasons.append("opportunity_skeptic_failed")
        result={"id":hyp["id"],"type":"NEW_OPPORTUNITY_HYPOTHESIS","family":hyp["family"],"condition":hyp["condition"],
          "horizon_minutes":h,"K":k,"complexity":2 if hyp["condition"]["type"]=="all" else 1,"support":len(entries),"sessions":int(sessions),"years":int(years),
          "frequency":len(entries)/len(baseline),"opportunity_rate":_num(entries.large_future_excursion.mean()),"baseline_opportunity_rate":_num(baseline.large_future_excursion.mean()),
          "opportunity_rate_lift":effect,"lift_ci95":ci,"raw_p_value":p,"expected_move_size":move,"expected_cost":cost,"edge_to_cost_ratio":ratio,
          "opportunity_surplus":_num(entries.opportunity_surplus.mean()),"time_to_excursion":{"median_minutes":_num(entries.time_to_excursion_minutes.median()),"p75_minutes":_num(entries.time_to_excursion_minutes.quantile(.75))},
          "excursion_distribution":{f"p{x}":_num(entries.max_absolute_excursion.quantile(x/100)) for x in (50,75,90,95)},
          "walk_forward":folds,"temporal_stability":year_lifts,"regime_stability":{str(a):_num(b) for a,b in entries.groupby("state_regime_v0").opportunity_surplus.mean().items()},
          "skeptic":skeptic,"support_passed":support,"stability_passed":stable,"rejection_reasons":reasons,"status":"TESTING",
          "validation_inspected":False,"locked_oos_inspected":False}
        return result,entries

    def run(self):
        frame=self._load(); results=[]; entry_map={}
        for hyp in self.config["hypotheses"]:
            r,e=self._evaluate(frame,hyp); results.append(r); entry_map[r["id"]]=e
        q=benjamini_hochberg([r["raw_p_value"] for r in results])
        for r,x in zip(results,q):
            r["bh_fdr_q_value"]=x
            if x>.05:r["rejection_reasons"].append("bh_fdr_failed")
            r["status"]="OPPORTUNITY_SURVIVOR" if not r["rejection_reasons"] else "REJECTED"
            r["opportunity_value"]=opportunity_value(r["expected_move_size"],r["expected_cost"],r["frequency"],abs(r["opportunity_rate_lift"] or 0),complexity=r["complexity"])
            r["research_value_v3"]=_num(.35*min(1,r["edge_to_cost_ratio"]/3)+.2*min(1,r["frequency"]/.1)+.15*(1-x)+.15*min(1,r["sessions"]/500)-.08*r["complexity"])
        survivors=[r for r in results if r["status"]=="OPPORTUNITY_SURVIVOR"]
        directions=[]
        for r in survivors:
            for action in ("ENTER_LONG","ENTER_SHORT"):
                d=_direction(entry_map[r["id"]],action); d["hypothesis_id"]=r["id"]; directions.append(d)
        dq=benjamini_hochberg([d["raw_p_value"] for d in directions])
        for d,x in zip(directions,dq):
            d["bh_fdr_q_value"]=x; ci=d["confidence_interval_95"]
            ok=d["expected_net_return"] is not None and d["expected_net_return"]>0 and ci[0] is not None and ci[0]>0 and x<=.05 and d["stability_passed"] and d["skeptic"]["passed"]
            d["status"]="DIRECTION_SURVIVOR" if ok else "REJECTED"
        dev=[]
        for r in survivors:
            passed=[d for d in directions if d["hypothesis_id"]==r["id"] and d["status"]=="DIRECTION_SURVIVOR"]
            if passed:r["status"]="DEV_ECONOMIC_SURVIVOR"; dev.append(r["id"])
            elif any(d["hypothesis_id"]==r["id"] for d in directions):r["status"]="VOLATILITY_OPPORTUNITY_ONLY"
        prereg_hash=hashlib.sha256(self.config_path.read_bytes()).hexdigest()
        local_paths=[self.root.parent.parent.parent/"AppData/Roaming/MetaQuotes/Terminal/Common/Files/XAUUSD_20Y_History.csv",
                     self.root.parent.parent.parent/"AppData/Roaming/MetaQuotes/Terminal/Common/Files/XAUUSD_Deep_History.csv"]
        proxy_cost=frame["cost_spread_return_30m"].dropna(); spread=frame["state_spread_points"].dropna()
        vol_bucket=pd.qcut(frame["state_volatility_15m_causal"],4,labels=["Q1","Q2","Q3","Q4"],duplicates="drop")
        reality={"report_id":"COST_REALITY_REPORT_V1","status":"REAL_TICK_DEV_UNAVAILABLE","usable_new_sources":0,"bid_ask_coverage_dev":0.0,
          "xm_proxy_coverage_dev":1.0,"slippage":"UNAVAILABLE_NOT_ASSUMED_ZERO","local_search":{"active_terminal":"XMGlobal-MT5 6",
          "stale_second_terminal_registration":"BFB1BD1E6F2B8D41CDA133F2D2F5DF97 origin path missing",
          "ohlc_files":[], "inspection_status":"UNCERTIFIED_EXTERNAL_SOURCES_NOT_OPENED"},
          "existing_cost_source":{"SOURCE_ID":"MT5-XMGLOBAL-GOLD-M1-V1","BROKER":"XM Global Limited","SYMBOL":"GOLD/XAUUSD",
            "TIMESTAMP":"2015-01-02/2019-12-31 DEV","BID":False,"ASK":False,"SPREAD":"M1 spread points proxy",
            "PROVENANCE":"MetaTrader5 Python API M1 acquisition; broker chart bid-based",
            "HASH":self.store.manifest["file_hashes"]["DEV"]},
          "xm_proxy_distribution":{"spread_points":{f"p{x}":_num(spread.quantile(x/100)) for x in (50,75,90,95)},
            "spread_return":{f"p{x}":_num(proxy_cost.quantile(x/100)) for x in (50,75,90,95)},
            "by_minute_bucket":{str(a):_num(b) for a,b in frame.groupby((frame.state_minute_of_session//30)*30).cost_spread_return_30m.mean().items()},
            "by_regime":{str(a):_num(b) for a,b in frame.groupby("state_regime_v0").cost_spread_return_30m.mean().items()},
            "by_volatility_quartile":{str(a):_num(b) for a,b in frame.groupby(vol_bucket,observed=True).cost_spread_return_30m.mean().items()}},
          "authorized_candidates":[{"source":"HistData.com XAUUSD Generic ASCII ticks","fields":"DateTime,Bid,Ask,Volume","timezone":"EST fixed, no DST","access":"located; automated response empty, not ingested","url":"https://www.histdata.com/download-free-forex-data/"},
             {"source":"Dukascopy JForex history","fields":"best bid/ask ticks","access":"API/platform candidate; not ingested","url":"https://www.dukascopy.com/wiki/en/development/strategy-api/historical-data/history-ticks/"}],
          "mixing_policy":"No external observations were merged with XM; future source must remain separately identified and mapped",
          "comparison_to_xm_proxy":"NOT_COMPUTABLE_WITHOUT_INGESTED_INDEPENDENT_TICKS"}
        atomic_write_json(self.root/"reports/evidence/COST_REALITY_REPORT_V1.json",reality)
        summary={"campaign_id":self.config["campaign_id"],"mode":"RESEARCH_ONLY","partition":"DEV","preregistration_sha256":prereg_hash,
          "proposed":30,"executed":30,"family_distribution":dict(Counter(r["family"] for r in results)),"results":results,"direction_tests":directions,
          "status_counts":dict(Counter(r["status"] for r in results)),"opportunity_survivors":[r["id"] for r in results if r["status"] in ("VOLATILITY_OPPORTUNITY_ONLY","DEV_ECONOMIC_SURVIVOR")],
          "direction_survivors":[f"{d['hypothesis_id']}:{d['action']}" for d in directions if d["status"]=="DIRECTION_SURVIVOR"],"dev_economic_survivors":dev,
          "ranking_research_value_v3":[{"id":r["id"],"value":r["research_value_v3"],"status":r["status"]} for r in sorted(results,key=lambda z:-z["research_value_v3"])],
          "ranking_opportunity_value":[{"id":r["id"],"value":r["opportunity_value"],"status":r["status"]} for r in sorted(results,key=lambda z:-z["opportunity_value"])],
          "cost_reality_report":"reports/evidence/COST_REALITY_REPORT_V1.json","knowledge_value":1.0,"research_value":_num(np.mean([r["research_value_v3"] for r in results])),
          "opportunity_value":max([r["opportunity_value"] for r in survivors],default=0),"trade_value":max([max(0,d["expected_net_return"] or 0) for d in directions if d["status"]=="DIRECTION_SURVIVOR"],default=0),
          "abstention_value":_num(np.mean([max(0,-(d["expected_net_return"] or 0)) for d in directions])) if directions else 0.0,
          "reversal_family":{"status":"CLOSED","research_value":0.01,"labels":["REVERSAL_RELATIVE_VALIDATED_BUT_NOT_MONETIZABLE","DO_NOT_REOPEN_WITH_POSTHOC_FILTERS"]},
          "validation_reads":0,"validation_inspected":False,"locked_oos_reads":0,"locked_oos_inspected":False,"ea_created":False,"live_trading":False,
          "demo_collector":{"status":"PREPARED_NOT_EXECUTED","path":"scripts/collect_demo_ticks.py","orders_enabled":False},
          "limitations":["single-broker XM M1 proxy costs","no DEV bid/ask ticks","unknown slippage","counterfactual direction returns","2015 calibration only"],
          "highest_value_uncertainty":"Independent bid/ask and prospective slippage plus directional predictability of any robust large-move state",
          "next_recommendation":"Prompt #9 should validate data reality prospectively: run the read-only demo collector for a predeclared window, map an independent XAUUSD bid/ask source without merging brokers, and only if a frozen DEV_ECONOMIC_SURVIVOR exists design a new independent validation. Keep 2020-2022 and LOCKED_OOS closed."}
        atomic_write_json(self.root/"reports/evidence/PROMPT_8_OPPORTUNITY_CAMPAIGN.json",summary)
        atomic_write_json(self.root/"hypotheses/opportunity_registry_v1.json",results)
        value_state=read_json(self.root/"state/value_model_state.json",{})
        value_state["prompt_8"]={"reversal_family_research_value":.01,"opportunity_research_value":summary["research_value"],
          "opportunity_value":summary["opportunity_value"],"trade_value":summary["trade_value"],"abstention_value":summary["abstention_value"]}
        atomic_write_json(self.root/"state/value_model_state.json",value_state)
        research_state=read_json(self.root/"state/research_state.json",{})
        research_state["opportunity_campaign"]={"id":summary["campaign_id"],"status_counts":summary["status_counts"],
          "validation_inspected":False,"locked_oos_inspected":False,"reversal_family":"CLOSED"}
        atomic_write_json(self.root/"state/research_state.json",research_state)
        self._memory(summary,prereg_hash)
        return summary

    def _memory(self,summary,prereg_hash):
        semantic=SemanticMemory(self.root/"memory_db")
        for tag,content in [
          ("reversal-family-closed-v1","REVERSAL_RELATIVE_VALIDATED_BUT_NOT_MONETIZABLE. DO_NOT_REOPEN_WITH_POSTHOC_FILTERS. Research Value is 0.01 unless genuinely new external evidence arrives."),
          ("prompt-8-opportunity-v1",f"Prompt #8 tested 30 preregistered large-move hypotheses. Opportunity survivors={summary['opportunity_survivors']}; direction survivors={summary['direction_survivors']}; DEV economic survivors={summary['dev_economic_survivors']}. Brokers were not mixed and WAIT remains mandatory where net direction failed.")]:
            if not any(tag in x.get("tags",[]) for x in semantic.all()):
                item=semantic.add_knowledge(content,evidence_ids=[summary["campaign_id"],prereg_hash],confidence=1.0,tags=[tag,"dev-only","research-only"])
                LongTermMemory(self.root/"memory_db").promote(item)
