import os as _o, sys as _s
_p = _o.path.dirname(_o.path.abspath(__file__))
while not _o.path.exists(_o.path.join(_p, 'src', 'config.py')): _p = _o.path.dirname(_p)
_s.path.insert(0, _o.path.join(_p, 'src'))
from config import WS_ROOT  # PATH-PATCH: was an absolute path to the original working directory
"""
Part 1. Selma reconciliation: same column, same dates, earlier pilot episodes vs new audit.
Part 2. Record checks for candidate stations (inspection flags, not automatic rejection of unusual values).
Part 3. Pre-specified station selection for the small pilot.

SELECTION RULE (fixed before running; uses 2019-2021 only; final evaluation year 2022 is not downloaded or inspected):
  From the 39 audit-qualifying stations, keep those with no unresolved record flag:
    completeness (all of T5, T10, T20, SM10 valid) >= 60% of hours
    longest run of identical hourly SM10 values < 7 days
    SM10 one-hour jumps > 0.05 with no precipitation in the previous 6 h: <= 20 per year
    temperature amplitude ordering A(T5) > A(T10) > A(T20) on >= 90% of informative days
  Rank by: within-site two-state bins, then residual moisture SD after temperature + season (sd_TS).
  Take the top 5, at most one per state. Add Selma as the reference station (6 total).
"""
import sys, io, os, glob, warnings
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
warnings.filterwarnings('ignore')
import numpy as np, pandas as pd

SO = WS_ROOT
IN = os.path.join(SO, 'multi')
def load(stn, years=(2019, 2020, 2021)):
    ps = [np.load(os.path.join(IN, f'{stn}_{y}.npz')) for y in years if os.path.exists(os.path.join(IN, f'{stn}_{y}.npz'))]
    return (np.concatenate([p['date'] for p in ps]), np.concatenate([p['hour'] for p in ps]), np.concatenate([p['P'] for p in ps]),
            np.concatenate([p['SM'] for p in ps]), np.concatenate([p['ST'] for p in ps]))

# ---------------- Part 1: Selma reconciliation ----------------
print('=== PART 1. SELMA RECONCILIATION ===')
raw = []
for yr in (2019, 2020):
    for line in open(os.path.join(SO, 'raw', f'CRNH0203-{yr}-AL_Selma_13_WNW.txt')):
        p = line.split()
        if len(p) >= 38: raw.append([float(p[29]), float(p[33]), float(p[34]), float(p[35])])
raw = np.array(raw); raw[raw < -90] = np.nan
d, h, P, SM, ST = load('AL_Selma_13_WNW', (2019, 2020))
same = np.allclose(np.nan_to_num(raw[:, 0], nan=-1), np.nan_to_num(SM[:, 1], nan=-1), atol=1e-4) and \
       np.allclose(np.nan_to_num(raw[:, 1:], nan=-1), np.nan_to_num(ST[:, :3], nan=-1), atol=1e-3)
print(f'Rows: pilot raw files {len(raw)}, audit arrays {len(SM)}. Column 29 (SOIL_MOISTURE_10) and soil T 5/10/20 identical hour by hour: {same}')
# rebuild pilot episode mask exactly as 04b/11 did (all 5 T and all 5 SM valid, all 5 T > 1 C, runs >= 144 h)
valid = np.all(~np.isnan(ST), 1) & np.all(~np.isnan(SM), 1) & np.all(ST > 1.0, 1)
inep = np.zeros(len(valid), bool); s0 = None
for i in range(len(valid) + 1):
    v = valid[i] if i < len(valid) else False
    if v and s0 is None: s0 = i
    if not v and s0 is not None:
        if i - s0 >= 144: inep[s0:i] = True
        s0 = None
print(f'Pilot-episode hours rebuilt: {inep.sum()} (pilot reported 14,703)')
th = SM[:, 1]
A = pd.read_csv(os.path.join(SO, 'audit_dry_days.csv')); A = A[A.station == 'AL_Selma_13_WNW']
dd = pd.DataFrame({'date': d, 'ep': inep}).groupby('date').ep.all()
A['in_ep'] = A.date.map(dd).fillna(False).astype(bool)
A1920 = A[A.date < 20210101]
def q(x): return ' '.join(f'{v:.3f}' for v in np.percentile(x, [0, 5, 25, 50, 75, 95, 100]))
print('SM10 percentiles [min p5 p25 p50 p75 p95 max]:')
print(f'  all valid hours 2019-2020            : {q(th[~np.isnan(th)])}')
print(f'  pilot-episode hours 2019-2020        : {q(th[inep])}')
print(f'  audit dry informative days 2019-2021 : {q(A.theta)}  (n={len(A)})')
print(f'  audit dry days 2019-2020             : {q(A1920.theta)}  (n={len(A1920)})')
print(f'  audit dry days inside pilot episodes : {q(A1920[A1920.in_ep].theta)}  (n={int(A1920.in_ep.sum())})')
print(f'  audit dry days outside pilot episodes: {q(A1920[~A1920.in_ep].theta) if (~A1920.in_ep).sum() else "none"}  (n={int((~A1920.in_ep).sum())})')
print('Pilot validity required all five depths of moisture and temperature; the audit required only 5/10/20 cm temperature and 10 cm moisture.')
def twostate(df):
    if len(df) < 30: return 'n<30'
    p25, p75 = np.percentile(df.theta, [25, 75]); b = np.floor(df.Tin / 3) * 3
    bins = [x for x in np.unique(b) if ((df.theta[b == x] <= p25).sum() >= 5) and ((df.theta[b == x] >= p75).sum() >= 5)]
    return f'{len(bins)} bins ({", ".join(str(int(x)) for x in bins)}); r(theta,Tin)={np.corrcoef(df.theta, df.Tin)[0, 1]:.2f}; theta IQR {p25:.3f}-{p75:.3f}'
print('Two-state contrast, audit definition:')
print('  audit dry days 2019-2021      :', twostate(A))
print('  audit dry days 2019-2020      :', twostate(A1920))
print('  dry days inside pilot episodes:', twostate(A1920[A1920.in_ep]))
# training vs test episodes of the 4-model rerun (episodes 1-11 = up to 2020-10-10; 12-14 after)
tr = A1920[A1920.in_ep & (A1920.date <= 20201010)]; te = A1920[A1920.in_ep & (A1920.date > 20201010)]
print('  rerun training episodes 1-11  :', twostate(tr))
print('  rerun test episodes 12-14     :', twostate(te))

# ---------------- Part 2: record checks ----------------
print('\n=== PART 2. RECORD CHECKS (2019-2021) for audit-qualifying stations ===')
R = pd.read_csv(os.path.join(SO, 'audit_station_table.csv'))
R['qual'] = (R.n_dry >= 200) & (R.two_state_bins >= 3) & (R.sd_TS >= 0.03) & (R.insane < 0.05)
Q = R[R.qual].copy()
tt = np.arange(24); Hm = np.linalg.pinv(np.vstack([np.ones(24), tt - 11.5, np.cos(2 * np.pi * tt / 24), np.sin(2 * np.pi * tt / 24)]).T)
out = []
for stn in Q.station:
    d, h, P, SM, ST = load(stn); th = SM[:, 1]; n = len(th)
    comp = float(np.mean(np.all(~np.isnan(ST[:, :3]), 1) & ~np.isnan(th)))
    run = 1; best = 1
    for i in range(1, n):
        if not np.isnan(th[i]) and th[i] == th[i - 1]: run += 1; best = max(best, run)
        else: run = 1
    Pr = np.nan_to_num(P); P6 = np.convolve(Pr, np.ones(6), 'full')[:n]
    dth = np.abs(np.diff(th)); jumps = int(np.nansum((dth > 0.05) & (P6[1:] <= 0.0)))
    df = pd.DataFrame({'d': d, 'h': h, 'T5': ST[:, 0], 'T10': ST[:, 1], 'T20': ST[:, 2]}).dropna()
    ok = 0; tot = 0
    for _, s in df.groupby('d'):
        if len(s) != 24 or s[['T5', 'T10', 'T20']].values.min() <= 1: continue
        s = s.sort_values('h'); a = [np.hypot(*(Hm @ s[c].values)[2:]) for c in ('T5', 'T10', 'T20')]
        if a[0] < 1.0: continue
        tot += 1; ok += (a[0] > a[1] > a[2])
    yrs = n / 8766
    rec = dict(station=stn, state=stn[:2], completeness=comp, stuck_days=best / 24, jumps_per_yr=jumps / yrs, amp_order=ok / max(tot, 1),
               th_min=float(np.nanmin(th)), th_max=float(np.nanmax(th)), two_state_bins=int(Q.set_index('station').loc[stn, 'two_state_bins']),
               sd_TS=float(Q.set_index('station').loc[stn, 'sd_TS']), r_thT=float(Q.set_index('station').loc[stn, 'r_thT']))
    rec['flag'] = ';'.join(f for f, c in [('completeness', comp < 0.6), ('stuck', best / 24 >= 7), ('jumps', jumps / yrs > 20), ('amp_order', ok / max(tot, 1) < 0.9)] if c)
    out.append(rec)
C = pd.DataFrame(out).sort_values(['two_state_bins', 'sd_TS'], ascending=False)
pd.set_option('display.width', 250)
print(C.round(3).to_string(index=False))
C.to_csv(os.path.join(SO, 'record_checks.csv'), index=False)

# ---------------- Part 3: selection ----------------
print('\n=== PART 3. PRE-SPECIFIED SELECTION ===')
sel = []; states = set()
for _, r in C[C.flag == ''].iterrows():
    if r.station == 'AL_Selma_13_WNW' or r.state in states: continue
    sel.append(r.station); states.add(r.state)
    if len(sel) == 5: break
sel.append('AL_Selma_13_WNW')
print('Selected:', sel)
print('Flagged (inspect, not rejected as faulty):', C[C.flag != ''][['station', 'flag']].to_string(index=False))
open(os.path.join(SO, 'pilot_stations.txt'), 'w').write('\n'.join(sel))
