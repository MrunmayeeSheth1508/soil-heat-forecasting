import os as _o, sys as _s
_p = _o.path.dirname(_o.path.abspath(__file__))
while not _o.path.exists(_o.path.join(_p, 'src', 'config.py')): _p = _o.path.dirname(_p)
_s.path.insert(0, _o.path.join(_p, 'src'))
from config import WS_ROOT  # PATH-PATCH: was an absolute path to the original working directory
"""Forecast-feasibility library (spec: phase3/forecast/forecast_spec_frozen.md). Every forecaster receives ONLY the past (hourly frame truncated at the issue hour)."""
import os, glob, sys
import numpy as np, pandas as pd
ROOT = WS_ROOT; sys.path.insert(0, ROOT)
from heatsolver import simulate, make_grid, init_profile, sample
from pilotA_estimator import fit_window
P3 = os.path.join(ROOT, 'phase3'); DATA = os.path.join(P3, 'data'); DEVYEARS = (2012, 2017); VALYEARS = (2018, 2021)
DEPTH_COLS = ['T5', 'T10', 'T20', 'T50', 'T100']; HORIZON = 72; ISSUE_HOUR = 8; W = 2 * np.pi / 24.0

def load_station(stn):
    a = np.vstack([np.load(f) for f in sorted(glob.glob(os.path.join(DATA, f'{stn}_*.npy')))])
    t = pd.to_datetime(a[:, 0].astype(int).astype(str), format='%Y%m%d', errors='coerce') + pd.to_timedelta(a[:, 1], unit='h')
    df = pd.DataFrame(a[:, 15:20], index=t, columns=DEPTH_COLS); df['Tmx'] = a[:, 4]; df['P'] = a[:, 6]; df['M10'] = a[:, 11]
    df = df[~df.index.isna()]; df = df[~df.index.duplicated()].sort_index()
    return df.reindex(pd.date_range(df.index.min(), df.index.max(), freq='h'))

def daily(df, col, how, minh=20):
    g = df[col].resample('D'); s = getattr(g, how)(); s[g.count() < minh] = np.nan; return s

def doy_stat(series, q, win=7, years=DEVYEARS):
    """calendar-day statistic pooled over day of year +/-win and DEVELOPMENT years only (series is a daily pandas Series)"""
    s = series[(series.index.year >= years[0]) & (series.index.year <= years[1])]
    doy = s.index.dayofyear.values; yrs = np.unique(s.index.year.values); M = np.full((len(yrs), 367), np.nan)
    for i, y in enumerate(yrs): m = s.index.year.values == y; M[i, doy[m]] = s.values[m]
    out = np.full(367, np.nan)
    for d in range(1, 367):
        idx = [((d - 1 + o) % 366) + 1 for o in range(-win, win + 1)]; v = M[:, idx].ravel(); v = v[~np.isnan(v)]
        if len(v) >= 20: out[d] = np.percentile(v, q)
    return out

class Station:
    """development-only references for one station"""
    def __init__(self, stn, alpha_global, alpha_station):
        self.name = stn; self.df = load_station(stn)
        self.tmx_daily = daily(self.df, 'Tmx', 'max'); self.hot_thr = doy_stat(self.tmx_daily, 90)
        self.clim = {c: doy_stat(daily(self.df, c, 'mean'), 50) for c in ('T20', 'T50')}
        self.m10_p40 = doy_stat(daily(self.df, 'M10', 'mean'), 40)
        self.alpha_global = alpha_global; self.alpha_station = alpha_station
        d = self.tmx_daily; self.hot = pd.Series(np.where(d.notna(), d.values >= self.hot_thr[d.index.dayofyear.values], False), index=d.index)

def detect_spells(st):
    """real-time detection: returns list of (third_hot_day, issue_timestamp). Uses only past days at each step."""
    active = False; nhot = 0; gap = 0; issued = False; out = []
    for d, h in st.hot.items():
        if h:
            if not active: active = True; nhot = 1; gap = 0; issued = False
            else: nhot += 1; gap = 0
            if nhot == 3 and not issued: issued = True; out.append((d, d + pd.Timedelta(days=1, hours=ISSUE_HOUR)))
        elif active:
            gap += 1
            if gap >= 3: active = False
    return out

def last_valid(df_past, col, lookback=3):
    v = df_past[col].iloc[-(lookback + 1):].dropna(); return float(v.iloc[-1]) if len(v) else np.nan

def validity(st, ts):
    """returns dict of validity flags using only data <= ts, plus the outcome-validity flags (outcome used only for flags, never as input)"""
    df = st.df; i0 = df.index.get_loc(ts); past = df.iloc[max(i0 - 167, 0):i0 + 1]; r = {}
    r['init_ok'] = all(np.isfinite(last_valid(past, c)) for c in DEPTH_COLS)
    r['past_ok'] = (len(past) == 168) and all(past[c].notna().mean() >= 0.80 for c in DEPTH_COLS)
    tr = past.iloc[-24:]; r['anom_ok'] = all(tr[c].notna().sum() >= 18 for c in ('T20', 'T50'))
    fut = df.iloc[i0 + 1:i0 + 1 + HORIZON]
    for c, k in (('T20', 'out20_ok'), ('T50', 'out50_ok')): r[k] = (len(fut) == HORIZON) and (fut[c].notna().mean() >= 0.90)
    return r

# ----------------------------------------------------------------- forecasters (take the past only)
def f_persistence(past):
    return np.column_stack([np.full(HORIZON, last_valid(past, c)) for c in ('T20', 'T50')])

def f_clim_anomaly(past, st, ts):
    out = []
    tr = past.iloc[-24:]; hours = tr.index; doy_tr = hours.dayofyear.values
    fh = pd.date_range(ts + pd.Timedelta(hours=1), periods=HORIZON, freq='h'); doy_f = fh.dayofyear.values
    for c in ('T20', 'T50'):
        clim = st.clim[c]; a0 = float(tr[c].mean() - np.nanmean(clim[doy_tr])); out.append(clim[doy_f] + a0)
    return np.column_stack(out)

def boundary_forecast(series_past, n_back=168):
    """level = trailing 24 h mean; plus a 24 h harmonic fitted to the preceding 168 h after removing block means (blocks of 24 h ending at the issue hour)"""
    y = series_past.values[-n_back:]; n = len(y); t = np.arange(-n + 1, 1, dtype=float)   # t = 0 is the issue hour
    level = np.nanmean(y[-24:]); res = np.full(n, np.nan)
    for b in range(n // 24):
        sl = slice(n - 24 * (b + 1), n - 24 * b); res[sl] = y[sl] - np.nanmean(y[sl])
    ok = np.isfinite(res)
    if ok.sum() < 48: a = bq = 0.0
    else:
        X = np.column_stack([np.cos(W * t[ok]), np.sin(W * t[ok])]); coef, *_ = np.linalg.lstsq(X, res[ok], rcond=None); a, bq = coef
    th = np.arange(1, HORIZON + 1, dtype=float); return level + a * np.cos(W * th) + bq * np.sin(W * th)

def conduction_forecast(past, alpha, bnd_top=None, bnd_bot=None):
    """uniform-diffusivity solver, 5-100 cm. Boundaries: forecast from past by the fixed rule unless explicit (observed) future arrays are given (reconstruction diagnostic only)."""
    z, dz = make_grid(0.05, 1.0, 38)
    prof = [last_valid(past, c) for c in DEPTH_COLS]; T0 = init_profile(z, np.array([0.05, 0.10, 0.20, 0.50, 1.0]), prof)
    bt = boundary_forecast(past['T5']) if bnd_top is None else bnd_top; bb = boundary_forecast(past['T100']) if bnd_bot is None else bnd_bot
    top = np.concatenate([[prof[0]], bt]); bot = np.concatenate([[prof[4]], bb]); sim = simulate(alpha, top, bot, z, T0)
    return sample(sim, z, [0.20, 0.50])[1:], bt, bb

def fit_alpha_past(past, alpha_fallback):
    """C2: effective diffusivity from the preceding 168 h with the ARCHIVED estimator; used only if identified, else the development global value"""
    h = past[DEPTH_COLS].iloc[-168:]
    if len(h) < 168 or h.isna().mean().max() > 0.10: return alpha_fallback, False
    hf = h.interpolate(limit=3, limit_area='inside')
    if hf.isna().any().any(): return alpha_fallback, False
    f = fit_window(hf)
    return (float(np.exp(f['lna'])), True) if f['ident'] else (alpha_fallback, False)

def forecast_all(st, ts, with_recon=False):
    """ALL competitors for one issue. Slices the station frame at the issue hour internally; nothing after ts is read except in the clearly separated reconstruction diagnostic."""
    df = st.df; i0 = df.index.get_loc(ts); past = df.iloc[max(i0 - 167, 0):i0 + 1].copy()
    out = {'B1': f_persistence(past), 'B2': f_clim_anomaly(past, st, ts)}
    a2, used = fit_alpha_past(past, st.alpha_global); out['alpha_C2'] = a2; out['alpha_C2_fitted'] = used
    out['C1'], _, _ = conduction_forecast(past, st.alpha_global)
    out['C2'], bt, bb = conduction_forecast(past, a2); out['bnd_top'] = bt; out['bnd_bot'] = bb
    out['C3'], _, _ = conduction_forecast(past, st.alpha_station)
    if with_recon:
        fut = df.iloc[i0 + 1:i0 + 1 + HORIZON]; ft = fut['T5'].interpolate(limit_direction='both').values; fb = fut['T100'].interpolate(limit_direction='both').values
        out['RECON'], _, _ = conduction_forecast(past, a2, ft, fb)
    return out

def development_alphas():
    """global and per-station development effective diffusivity references from ARCHIVED pilot fits with start year <= 2017 and identified stress windows"""
    p = pd.read_csv(os.path.join(P3, 'archive_pre_diag', 'pilotA_part2_dev.csv')); p = p[p.usable].copy(); p['start'] = pd.to_datetime(p.start)
    p = p[(p.start.dt.year <= DEVYEARS[1]) & p.w1_ident.astype(bool)]
    g = float(np.exp(p.w1_lna.median())); s = p.groupby('station').w1_lna.agg(['median', 'count']); sd = {k: float(np.exp(r['median'])) for k, r in s.iterrows() if r['count'] >= 2}
    return g, sd, len(p)
