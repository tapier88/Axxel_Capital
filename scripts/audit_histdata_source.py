"""Bounded source diagnostic; not an ingestion adapter or research entry point.

Run from repository root: python -m scripts.audit_histdata_source
No market rows are published to engine datasets or gold. Originals are read-only.
"""
from pathlib import Path
from datetime import timezone, timedelta
import json
import zipfile

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

from src.data.engine import DataEngine, _json, _publish
from src.utils.hashing import file_hash

OUT = Path('reports/data_integrity/histdata-2015-2017-2026-09-04')
XM_ID = 'DE1-658ff72ef8932e5b4d50118751d039fc11015010ec6f1101c3dce81805b58706'
PRICE = ['open', 'high', 'low', 'close']


def verify_preservation(root, inventory):
    for item in inventory['files']:
        path = root / item['path']
        if file_hash(path) != item['sha256'] or path.stat().st_size != item['size_bytes']:
            raise PermissionError('Preserved source bytes changed: ' + str(path))
    for year in (2015, 2016, 2017):
        archive = root / f'data/external/histdata/original_zip/HISTDATA_COM_ASCII_XAUUSD_M1{year}.zip'
        expected = {f'DAT_ASCII_XAUUSD_M1_{year}.{ext}' for ext in ('txt', 'csv')}
        with zipfile.ZipFile(archive) as z:
            if len(z.infolist()) != 2 or set(z.namelist()) != expected or z.testzip() is not None:
                raise PermissionError('Unexpected or corrupt archive members')
            for name in sorted(expected):
                copy = archive.parent.parent / 'extracted' / archive.stem / name
                if z.read(name) != copy.read_bytes():
                    raise PermissionError('Extracted bytes differ from preserved member')


def parse_csv(path, year, bounds):
    if year not in (2015, 2016, 2017):
        raise PermissionError('Only user-authorized HistData years')
    b = pd.read_csv(path, sep=';', header=None, dtype=str, keep_default_na=False)
    if b.shape[1] != 6 or b.empty:
        raise ValueError('Expected six nonempty headerless fields')
    b.columns = ['timestamp_raw'] + PRICE + ['volume_raw']
    if not b.timestamp_raw.str.fullmatch(str(year) + r'\d{4} \d{6}').all():
        raise PermissionError('Timestamp outside declared year or malformed')
    local = pd.to_datetime(b.timestamp_raw, format='%Y%m%d %H%M%S', errors='raise')
    # Separate provider-declared projection. No original timestamp is replaced.
    b['timestamp_utc'] = local.dt.tz_localize(timezone(timedelta(hours=-5))).dt.tz_convert('UTC')
    start, end = bounds
    if not ((b.timestamp_utc >= start) & (b.timestamp_utc + pd.Timedelta(minutes=1) < end)).all():
        raise PermissionError('HistData projection outside DEV')
    for col in PRICE + ['volume_raw']:
        b[col] = pd.to_numeric(b[col], errors='raise')
    b.insert(0, 'source_line', np.arange(1, len(b) + 1))
    b.insert(0, 'source_year', year)
    return b


def quality(b):
    t = b.timestamp_utc
    delta = t.diff().dt.total_seconds().div(60)
    nums = b[PRICE + ['volume_raw']]
    masks = {
        'NONFINITE': ~np.isfinite(nums).all(axis=1),
        'NONPOSITIVE_PRICE': b[PRICE].le(0).any(axis=1),
        'INVALID_OHLC': (b.high < b[['open', 'close', 'low']].max(axis=1)) | (b.low > b[['open', 'close', 'high']].min(axis=1)),
        'NEGATIVE_VOLUME': b.volume_raw.lt(0),
        'OUT_OF_ORDER': delta.lt(0),
        'EXACT_DUPLICATE': b[['timestamp_raw'] + PRICE + ['volume_raw']].duplicated(),
        'DUPLICATE_TIMESTAMP': t.duplicated(keep=False),
        'OFF_MINUTE_GRID': t.astype('int64').mod(60_000_000_000).ne(0),
        'PRICE_JUMP': b.close.pct_change(fill_method=None).abs().gt(.02),
        'STALE_RUN': b.close.eq(b.close.shift()).rolling(5, min_periods=5).sum().eq(5),
    }
    findings = pd.concat([b.loc[m].assign(code=k) for k, m in masks.items()], ignore_index=True)
    gi = np.flatnonzero(delta.gt(1))
    gaps = pd.DataFrame(dict(previous_utc=t.iloc[gi-1].to_numpy(), next_utc=t.iloc[gi].to_numpy(),
                             previous_raw=b.timestamp_raw.iloc[gi-1].to_numpy(), next_raw=b.timestamp_raw.iloc[gi].to_numpy(),
                             source_year=b.source_year.iloc[gi].to_numpy(), source_line=b.source_line.iloc[gi].to_numpy(),
                             missing_grid_minutes=delta.iloc[gi].to_numpy()-1))
    gaps['cause'] = 'UNRESOLVED_NOT_PROVEN_DATA_LOSS'
    groups = b.close.ne(b.close.shift()).cumsum()
    ids = groups[masks['STALE_RUN']].unique()
    episodes = []
    for gid in ids:
        run = b.loc[groups == gid]
        episodes.append(dict(start=run.timestamp_utc.iloc[0], end=run.timestamp_utc.iloc[-1],
                             source_year=int(run.source_year.iloc[0]), source_line=int(run.source_line.iloc[0]),
                             bars=len(run), alerts=int(masks['STALE_RUN'].loc[run.index].sum()),
                             nonflat_bars=int(run.high.ne(run.low).sum()),
                             gap_edges=int(run.timestamp_utc.diff().gt(pd.Timedelta(minutes=1)).sum())))
    summary = dict(rows=len(b), from_utc=t.iloc[0].isoformat(), to_utc=t.iloc[-1].isoformat(),
                   from_raw=b.timestamp_raw.iloc[0], to_raw=b.timestamp_raw.iloc[-1],
                   counts={k:int(m.sum()) for k,m in masks.items()},
                   gaps=len(gaps), absent_24h_grid_minutes=int(gaps.missing_grid_minutes.sum()),
                   stale_episodes=len(episodes), volume_zero_rows=int(b.volume_raw.eq(0).sum()),
                   spread_available=False, verified_session_closures=0, verified_data_losses=0)
    return summary, gaps, findings, pd.DataFrame(episodes)


def compare_offsets(h, x):
    """All candidates retained. No clock correction, model fit or selected dataset."""
    hidx = pd.DatetimeIndex(h.timestamp_utc)
    hp = h[PRICE].to_numpy()
    xp = x[PRICE].to_numpy()
    months = x.timestamp_utc.dt.strftime('%Y-%m').to_numpy()
    results = []
    for hours in range(-12, 13):
        pos = hidx.get_indexer(x.timestamp_utc - pd.Timedelta(hours=hours))
        found = pos >= 0
        absdiff = np.abs(xp[found] - hp[pos[found]])
        month = months[found]
        for period in ['ALL'] + sorted(set(month)):
            a = absdiff if period == 'ALL' else absdiff[month == period]
            if not len(a):
                continue
            results.append(dict(xm_hours_subtracted=hours, period=period, matched_bars=len(a),
                                mean_abs_ohlc=float(a.mean()), median_abs_ohlc=float(np.median(a)),
                                p95_abs_ohlc=float(np.quantile(a,.95)),
                                median_abs_close=float(np.median(a[:,3])),
                                exact_ohlc_bars=int((a == 0).all(axis=1).sum())))
    return pd.DataFrame(results)


def gap_comparison(h, x):
    ht = pd.DatetimeIndex(h.timestamp_utc).asi8
    xt = x.timestamp_utc
    ii = np.flatnonzero(xt.diff().gt(pd.Timedelta(minutes=1)))
    result = []
    for hours in (0, 2, 3):
        for i in ii:
            a = xt.iloc[i-1] - pd.Timedelta(hours=hours) + pd.Timedelta(minutes=1)
            b = xt.iloc[i] - pd.Timedelta(hours=hours)
            expected = int((b-a).total_seconds()/60)
            count = int(np.searchsorted(ht,b.value)-np.searchsorted(ht,a.value))
            result.append(dict(xm_source_row=int(x.source_row.iloc[i]), xm_hours_subtracted=hours,
                               start_utc=a, end_exclusive_utc=b, xm_absent_minutes=expected,
                               histdata_present_minutes=count, histdata_absent_minutes=expected-count,
                               relation='ALL_PRESENT' if count==expected else 'ALL_ABSENT' if count==0 else 'PARTIAL',
                               clock_attested=False, cause_confirmed=False))
    return pd.DataFrame(result)


def run(root=Path('.').resolve()):
    output = root / OUT
    inventory = json.loads((output/'preservation_before.json').read_text(encoding='utf-8'))
    verify_preservation(root, inventory)
    engine = DataEngine(root)
    bounds = engine._bounds()
    frames, annual = [], []
    def csv(name, f):
        _publish(output/(name+'.csv'), lambda p: f.to_csv(p, index=False))
    for year in (2015, 2016, 2017):
        path = root / f'data/external/histdata/extracted/HISTDATA_COM_ASCII_XAUUSD_M1{year}/DAT_ASCII_XAUUSD_M1_{year}.csv'
        b = parse_csv(path, year, bounds)
        summary, gaps, findings, episodes = quality(b)
        summary['year'] = year
        total = int((pd.Timestamp(year=year+1,month=1,day=1)-pd.Timestamp(year=year,month=1,day=1)).total_seconds()/60)
        summary.update(calendar_minutes=total, calendar_24h_coverage_fraction=len(b)/total,
                       unique_local_days=int(b.timestamp_raw.str[:8].nunique()),
                       calendar_coverage_not_session_completeness=True)
        annual.append(summary)
        csv(f'{year}_gaps', gaps); csv(f'{year}_findings', findings); csv(f'{year}_stale', episodes)
        frames.append(b)
    h = pd.concat(frames, ignore_index=True)  # same source only, retains source_year/source_line
    summary, gaps, findings, episodes = quality(h)
    csv('all_gaps', gaps); csv('all_findings', findings); csv('all_stale', episodes)
    _json(output/'quality_summary.json',dict(annual=annual, combined=summary))
    if any(summary['counts'][k] for k in ['NONFINITE','NONPOSITIVE_PRICE','INVALID_OHLC','NEGATIVE_VOLUME','OUT_OF_ORDER','DUPLICATE_TIMESTAMP','OFF_MINUTE_GRID']):
        raise ValueError('Structural findings: stop comparison, retain findings for REJECTED review')
    parent = engine.manifest(XM_ID, research=False, partition='DEV')
    paths = {k:engine._path(parent['artifacts'][k]['path']) for k in ('silver','findings')}
    for p in paths.values():
        f = pq.ParquetFile(p)
        col = f.schema_arrow.get_field_index('timestamp_utc')
        for i in range(f.num_row_groups):
            st = f.metadata.row_group(i).column(col).statistics
            if not st or not st.has_min_max or pd.Timestamp(st.min)<bounds[0] or pd.Timestamp(st.max)+pd.Timedelta(minutes=1)>=bounds[1]:
                raise PermissionError('XM footer not wholly DEV')
    x = pq.read_table(paths['silver']).to_pandas()
    xf = pq.read_table(paths['findings']).to_pandas()
    for table in (x,xf):
        if not ((table.timestamp_utc>=bounds[0]) & (table.timestamp_utc+pd.Timedelta(minutes=1)<bounds[1])).all():
            raise PermissionError('XM timestamps outside DEV')
    if len(x)!=parent['rows'] or xf.code.value_counts().to_dict()!=parent['quality']['counts']:
        raise ValueError('XM parent count mismatch')
    _json(output/'xm_parent_snapshot.json',parent)
    offsets = compare_offsets(h,x); csv('clock_offset_grid',offsets)
    gaps_comp = gap_comparison(h,x); csv('xm_gap_comparison',gaps_comp)
    from src.data.integrity_audit import diagnose
    xd, xs = diagnose(x,xf)
    windows = [(f'STALE_{i+1:03}',pd.Timestamp(e['from_timestamp']),pd.Timestamp(e['to_timestamp'])) for i,e in xd['stale_episodes'].iterrows()]
    windows += [('ZERO_SPREAD_MARCH',pd.Timestamp('2017-03-22 07:29Z'),pd.Timestamp('2017-03-22 10:15Z')),
                ('ZERO_SPREAD_OCTOBER',pd.Timestamp('2017-10-30 19:26Z'),pd.Timestamp('2017-10-30 20:47Z')),
                ('JUMP_20150720',pd.Timestamp('2015-07-20 04:24Z'),pd.Timestamp('2015-07-20 04:34Z'))]
    ht = pd.DatetimeIndex(h.timestamp_utc)
    global_stale = h.close.eq(h.close.shift()).rolling(5,min_periods=5).sum().eq(5)
    global_ret = h.close.pct_change(fill_method=None)
    events, samples = [], []
    for label, start, end in windows:
        for hours in (0,2,3):
            a,b = start-pd.Timedelta(hours=hours),end-pd.Timedelta(hours=hours)
            left,right=ht.searchsorted(a),ht.searchsorted(b,side='right')
            f=h.iloc[left:right]
            n=int((b-a).total_seconds()/60)+1
            events.append(dict(window=label,xm_hours_subtracted=hours,start_utc=a,end_utc=b,
                               expected_grid_minutes=n,histdata_bars=len(f),
                               histdata_missing_minutes=n-len(f), histdata_distinct_closes=int(f.close.nunique()),
                               histdata_stale_alerts=int(global_stale.iloc[left:right].sum()),
                               histdata_jump_alerts=int(global_ret.iloc[left:right].abs().gt(.02).sum()),
                               histdata_min_return=None if f.empty else float(global_ret.iloc[left:right].min()),
                               histdata_nonflat_bars=int(f.high.ne(f.low).sum()),
                               spread_comparison='NOT_ASSESSABLE_NO_ASK_OR_SPREAD',clock_attested=False))
            if label=='JUMP_20150720':
                samples.append(f.assign(window=label,xm_hours_subtracted=hours,close_return=global_ret.iloc[left:right]))
    csv('known_windows',pd.DataFrame(events)); csv('jump_window_bars',pd.concat(samples,ignore_index=True))
    coverage=[]
    for year in (2015,2016,2017):
        xx=x.loc[x.timestamp_utc.dt.year.eq(year)]
        hh=h.loc[h.source_year.eq(year)]
        coverage.append(dict(year=year,histdata_bars=len(hh),xm_bars=len(xx),xm_from=xx.timestamp_utc.min().isoformat(),xm_to=xx.timestamp_utc.max().isoformat(),
                             histdata_from=hh.timestamp_utc.min().isoformat(),histdata_to=hh.timestamp_utc.max().isoformat(),
                             xm_gaps=int(xx.timestamp_utc.diff().gt(pd.Timedelta(minutes=1)).sum()),
                             matching_declared_timestamps=int(xx.timestamp_utc.isin(hh.timestamp_utc).sum())))
    csv('coverage_comparison',pd.DataFrame(coverage))
    if engine.manifest(XM_ID,research=False)!=parent:
        raise PermissionError('XM parent changed during comparison')
    verify_preservation(root, inventory)
    protected=json.loads((output/'protected_before.json').read_text())
    if any(file_hash(root/p)!=digest for p,digest in protected.items()):
        raise PermissionError('Protected baseline changed')
    _json(output/'audit_execution.json',dict(status='DIAGNOSTIC_PASS_CERTIFICATION_BLOCKED',
          source_files_unchanged=True, extracted_member_identity_verified=True,
          xm_dataset=XM_ID,xm_rows=len(x),xm_quality_counts=xs['counts'],
          parent_status=parent['status'],parent_certificate_sha256=parent['certificate_sha256'],
          code_sha256=file_hash(Path(__file__)),partition='DEV',
          histdata_timezone='provider-declared fixed UTC-05:00; diagnostic UTC projection',
          acquisition_date=None,download_receipt_available=False,
          source_separation=True,price_repairs=0,filled_bars=0,threshold_changes=0,
          datasets_promoted=0,certified_rows=0,validation_opened=False,locked_oos_opened=False,
          mixed_xm_parent_opened_or_hashed=False,ml_or_backtest=False,DATA_ENGINE_CERTIFIED=False))
    print(json.dumps(dict(annual=annual,combined=summary),indent=2))


if __name__ == '__main__':
    run()
