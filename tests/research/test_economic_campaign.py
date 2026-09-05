from __future__ import annotations
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.data.cost_model import cost_model_v2
from src.experience_store.parquet_store import ParquetExperienceStore
from src.research.economic_campaign import EconomicCampaign, _policy_mask
from src.validation.walk_forward import assert_no_overlap, expanding_year_splits
from src.value.trade_value import abstention_value, trade_value_v1

ROOT=Path(__file__).resolve().parents[2]


def test_campaign_is_dev_only():
    c=EconomicCampaign(ROOT)
    assert c.config["partition"]=="DEV" and not c.config["validation_access"] and not c.config["locked_oos_access"]


def test_bounded_multiple_testing_registry():
    c=EconomicCampaign(ROOT)
    assert len(c.config["signals"])*len(c.config["filters"])==24


def test_only_one_additional_condition():
    c=EconomicCampaign(ROOT)
    assert all(" and " not in f["rule"] for f in c.config["filters"] if f["id"]!="FAVORABLE_VOLATILITY")


def test_features_are_causal_state_only():
    c=EconomicCampaign(ROOT)
    forbidden=("label_","outcome_","future")
    assert not any(any(x in f["rule"] for x in forbidden) for f in c.config["filters"])


def test_cost_provenance_proxy_and_missing_slippage():
    x=cost_model_v2(spread_price=.2,close=2000,source_id="S",broker="B",timestamp="T")
    assert x["method"]=="PROXY_COST" and x["SOURCE_ID"]=="S"
    assert x["REAL_TICK_COST"] is None and x["slippage_status"]=="UNAVAILABLE_NOT_ASSUMED_ZERO"


def test_real_tick_cost_precedence():
    x=cost_model_v2(spread_price=.2,close=2000,source_id="S",broker="B",timestamp="T",real_tick_cost=.0002)
    assert x["method"]=="REAL_TICK_COST" and x["PROXY_COST"] is None


def test_trade_value_enters_only_with_positive_lower_ci():
    x=trade_value_v1([.01]*200,[.001]*200,action="ENTER_LONG",minimum_support=100)
    assert x["decision"]=="ENTER_LONG" and x["confidence_interval_95"][0]>0


def test_trade_value_waits_on_negative_net():
    x=trade_value_v1([.001]*200,[.002]*200,action="ENTER_SHORT",minimum_support=100)
    assert x["decision"]=="WAIT"


def test_abstention_value():
    assert abstention_value(-.001)["optimal_action"]=="WAIT"
    assert abstention_value(.001)["optimal_action"]=="ENTER"


def test_walk_forward_is_temporal_not_random():
    ts=pd.date_range("2015-01-01","2017-12-31",freq="30D",tz="UTC")
    splits=expanding_year_splits(ts,first_test_year=2016,horizon_minutes=30,embargo_minutes=30)
    assert [x["test_year"] for x in splits]==[2016,2017]
    for split in splits:
        assert ts[split["train_mask"]].max()<ts[split["test_mask"]].min()


def test_purging_and_embargo():
    ts=pd.date_range("2015-12-31 22:00","2016-01-01 03:00",freq="10min",tz="UTC")
    split=expanding_year_splits(ts,first_test_year=2016,horizon_minutes=30,embargo_minutes=30)[0]
    assert_no_overlap(ts,split,30)


def test_locked_oos_hard_lock():
    store=ParquetExperienceStore(ROOT)
    with pytest.raises(PermissionError): store.query(partitions=("LOCKED_OOS",),limit=1)


def test_cost_stress_gate_is_one_x():
    c=EconomicCampaign(ROOT)
    assert 1.0 in c.config["cost_multipliers"] and c.config["primary_metric"]=="EXPECTED_NET_RETURN"


def test_minimum_support_declared():
    c=EconomicCampaign(ROOT)
    assert c.config["minimum_rows"]>0 and c.config["minimum_sessions"]>0 and c.config["minimum_years"]>=3


def test_complexity_penalty_declared():
    assert EconomicCampaign(ROOT).config["complexity_penalty_per_condition"]>0


def test_policy_thresholds_use_training_data():
    train=pd.DataFrame({"state_spread_points":[1,2,3,4]})
    test=pd.DataFrame({"state_spread_points":[1,4]})
    mask, learned=_policy_mask(train,test,{"field":"x"},"LOW_COST")
    assert learned["q25_spread_points"]==1.75 and mask.tolist()==[True,False]


def test_no_ea_or_live_trading():
    c=EconomicCampaign(ROOT)
    assert c.config["ea"] is False and c.config["live_trading"] is False
