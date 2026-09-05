"""Synthetic audit regressions: causal uncertainty must never become certification."""
from unittest.mock import patch
import pandas as pd
import pytest
from src.data.quality import normalize_and_validate
from src.data.integrity_audit import diagnose, audit
from src.data.engine import DataEngine
from src.utils.serialization import atomic_write_json

META = dict(source_id='SYNTHETIC', broker='TEST', symbol_exact='GOLD', symbol_international='XAUUSD',
            timeframe='M1', timezone='UTC', point=.01, digits=2, timestamp_semantics='BAR_OPEN')


def fixture():
    times = ['2016-01-08T21:59Z', '2016-01-10T23:00Z', '2016-01-11T00:00Z',
             *pd.date_range('2016-01-11T00:02Z', periods=8, freq='min')]
    n = len(times)
    return pd.DataFrame(dict(timestamp_utc=pd.to_datetime(times, utc=True), symbol=['GOLD']*n,
                             open=[100.]*n, high=[101.]*n, low=[99.]*n, close=[100.]*n,
                             tick_volume=[20]*n, spread=[0]*n, real_volume=[0]*n))


def test_exhaustive_gaps_stale_not_frozen_feed_and_no_certification():
    _, bars, flags, _ = normalize_and_validate(fixture(), META, 1)
    original = bars.copy(deep=True)
    tables, summary = diagnose(bars, flags)
    assert summary['gap_morphology'] == {'WEEKEND_SPANNING': 2, 'INTRADAY': 1}
    assert summary['counts']['GAP'] == 3
    assert summary['stale_episodes'] == 1
    assert summary['stale_episodes_crossing_gaps'] == 1
    assert summary['zero_spread_positive_tick_bars'] == len(bars)
    assert tables['stale_episodes'].alerts.sum() == summary['counts']['STALE_RUN']
    assert tables['segments'].rows.sum() == len(bars)
    assert tables['gaps'].absent_grid_minutes.sum() == summary['absent_grid_minutes']
    assert not tables['gaps'].closure_verified.any()
    assert not tables['segments'].research_eligible.any()
    pd.testing.assert_frame_equal(original, bars)


def test_jump_across_gap_is_kept_and_incomplete_findings_fail():
    frame = fixture(); frame.loc[1:, ['open','close']] = 110.; frame.loc[1:, 'high'] = 111.
    _, bars, flags, _ = normalize_and_validate(frame, META, 1)
    tables, summary = diagnose(bars, flags)
    jump = tables['anomaly_rows'].query("code == 'PRICE_JUMP'").iloc[0]
    assert summary['counts']['PRICE_JUMP'] == 1
    assert jump.elapsed_minutes > 1
    assert jump.close_change_fraction == pytest.approx(.1)
    with pytest.raises(ValueError, match='Gap reconciliation'):
        diagnose(bars, flags.loc[flags.code != 'GAP'])


def test_audit_preserves_certificate_and_research_block(tmp_path):
    atomic_write_json(tmp_path/'config/partitions_gold_m1_v2.json',
                      {'frozen':True,'created_before_outcome_analysis':True,
                       'DEV':{'from':'2015-01-01T00:00Z','to_exclusive':'2020-01-01T00:00Z'}})
    source = tmp_path/'source.parquet'; fixture().to_parquet(source,index=False)
    engine = DataEngine(tmp_path); parent = engine.ingest_parquet(source, META)
    output = tmp_path/'reports/data_integrity/test'
    report = audit(tmp_path,parent['dataset_id'],output)
    assert audit(tmp_path,parent['dataset_id'],output) == report
    assert engine.manifest(parent['dataset_id'],research=False) == parent
    with pytest.raises(PermissionError, match='cannot enter research'):
        engine.query(parent['dataset_id'])
    with patch('src.data.integrity_audit.pq.read_table', side_effect=AssertionError('No payload')):
        with pytest.raises(PermissionError):
            audit(tmp_path,'LOCKED_OOS',output)
