import os as _o, sys as _s
_p = _o.path.dirname(_o.path.abspath(__file__))
while not _o.path.exists(_o.path.join(_p, 'src', 'config.py')): _p = _o.path.dirname(_p)
_s.path.insert(0, _o.path.join(_p, 'src'))
from config import WS_ROOT  # PATH-PATCH: was an absolute path to the original working directory
"""
Follow-up: is alpha constant in time within an episode, and does windowed alpha track measured moisture?
Windowed (96 h, stride 48 h, first 24 h discarded) in-sample fit of one alpha per window on the 5-20 cm slab, observation at 10 cm.
Solver verified separately (09_amplitude_check.py Q2).
"""
import sys, io, os, warnings
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
warnings.filterwarnings('ignore')
import numpy as np
from scipy.stats import spearmanr
from scipy.linalg import solve_banded

raw_dir = (WS_ROOT + r'\raw')
NZ = 7; OBS = 2; dz = 0.025
def load(stn, years):
    rows = []
    for yr in years:
        p = os.path.join(raw_dir, f'CRNH0203-{yr}-{stn}.txt')
        if os.path.exists(p):
            for line in open(p):
                s = line.split()
                if len(s) >= 38: rows.append(s)
    st = np.full((len(rows), 5), np.nan); sm = np.full((len(rows), 5), np.nan)
    for j, s in enumerate(rows):
        for k, c in enumerate([33, 34, 35, 36, 37]):
            try:
                v = float(s[c]); st[j, k] = v if v > -9998 else np.nan
            except: pass
        for k, c in enumerate([28, 29, 30, 31, 32]):
            try:
                v = float(s[c]); sm[j, k] = v if v > -98 else np.nan
            except: pass
    return st, sm

def cn(alpha, Ttop, Tbot, Tinit):
    N = len(Ttop); r = alpha * 3600.0 / dz ** 2; ni = NZ - 2
    ab = np.zeros((3, ni)); ab[0, 1:] = -r / 2; ab[1, :] = 1 + r; ab[2, :-1] = -r / 2
    T = Tinit.astype(float).copy(); out = np.zeros(N); out[0] = T[OBS]
    for n in range(1, N):
        rhs = (r / 2) * T[:-2] + (1 - r) * T[1:-1] + (r / 2) * T[2:]
        rhs[0] += (r / 2) * Ttop[n]; rhs[-1] += (r / 2) * Tbot[n]
        T[1:-1] = solve_banded((1, 1), ab, rhs); T[0] = Ttop[n]; T[-1] = Tbot[n]; out[n] = T[OBS]
    return out

def amp(x):
    n = len(x); t = np.arange(n)
    A = np.vstack([np.ones(n), t - t.mean(), np.cos(2 * np.pi * t / 24), np.sin(2 * np.pi * t / 24)]).T
    c, *_ = np.linalg.lstsq(A, x, rcond=None); return np.hypot(c[2], c[3])

st, sm = load('AL_Selma_13_WNW', [2019, 2020])
vT = np.all(~np.isnan(st), axis=1) & np.all(st > 1.0, axis=1)
vS = vT & np.all(~np.isnan(sm), axis=1)
def episodes(v, minlen):
    out = []; ine = False
    for i in range(len(v)):
        if v[i] and not ine: s0 = i; ine = True
        elif not v[i] and ine:
            if i - s0 >= minlen: out.append((s0, i))
            ine = False
    if ine and len(v) - s0 >= minlen: out.append((s0, len(v)))
    return out
print('EPISODE COUNTS: temperature-only validity, >=96 h:', len(episodes(vT, 96)), ' >=144 h:', len(episodes(vT, 144)))
print('                temperature+moisture validity, >=96 h:', len(episodes(vS, 96)), ' >=144 h:', len(episodes(vS, 144)))
pl = open((WS_ROOT + r'\pilot_out2.txt'), encoding='utf-8', errors='replace').read().splitlines()
screen = [l for l in pl if l.strip()[:3].strip().isdigit() and 'e-' in l]
print('Rows in pilot_out2.txt episode screen table:', len(screen))

grid = np.exp(np.linspace(np.log(5e-8), np.log(5e-6), 45))
rec = []
for ep_i, (es, ee) in enumerate(episodes(vS, 144)):
    for w0 in range(es, ee - 96 + 1, 48):
        sl = slice(w0, w0 + 96)
        T5, T10, T20 = st[sl, 0], st[sl, 1], st[sl, 2]
        if amp(T5) < 1.0: continue
        init = np.linspace(T5[0], T20[0], NZ)
        best = None
        for a in grid:
            m = cn(a, T5, T20, init)
            rm = np.sqrt(np.mean((m[24:] - T10[24:]) ** 2))
            if best is None or rm < best[1]: best = (a, rm, amp(m[24:]) / max(amp(T10[24:]), 1e-9))
        rec.append((ep_i + 1, w0, best[0], best[1], best[2], sm[sl, 0].mean(), sm[sl, 1].mean(), sm[sl, 2].mean(), st[sl, 1].mean(), amp(T10)))
R = np.array(rec)
print(f'\nWindows fitted: {len(R)} from {len(set(R[:, 0]))} episodes (96 h windows, 5 cm diurnal amplitude >= 1 C)')
print(f'Per-window alpha: median {np.median(R[:, 2]):.2e}; 10th-90th pct {np.percentile(R[:, 2], 10):.2e} - {np.percentile(R[:, 2], 90):.2e}')
print(f'Per-window amplitude ratio at best alpha: median {np.median(R[:, 4]):.3f}; 10th-90th pct {np.percentile(R[:, 4], 10):.3f} - {np.percentile(R[:, 4], 90):.3f}')
print(f'Per-window RMSE: median {np.median(R[:, 3]):.3f} C')
ae = np.log(R[:, 2])
names = ['SM 5 cm', 'SM 10 cm', 'SM 20 cm', 'T 10 cm mean']
print('\nSpearman correlation of log(window alpha) with window-mean covariate:')
print(f'{"covariate":>14} {"pooled rho":>11} {"p":>9} {"within-episode rho (episodes demeaned)":>40}')
for k, nme in zip([5, 6, 7, 8], names):
    x = R[:, k]; rho, p = spearmanr(x, ae)
    xd = x.copy(); yd = ae.copy()
    for e in set(R[:, 0]):
        m = R[:, 0] == e; xd[m] -= xd[m].mean(); yd[m] -= yd[m].mean()
    rho2, p2 = spearmanr(xd, yd)
    print(f'{nme:>14} {rho:11.3f} {p:9.1e} {rho2:12.3f} (p {p2:.1e})')
# how much of alpha variance is between episodes vs within
tot = ae.var(); within = np.mean([ae[R[:, 0] == e].var() for e in set(R[:, 0])])
print(f'\nVariance of log alpha: total {tot:.3f}, mean within-episode {within:.3f}')
print('Effective independent windows is far fewer than the window count: windows overlap by 50% and are autocorrelated.')
