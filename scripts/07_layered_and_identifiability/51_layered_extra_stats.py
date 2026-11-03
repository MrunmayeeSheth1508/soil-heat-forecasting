import os as _o, sys as _s
_p = _o.path.dirname(_o.path.abspath(__file__))
while not _o.path.exists(_o.path.join(_p, 'src', 'config.py')): _p = _o.path.dirname(_p)
_s.path.insert(0, _o.path.join(_p, 'src'))
from config import WS_ROOT  # PATH-PATCH: was an absolute path to the original working directory
import sys, io, os, numpy as np, pandas as pd
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
P3 = (WS_ROOT + r'\phase3'); AR = os.path.join(P3, 'archive_pre_diag'); L = []
EV = pd.read_csv(os.path.join(AR, 'event_inventory.csv')); EV = EV[(EV.variant == 'primary') & EV.complete_sequence].copy(); EV['start'] = pd.to_datetime(EV.start); EV['year'] = EV.start.dt.year
EV = EV.sort_values('start').reset_index(drop=True); cl = 0; last = None; ids = []
for s in EV.start:
    if last is not None and (s - last).days > 3: cl += 1
    ids.append(cl); last = s
EV['cluster'] = ids; L.append('CLUSTER IMPLEMENTATION: events sorted by start date; a new cluster starts when the gap to the previous event (any station) exceeds 3 days (chained / transitive; no distance limit).')
for nm, d in (('development', EV[EV.year <= 2018]), ('test', EV[EV.year >= 2019]), ('all', EV)):
    g = d.groupby('cluster').agg(n=('station', 'size'), st=('station', 'nunique'), span=('start', lambda x: (x.max() - x.min()).days))
    L.append(f'{nm}: events {len(d)}, clusters {len(g)}; events per cluster median {g.n.median():.0f}, max {g.n.max()}; stations per cluster max {g.st.max()}; largest chained span {g.span.max()} days; clusters with span > 7 days: {int((g.span > 7).sum())}')
L.append('\nEVENT-LEVEL MAGNITUDE of the simulated (fixed-property) apparent change in ln alpha vs the observed change (identified events)')
for m in ('dev', 'test'):
    e = pd.read_csv(os.path.join(P3, f'layered_events_{m}.csv')); w = pd.read_csv(os.path.join(P3, f'layered_windows_{m}.csv')); w = w[w.status == 'usable']
    ob = (w.lna2_obs - w.lna1_obs)[w.ident_obs]
    L.append(f'{m}: OBSERVED identified events n {len(ob)}: median |delta| {ob.abs().median():.2f}, SD {ob.std():.2f}, 90th percentile |delta| {ob.abs().quantile(.9):.2f}')
    for c in ('U', 'G_low', 'G_high', 'S_central'):
        d = e[(e.run == 'R0_refined_nf') & (e.column == c)]
        L.append(f'   SIMULATED {c:9s} n {len(d):3d}: median |delta| {d.delta.abs().median():.2f}, SD {d.delta.std():.2f}, 90th percentile |delta| {d.delta.abs().quantile(.9):.2f}, max |delta| {d.delta.abs().max():.2f}')
open(os.path.join(P3, 'layered_extra_stats.txt'), 'w', encoding='utf-8').write('\n'.join(L)); print('\n'.join(L))
# combined event-level output
a = pd.read_csv(os.path.join(P3, 'layered_events_dev.csv')).assign(split='development'); b = pd.read_csv(os.path.join(P3, 'layered_events_test.csv')).assign(split='test')
pd.concat([a, b]).to_csv(os.path.join(P3, 'layered_event_level_all.csv'), index=False); print('combined event-level rows', len(a) + len(b))
