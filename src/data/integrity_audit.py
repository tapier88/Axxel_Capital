"""Diagnostic audit of a committed DEV Data Engine artifact; never a research loader.

Morphology is NOT a verified broker calendar. No certificate or quality policy changes.
"""
from pathlib import Path
import pandas as pd
import pyarrow.parquet as pq

from src.data.engine import DataEngine, _json, _publish, identity
from src.utils.hashing import file_hash


def diagnose(bars, findings):
    b = bars.reset_index(drop=True).copy()
    ts = b.timestamp_utc
    if b.empty or not ts.is_monotonic_increasing or ts.duplicated().any():
        raise ValueError('Audit requires nonempty unique chronological bars')
    delta = ts.diff().dt.total_seconds().div(60)
    gap_indices = b.index[delta > 1]
    if set(b.loc[gap_indices, 'source_row']) != set(findings.loc[findings.code == 'GAP', 'source_row']):
        raise ValueError('Gap reconciliation failed')
    gaps = []
    for i in gap_indices:
        left, right = ts.iloc[i-1], ts.iloc[i]
        dates = pd.date_range(left.normalize(), right.normalize(), freq='D')
        weekend = any(d.dayofweek >= 5 for d in dates)
        morphology = ('WEEKEND_SPANNING' if weekend else
                      'CROSS_DATE' if left.date() != right.date() else 'INTRADAY')
        gaps.append(dict(source_row=int(b.source_row.iloc[i]), previous_source_row=int(b.source_row.iloc[i-1]),
                         previous_timestamp=left.isoformat(), next_timestamp=right.isoformat(),
                         missing_from=(left+pd.Timedelta(minutes=1)).isoformat(), missing_to_exclusive=right.isoformat(),
                         elapsed_minutes=float(delta.iloc[i]), absent_grid_minutes=float(delta.iloc[i]-1),
                         previous_clock=left.strftime('%H:%M'), next_clock=right.strftime('%H:%M'),
                         previous_weekday=left.day_name(), next_weekday=right.day_name(),
                         morphology=morphology, cause='UNRESOLVED', decision='REVIEW',
                         closure_verified=False, data_loss_verified=False))
    g = pd.DataFrame(gaps)
    details = findings.merge(b, on=['source_row', 'timestamp_utc'], how='left', validate='many_to_one')
    details['elapsed_minutes'] = details.source_row.map(pd.Series(delta.values, index=b.source_row))
    details['previous_close'] = details.source_row.map(pd.Series(b.close.shift().values, index=b.source_row))
    details['close_change_fraction'] = details.close / details.previous_close - 1
    # Repeated closes are grouped independently of clock continuity to explain V1 alerts.
    groups = b.close.ne(b.close.shift()).cumsum()
    alerted_ids = set(findings.loc[findings.code == 'STALE_RUN', 'source_row'])
    episode_ids = groups[b.source_row.isin(alerted_ids)].unique()
    episodes = []
    for group in episode_ids:
        run = b.loc[groups == group]
        run_alerts = run.source_row.isin(alerted_ids)
        episodes.append(dict(from_timestamp=run.timestamp_utc.iloc[0].isoformat(),
                             to_timestamp=run.timestamp_utc.iloc[-1].isoformat(),
                             first_source_row=int(run.source_row.iloc[0]), last_source_row=int(run.source_row.iloc[-1]),
                             bars=len(run), alerts=int(run_alerts.sum()), close=float(run.close.iloc[0]),
                             gap_edges=int((delta.loc[run.index[1:]] > 1).sum()),
                             nonflat_ohlc_bars=int((run.high != run.low).sum()),
                             positive_tick_bars=int((run.tick_volume > 0).sum()),
                             cause='UNRESOLVED_NOT_PROOF_OF_FROZEN_FEED'))
    e = pd.DataFrame(episodes)
    # Exhaustive partition into observed contiguous M1 blocks, never eligible research subsets.
    blocks = []
    block_id = (delta.ne(1)).cumsum()
    flagged_ids = set(findings.source_row)
    for _, run in b.groupby(block_id, sort=False):
        blocks.append(dict(from_timestamp=run.timestamp_utc.iloc[0].isoformat(),
                           to_timestamp=run.timestamp_utc.iloc[-1].isoformat(), rows=len(run),
                           first_source_row=int(run.source_row.iloc[0]), last_source_row=int(run.source_row.iloc[-1]),
                           flagged_rows=int(run.source_row.isin(flagged_ids).sum()),
                           source_integrity_certifiable=False, research_eligible=False))
    counts = {str(k): int(v) for k, v in findings.code.value_counts().items()}
    if counts.get('ZERO_SPREAD', 0) != int(b.spread.eq(0).sum()):
        raise ValueError('Zero spread reconciliation failed')
    if counts.get('PRICE_JUMP', 0) != int(b.close.pct_change(fill_method=None).abs().gt(.02).sum()):
        raise ValueError('Jump reconciliation failed')
    stale = b.close.eq(b.close.shift()).rolling(5, min_periods=5).sum().eq(5)
    if set(b.loc[stale, 'source_row']) != alerted_ids:
        raise ValueError('Stale reconciliation failed')
    zeros = details.loc[details.code == 'ZERO_SPREAD']
    summary = dict(rows=len(b), counts=counts, gap_morphology={} if g.empty else g.morphology.value_counts().to_dict(),
                   absent_grid_minutes=0 if g.empty else float(g.absent_grid_minutes.sum()),
                   verified_closures=0, verified_data_losses=0, unresolved_gaps=len(g),
                   stale_episodes=len(e), stale_episodes_crossing_gaps=0 if e.empty else int(e.gap_edges.gt(0).sum()),
                   stale_nonflat_ohlc_bars=0 if e.empty else int(e.nonflat_ohlc_bars.sum()),
                   zero_spread_positive_tick_bars=int(zeros.tick_volume.gt(0).sum()),
                   zero_spread_nonflat_bars=int(zeros.high.ne(zeros.low).sum()),
                   contiguous_blocks=len(blocks), strongly_certifiable_rows=0,
                   eligible_research_rows=0, DATA_ENGINE_CERTIFIED=False)
    return {'gaps': g, 'anomaly_rows': details.loc[details.code != 'GAP'],
            'stale_episodes': e, 'segments': pd.DataFrame(blocks)}, summary


def audit(root: Path, dataset_id: str, output: Path):
    engine = DataEngine(root)
    # Existing engine validates identity, fixed artifact paths and all DEV artifact hashes.
    parent = engine.manifest(dataset_id, research=False, partition='DEV')
    if parent['recipe']['metadata']['timeframe'] != 'M1':
        raise PermissionError('This diagnostic is M1 only')
    start, end = engine._bounds()
    paths = {name: engine._path(parent['artifacts'][name]['path']) for name in ('silver', 'findings')}
    for path in paths.values():
        footer = pq.ParquetFile(path)
        col = footer.schema_arrow.get_field_index('timestamp_utc')
        for i in range(footer.num_row_groups):
            stats = footer.metadata.row_group(i).column(col).statistics
            if stats is None or not stats.has_min_max or pd.Timestamp(stats.min) < start or pd.Timestamp(stats.max)+pd.Timedelta(minutes=1) >= end:
                raise PermissionError('Audit footer outside permitted DEV')
    tables = {name: pq.read_table(path).to_pandas() for name, path in paths.items()}
    for table in tables.values():
        if not ((table.timestamp_utc >= start) & (table.timestamp_utc+pd.Timedelta(minutes=1) < end)).all():
            raise PermissionError('Audit timestamps outside DEV')
    outputs, summary = diagnose(tables['silver'], tables['findings'])
    if summary['counts'] != parent['quality']['counts'] or summary['rows'] != parent['rows']:
        raise ValueError('Official finding totals changed')
    # Verify again before publishing; source and certificate remain untouched.
    if engine.manifest(dataset_id, research=False) != parent:
        raise PermissionError('Parent changed during audit')
    for name, frame in outputs.items():
        _publish(output / (name+'.csv'), lambda target, frame=frame: frame.to_csv(target, index=False))
    report = dict(audit_version='DEV-INTEGRITY-DIAGNOSTIC-V1', dataset_id=dataset_id,
                  parent_certificate_sha256=parent['certificate_sha256'], parent_status=parent['status'],
                  code_sha256=file_hash(Path(__file__)), summary=summary,
                  from_timestamp=parent['from'], to_timestamp=parent['to'],
                  payloads_read=[parent['artifacts'][name]['path'] for name in paths],
                  integrity_hashes_checked=parent['artifacts'],
                  parent_mixed_source_opened=False, validation_opened=False, locked_oos_opened=False,
                  research_run=False, thresholds_changed=False, certificate_changed=False,
                  calendar_policy='Morphology only; no verified historical session calendar available',
                  artifacts={name: {'path': (output/(name+'.csv')).relative_to(root).as_posix(),
                                    'sha256': file_hash(output/(name+'.csv'))} for name in outputs})
    report['audit_id'] = 'DIA-'+identity(report)
    _json(output/'audit.json', report)
    return report
