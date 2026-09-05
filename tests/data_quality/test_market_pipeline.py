"""Retired V1 paths must fail closed; pure mechanics remain covered."""
from pathlib import Path
from unittest.mock import patch
import pytest
from src.data.pipeline import build_experience_dataset
from src.data.timezone import parse_utc, to_cot_iso
from src.data.cost_model import evaluate_cost
from src.experience_store.market_store import MarketExperienceStore

def test_v1_builder_denied_before_source_read(tmp_path):
    with patch("src.data.pipeline.read_json", side_effect=AssertionError("No source reads")):
        with pytest.raises(PermissionError):
            build_experience_dataset(tmp_path, "missing.json")

@pytest.mark.parametrize("allow_locked", [False, True])
def test_v1_mixed_reader_denied_before_source_read(tmp_path, allow_locked):
    with patch("src.experience_store.market_store.read_json", side_effect=AssertionError("No source reads")):
        with pytest.raises(PermissionError):
            MarketExperienceStore(tmp_path).all(allow_locked=allow_locked)

def test_timezone_utc_to_cot():
    assert to_cot_iso(parse_utc("2016-01-05T13:00:00Z")) == "2016-01-05T08:00:00-05:00"

def test_missing_costs_are_not_invented():
    assert evaluate_cost({}, "WAIT")["round_trip_return"] == 0.
    assert evaluate_cost({"recent_ohlc": {"close": 2000.}}, "LONG")["round_trip_return"] is None
