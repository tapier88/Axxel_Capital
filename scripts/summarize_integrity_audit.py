"""Post-observation descriptive triage; no classification is a verified closure."""
from pathlib import Path
import sys
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.data.engine import _json, _publish

if __name__ == '__main__':
    p = ROOT/'reports/data_integrity/2026-09-04'
    g = pd.read_csv(p/'diagnostic/gaps.csv')
    pairs = {('23:58','01:00'), ('22:58','00:00'), ('00:13','01:00'), ('23:13','00:00')}
    g['triage'] = 'OTHER_UNRESOLVED'
    g.loc[(g.morphology == 'INTRADAY') & g.elapsed_minutes.isin([2,3]), 'triage'] = 'SHORT_INTRADAY_UNRESOLVED'
    g.loc[[tuple(row) in pairs for row in g[['previous_clock','next_clock']].values], 'triage'] = 'RECURRING_SESSION_PATTERN_UNVERIFIED'
    g.loc[g.morphology == 'WEEKEND_SPANNING', 'triage'] = 'WEEKEND_CLOSURE_CANDIDATE_UNVERIFIED'
    g['triage_basis'] = 'Post-observation descriptive grouping; not a frozen certification rule'
    _publish(p/'gap_triage.csv', lambda target: g.to_csv(target,index=False))
    stats = g.groupby('triage').agg(gaps=('source_row','size'), absent_grid_minutes=('absent_grid_minutes','sum')).reset_index().to_dict('records')
    assert sum(x['gaps'] for x in stats) == len(g)
    _json(p/'triage_summary.json', {'categories':stats,'all_causes_unresolved':True,
          'does_not_modify_parent_findings':True,'calendar_verified':False,'gap_total':int(len(g))})
    pairs_table = g.groupby(['morphology','previous_clock','next_clock','elapsed_minutes']).size().reset_index(name='gaps')
    _publish(p/'clock_patterns.csv', lambda target:pairs_table.to_csv(target,index=False))
