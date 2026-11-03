import os as _o, sys as _s
_p = _o.path.dirname(_o.path.abspath(__file__))
while not _o.path.exists(_o.path.join(_p, 'src', 'config.py')): _p = _o.path.dirname(_p)
_s.path.insert(0, _o.path.join(_p, 'src'))
from config import WS_ROOT  # PATH-PATCH: was an absolute path to the original working directory
"""
Multi-station contrast audit (USCRN, lower 48, 2019-2021). No model fitting.

PRE-SPECIFIED DEFINITIONS (fixed before results)
 Informative day (local standard time day):
   - all 24 hours valid for soil T at 5, 10, 20 cm and soil moisture at 10 cm
   - min(T5, T10, T20) over the day > 1 C (no freezing)
   - 24 h harmonic amplitude of T5 >= 1.0 C (enough diurnal forcing)
 Dry informative day: informative, precipitation <= 1 mm that day AND the previous day (limits infiltration heat transport).
 Per day: theta = mean 10 cm moisture; Tin = mean of (T5 + T20)/2 (boundary temperatures only, matches the model input).
 Per station, on dry informative days:
   r_thT     Pearson correlation of theta and Tin (within-site collinearity)
   sd_T      residual SD of theta after regression on Tin
   sd_TS     residual SD of theta after regression on Tin + annual harmonic (sin, cos of day of year)
   two-state bins: Tin bins 3 C wide containing >= 5 days with theta <= station P25 AND >= 5 days with theta >= station P75
             (contrasting moisture states at overlapping temperatures, within the site)
   spread    day-weighted median over bins (>= 15 days) of theta P90 - P10 within the bin
 Station qualifies for the identifiability study if:
   >= 200 dry informative days, >= 3 two-state bins, and sd_TS >= 0.03 m3/m3
   and moisture sensor sane: < 5% of hours with theta10 > 0.60 or < 0.01.
 Pooled check over qualifying stations: site-demeaned correlation of theta and Tin (fixed-site-effect collinearity),
   variance inflation 1/(1-r^2), and spread of within-site r_thT signs.
"""
import sys, io, os, glob, warnings
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
warnings.filterwarnings('ignore')
import numpy as np, pandas as pd

IN = (WS_ROOT + r'\multi')
files = sorted(glob.glob(os.path.join(IN, '*.npz')))
stations = sorted(set(os.path.basename(f).rsplit('_', 1)[0] for f in files))
tt = np.arange(24)
H = np.vstack([np.ones(24), tt - 11.5, np.cos(2 * np.pi * tt / 24), np.sin(2 * np.pi * tt / 24)]).T
Hp = np.linalg.pinv(H)

rows = []; daily_all = []
for stn in stations:
    parts = [np.load(f) for f in sorted(glob.glob(os.path.join(IN, f'{stn}_*.npz')))]
    date = np.concatenate([p['date'] for p in parts]); hour = np.concatenate([p['hour'] for p in parts])
    P = np.concatenate([p['P'] for p in parts]); SM = np.concatenate([p['SM'] for p in parts]); ST = np.concatenate([p['ST'] for p in parts])
    th10 = SM[:, 1]; v = th10[~np.isnan(th10)]
    insane = float(np.mean((v > 0.60) | (v < 0.01))) if len(v) else np.nan
    df = pd.DataFrame({'date': date, 'hour': hour, 'P': P, 'T5': ST[:, 0], 'T10': ST[:, 1], 'T20': ST[:, 2], 'th': th10})
    g = df.groupby('date')
    recs = []
    for d, s in g:
        if len(s) != 24: continue
        X = s[['T5', 'T10', 'T20', 'th']].values
        if np.isnan(X).any(): continue
        if X[:, :3].min() <= 1.0: continue
        s = s.sort_values('hour'); c = Hp @ s['T5'].values
        a5 = float(np.hypot(c[2], c[3]))
        if a5 < 1.0: continue
        recs.append((d, float(np.nansum(s['P'].values)), s['th'].mean(), 0.5 * (s['T5'] + s['T20']).mean(), a5))
    # precipitation of previous calendar day (need all days, not just informative)
    Pd = g['P'].apply(lambda x: np.nansum(x.values)).to_dict()
    D = pd.DataFrame(recs, columns=['date', 'P', 'theta', 'Tin', 'a5'])
    if len(D) == 0:
        rows.append(dict(station=stn, n_inf=0)); continue
    dts = pd.to_datetime(D['date'].astype(str), format='%Y%m%d')
    prev = (dts - pd.Timedelta(days=1)).dt.strftime('%Y%m%d').astype(int)
    D['Pprev'] = [Pd.get(k, np.nan) for k in prev]
    D['doy'] = dts.dt.dayofyear.values
    dry = D[(D.P <= 1.0) & (D.Pprev <= 1.0)].copy()
    rec = dict(station=stn, n_inf=len(D), n_dry=len(dry), insane=insane)
    if len(dry) >= 30:
        th = dry.theta.values; T = dry.Tin.values; w = 2 * np.pi * dry.doy.values / 365.25
        rec['r_thT'] = float(np.corrcoef(th, T)[0, 1])
        X1 = np.vstack([np.ones_like(T), T]).T; X2 = np.vstack([np.ones_like(T), T, np.sin(w), np.cos(w)]).T
        rec['sd_th'] = float(th.std())
        rec['sd_T'] = float(np.std(th - X1 @ np.linalg.lstsq(X1, th, rcond=None)[0]))
        rec['sd_TS'] = float(np.std(th - X2 @ np.linalg.lstsq(X2, th, rcond=None)[0]))
        p25, p75 = np.percentile(th, [25, 75]); rec['th_p25'] = p25; rec['th_p75'] = p75
        bins = np.floor(T / 3.0) * 3.0
        two = []; spreads = []; wts = []
        for b in np.unique(bins):
            m = bins == b
            if (th[m] <= p25).sum() >= 5 and (th[m] >= p75).sum() >= 5: two.append(b)
            if m.sum() >= 15:
                spreads.append(np.percentile(th[m], 90) - np.percentile(th[m], 10)); wts.append(m.sum())
        rec['two_state_bins'] = len(two)
        rec['two_state_Trange'] = f'{min(two):.0f}-{max(two) + 3:.0f}' if two else ''
        if spreads:
            o = np.argsort(spreads); cw = np.cumsum(np.array(wts)[o]); rec['spread'] = float(np.array(spreads)[o][np.searchsorted(cw, cw[-1] / 2)])
        rec['Tin_min'] = float(T.min()); rec['Tin_max'] = float(T.max())
        rec['a5_med'] = float(dry.a5.median())
        dry['station'] = stn; daily_all.append(dry)
    rows.append(rec)

R = pd.DataFrame(rows)
R.to_csv(os.path.join(os.path.dirname(IN), 'audit_station_table.csv'), index=False)
if daily_all: pd.concat(daily_all).to_csv(os.path.join(os.path.dirname(IN), 'audit_dry_days.csv'), index=False)
R['qual'] = (R.n_dry >= 200) & (R.two_state_bins >= 3) & (R.sd_TS >= 0.03) & (R.insane < 0.05)
pd.set_option('display.width', 250); pd.set_option('display.max_rows', 300)
print(f'Stations with data files: {len(stations)}; with >=30 dry informative days: {int(R.r_thT.notna().sum())}')
cols = ['station', 'n_inf', 'n_dry', 'r_thT', 'sd_th', 'sd_T', 'sd_TS', 'two_state_bins', 'two_state_Trange', 'spread', 'Tin_min', 'Tin_max', 'a5_med', 'insane', 'qual']
S = R[R.r_thT.notna()].sort_values(['qual', 'two_state_bins', 'sd_TS'], ascending=False)
print(S[cols].round(3).to_string(index=False))
print('\nReference: AL_Selma_13_WNW row above.')
Q = R[R.qual]
print(f'\nQUALIFYING STATIONS: {len(Q)}')
print('Distribution of within-site r(theta, Tin) across ALL stations with data:', np.round(np.percentile(S.r_thT, [0, 10, 25, 50, 75, 90, 100]), 2))
print('Count r<-0.5:', int((S.r_thT < -0.5).sum()), ' -0.5..-0.2:', int(((S.r_thT >= -0.5) & (S.r_thT < -0.2)).sum()),
      ' -0.2..0.2:', int(((S.r_thT >= -0.2) & (S.r_thT <= 0.2)).sum()), ' >0.2:', int((S.r_thT > 0.2).sum()))
if len(Q):
    A = pd.concat(daily_all); A = A[A.station.isin(Q.station)]
    A['th_d'] = A.theta - A.groupby('station').theta.transform('mean'); A['T_d'] = A.Tin - A.groupby('station').Tin.transform('mean')
    r = np.corrcoef(A.th_d, A.T_d)[0, 1]
    print(f'Pooled (qualifying stations, site-demeaned) r(theta, Tin) = {r:.3f}; variance inflation = {1 / (1 - r ** 2):.2f}; days = {len(A)}')
    print('Qualifying-station r(theta, Tin):', np.round(np.sort(Q.r_thT.values), 2))
    # Selma-like comparison for reference: same quantity at Selma alone
    s = pd.concat(daily_all); s = s[s.station == 'AL_Selma_13_WNW']
    if len(s): print(f'Selma alone (dry informative days 2019-2021): r(theta, Tin) = {np.corrcoef(s.theta, s.Tin)[0, 1]:.3f}')
