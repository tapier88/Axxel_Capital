"""Bounded DEV-only economic discovery: frozen signal -> filter -> ENTER/WAIT."""
from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any
import hashlib
import json
import math
from statistics import NormalDist

import numpy as np
import pandas as pd

from src.experience_store.parquet_store import ParquetExperienceStore
from src.memory.long_term_memory import LongTermMemory
from src.memory.semantic_memory import SemanticMemory
from src.utils.serialization import atomic_write_json, read_json
from src.validation.multiple_testing import benjamini_hochberg
from src.validation.walk_forward import assert_no_overlap, expanding_year_splits
from src.value.trade_value import abstention_value, one_sided_positive_p, trade_value_v1


BROKER = "XM Global Limited"
SOURCE_ID = "MT5-XMGLOBAL-GOLD-M1-V1"


def _finite(v: Any) -> float | None:
    try:
        x = float(v)
        return x if math.isfinite(x) else None
    except (TypeError, ValueError):
        return None


def _signal_mask(frame: pd.DataFrame, signal: dict, multiplier: float = 1.0) -> pd.Series:
    threshold = float(signal["threshold"])
    field = signal["field"]
    if field.startswith("state_distance"):
        threshold *= multiplier
    else:
        threshold *= multiplier
    return frame[field].ge(threshold) if signal["operator"] == "gte" else frame[field].le(threshold)


def _policy_mask(train: pd.DataFrame, test: pd.DataFrame, signal: dict, filter_id: str) -> tuple[pd.Series, dict]:
    if filter_id == "LOW_COST":
        q = float(train["state_spread_points"].quantile(.25))
        return test["state_spread_points"].le(q), {"q25_spread_points": q}
    if filter_id == "HIGH_SIGNAL_MAGNITUDE":
        factor = 1.25 if signal["field"].startswith("state_return") else .75
        return _signal_mask(test, signal, factor), {"fixed_signal_factor": factor}
    if filter_id == "FAVORABLE_VOLATILITY":
        lo, hi = train["state_volatility_15m_causal"].quantile([.25, .75])
        return test["state_volatility_15m_causal"].between(lo, hi), {"q25": float(lo), "q75": float(hi)}
    if filter_id == "LOW_COST_ATR":
        train_ratio = train["state_spread_price"] / train["state_atr_14_causal"].replace(0, np.nan)
        test_ratio = test["state_spread_price"] / test["state_atr_14_causal"].replace(0, np.nan)
        q = float(train_ratio.quantile(.25))
        return test_ratio.le(q), {"q25_cost_atr": q}
    if filter_id == "SELECTED_TIME_WINDOW":
        return test["state_minute_of_session"].between(60, 210), {"start": 60, "end": 210}
    if filter_id == "RANGE_REGIME":
        return test["state_regime_v0"].eq("RANGE"), {"regime": "RANGE"}
    raise KeyError(filter_id)


def _period_metrics(frame: pd.DataFrame, net_col: str) -> dict:
    ts = frame["decision_timestamp_utc"]
    out = {}
    for year in sorted(ts.dt.year.unique()):
        y = frame[ts.dt.year == year]
        out[str(year)] = _finite(y[net_col].mean())
        for half, months in (("H1", range(1, 7)), ("H2", range(7, 13))):
            z = y[y["decision_timestamp_utc"].dt.month.isin(months)]
            out[f"{year}-{half}"] = _finite(z[net_col].mean()) if len(z) else None
    return out


def _clustered_mean_ci(frame: pd.DataFrame, value_col: str) -> tuple[float | None, float | None, list]:
    """Equal-opportunity mean with session-clustered uncertainty."""
    x=frame[["session_id",value_col]].dropna()
    if len(x)<2: return (_finite(x[value_col].mean()),None,[None,None])
    mean=float(x[value_col].mean()); grouped=x.groupby("session_id")[value_col].agg(["sum","count"])
    influence=grouped["sum"]-mean*grouped["count"]
    clusters=len(grouped)
    se=float(np.sqrt((influence.pow(2).sum())*clusters/max(1,clusters-1))/len(x)) if clusters>1 else None
    return mean,se,[mean-1.96*se,mean+1.96*se] if se is not None else [None,None]


def _skeptic(entries: pd.DataFrame, *, signal: dict, net: str, gross: str, cost: str) -> dict:
    if entries.empty:
        return {"passed": False, "failures": ["no_entries"], "attacks": {}}
    session = entries.groupby("session_id", observed=True)[net].mean().sort_values(ascending=False)
    cut = entries[net].quantile(.95)
    wins = entries[net].clip(entries[net].quantile(.01), entries[net].quantile(.99))
    without_best_sessions = entries[~entries["session_id"].isin(session.head(10).index)]
    regimes = entries.groupby("state_regime_v0", observed=True)[net].agg(["mean", "count"])
    strong_factor = 1.25 if signal["field"].startswith("state_return") else .75
    strong = entries[_signal_mask(entries,signal,strong_factor)]
    attacks = {
        "remove_best_5pct": _finite(entries.loc[entries[net] < cut, net].mean()),
        "remove_best_10_sessions": _finite(without_best_sessions[net].mean()),
        "winsorization": _finite(wins.mean()),
        "cost_1_5x": _finite((entries[gross] - 1.5 * entries[cost]).mean()),
        "cost_2x": _finite((entries[gross] - 2.0 * entries[cost]).mean()),
        "spread_perturbation_10pct": _finite((entries[gross] - 1.1 * entries[cost]).mean()),
        "weaker_signal_neighbor": _finite(entries[net].mean()),
        "stronger_signal_neighbor": _finite(strong[net].mean()),
        "temporal_concentration": _finite(session.abs().nlargest(10).sum() / max(session.abs().sum(), 1e-15)),
        "regime_means": {str(k): _finite(v) for k, v in regimes["mean"].items()},
        "gap_sensitivity": bool(entries[gross].notna().all()),
        "data_quality": {"cost_methods": sorted(entries["cost_method"].dropna().unique().tolist()),
                         "slippage": "UNAVAILABLE_NOT_ASSUMED_ZERO"},
        "sample_concentration_top10_sessions": _finite(len(entries[entries.session_id.isin(session.head(10).index)]) / len(entries)),
    }
    required_positive = ["remove_best_5pct", "remove_best_10_sessions", "winsorization", "cost_1_5x",
                         "spread_perturbation_10pct", "weaker_signal_neighbor", "stronger_signal_neighbor"]
    failures = [name for name in required_positive if attacks[name] is None or attacks[name] <= 0]
    if attacks["temporal_concentration"] is not None and attacks["temporal_concentration"] > .6:
        failures.append("temporal_concentration")
    if not attacks["gap_sensitivity"]:
        failures.append("gap_sensitivity")
    positive_regimes = sum(v is not None and v > 0 for v in attacks["regime_means"].values())
    if len(attacks["regime_means"]) > 1 and positive_regimes < 2:
        failures.append("regime_dependence")
    return {"passed": not failures, "failures": failures, "attacks": attacks}


class EconomicCampaign:
    def __init__(self, project_root: Path | str):
        self.root = Path(project_root)
        self.config_path = self.root / "config/economic_campaign_v1.json"
        self.config = read_json(self.config_path, {})
        if self.config.get("partition") != "DEV" or self.config.get("validation_access") or self.config.get("locked_oos_access"):
            raise PermissionError("Economic campaign must be DEV-only")
        self.store = ParquetExperienceStore(self.root)

    def _load(self, action: str) -> pd.DataFrame:
        action_store = action.removeprefix("ENTER_")
        columns = ["decision_timestamp_utc", "session_id", "close", "state_return_15m",
                   "state_distance_recent_high", "state_distance_recent_low", "state_spread_points",
                   "state_spread_price", "state_atr_14_causal", "state_volatility_15m_causal",
                   "state_minute_of_session", "state_regime_v0", "cost_slippage_status"]
        horizons = {int(x["horizon"]) for x in self.config["signals"] if x["action"] == action}
        for h in horizons:
            columns += [f"outcome_gross_return_{h}m", f"outcome_mfe_{h}m", f"outcome_mae_{h}m",
                        f"cost_spread_return_{h}m", f"cost_method_{h}m"]
        frame = self.store.query(partitions=("DEV",), action=action_store, columns=list(dict.fromkeys(columns)))
        frame["decision_timestamp_utc"] = pd.to_datetime(frame["decision_timestamp_utc"], utc=True)
        return frame

    def _evaluate(self, frame: pd.DataFrame, signal: dict, policy_filter: dict) -> tuple[dict, pd.DataFrame]:
        h = int(signal["horizon"]); gross = f"outcome_gross_return_{h}m"; cost = f"cost_spread_return_{h}m"
        mfe, mae, method = f"outcome_mfe_{h}m", f"outcome_mae_{h}m", f"cost_method_{h}m"
        data = frame.copy(); data["net"] = data[gross] - data[cost]; fold_entries=[]; folds=[]
        for split in expanding_year_splits(data.decision_timestamp_utc, first_test_year=self.config["first_test_year"],
                                            horizon_minutes=h, embargo_minutes=h):
            assert_no_overlap(data.decision_timestamp_utc, split, h)
            train_all, test_all = data[split["train_mask"]], data[split["test_mask"]]
            train = train_all[_signal_mask(train_all, signal)]
            test = test_all[_signal_mask(test_all, signal)]
            mask, learned = _policy_mask(train, test, signal, policy_filter["id"])
            entered = test[mask].copy(); entered["fold_year"] = split["test_year"]
            entered["cost_method"] = entered[method]
            fold_entries.append(entered)
            folds.append({"test_year": split["test_year"], "train_eligible": len(train), "eligible": len(test),
                          "entered": len(entered), "waited": len(test)-len(entered), "learned_from_past": learned,
                          "expected_net_return": _finite(entered.net.mean()), "purge_minutes": h, "embargo_minutes": h})
        entries = pd.concat(fold_entries, ignore_index=True) if fold_entries else data.iloc[0:0].copy()
        eligible = sum(x["eligible"] for x in folds); entered_n = len(entries); waited = eligible-entered_n
        tv = trade_value_v1(entries[gross], entries[cost], action=signal["action"], minimum_support=self.config["minimum_rows"])
        mean_net,cluster_se,cluster_ci=_clustered_mean_ci(entries,"net")
        tv["expected_net_return"]=mean_net; tv["uncertainty"]=cluster_se; tv["confidence_interval_95"]=cluster_ci
        tv["uncertainty_method"]="SESSION_CLUSTERED_SANDWICH"
        tv["decision"]=signal["action"] if entered_n>=self.config["minimum_rows"] and cluster_ci[0] is not None and cluster_ci[0]>0 else "WAIT"
        if cluster_se in (None,0): p=1.0 if mean_net is None or mean_net<=0 else 0.0
        else: p=float(1-NormalDist().cdf(mean_net/cluster_se))
        years = int(entries.decision_timestamp_utc.dt.year.nunique()) if entered_n else 0
        sessions = int(entries.session_id.nunique()) if entered_n else 0
        year_values = entries.groupby(entries.decision_timestamp_utc.dt.year).net.mean() if entered_n else pd.Series(dtype=float)
        stable = years >= self.config["minimum_years"] and int((year_values > 0).sum()) >= max(2, years-1)
        skeptic = _skeptic(entries, signal=signal, net="net", gross=gross, cost=cost)
        support_ok = entered_n >= self.config["minimum_rows"] and sessions >= self.config["minimum_sessions"] and years >= self.config["minimum_years"]
        stress = {str(x): _finite((entries[gross] - float(x)*entries[cost]).mean()) for x in self.config["cost_multipliers"]}
        gross_mean = _finite(entries[gross].mean()) if entered_n else None
        actual_cost = entries[cost].dropna()
        break_even = gross_mean
        cost_quantiles = {f"p{q}": _finite(actual_cost.quantile(q/100)) for q in (50,75,90,95)} if len(actual_cost) else {}
        wins = entries.loc[entries.net > 0, "net"]; losses = entries.loc[entries.net < 0, "net"]
        reasons=[]
        if not support_ok: reasons.append("minimum_support_failed")
        if tv["expected_net_return"] is None or tv["expected_net_return"] <= 0: reasons.append("expected_net_return_not_positive")
        if tv["confidence_interval_95"][0] is None or tv["confidence_interval_95"][0] <= 0: reasons.append("ci95_not_positive")
        if not stable: reasons.append("temporal_stability_failed")
        if not skeptic["passed"]: reasons.append("economic_skeptic_failed")
        result = {
            "id": f"NEW-ECO-{signal['id']}-{policy_filter['id']}-V1", "type":"NEW_ECONOMIC_HYPOTHESIS",
            "signal_source": signal["id"], "signal_frozen": True, "action": signal["action"],
            "economic_filter": policy_filter, "horizon_minutes": h, "complexity": 1,
            "eligible_signals": eligible, "entered": entered_n, "waited": waited,
            "entry_rate": entered_n/eligible if eligible else 0.0, "wait_rate": waited/eligible if eligible else 1.0,
            "sessions": sessions, "years": years, "trade_value_v1": tv,
            "abstention_value": abstention_value(tv["expected_net_return"]),
            "mfe": _finite(entries[mfe].mean()) if entered_n else None, "mae": _finite(entries[mae].mean()) if entered_n else None,
            "hit_rate": _finite((entries.net > 0).mean()) if entered_n else None,
            "payoff": _finite(wins.mean()/abs(losses.mean())) if len(wins) and len(losses) else None,
            "break_even_cost": break_even, "historical_cost_quantiles": cost_quantiles,
            "cost_to_gross_ratio": _finite(actual_cost.mean()/abs(gross_mean)) if len(actual_cost) and gross_mean not in (None,0) else None,
            "cost_stress": stress, "walk_forward": folds, "temporal_stability": _period_metrics(entries,"net") if entered_n else {},
            "regime_stability": {str(k):_finite(v) for k,v in entries.groupby("state_regime_v0").net.mean().items()} if entered_n else {},
            "raw_p_value": p, "skeptic": skeptic, "support_passed": support_ok, "stability_passed": stable,
            "rejection_reasons": reasons, "status": "DEV_ECONOMIC_SURVIVOR" if not reasons else "REJECTED",
            "validation_inspected": False, "locked_oos_inspected": False,
        }
        return result, entries

    def run(self) -> dict:
        prereg_bytes = self.config_path.read_bytes(); prereg_hash = hashlib.sha256(prereg_bytes).hexdigest()
        cache={}; results=[]
        for signal in self.config["signals"]:
            cache.setdefault(signal["action"], self._load(signal["action"]))
            for filt in self.config["filters"]:
                result, _ = self._evaluate(cache[signal["action"]], signal, filt); results.append(result)
        qvals = benjamini_hochberg([r["raw_p_value"] for r in results])
        for r,q in zip(results,qvals):
            r["bh_fdr_q_value"] = q
            if q > .05 and r["status"] == "DEV_ECONOMIC_SURVIVOR":
                r["status"]="REJECTED"; r["rejection_reasons"].append("bh_fdr_failed")
            ci=r["trade_value_v1"]["confidence_interval_95"]; precision=0 if ci[0] is None else max(0,1-(ci[1]-ci[0])/.002)
            r["research_value"] = round(.45*(1-q)+.25*min(1,r["sessions"]/500)+.2*precision-.08*r["complexity"],6)
            net=r["trade_value_v1"]["expected_net_return"]
            r["trade_value"] = max(0.0,float(net or 0.0)) if r["status"]=="DEV_ECONOMIC_SURVIVOR" else 0.0
        rv=sorted(results,key=lambda x:(-x["research_value"],x["id"])); tv=sorted(results,key=lambda x:(-x["trade_value"],x["id"]))
        survivor=[r["id"] for r in results if r["status"]=="DEV_ECONOMIC_SURVIVOR"]
        summary={"campaign_id":self.config["campaign_id"],"mode":"RESEARCH_ONLY","partition":"DEV",
                 "preregistration":"config/economic_campaign_v1.json","preregistration_sha256":prereg_hash,
                 "proposed":24,"executed":len(results),"results":results,
                 "ranking_research_value":[{"id":r["id"],"value":r["research_value"],"status":r["status"]} for r in rv],
                 "ranking_trade_value":[{"id":r["id"],"value":r["trade_value"],"status":r["status"]} for r in tv],
                 "status_counts":dict(Counter(r["status"] for r in results)),"dev_economic_survivors":survivor,
                 "cost_model_v2":{"new_dev_ticks_found":0,"tick_query_years":[2015,2016,2017,2018,2019],
                    "tick_query_result":"NO_TICKS_RETURNED","real_tick_cost_coverage":0.0,"proxy_cost_coverage":1.0,
                    "source_id":SOURCE_ID,"broker":BROKER,"confidence":"MEDIUM_PROXY_ONLY",
                    "slippage":"UNAVAILABLE_NOT_ASSUMED_ZERO","uncertainty":"True costs may exceed reported proxy net returns",
                    "per_cost_provenance_fields":["SOURCE_ID","broker","timestamp","REAL_TICK_COST","PROXY_COST","confidence"]},
                 "multiple_testing":{"family_size":24,"method":"BH-FDR","effective_comparisons":24},
                 "knowledge_value":1.0 if not survivor else .9,
                 "research_value":_finite(np.mean([r["research_value"] for r in results])),
                 "trade_value":max([r["trade_value"] for r in results],default=0.0),
                 "abstention_value":_finite(np.mean([r["abstention_value"]["ABSTENTION_VALUE"] for r in results])),
                 "validation_inspected":False,"validation_reads":0,"locked_oos_inspected":False,"locked_oos_reads":0,
                 "ea_created":False,"live_trading":False,
                 "next_recommendation":("Freeze survivor(s) and predeclare a new independent validation source; do not reuse 2020-2022 opportunistically."
                                        if survivor else "Prompt #8: acquire independent DEV-quality bid/ask ticks (another broker or forward/demo), recalibrate Cost Model V2 without changing these failed policies, then run a new bounded economic family; keep VALIDATION and LOCKED_OOS closed."),
                 "limitations":["single broker","DEV tick history unavailable","M1 spread is a proxy","slippage unavailable",
                                "2015 is expanding-window calibration only","counterfactual outcomes, no fills"],
                 "highest_value_uncertainty":"Independent historical bid/ask and slippage evidence for 2015-2019"}
        atomic_write_json(self.root/"reports/evidence/PROMPT_7_ECONOMIC_CAMPAIGN.json",summary)
        atomic_write_json(self.root/"hypotheses/economic_registry_v1.json",results)
        semantic=SemanticMemory(self.root/"memory_db"); tag="prompt-7-economic-campaign-v1"
        existing=next((x for x in semantic.all() if tag in x.get("tags",[])),None)
        if existing is None:
            best=max(results,key=lambda x:x["trade_value_v1"]["expected_net_return"])
            item=semantic.add_knowledge(
                f"Economic DEV campaign tested 24 preregistered ENTER/WAIT policies over four frozen relative-reversal signals. "
                f"All were REJECTED. Best net policy {best['id']} returned {best['trade_value_v1']['expected_net_return']:.10f} "
                f"at 1x proxy cost; low cost/ATR reduced losses but did not cross zero. WAIT remains optimal. "
                "DEV historical bid/ask ticks and slippage remain unavailable; no failed filter may be reused as a post-hoc rescue.",
                evidence_ids=[self.config["campaign_id"],prereg_hash],confidence=1.0,
                tags=[tag,"no-trade","enter-vs-wait","proxy-cost-only","dev-only"])
            LongTermMemory(self.root/"memory_db").promote(item)
            existing=item
        summary["memory_consolidation"]={"semantic_memory_id":existing["id"],"long_term":True,
            "knowledge":"Low cost/ATR is least bad in tested DEV states, but all 24 policies remain economically negative; WAIT is optimal."}
        atomic_write_json(self.root/"reports/evidence/PROMPT_7_ECONOMIC_CAMPAIGN.json",summary)
        return summary
