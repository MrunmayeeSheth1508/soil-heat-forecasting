import os as _o, sys as _s
_p = _o.path.dirname(_o.path.abspath(__file__))
while not _o.path.exists(_o.path.join(_p, 'src', 'config.py')): _p = _o.path.dirname(_p)
_s.path.insert(0, _o.path.join(_p, 'src'))
from config import WS_ROOT  # PATH-PATCH: was an absolute path to the original working directory
"""
Layered-column null diagnostic (frozen in phase3/layered_spec_frozen.md). Usage: python 46_layered_diagnostic.py dev | test   (test can run ONLY ONCE).
All 'sim' quantities are SIMULATED, never measured. Output: phase3/layered_events_{mode}.csv (event x column x variant), phase3/layered_windows_{mode}.csv (per-event window info).
"""
import sys, io, os, glob, warnings, time, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace'); warnings.filterwarnings('ignore')
import numpy as np, pandas as pd
ROOT = WS_ROOT; sys.path.insert(0, ROOT)
from heatsolver import make_grid, init_profile, sample
from layeredsolver import simulate_layered
from pilotA_estimator import fit_window, getwin, LA, AL
MODE = sys.argv[1]; assert MODE in ('dev', 'test')
P3 = os.path.join(ROOT, 'phase3'); D = os.path.join(P3, 'data'); AR = os.path.join(P3, 'archive_pre_diag')
MARK = os.path.join(P3, 'layered_test_RUN_ONCE.marker')
if MODE == 'test':
    if os.path.exists(MARK): print('REFUSED: the test analysis was already run for this diagnostic:', open(MARK).read()); sys.exit(1)
    open(MARK, 'w').write(f'test analysis started {time.ctime()}; the original test results (contrast +0.141) were already known when this diagnostic was designed.')
# ---- events, ordering, clusters, split (identical to the archived pilot)
EV = pd.read_csv(os.path.join(AR, 'event_inventory.csv')); EV = EV[(EV.variant == 'primary') & EV.complete_sequence].copy()
EV['start'] = pd.to_datetime(EV.start); EV['end'] = pd.to_datetime(EV.end); EV['wet_day'] = pd.to_datetime(EV.wet_day); EV['year'] = EV.start.dt.year
EV = EV.sort_values('start').reset_index(drop=True); cl = 0; last = None; ids = []
for s in EV.start:
    if last is not None and (s - last).days > 3: cl += 1
    ids.append(cl); last = s
EV['cluster'] = ids
EVs = EV[(EV.year <= 2018) if MODE == 'dev' else (EV.year >= 2019)].copy()
print(MODE, 'sequences', len(EVs), 'clusters', EVs.cluster.nunique(), flush=True)
def load_hourly(stn):
    a = np.vstack([np.load(f) for f in sorted(glob.glob(os.path.join(D, f'{stn}_*.npy')))])
    t = pd.to_datetime(a[:, 0].astype(int).astype(str), format='%Y%m%d', errors='coerce') + pd.to_timedelta(a[:, 1], unit='h')
    df = pd.DataFrame(a[:, 15:20], index=t, columns=['T5', 'T10', 'T20', 'T50', 'T100'])
    df = df[~df.index.isna()]; df = df[~df.index.duplicated()].sort_index(); return df.reindex(pd.date_range(df.index.min(), df.index.max(), freq='h'))
H = {s: load_hourly(s) for s in EVs.station.unique()}
# ---- columns (frozen)
CF = pd.read_csv(os.path.join(P3, 'columns_frozen.csv'))
def S_col(stn, variant):
    c = CF[(CF.kind == 'S') & (CF.station == stn) & (CF.variant == variant)].sort_values('layer')
    return (None if len(c) != 3 else ([0.2, 0.5], c.k.values.tolist(), c.C.values.tolist()))
def fixed_col(name):
    c = CF[(CF.station == 'ALL') & (CF.variant == name)].sort_values('layer')
    return ([0.2], c.k.values.tolist(), c.C.values.tolist()) if len(c) == 2 else ([], c.k.values.tolist(), c.C.values.tolist())
aU = float(CF[(CF.variant == 'U')].alpha.iloc[0]); CU = float(CF[(CF.variant == 'U')].C.iloc[0])
def columns_for(stn):
    cols = {'U': fixed_col('U'), 'U_a2e7': ([], [2e-7 * CU], [CU]), 'U_a1e6': ([], [1e-6 * CU], [CU]), 'G_low': fixed_col('G_low'), 'G_high': fixed_col('G_high')}
    for v in ('central', 'dry_ref', 'wet_ref', 'Cs_low', 'Cs_high'):
        c = S_col(stn, v)
        if c is not None: cols['S_' + v] = c
    return cols
RUNS = [dict(name='R0_refined_nf', nint=76, dt=900.0, rnd=False, Bs=6, only=None), dict(name='R1_base_nf', nint=38, dt=3600.0, rnd=False, Bs=6, only=None),
        dict(name='R2_refined_round', nint=76, dt=900.0, rnd=True, Bs=6, only=None), dict(name='R3_refined_nf_Bs24', nint=76, dt=900.0, rnd=False, Bs=24, only=('U', 'S_central', 'G_low', 'G_high'))]
def generate(hf, ifc, kl, Cl, nint, dt):
    z, dz = make_grid(0.05, 1.0, nint)
    T0 = init_profile(z, np.array([0.05, 0.10, 0.20, 0.50, 1.0]), [hf['T5'].values[0], hf['T10'].values[0], hf['T20'].values[0], hf['T50'].values[0], hf['T100'].values[0]])
    n = len(hf); sub = int(round(3600 / dt)); tt = np.arange(0, (n - 1) * 3600 + 1, dt); th = np.arange(n) * 3600.0
    sim, ke, Ce = simulate_layered(z, ifc, kl, Cl, np.interp(tt, th, hf['T5'].values), np.interp(tt, th, hf['T100'].values), T0, dt)
    return sample(sim[::sub], z, [0.10, 0.20, 0.50])
def spec(x):
    x = x - np.polyval(np.polyfit(np.arange(len(x)), x, 1), np.arange(len(x))); f = np.fft.rfftfreq(len(x), 1.0); P = np.abs(np.fft.rfft(x)) ** 2; per = np.where(f > 0, 1 / np.maximum(f, 1e-9), np.inf)
    tot = P[1:].sum(); return float(P[(per >= 18) & (per <= 30)].sum() / tot) if tot > 0 else np.nan
# ---- archived real-data results for reproduction check
A2 = pd.read_csv(os.path.join(AR, f'pilotA_part2_{MODE}.csv')); A2['start'] = pd.to_datetime(A2.start)
rows = []; wins = []; mism = 0; nchk = 0
for _, e in EVs.iterrows():
    stn = e.station; wets = pd.notna(e.wet_day)
    ws = (e.start - pd.Timedelta(days=2), e.end + pd.Timedelta(days=2, hours=23))
    if wets:
        w2 = (e.wet_day + pd.Timedelta(days=1), min(e.wet_day + pd.Timedelta(days=10, hours=23), e.end + pd.Timedelta(days=21, hours=23)))
        if (w2[1] - w2[0]).days + 1 < 7: wins.append(dict(station=stn, start=e.start, cluster=e.cluster, wet=True, status='dropped_short_post_window')); continue
    else: w2 = (e.end + pd.Timedelta(days=4), e.end + pd.Timedelta(days=14, hours=23))
    h1 = getwin(H, stn, *ws); h2 = getwin(H, stn, *w2)
    if h1 is None or h2 is None: wins.append(dict(station=stn, start=e.start, cluster=e.cluster, wet=wets, status='dropped_missing_data')); continue
    overlap = bool(ws[1] >= w2[0])
    # reproduction of the archived real-data fits (event level)
    o1 = fit_window(h1); o2 = fit_window(h2); a = A2[(A2.station == stn) & (A2.start == e.start)]
    if len(a):
        a = a.iloc[0]; nchk += 1
        if not (abs(a.lna1_base - o1['lna']) < 1e-12 and abs(a.lna2_base - o2['lna']) < 1e-12 and bool(a.ident) == bool(o1['ident'] and o2['ident'])): mism += 1
    wins.append(dict(station=stn, start=e.start, cluster=e.cluster, wet=wets, status='usable', month=e.month, overlap=overlap, n1=len(h1), n2=len(h2),
                     diurnal1=spec(h1['T5'].values), diurnal2=spec(h2['T5'].values), grad1=float(np.mean(np.abs(h1['T5'] - h1['T100']))), grad2=float(np.mean(np.abs(h2['T5'] - h2['T100']))),
                     lna1_obs=o1['lna'], lna2_obs=o2['lna'], ident_obs=bool(o1['ident'] and o2['ident']), rmse1_obs=o1['rmse'], rmse2_obs=o2['rmse']))
    cols = columns_for(stn)
    for R in RUNS:
        for cname, (ifc, kl, Cl) in cols.items():
            if R['only'] is not None and cname not in R['only']: continue
            fits = []
            for hf in (h1, h2):
                pr = generate(hf, ifc, kl, Cl, R['nint'], R['dt'])
                if R['rnd']: pr = np.round(pr, 1)
                hs = hf.copy(); hs[['T10', 'T20', 'T50']] = pr
                fits.append(fit_window(hs, Bs=R['Bs']))
            f1, f2 = fits
            rows.append(dict(run=R['name'], column=cname, station=stn, start=e.start, cluster=e.cluster, wet=wets, month=e.month, lna1=f1['lna'], lna2=f2['lna'], delta=f2['lna'] - f1['lna'],
                             ident1=f1['ident'], ident2=f2['ident'], ident=bool(f1['ident'] and f2['ident']), rmse1=f1['rmse'], rmse2=f2['rmse'], w1=f1['hi'] - f1['lo'], w2=f2['hi'] - f2['lo']))
    if len(wins) % 20 == 0: print('  events processed', len(wins), flush=True)
pd.DataFrame(rows).to_csv(os.path.join(P3, f'layered_events_{MODE}.csv'), index=False); pd.DataFrame(wins).to_csv(os.path.join(P3, f'layered_windows_{MODE}.csv'), index=False)
msg = f'{MODE}: reproduction of archived real-data event-level fits: checked {nchk}, mismatches {mism}'; print(msg)
open(os.path.join(P3, f'layered_repro_check_{MODE}.txt'), 'w').write(msg)
