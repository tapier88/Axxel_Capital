from __future__ import annotations
from datetime import datetime,timedelta,timezone
from pathlib import Path
import inspect
import json
import numpy as np
import pandas as pd
import pytest

from src.data import demo_tick_collector
from src.experience_store.parquet_store import ParquetExperienceStore
from src.research.opportunity_campaign import OpportunityCampaign,_condition_mask,_derive
from src.value.opportunity_value import edge_to_cost_ratio,opportunity_labels,opportunity_value

ROOT=Path(__file__).resolve().parents[2]

def test_edge_to_cost_ratio():assert edge_to_cost_ratio(.003,.001)==3
def test_edge_to_cost_rejects_zero():
    with pytest.raises(ValueError):edge_to_cost_ratio(1,0)
def test_opportunity_labels_k2():
    x=opportunity_labels([.003],[.001],[.001],k=2,horizon=15)
    assert x["large_future_excursion"].tolist()==[True] and x["opportunity_surplus"][0]==pytest.approx(.001)
def test_time_to_excursion():
    x=opportunity_labels([.004],[0],[.001],k=3,horizon=30,shorter_excursions={5:np.array([.002]),15:np.array([.004])})
    assert x["time_to_excursion_minutes"][0]==15
def test_opportunity_value_penalizes_complexity():
    assert opportunity_value(.003,.001,.2,.01,complexity=1)>opportunity_value(.003,.001,.2,.01,complexity=2)
def test_exactly_30_registered():assert len(OpportunityCampaign(ROOT).config["hypotheses"])==30
def test_family_distribution_three_each():
    h=OpportunityCampaign(ROOT).config["hypotheses"]
    assert set(pd.Series([x["family"] for x in h]).value_counts())=={3}
def test_no_reversal_family_or_disc_ids():
    h=OpportunityCampaign(ROOT).config["hypotheses"]
    assert not any("REVERS" in x["family"] or "DISC-" in x["id"] for x in h)
def test_only_causal_condition_fields():
    h=OpportunityCampaign(ROOT).config["hypotheses"]
    assert "label_" not in str([x["condition"] for x in h]) and "outcome_" not in str([x["condition"] for x in h])
def test_max_two_conditions():
    h=OpportunityCampaign(ROOT).config["hypotheses"]
    assert max(len(x["condition"].get("clauses",[x["condition"]])) for x in h)<=2
def test_horizon_frozen():assert all(x["horizon"] in (5,15,30,60) for x in OpportunityCampaign(ROOT).config["hypotheses"])
def test_k_predeclared():assert set(x["K"] for x in OpportunityCampaign(ROOT).config["hypotheses"])=={2,3}
def test_threshold_learned_from_train_only():
    tr=pd.DataFrame({"x":[1,2,3,4]});te=pd.DataFrame({"x":[1,5]});m,l=_condition_mask(tr,te,{"type":"qgte","field":"x","q":.75})
    assert l["threshold"]==3.25 and m.tolist()==[False,True]
def test_derived_state_uses_no_future():
    f=pd.DataFrame({"state_return_1m":[1],"state_return_5m":[1],"state_return_15m":[1],"state_momentum_15m_causal":[1],
      "state_distance_recent_high":[1],"state_distance_recent_low":[2],"state_volatility_15m_causal":[1],"state_volatility_60m_causal":[2],"state_atr_14_causal":[2],"state_bar_range":[1]})
    assert all(x.startswith("state_") for x in _derive(f).columns)
def test_validation_and_oos_locks():
    c=OpportunityCampaign(ROOT);assert not c.config["validation_access"] and not c.config["locked_oos_access"]
    with pytest.raises(PermissionError):ParquetExperienceStore(ROOT).query(partitions=("LOCKED_OOS",),limit=1)
def test_demo_collector_rejects_historical():
    now=datetime.now(timezone.utc)
    with pytest.raises(PermissionError):demo_tick_collector.validate_prospective_window(now-timedelta(days=1),now,now=now)
def test_demo_collector_caps_window():
    now=datetime.now(timezone.utc)
    with pytest.raises(ValueError):demo_tick_collector.validate_prospective_window(now+timedelta(hours=1),now+timedelta(hours=26),now=now)
def test_demo_collector_has_no_trade_api():
    source=inspect.getsource(demo_tick_collector)
    assert "order_send" not in source and "orders_sent\":0" in source
def test_no_ea_or_live():
    c=OpportunityCampaign(ROOT).config;assert c["ea"] is False and c["live_trading"] is False

def _artifact():return json.loads((ROOT/"reports/evidence/PROMPT_8_OPPORTUNITY_CAMPAIGN.json").read_text())
def test_multiple_testing_registry_has_30_q_values():
    r=_artifact()["results"];assert len(r)==30 and all("bh_fdr_q_value" in x for x in r)
def test_opportunity_survivor_gate():
    for x in _artifact()["results"]:
        if x["status"] in ("VOLATILITY_OPPORTUNITY_ONLY","DEV_ECONOMIC_SURVIVOR"):
            assert x["edge_to_cost_ratio"]>x["K"] and x["lift_ci95"][0]>0
def test_direction_survivor_gate():
    for x in _artifact()["direction_tests"]:
        if x["status"]=="DIRECTION_SURVIVOR":
            assert x["expected_net_return"]>0 and x["confidence_interval_95"][0]>0 and x["bh_fdr_q_value"]<=.05
def test_artifact_locks_and_no_trade():
    x=_artifact();assert x["validation_reads"]==0 and x["locked_oos_reads"]==0 and not x["live_trading"]
def test_cost_reality_provenance():
    x=json.loads((ROOT/"reports/evidence/COST_REALITY_REPORT_V1.json").read_text())["existing_cost_source"]
    assert all(k in x for k in ("SOURCE_ID","BROKER","SYMBOL","TIMESTAMP","BID","ASK","SPREAD","PROVENANCE","HASH"))
