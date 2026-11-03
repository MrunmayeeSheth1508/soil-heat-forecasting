import os as _o, sys as _s
_p = _o.path.dirname(_o.path.abspath(__file__))
while not _o.path.exists(_o.path.join(_p, 'src', 'config.py')): _p = _o.path.dirname(_p)
_s.path.insert(0, _o.path.join(_p, 'src'))
from config import WS_ROOT  # PATH-PATCH: was an absolute path to the original working directory
"""
Selma 5-20 cm shallow pilot — exploratory conditional reconstruction test.

Design:
  Boundaries : measured T at 5 cm and 20 cm
  Interior   : measured T at 10 cm (single observation depth)
  Moisture   : measured SM at 10 cm (labelled as representative layer measurement — assumption)

Models:
  M0 : constant effective diffusivity alpha (1 parameter)
  M1 : alpha(t) = max(alpha0 + beta * SM_10cm(t), 1e-9)  (2 parameters, positive)

Split: chronological, fixed before any model fitting.
  Calibration : hours 0-377  (first 2/3 of episode, ~15.7 days)
  Validation  : hours 378-566 (final 1/3, ~7.9 days)
  Warm-up     : first 48 hrs of calibration excluded from cost (spin-up)

Comparators:
  M0_ep : M0 fitted separately per episode (same as M0 here — single episode)
  M_wd  : separate constant alpha fitted on wet vs dry hours of VALIDATION block
           — labelled RETROSPECTIVE, not held-out predictions

Forward model: 1D heat equation on 5-20 cm, Crank-Nicolson scheme.
  Grid: z = 5, 7.5, 10, 12.5, 15, 17.5, 20 cm  (dz = 2.5 cm)
  dt   = 3600 s (hourly)

Corrections applied per mentor:
  - Gradient threshold not used to exclude hours from model
  - SM at 10 cm used directly, not proxied from 5 cm
  - No hard 0.1 C threshold for detectability
  - Wet/dry comparator labelled retrospective
  - Rounding sensitivity reported separately
  - Temporal dependence of residuals assessed via autocorrelation
"""
import sys, io, os, warnings
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
warnings.filterwarnings('ignore')

import numpy as np
from scipy.optimize import minimize
from scipy.linalg import solve_banded

# ------------------------------------------------------------------ #
# 1. Load Episode 4
# ------------------------------------------------------------------ #
MISS_T = -9999.0; MISS_SM = -99.0
raw_dir = (WS_ROOT + r'\raw')

def load_station(stn, years):
    rows = []
    for yr in years:
        path = os.path.join(raw_dir, f'CRNH0203-{yr}-{stn}.txt')
        if not os.path.exists(path): continue
        with open(path) as f:
            for line in f:
                p = line.split()
                if len(p) >= 38: rows.append(p)
    n = len(rows)
    st = np.full((n,5), np.nan); sm = np.full((n,5), np.nan)
    for j, p in enumerate(rows):
        for k, col in enumerate([33,34,35,36,37]):
            try:
                v = float(p[col])
                if v > MISS_T+1: st[j,k] = v
            except: pass
        for k, col in enumerate([28,29,30,31,32]):
            try:
                v = float(p[col])
                if v > MISS_SM+1: sm[j,k] = v
            except: pass
    return st, sm

st, sm = load_station('AL_Selma_13_WNW', [2019,2020])

# Reconstruct episodes (same logic as before)
valid = (np.all(~np.isnan(st), axis=1) & np.all(~np.isnan(sm), axis=1) &
         np.all(st > 1.0, axis=1))
episodes = []
in_ep = False; es = 0
for i in range(len(valid)):
    if valid[i] and not in_ep:   es = i; in_ep = True
    elif not valid[i] and in_ep:
        if i-es >= 96: episodes.append((es,i))
        in_ep = False
if in_ep and len(valid)-es >= 96: episodes.append((es, len(valid)))

ep4_start, ep4_end = episodes[3]
T5  = st[ep4_start:ep4_end, 0]   # boundary
T10 = st[ep4_start:ep4_end, 1]   # observation (withheld from fit in validation)
T20 = st[ep4_start:ep4_end, 3]   # boundary (index 3 = 50cm... wait)

# Column mapping: ST_COLS = [33,34,35,36,37] -> depths [5,10,20,50,100]
# Index 0=5cm, 1=10cm, 2=20cm, 3=50cm, 4=100cm
T5  = st[ep4_start:ep4_end, 0]   # 5 cm  boundary
T10 = st[ep4_start:ep4_end, 1]   # 10 cm observation
T20 = st[ep4_start:ep4_end, 2]   # 20 cm boundary
SM10= sm[ep4_start:ep4_end, 1]   # 10 cm moisture (representative layer measurement)

N = len(T5)
print(f"Episode 4: {N} hours  ({N/24:.1f} days)")
print(f"T5  range: {T5.min():.1f} to {T5.max():.1f} C")
print(f"T10 range: {T10.min():.1f} to {T10.max():.1f} C")
print(f"T20 range: {T20.min():.1f} to {T20.max():.1f} C")
print(f"SM10 range: {SM10.min():.3f} to {SM10.max():.3f} m3/m3")

# ------------------------------------------------------------------ #
# 2. Chronological split — FIXED before fitting
# ------------------------------------------------------------------ #
CALIB_END  = 378   # hours 0..377 = calibration
WARMUP     = 48    # first 48 h excluded from cost
VAL_START  = 378   # hours 378..566 = validation

print(f"\nCalibration : hours 0-{CALIB_END-1}  ({CALIB_END/24:.1f} days)")
print(f"  Warm-up   : first {WARMUP} hours excluded from cost function")
print(f"Validation  : hours {VAL_START}-{N-1}  ({(N-VAL_START)/24:.1f} days)")

# Moisture variation check
print(f"\nMoisture at 10 cm:")
print(f"  Calibration block: min={SM10[:CALIB_END].min():.3f}  "
      f"max={SM10[:CALIB_END].max():.3f}  "
      f"range={SM10[:CALIB_END].max()-SM10[:CALIB_END].min():.3f}")
print(f"  Validation block:  min={SM10[VAL_START:].min():.3f}  "
      f"max={SM10[VAL_START:].max():.3f}  "
      f"range={SM10[VAL_START:].max()-SM10[VAL_START:].min():.3f}")
sm_calib_range = SM10[:CALIB_END].max() - SM10[:CALIB_END].min()
print(f"  Moisture range in calibration: {sm_calib_range:.3f} m3/m3")
if sm_calib_range < 0.05:
    print("  WARNING: moisture range in calibration < 0.05 — beta is weakly constrained.")
    print("  M1 fit may mainly extrapolate moisture relationship to validation block.")

# ------------------------------------------------------------------ #
# 3. Forward model: Crank-Nicolson on 5-20 cm grid
# ------------------------------------------------------------------ #
# Grid: z = 0.05, 0.075, 0.10, 0.125, 0.15, 0.175, 0.20 m
# Nodes: 0=5cm(BC), 1=7.5cm, 2=10cm(obs), 3=12.5cm, 4=15cm, 5=17.5cm, 6=20cm(BC)
dz  = 0.025   # m
dt  = 3600.0  # s
NZ  = 7       # nodes including boundaries
OBS_NODE = 2  # index of 10 cm in grid

def run_crank_nicolson(alpha_vec, T_top, T_bot, T_init):
    """
    alpha_vec: array of length N, effective diffusivity at each time step (m2/s)
    T_top, T_bot: boundary temperatures (length N)
    T_init: initial temperature profile at all NZ nodes (length 7)
    Returns T_interior: (N, NZ-2) array of interior node temperatures
    """
    r_vec = alpha_vec * dt / dz**2   # Fourier number, varies with alpha
    T = T_init.copy()
    out = np.zeros((len(T_top), NZ))
    out[0] = T.copy()

    for n in range(1, len(T_top)):
        r = r_vec[n]
        # Interior nodes 1..5 (indices in full array)
        # Crank-Nicolson: A * T_new = b
        # Size of interior system: NZ-2 = 5
        ni = NZ - 2  # 5 interior nodes
        # Tridiagonal: lower=-r/2, diag=1+r, upper=-r/2
        diag  = np.full(ni, 1.0 + r)
        off   = np.full(ni-1, -r/2.0)
        # Right-hand side from explicit part
        rhs   = np.zeros(ni)
        T_int = T[1:-1]  # interior values
        rhs   = (r/2)*T[:-2][:-1] + (1-r)*T_int + (r/2)*T[2:][1:]
        # Wait - let me redo this properly
        # T_int = T[1], T[2], T[3], T[4], T[5]
        # For node i (1..5 in full array, 0..4 in interior):
        # explicit: (r/2)*T[i-1] + (1-r)*T[i] + (r/2)*T[i+1]
        rhs = np.zeros(ni)
        for i in range(ni):
            ig = i + 1  # global index
            rhs[i] = (r/2)*T[ig-1] + (1-r)*T[ig] + (r/2)*T[ig+1]
        # Add boundary contributions to rhs
        rhs[0]    += (r/2) * T_top[n]
        rhs[-1]   += (r/2) * T_bot[n]
        # Add explicit boundary contributions
        rhs[0]    += (r/2) * T_top[n-1]  # already included above? No.
        # Correct form:
        # rhs[0] from explicit: (r/2)*T_top[n-1] + (1-r)*T[1] + (r/2)*T[2]
        # implicit adds: -(r/2)*T_int_new[0] ... + (r/2)*T_top[n] on lhs? 
        # Let me use standard CN properly:
        # (1+r)*T_new[i] - (r/2)*T_new[i-1] - (r/2)*T_new[i+1] = 
        # (1-r)*T[i] + (r/2)*T[i-1] + (r/2)*T[i+1]
        rhs = np.zeros(ni)
        for i in range(ni):
            ig = i + 1
            lbc = T_top[n-1] if ig == 1   else T[ig-1]
            rbc = T_bot[n-1] if ig == NZ-2 else T[ig+1]
            rhs[i] = (r/2)*lbc + (1-r)*T[ig] + (r/2)*rbc
        # Boundary adjustments on rhs
        rhs[0]  += (r/2)*T_top[n]
        rhs[-1] += (r/2)*T_bot[n]

        # Solve tridiagonal
        ab = np.zeros((3, ni))
        ab[0, 1:]  = -r/2    # upper
        ab[1, :]   = 1 + r   # diagonal
        ab[2, :-1] = -r/2    # lower
        T_new_int  = solve_banded((1,1), ab, rhs)
        T[0]   = T_top[n]
        T[1:-1]= T_new_int
        T[-1]  = T_bot[n]
        out[n] = T.copy()

    return out  # (N, 7)

def cost_function(params, model_type, t_slice, sm_slice):
    """params: [log_alpha] for M0, [log_alpha0, log_beta] for M1"""
    n_t = len(t_slice[0])
    if model_type == 'M0':
        alpha = np.exp(params[0])
        alpha_vec = np.full(n_t, alpha)
    else:  # M1
        alpha0 = np.exp(params[0])
        beta   = np.exp(params[1])
        alpha_vec = np.maximum(alpha0 + beta * sm_slice, 1e-9)

    # Initial profile: linear interpolation between T5[0] and T20[0]
    T_init = np.linspace(T5[t_slice[0][0]] if hasattr(t_slice[0],'__len__') else T5[0],
                         T20[t_slice[0][0]] if hasattr(t_slice[0],'__len__') else T20[0], NZ)
    # Simpler: use the time indices directly
    idx = t_slice
    T_init = np.linspace(T5[idx[0]], T20[idx[0]], NZ)
    out = run_crank_nicolson(alpha_vec, T5[idx], T20[idx], T_init)
    pred_10cm = out[:, OBS_NODE]
    resid     = pred_10cm[WARMUP:] - T10[idx[WARMUP:]]
    return np.sum(resid**2)

# ------------------------------------------------------------------ #
# 4. Fit on calibration block
# ------------------------------------------------------------------ #
calib_idx = np.arange(0, CALIB_END)
val_idx   = np.arange(VAL_START, N)

print("\n=== FITTING ON CALIBRATION BLOCK (hours 0-377) ===")

def fit_model(model_type, idx, sm_arr, x0, bounds_log):
    def cost(params):
        n_t = len(idx)
        if model_type == 'M0':
            a = np.exp(params[0])
            alpha_vec = np.full(n_t, a)
        else:
            a0 = np.exp(params[0]); b = np.exp(params[1])
            alpha_vec = np.maximum(a0 + b * sm_arr, 1e-9)
        T_init = np.linspace(T5[idx[0]], T20[idx[0]], NZ)
        out    = run_crank_nicolson(alpha_vec, T5[idx], T20[idx], T_init)
        pred   = out[:, OBS_NODE]
        resid  = pred[WARMUP:] - T10[idx[WARMUP:]]
        return np.sum(resid**2)
    res = minimize(cost, x0, method='Nelder-Mead',
                   options={'maxiter':2000, 'xatol':1e-6, 'fatol':1e-8})
    return res

# M0 calibration
res_M0 = fit_model('M0', calib_idx, None, x0=[-13.0], bounds_log=None)
alpha_M0 = np.exp(res_M0.x[0])
print(f"\nM0 (constant alpha): alpha = {alpha_M0:.3e} m2/s  "
      f"(convergence: {res_M0.success}, nfev={res_M0.nfev})")

# M1 calibration
res_M1 = fit_model('M1', calib_idx, SM10[calib_idx], x0=[-13.0, -15.0], bounds_log=None)
alpha0_M1 = np.exp(res_M1.x[0]); beta_M1 = np.exp(res_M1.x[1])
print(f"M1 (alpha0 + beta*SM): alpha0={alpha0_M1:.3e}  beta={beta_M1:.3e}  "
      f"(alpha at mean SM={alpha0_M1+beta_M1*SM10[calib_idx].mean():.3e})")
print(f"  (convergence: {res_M1.success}, nfev={res_M1.nfev})")

# ------------------------------------------------------------------ #
# 5. Evaluate on VALIDATION block (held out)
# ------------------------------------------------------------------ #
print("\n=== VALIDATION (hours 378-566, held out from fitting) ===")

def predict(model_type, idx, sm_arr, params):
    n_t = len(idx)
    if model_type == 'M0':
        alpha_vec = np.full(n_t, np.exp(params[0]))
    else:
        a0 = np.exp(params[0]); b = np.exp(params[1])
        alpha_vec = np.maximum(a0 + b*sm_arr, 1e-9)
    T_init = np.linspace(T5[idx[0]], T20[idx[0]], NZ)
    out    = run_crank_nicolson(alpha_vec, T5[idx], T20[idx], T_init)
    return out[:, OBS_NODE]

pred_M0_val = predict('M0', val_idx, None,         res_M0.x)
pred_M1_val = predict('M1', val_idx, SM10[val_idx], res_M1.x)
obs_val     = T10[val_idx]

err_M0 = pred_M0_val - obs_val
err_M1 = pred_M1_val - obs_val

print(f"\nM0 validation errors: mean={err_M0.mean():.4f}  std={err_M0.std():.4f}  "
      f"RMSE={np.sqrt((err_M0**2).mean()):.4f} C")
print(f"M1 validation errors: mean={err_M1.mean():.4f}  std={err_M1.std():.4f}  "
      f"RMSE={np.sqrt((err_M1**2).mean()):.4f} C")
print(f"RMSE improvement (M1 vs M0): {np.sqrt((err_M0**2).mean()) - np.sqrt((err_M1**2).mean()):.4f} C")

# Residual autocorrelation
def acf1(x):
    xc = x - x.mean()
    if xc.std() < 1e-10: return 0.0
    return np.correlate(xc, xc, 'full')[len(x)-1+1] / np.correlate(xc, xc, 'full')[len(x)-1]
print(f"\nResidual lag-1 autocorrelation:")
print(f"  M0: {acf1(err_M0):.3f}  (high = correlated errors, effective N < {len(err_M0)})")
print(f"  M1: {acf1(err_M1):.3f}")

# Amplitude and phase at 10 cm (informative beyond RMSE)
# Compare amplitude of oscillation in predicted vs observed
from numpy.fft import fft, fftfreq
freqs = fftfreq(len(obs_val), d=1)  # cycles per hour
f_day = 1/24.0
idx_day = np.argmin(np.abs(freqs - f_day))
amp_obs  = 2*abs(fft(obs_val)[idx_day])  / len(obs_val)
amp_M0   = 2*abs(fft(pred_M0_val)[idx_day]) / len(obs_val)
amp_M1   = 2*abs(fft(pred_M1_val)[idx_day]) / len(obs_val)
print(f"\nDiurnal amplitude at 10 cm (validation block):")
print(f"  Observed: {amp_obs:.3f} C")
print(f"  M0 pred:  {amp_M0:.3f} C")
print(f"  M1 pred:  {amp_M1:.3f} C")

# ------------------------------------------------------------------ #
# 6. Retrospective wet/dry constants on VALIDATION (labelled clearly)
# ------------------------------------------------------------------ #
print("\n=== RETROSPECTIVE WET/DRY FIT ON VALIDATION (not held out) ===")
print("  These are fitted using validation observations — not predictions. Label accordingly.")
sm_val = SM10[val_idx]
wet_thresh = np.percentile(sm_val, 50)
wet_mask_v = sm_val >= wet_thresh
dry_mask_v = ~wet_mask_v
print(f"  SM threshold (median): {wet_thresh:.3f}")
print(f"  Wet hours: {wet_mask_v.sum()}  Dry hours: {dry_mask_v.sum()}")
if wet_mask_v.sum() >= 48 and dry_mask_v.sum() >= 48:
    print(f"  Dry-period mean T10 obs: {obs_val[dry_mask_v].mean():.3f} C  "
          f"wet: {obs_val[wet_mask_v].mean():.3f} C")
    print(f"  Dry-period mean SM10:    {sm_val[dry_mask_v].mean():.3f}  "
          f"wet: {sm_val[wet_mask_v].mean():.3f}")
    print(f"  (A forward model conditioned on this split would need separate fitting)")

# ------------------------------------------------------------------ #
# 7. Rounding sensitivity
# ------------------------------------------------------------------ #
print("\n=== ROUNDING SENSITIVITY ===")
print("  Perturbing boundaries by +/-0.1 C to assess sensitivity of fitted alpha:")
perturb_results = []
for delta_top, delta_bot in [(0,0), (+0.1,0), (-0.1,0), (0,+0.1), (0,-0.1)]:
    T5_p  = T5  + delta_top
    T20_p = T20 + delta_bot
    # Refit M0 with perturbed boundaries
    def cost_p(params):
        a = np.exp(params[0])
        T_init = np.linspace(T5_p[calib_idx[0]], T20_p[calib_idx[0]], NZ)
        out = run_crank_nicolson(np.full(len(calib_idx), a),
                                  T5_p[calib_idx], T20_p[calib_idx], T_init)
        return np.sum((out[WARMUP:, OBS_NODE] - T10[calib_idx[WARMUP:]])**2)
    res_p = minimize(cost_p, [-13.0], method='Nelder-Mead',
                     options={'maxiter':1000,'xatol':1e-5,'fatol':1e-7})
    alpha_p = np.exp(res_p.x[0])
    perturb_results.append((delta_top, delta_bot, alpha_p))
    print(f"  delta_top={delta_top:+.1f} delta_bot={delta_bot:+.1f}: "
          f"alpha={alpha_p:.3e}  change={100*(alpha_p/alpha_M0-1):.1f}%")

# ------------------------------------------------------------------ #
# 8. Screen other episodes — does M1 beat M0?
# ------------------------------------------------------------------ #
print("\n=== SCREEN OTHER EPISODES (calibration/validation within each) ===")
print("  Using same 2/3 calib / 1/3 val split per episode.")
print("  Episodes with < 144 hours (6 days) skipped.")

ep_results = []
for ep_i, (es, ee) in enumerate(episodes):
    ep_len = ee - es
    if ep_len < 144: continue
    T5_e  = st[es:ee, 0]; T10_e = st[es:ee, 1]; T20_e = st[es:ee, 2]
    SM10_e= sm[es:ee, 1]
    N_e   = ep_len
    c_end = int(N_e * 2 / 3)
    v_start = c_end
    wu = min(48, c_end // 4)
    c_idx = np.arange(0, c_end)
    v_idx = np.arange(v_start, N_e)

    # Check SM range in calibration
    sm_rng_c = SM10_e[c_idx].max() - SM10_e[c_idx].min()

    # Quick M0 fit
    def cost_ep(params, T5_loc, T20_loc, T10_loc, SM_loc, idx, wu_loc):
        a = np.exp(params[0])
        T_init = np.linspace(T5_loc[idx[0]], T20_loc[idx[0]], NZ)
        out = run_crank_nicolson(np.full(len(idx),a),
                                  T5_loc[idx], T20_loc[idx], T_init)
        return np.sum((out[wu_loc:, OBS_NODE] - T10_loc[idx[wu_loc:]])**2)

    try:
        r0 = minimize(lambda p: cost_ep(p,T5_e,T20_e,T10_e,SM10_e,c_idx,wu),
                      [-13.0], method='Nelder-Mead',
                      options={'maxiter':1500,'xatol':1e-5,'fatol':1e-7})
        a0 = np.exp(r0.x[0])
        T_init_v = np.linspace(T5_e[v_idx[0]], T20_e[v_idx[0]], NZ)
        out_v = run_crank_nicolson(np.full(len(v_idx),a0),
                                    T5_e[v_idx], T20_e[v_idx], T_init_v)
        rmse_M0 = np.sqrt(np.mean((out_v[:,OBS_NODE] - T10_e[v_idx])**2))

        def cost_ep1(params):
            a00 = np.exp(params[0]); b = np.exp(params[1])
            av = np.maximum(a00 + b*SM10_e[c_idx], 1e-9)
            T_init = np.linspace(T5_e[c_idx[0]], T20_e[c_idx[0]], NZ)
            out = run_crank_nicolson(av, T5_e[c_idx], T20_e[c_idx], T_init)
            return np.sum((out[wu:,OBS_NODE] - T10_e[c_idx[wu:]])**2)
        r1 = minimize(cost_ep1, [-13.0,-15.0], method='Nelder-Mead',
                      options={'maxiter':2000,'xatol':1e-5,'fatol':1e-7})
        a00=np.exp(r1.x[0]); b=np.exp(r1.x[1])
        av_v = np.maximum(a00 + b*SM10_e[v_idx], 1e-9)
        T_init_v = np.linspace(T5_e[v_idx[0]], T20_e[v_idx[0]], NZ)
        out_v1 = run_crank_nicolson(av_v, T5_e[v_idx], T20_e[v_idx], T_init_v)
        rmse_M1 = np.sqrt(np.mean((out_v1[:,OBS_NODE] - T10_e[v_idx])**2))

        ep_results.append(dict(ep=ep_i+1, dur=ep_len, sm_rng_c=sm_rng_c,
                               alpha_M0=a0, rmse_M0=rmse_M0, rmse_M1=rmse_M1,
                               diff=rmse_M0-rmse_M1))
    except Exception as ex:
        pass

print(f"\n{'Ep':>3}  {'dur(h)':>7}  {'SM_rng_calib':>13}  {'alpha_M0':>10}  "
      f"{'RMSE_M0':>8}  {'RMSE_M1':>8}  {'M0-M1':>8}")
for r in ep_results:
    flag = ' *' if r['sm_rng_c'] < 0.05 else ''
    print(f"{r['ep']:>3}  {r['dur']:>7}  {r['sm_rng_c']:>13.3f}  "
          f"{r['alpha_M0']:>10.3e}  {r['rmse_M0']:>8.4f}  {r['rmse_M1']:>8.4f}  "
          f"{r['diff']:>8.4f}{flag}")
print("  * SM range in calibration < 0.05 — moisture coefficient weakly constrained")

print("\n=== SUMMARY ===")
print("""
This pilot tests whether alpha(theta) transfers across time within a single station.
It does NOT identify conductivity, heat capacity or advection separately.
It does NOT establish a literature contribution or justify building PINO.
Results are exploratory; physical interpretation requires surviving:
  - Multiple independent episodes at this station
  - At least one independent station
  - Literature gap confirmation
""")
