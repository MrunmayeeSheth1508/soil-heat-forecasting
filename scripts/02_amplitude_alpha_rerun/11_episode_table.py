import os as _o, sys as _s
_p = _o.path.dirname(_o.path.abspath(__file__))
while not _o.path.exists(_o.path.join(_p, 'src', 'config.py')): _p = _o.path.dirname(_p)
_s.path.insert(0, _o.path.join(_p, 'src'))
from config import WS_ROOT  # PATH-PATCH: was an absolute path to the original working directory
import sys, io, os, warnings
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
warnings.filterwarnings('ignore')
import numpy as np

raw_dir = (WS_ROOT + r'\raw')
rows = []
for yr in (2019, 2020):
    p = os.path.join(raw_dir, f'CRNH0203-{yr}-AL_Selma_13_WNW.txt')
    for line in open(p):
        s = line.split()
        if len(s) >= 38: rows.append(s)
n = len(rows)
st = np.full((n, 5), np.nan); sm = np.full((n, 5), np.nan); date = []; hour = []
for j, s in enumerate(rows):
    date.append(s[1]); hour.append(s[2])
    for k, c in enumerate([33, 34, 35, 36, 37]):
        try:
            v = float(s[c]); st[j, k] = v if v > -9998 else np.nan
        except: pass
    for k, c in enumerate([28, 29, 30, 31, 32]):
        try:
            v = float(s[c]); sm[j, k] = v if v > -98 else np.nan
        except: pass
valid = np.all(~np.isnan(st), axis=1) & np.all(~np.isnan(sm), axis=1) & np.all(st > 1.0, axis=1)
eps = []; ine = False
for i in range(n):
    if valid[i] and not ine: s0 = i; ine = True
    elif not valid[i] and ine:
        if i - s0 >= 144: eps.append((s0, i))
        ine = False
if ine and n - s0 >= 144: eps.append((s0, n))

def amp(x):
    m = len(x); t = np.arange(m)
    A = np.vstack([np.ones(m), t - t.mean(), np.cos(2 * np.pi * t / 24), np.sin(2 * np.pi * t / 24)]).T
    c, *_ = np.linalg.lstsq(A, x, rcond=None); return float(np.hypot(c[2], c[3]))

print(f'Rows {n}; episodes >=144 h with temperature+moisture valid: {len(eps)}')
print(f'{"ep":>3} {"start UTC":>10} {"end UTC":>10} {"hours":>6} {"SM10 min":>9} {"SM10 max":>9} {"SM10 rng":>9} {"SM10 mean":>10} {"T5 amp":>7} {"T10 amp":>8} {"Tmean(5,20)":>12}')
save = {}
for k, (a, b) in enumerate(eps):
    print(f'{k + 1:3d} {date[a]:>10} {date[b - 1]:>10} {b - a:6d} {sm[a:b, 1].min():9.3f} {sm[a:b, 1].max():9.3f} {np.ptp(sm[a:b, 1]):9.3f} {sm[a:b, 1].mean():10.3f} {amp(st[a:b, 0]):7.2f} {amp(st[a:b, 1]):8.2f} {st[a:b, [0, 2]].mean():12.1f}')
    save[f'T_{k}'] = st[a:b]; save[f'S_{k}'] = sm[a:b]
np.savez((WS_ROOT + r'\episodes14.npz'), n=len(eps), starts=[date[a] for a, b in eps], **save)
tot = sum(b - a for a, b in eps)
print('Total hours', tot)
allsm = np.concatenate([sm[a:b, 1] for a, b in eps]); allT = np.concatenate([st[a:b][:, [0, 2]].mean(1) for a, b in eps])
print('Hourly correlation SM10 vs mean(T5,T20):', round(float(np.corrcoef(allsm, allT)[0, 1]), 3))
em = np.array([sm[a:b, 1].mean() for a, b in eps]); et = np.array([st[a:b][:, [0, 2]].mean() for a, b in eps])
print('Between-episode correlation of mean SM10 and mean T:', round(float(np.corrcoef(em, et)[0, 1]), 3), ' SM10 episode-means range', round(em.min(), 3), round(em.max(), 3))
