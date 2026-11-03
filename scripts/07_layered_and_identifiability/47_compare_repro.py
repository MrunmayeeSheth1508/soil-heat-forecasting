import os as _o, sys as _s
_p = _o.path.dirname(_o.path.abspath(__file__))
while not _o.path.exists(_o.path.join(_p, 'src', 'config.py')): _p = _o.path.dirname(_p)
_s.path.insert(0, _o.path.join(_p, 'src'))
from config import WS_ROOT  # PATH-PATCH: was an absolute path to the original working directory
"""Step 1b: compare the reproduced baseline (phase3/repro) with the archived outputs (phase3/archive_pre_diag). Also build the full attrition table."""
import os, sys, io, hashlib, numpy as np, pandas as pd
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
P3 = (WS_ROOT + r'\phase3'); A = os.path.join(P3, 'archive_pre_diag'); R = os.path.join(P3, 'repro')
L = []
def sha(p): return hashlib.sha256(open(p, 'rb').read()).hexdigest()
for mode in ('dev', 'test'):
    L.append(f'### {mode}')
    for f in (f'pilotA_out_{mode}.txt', f'pilotA_part1_{mode}.csv', f'pilotA_part2_{mode}.csv', f'pilotA_part3_{mode}.csv'):
        a, r = os.path.join(A, f), os.path.join(R, f)
        if not os.path.exists(r): L.append(f'{f}: repro MISSING'); continue
        same = sha(a) == sha(r); L.append(f'{f}: byte-identical = {same}')
        if not same and f.endswith('.csv'):
            da, dr = pd.read_csv(a), pd.read_csv(r); L.append(f'   shape archived {da.shape} repro {dr.shape}')
            if da.shape == dr.shape:
                num = da.select_dtypes('number').columns; md = float(np.nanmax(np.abs(da[num].values - dr[num].values))); L.append(f'   max abs numeric difference {md:.3e}')
        if not same and f.endswith('.txt'):
            la, lr = open(a, encoding='utf8').read().split('\n'), open(r, encoding='utf8').read().split('\n')
            diff = [(x, y) for x, y in zip(la, lr) if x != y]; L.append(f'   differing lines: {len(diff)} of {len(la)}')
            for x, y in diff[:6]: L.append('     A: ' + x[:150]); L.append('     R: ' + y[:150])
# attrition table (from the archived event-level files and the inventory)
EV = pd.read_csv(os.path.join(A, 'event_inventory.csv')); EV = EV[(EV.variant == 'primary') & EV.complete_sequence].copy(); EV['year'] = pd.to_datetime(EV.start).dt.year
L.append('\n### ATTRITION (archived event-level outputs)')
for mode, sel in (('dev', EV.year <= 2018), ('test', EV.year >= 2019)):
    e = EV[sel]; p2 = pd.read_csv(os.path.join(A, f'pilotA_part2_{mode}.csv')); u = p2[p2.usable]; i = u[u.ident]
    nw = int(e.wet_day.notna().sum()); L.append(f'{mode}: complete sequences {len(e)} (wetting {nw}, no wetting {len(e) - nw}); rows with windows tested {len(p2)}; '
                                                f'dropped for post-window shorter than 7 days (no row) {len(e) - len(p2)}; dropped for >10% missing/gaps {int((~p2.usable).sum())}; usable {len(u)} '
                                                f'(wet {int(u.wet.sum())}, ctrl {int((~u.wet).sum())}); identified in both windows {len(i)} (wet {int(i.wet.sum())}, ctrl {int((~i.wet).sum())}); '
                                                f'clusters {i.cluster.nunique()}')
    L.append(f'   not identified: stress window only {int((~u.w1_ident.astype(bool)).sum())}, post/ctrl window only {int((~u.w2_ident.astype(bool)).sum())}, either {int((~u.ident.astype(bool)).sum())}')
open(os.path.join(R, 'repro_comparison.txt'), 'w', encoding='utf-8').write('\n'.join(L)); print('\n'.join(L))
