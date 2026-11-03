import os as _o, sys as _s
_p = _o.path.dirname(_o.path.abspath(__file__))
while not _o.path.exists(_o.path.join(_p, 'src', 'config.py')): _p = _o.path.dirname(_p)
_s.path.insert(0, _o.path.join(_p, 'src'))
from config import WS_ROOT  # PATH-PATCH: was an absolute path to the original working directory
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import numpy as np, pandas as pd
R = pd.read_csv((WS_ROOT + r'\audit_station_table.csv'))
A = pd.read_csv((WS_ROOT + r'\audit_dry_days.csv'))
R['qual'] = (R.n_dry >= 200) & (R.two_state_bins >= 3) & (R.sd_TS >= 0.03) & (R.insane < 0.05)
Q = R[R.qual].copy()
g = A[A.station.isin(Q.station)].groupby('station').theta
Q = Q.set_index('station')
Q['th_p05'] = g.quantile(0.05); Q['th_p95'] = g.quantile(0.95)
print('Qualifying stations: 10 cm moisture distribution on dry informative days (m3/m3)')
print(Q[['n_dry', 'th_p05', 'th_p25', 'th_p75', 'th_p95', 'r_thT', 'two_state_bins']].sort_values('th_p05').round(3).to_string())
print('\nStations whose 5th percentile is below 0.15 (reach the dry range):', int((Q.th_p05 < 0.15).sum()), 'of', len(Q))
print('Stations whose 5th percentile is above 0.30 (always moist):', int((Q.th_p05 > 0.30).sum()), 'of', len(Q))
# pooled coverage of (theta, Tin) across qualifying stations, 3 C bins
B = A[A.station.isin(Q.index)].copy(); B['Tb'] = (np.floor(B.Tin / 3) * 3).astype(int)
cov = B.groupby('Tb').agg(days=('theta', 'size'), stations=('station', 'nunique'),
                          th_p05=('theta', lambda x: x.quantile(.05)), th_p95=('theta', lambda x: x.quantile(.95)))
print('\nPooled coverage across qualifying stations, by Tin bin:')
print(cov.round(3).to_string())
# within-site, temperature-matched moisture contrast: day pairs in same station & same 1 C Tin bin, |dtheta| >= 0.10
B['T1'] = np.floor(B.Tin).astype(int)
pairs = 0; stn_pairs = {}
for (s, t), grp in B.groupby(['station', 'T1']):
    th = np.sort(grp.theta.values); n = len(th)
    if n < 2: continue
    j = 0; c = 0
    for i in range(n):
        while j < n and th[j] - th[i] < 0.10: j += 1
        c += n - j
    pairs += c; stn_pairs[s] = stn_pairs.get(s, 0) + c
print(f'\nWithin-site day pairs at the same 1 C Tin with |dtheta| >= 0.10: {pairs} total; stations with >=100 such pairs: {sum(v >= 100 for v in stn_pairs.values())}')
