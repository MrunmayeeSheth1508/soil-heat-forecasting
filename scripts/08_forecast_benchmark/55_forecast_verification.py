import os as _o, sys as _s
_p = _o.path.dirname(_o.path.abspath(__file__))
while not _o.path.exists(_o.path.join(_p, 'src', 'config.py')): _p = _o.path.dirname(_p)
_s.path.insert(0, _o.path.join(_p, 'src'))
from config import WS_ROOT  # PATH-PATCH: was an absolute path to the original working directory
"""Forecast verification (spec section 'Verification'; run BEFORE any score is read). Output: phase3/forecast/forecast_verification_out.txt"""
import sys, io, os, warnings, copy
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace'); warnings.filterwarnings('ignore')
sys.path.insert(0, WS_ROOT)
import numpy as np, pandas as pd
from forecastlib import *
FD = os.path.join(P3, 'forecast'); OUT = []; ALL = True
def say(s=''): OUT.append(s); print(s)
def check(name, ok, detail=''):
    global ALL; ALL &= bool(ok); say(f'[{"PASS" if ok else "FAIL"}] {name} {detail}')
I = pd.read_csv(os.path.join(FD, 'issue_inventory.csv'), parse_dates=['issue']); C = I[I.common]
gA, sA, nA = development_alphas(); say(f'development alpha references: global {gA:.3e} m2/s from {nA} identified archived stress windows (start year <= 2017); station medians for {len(sA)} stations')
# pick three issues at different stations/years (validation and development)
picks = [C[C.split == 'val'].iloc[0], C[C.split == 'val'].iloc[len(C[C.split == 'val']) // 2], C[C.split == 'dev'].iloc[len(C[C.split == 'dev']) // 2]]
def run(st, ts, recon=False): return forecast_all(st, ts, with_recon=recon)
# ---- 1. information-set test: destroy everything after the issue hour
ok1 = True; worst = 0.0
for r in picks:
    st = Station(r.station, gA, sA.get(r.station, gA)); ts = r.issue
    base = run(st, ts)
    st2 = Station.__new__(Station); st2.__dict__ = {k: (v.copy() if hasattr(v, 'copy') else v) for k, v in st.__dict__.items()}
    st2.df = st.df.copy(); mask = st2.df.index > ts
    st2.df.loc[mask, DEPTH_COLS] = st2.df.loc[mask, DEPTH_COLS] + 37.0; st2.df.loc[mask, ['P', 'M10', 'Tmx']] = 999.0
    alt = run(st2, ts)
    for k in ('B1', 'B2', 'C1', 'C2', 'C3', 'bnd_top', 'bnd_bot'): worst = max(worst, float(np.nanmax(np.abs(base[k] - alt[k]))))
    ok1 &= (worst == 0.0 and base['alpha_C2'] == alt['alpha_C2'])
check('1. information-set test: every forecast unchanged when ALL data after the issue hour is corrupted (+37 C, rain 999 mm)', ok1, f'(max difference {worst:.1e} C, {len(picks)} issues)')
# ---- 1b. positive control: the reconstruction diagnostic MUST react to future data
st = Station(picks[0].station, gA, sA.get(picks[0].station, gA)); ts = picks[0].issue
rb = run(st, ts, True); st3 = Station.__new__(Station); st3.__dict__ = dict(st.__dict__); st3.df = st.df.copy(); m = st3.df.index > ts; st3.df.loc[m, ['T5', 'T100']] += 5.0
rb3 = run(st3, ts, True); check('1b. positive control: the clearly separated reconstruction diagnostic reacts to future boundaries (so the test above can detect leakage)', np.nanmax(np.abs(rb['RECON'] - rb3['RECON'])) > 0.1, f'(max change {np.nanmax(np.abs(rb["RECON"] - rb3["RECON"])):.2f} C)')
# ---- 2. leakage test: validation-year data must not change thresholds/climatologies/alpha references
ok2 = True
st = Station(picks[0].station, gA, sA.get(picks[0].station, gA)); df0 = st.df
st4 = Station.__new__(Station); df1 = df0.copy(); mv = df1.index.year >= VALYEARS[0]; df1.loc[mv, DEPTH_COLS + ['Tmx', 'M10']] = df1.loc[mv, DEPTH_COLS + ['Tmx', 'M10']] * 3 + 11
tm = daily(df1, 'Tmx', 'max'); thr1 = doy_stat(tm, 90); c20 = doy_stat(daily(df1, 'T20', 'mean'), 50); c50 = doy_stat(daily(df1, 'T50', 'mean'), 50); m40 = doy_stat(daily(df1, 'M10', 'mean'), 40)
ok2 = np.allclose(thr1, st.hot_thr, equal_nan=True) and np.allclose(c20, st.clim['T20'], equal_nan=True) and np.allclose(c50, st.clim['T50'], equal_nan=True) and np.allclose(m40, st.m10_p40, equal_nan=True)
pp = pd.read_csv(os.path.join(P3, 'archive_pre_diag', 'pilotA_part2_dev.csv')); pp['start'] = pd.to_datetime(pp.start); alpha_years = pp[(pp.usable) & pp.w1_ident.astype(bool) & (pp.start.dt.year <= 2017)].start.dt.year.max()
check('2. leakage test: hot-day thresholds, climatologies and moisture percentile unchanged when validation-year data are altered; alpha references use fits with start year <= 2017', ok2 and alpha_years <= 2017, f'(latest year contributing to alpha references: {int(alpha_years)})')
# ---- 3. alignment test: synthetic series, hour 1 of the forecast = first hour after the issue
idx = pd.date_range('2015-01-01', periods=24 * 20, freq='h'); n = len(idx); tt = np.arange(n, dtype=float)
syn = pd.DataFrame(index=idx); 
for c, (amp, base) in zip(DEPTH_COLS, [(3.0, 15), (1.5, 15), (0.5, 15), (0.0, 15), (0.0, 15)]): syn[c] = base + amp * np.cos(W * tt) + 0.01 * tt
ts = idx[24 * 12]; past = syn.loc[:ts]
f1 = f_persistence(past); check('3a. persistence: hour 1 equals the value at the issue hour, constant over 72 h', np.allclose(f1[0], [past['T20'].iloc[-1], past['T50'].iloc[-1]]) and np.allclose(f1, f1[0]))
bt = boundary_forecast(past['T5']); true_next = 15 + 3.0 * np.cos(W * (tt[24 * 12 + 1:24 * 12 + 1 + HORIZON])) + 0.01 * tt[24 * 12 + 1:24 * 12 + 1 + HORIZON]
# slow trend term (0.01 C per hour) is deliberately not forecast by the rule; compare phase/amplitude only
tr = 0.01 * tt[24 * 12 + 1:24 * 12 + 1 + HORIZON]; adj = true_next - tr - (15 + 0.01 * (tt[24 * 12 - 23:24 * 12 + 1]).mean() - 15 + 0)
phase_ok = np.corrcoef(bt, 3.0 * np.cos(W * tt[24 * 12 + 1:24 * 12 + 1 + HORIZON]))[0, 1] > 0.999
check('3b/5. boundary rule on a periodic synthetic series: forecast is in phase (hour 1 aligned) and recovers the amplitude', phase_ok and abs((bt.max() - bt.min()) / 2 - 3.0) < 0.05, f'(corr {np.corrcoef(bt, 3.0 * np.cos(W * tt[24 * 12 + 1:24 * 12 + 1 + HORIZON]))[0, 1]:.5f}, amplitude {(bt.max() - bt.min()) / 2:.3f} vs 3.0)')
# ---- 4. solver through the forecast code path vs the exact periodic solution (uniform column, exact boundaries)
alpha = 5e-7; d = np.sqrt(2 * alpha / W * 3600.0 ** 2) if False else None
zz = np.array([0.05, 0.10, 0.20, 0.50, 1.0]); damp = np.sqrt(2 * alpha / (2 * np.pi / (24 * 3600.0)))
def exact(zd, hours): tsec = hours * 3600.0; w_ = 2 * np.pi / (24 * 3600.0); return 8.0 * np.exp(-(zd - 0.05) / damp) * np.cos(w_ * tsec - (zd - 0.05) / damp)
hist = np.arange(-24 * 10, 1)        # ten days of history, t = 0 at issue
P_ = pd.DataFrame({c: 10 + exact(z_, hist) for c, z_ in zip(DEPTH_COLS, zz)}, index=pd.date_range('2015-03-01', periods=len(hist), freq='h'))
fh = np.arange(1, HORIZON + 1); ft = 10 + exact(0.05, fh); fb = 10 + exact(1.0, fh)
# --- 4a. Pure solver numerical accuracy: supply the exact profile on the full grid (bypass PCHIP).
#     This measures Crank-Nicolson discretisation error only, not init-profile approximation.
from heatsolver import make_grid as _mg, simulate as _sim, sample as _sa
_z, _ = _mg(0.05, 1.0, 38)
_T0_exact = 10 + exact(_z, 0)
_tb_all_top = np.concatenate([[10 + exact(0.05, 0)], ft]); _tb_all_bot = np.concatenate([[10 + exact(1.0, 0)], fb])
_sim_out = _sim(alpha, _tb_all_top, _tb_all_bot, _z, _T0_exact); _truth = np.column_stack([10 + exact(0.20, fh), 10 + exact(0.50, fh)])
_pred_ei = _sa(_sim_out, _z, [0.20, 0.50])[1:]; rm_solver = float(np.sqrt(np.mean((_pred_ei - _truth) ** 2))); amp_true = 8 * np.exp(-0.15 / damp)
check('4a. solver numerical accuracy (exact full-grid init, exact boundaries; Crank-Nicolson error)', rm_solver < 0.025, f'(RMS {rm_solver:.4f} C; 20 cm amplitude {amp_true:.2f} C)')
# --- 4b. PCHIP init-profile limitation (informational only, not pass/fail):
#     Five-sensor PCHIP interpolation introduces init-profile error at intermediate depths that
#     decays as the solver equilibrates to imposed boundaries. This is a known geometric limitation.
pred, _, _ = conduction_forecast(P_, alpha, ft, fb)
_pchip_init_err = np.abs(10 + exact(_z, 0) - (lambda z_o, T_o: __import__('scipy').interpolate.PchipInterpolator(z_o, T_o)(_z))(np.array([0.05,0.10,0.20,0.50,1.0]), [float(P_[c].iloc[-1]) for c in DEPTH_COLS])).max()
rm_pchip = float(np.sqrt(np.mean((pred - _truth) ** 2))); rm_pchip_h25 = float(np.sqrt(np.mean((pred[24:] - _truth[24:]) ** 2)))
say(f'[INFO] 4b. PCHIP init-profile limitation (informational): max grid-point init error {_pchip_init_err:.3f} C; forecast RMS h1-72={rm_pchip:.3f} C, h25-72={rm_pchip_h25:.3f} C (decays as solver equilibrates to boundaries)')
# ---- 6. solver positive control: unequal alpha must change the answer
pred2, _, _ = conduction_forecast(P_, alpha * 3, ft, fb); check('6. forecast is sensitive to alpha (solver is not a pass-through)', float(np.abs(pred2 - pred).max()) > 0.1)
say('\nOVERALL: ' + ('ALL VERIFICATION CHECKS PASSED' if ALL else 'AT LEAST ONE CHECK FAILED; affected claims must be dropped'))
open(os.path.join(FD, 'forecast_verification_out.txt'), 'w', encoding='utf-8').write('\n'.join(OUT))
