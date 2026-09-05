"""Synthetic only: no external historical or holdout files."""
import json
import zipfile
import pandas as pd
import pytest
from scripts.audit_histdata_source import parse_csv, quality, compare_offsets, gap_comparison, verify_preservation
from src.utils.hashing import file_hash

BOUNDS = (pd.Timestamp('2015-01-01T00:00Z'), pd.Timestamp('2020-01-01T00:00Z'))


def sample(tmp_path, rows):
    p = tmp_path/'synthetic.csv'
    p.write_text('\n'.join(rows)+'\n')
    return p


def test_fixed_est_summer_and_winter_raw_unchanged(tmp_path):
    p=sample(tmp_path,['20160104 120000;100;101;99;100;0','20160704 120000;100;101;99;100;0'])
    before=p.read_bytes()
    b=parse_csv(p,2016,BOUNDS)
    assert b.timestamp_utc.dt.hour.tolist()==[17,17]
    assert b.timestamp_raw.tolist()==['20160104 120000','20160704 120000']
    assert p.read_bytes()==before
    assert 'spread' not in b and 'tick_volume' not in b


@pytest.mark.parametrize('row,year,error',[
    ('20230101 000000;100;101;99;100;0',2016,PermissionError),
    ('20160101 000000;100;101;99;100;0',2023,PermissionError),
    ('20160101 000000;100;101;99;100',2016,ValueError),
    ('20161301 000000;100;101;99;100;0',2016,ValueError),
])
def test_bad_scope_and_schema_fail(tmp_path,row,year,error):
    with pytest.raises(error): parse_csv(sample(tmp_path,[row]),year,BOUNDS)


def test_dev_bounds_fail(tmp_path):
    p=sample(tmp_path,['20160101 000000;100;101;99;100;0'])
    with pytest.raises(PermissionError):
        parse_csv(p,2016,(pd.Timestamp('2017-01-01T00:00Z'),BOUNDS[1]))


def test_quality_retains_invalid_duplicates_order_and_gaps(tmp_path):
    rows=['20160104 000000;100;101;99;100;0']*2
    rows+=['20160104 000300;100;99;101;100;0','20160104 000200;100;101;99;100;0']
    b=parse_csv(sample(tmp_path,rows),2016,BOUNDS); before=b.copy(deep=True)
    s,g,f,e=quality(b)
    assert s['counts']['EXACT_DUPLICATE']==1
    assert s['counts']['DUPLICATE_TIMESTAMP']==2
    assert s['counts']['OUT_OF_ORDER']==1
    assert s['counts']['INVALID_OHLC']==1
    assert len(g)==1 and g.missing_grid_minutes.sum()==2
    assert g.cause.eq('UNRESOLVED_NOT_PROVEN_DATA_LOSS').all()
    pd.testing.assert_frame_equal(b,before)


def test_stale_and_jump_match_fixed_engine_thresholds(tmp_path):
    rows=[f'20160104 000{i}00;100;101;99;100;0' for i in range(6)]
    rows+=['20160104 000600;104;105;103;104;0']
    s,g,f,e=quality(parse_csv(sample(tmp_path,rows),2016,BOUNDS))
    assert s['counts']['STALE_RUN']==1 and s['stale_episodes']==1
    assert e.alerts.sum()==1 and e.bars.sum()==6
    assert s['counts']['PRICE_JUMP']==1


def test_offsets_sign_and_gap_half_open_no_source_mutation():
    t=pd.date_range('2016-01-04T12:00Z',periods=10,freq='min')
    h=pd.DataFrame({'timestamp_utc':t,**{c:list(range(100,110)) for c in ['open','high','low','close']}})
    x=h.copy(); x.timestamp_utc+=pd.Timedelta(hours=3); x['source_row']=range(10)
    before=x.copy(deep=True)
    grid=compare_offsets(h,x)
    best=grid.loc[grid.period.eq('ALL')].sort_values('mean_abs_ohlc').iloc[0]
    assert best.xm_hours_subtracted==3 and best.mean_abs_ohlc==0
    gap=gap_comparison(h,x.drop(index=[2,3]).reset_index(drop=True))
    r=gap.loc[gap.xm_hours_subtracted.eq(3)].iloc[0]
    assert r.xm_absent_minutes==2 and r.histdata_present_minutes==2
    assert not r.cause_confirmed
    pd.testing.assert_frame_equal(x,before)


def test_changed_bytes_stop_before_archive_access(tmp_path):
    p=tmp_path/'source';p.write_bytes(b'original')
    inv={'files':[{'path':'source','sha256':file_hash(p),'size_bytes':8}]}
    p.write_bytes(b'modified')
    with pytest.raises(PermissionError,match='bytes changed'): verify_preservation(tmp_path,inv)


def test_unexpected_zip_member_stops_without_extraction(tmp_path):
    p=tmp_path/'data/external/histdata/original_zip/HISTDATA_COM_ASCII_XAUUSD_M12015.zip'
    p.parent.mkdir(parents=True)
    with zipfile.ZipFile(p,'w') as z: z.writestr('../escape.csv','unsafe')
    with pytest.raises(PermissionError,match='archive members'): verify_preservation(tmp_path,{'files':[]})
    assert not (tmp_path/'escape.csv').exists()
