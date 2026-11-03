import os as _o, sys as _s
_p = _o.path.dirname(_o.path.abspath(__file__))
while not _o.path.exists(_o.path.join(_p, 'src', 'config.py')): _p = _o.path.dirname(_p)
_s.path.insert(0, _o.path.join(_p, 'src'))
from config import WS_ROOT  # PATH-PATCH: was an absolute path to the original working directory
"""EXPLORATORY post-hoc descriptive checks on the ARCHIVED OBSERVED pilot outputs (no new fits, no simulation): how the observed rain-linked contrast depends on selection.
Labelled post hoc: these were not in the frozen specification; the test split was already known."""
import sys, io, os, numpy as np, pandas as pd
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
P3 = (WS_ROOT + r'\phase3'); AR = os.path.join(P3, 'archive_pre_diag')
rng = np.random.default_rng(20261014)
def cb(df, B=2000):
    df = df.reset_index(drop=True)
    if df.wet.nunique() < 2 or len(df) < 4: return (np.nan, np.nan)
    ids = df.cluster.unique(); pos = {c: np.where(df.cluster.values == c)[0] for c in ids}; v = []
    for _ in range(B):
        x = df.iloc[np.concatenate([pos[c] for c in rng.choice(ids, len(ids))])]
        if x.wet.nunique() < 2: continue
        v.append(x[x.wet].d.mean() - x[~x.wet].d.mean())
    return (float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5))) if v else (np.nan, np.nan)
def ct(df): return float(df[df.wet].d.mean() - df[~df.wet].d.mean()) if df.wet.nunique() == 2 else np.nan
L = ['EXPLORATORY post-hoc selection checks on the archived OBSERVED fits (not simulated; no new fits)']
EDGE = (np.log(5e-8), np.log(5e-6))
for m in ('dev', 'test'):
    p = pd.read_csv(os.path.join(AR, f'pilotA_part2_{m}.csv')); p = p[p.usable].copy(); p['d'] = p.lna2_base - p.lna1_base
    w = pd.read_csv(os.path.join(P3, f'layered_windows_{m}.csv')); w['start'] = pd.to_datetime(w.start); p['start'] = pd.to_datetime(p.start)
    p = p.merge(w[['station', 'start', 'overlap']], on=['station', 'start'], how='left'); p['ident'] = p.ident.astype(bool); p['overlap'] = p.overlap.fillna(False).astype(bool); p['wet'] = p.wet.astype(bool)
    p['edge'] = (p.lna1_base <= EDGE[0] + 1e-9) | (p.lna1_base >= EDGE[1] - 1e-9) | (p.lna2_base <= EDGE[0] + 1e-9) | (p.lna2_base >= EDGE[1] - 1e-9)
    L.append(f'\n=== {m.upper()}: usable {len(p)} (wet {int(p.wet.sum())}, ctrl {int((~p.wet).sum())}); identified {int(p.ident.sum())}; overlap events {int(p.overlap.sum())}; grid-edge fits {int(p.edge.sum())} ===')
    for nm, d in [('identified (archived rule)', p[p.ident]), ('all usable', p), ('identified, no stress/post overlap', p[p.ident & ~p.overlap]), ('all usable, no overlap', p[~p.overlap]),
                  ('identified, May-Sep', p[p.ident & p.month.isin([5, 6, 7, 8, 9])]), ('not identified (either window)', p[~p.ident])]:
        c = ct(d); lo, hi = cb(d); L.append(f'{nm:38s}: contrast {c:+.3f} [{lo:+.3f}, {hi:+.3f}]  (wet {int(d.wet.sum())}, ctrl {int((~d.wet).sum())}, clusters {d.cluster.nunique()})')
    ni = p[~p.ident]; L.append(f'not-identified events: median |delta| {ni.d.abs().median():.2f} vs identified {p[p.ident].d.abs().median():.2f}; grid-edge fits among not-identified {int(ni.edge.sum())} of {len(ni)}')
    L.append(f'share of events identified: wet {p[p.wet].ident.mean():.2f}, ctrl {p[~p.wet].ident.mean():.2f}')
open(os.path.join(P3, 'observed_selection_checks.txt'), 'w', encoding='utf-8').write('\n'.join(L)); print('\n'.join(L))
