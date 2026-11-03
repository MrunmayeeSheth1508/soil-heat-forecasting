import os as _o, sys as _s
_p = _o.path.dirname(_o.path.abspath(__file__))
while not _o.path.exists(_o.path.join(_p, 'src', 'config.py')): _p = _o.path.dirname(_p)
_s.path.insert(0, _o.path.join(_p, 'src'))
from config import WS_ROOT  # PATH-PATCH: was an absolute path to the original working directory
"""
Corrected shallow pilot.

Changes from v1:
- Fixed Crank-Nicolson shape error (rhs construction was mixed up)
- SM at 10cm only ranges 0.027 in calibration (CRITICAL: nearly constant).
  This makes beta essentially unidentifiable from SM_10cm alone.
  Run two versions:
    (a) M1 using SM_5cm (larger range 0.156 within episode) as proxy — label as assumption
    (b) M1 using SM_10cm (measured at depth) — label as the direct measurement
  Report which moisture input constrains beta and which does not.
- Episode 4 moisture ranges:
    5cm:  0.147-0.303 = 0.156 (usable range)
    10cm: 0.247-0.279 = 0.032 (too narrow to constrain beta)
  Both are reported explicitly.
"""
import sys, io, os, warnings
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
warnings.filterwarnings('ignore')
import numpy as np
from scipy.optimize import minimize
from scipy.linalg import solve_banded

MISS_T = -9999.0; MISS_SM = -99.0
raw_dir = (WS_ROOT + r'\raw')
NZ = 7; OBS_NODE = 2; dz = 0.025; dt = 3600.0
WARMUP = 48

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
        for k,col in enumerate([33,34,35,36,37]):
            try:
                v = float(p[col])
                if v > MISS_T+1: st[j,k] = v
            except: pass
        for k,col in enumerate([28,29,30,31,32]):
            try:
                v = float(p[col])
                if v > MISS_SM+1: sm[j,k] = v
            except: pass
    return st, sm

def crank_nicolson(alpha_vec, T_top, T_bot, T_init):
    """
    Stable Crank-Nicolson on NZ-node grid.
    Interior nodes: indices 1..NZ-2  (NZ-2 = 5 nodes)
    """
    ni = NZ - 2   # 5 interior nodes
    T  = T_init.copy().astype(float)
    out = np.zeros((len(T_top), NZ))
    out[0] = T.copy()

    for n in range(1, len(T_top)):
        r = alpha_vec[n] * dt / dz**2

        # Build RHS from explicit step
        rhs = np.zeros(ni)
        for i in range(ni):
            ig = i + 1
            T_left  = T_top[n-1] if ig == 1      else T[ig-1]
            T_right = T_bot[n-1] if ig == NZ-2   else T[ig+1]
            rhs[i]  = (r/2)*T_left + (1-r)*T[ig] + (r/2)*T_right

        # Add implicit boundary contributions
        rhs[0]  += (r/2) * T_top[n]
        rhs[-1] += (r/2) * T_bot[n]

        # Solve banded system: lower=-r/2, diag=1+r, upper=-r/2
        ab = np.zeros((3, ni))
        ab[0, 1:]  = -r/2
        ab[1, :]   =  1 + r
        ab[2, :-1] = -r/2
        T_int_new = solve_banded((1,1), ab, rhs)

        T[0]    = T_top[n]
        T[1:-1] = T_int_new
        T[-1]   = T_bot[n]
        out[n]  = T.copy()
    return out   # shape (N, NZ)

def run_and_cost(params, model, T5, T20, T10, SM, calib_idx, wu):
    n  = len(calib_idx)
    if model == 'M0':
        av = np.full(n, np.exp(params[0]))
    else:
        a0 = np.exp(params[0]); b = np.exp(params[1])
        av = np.maximum(a0 + b * SM[calib_idx], 1e-9)
    T_init = np.linspace(T5[calib_idx[0]], T20[calib_idx[0]], NZ)
    out    = crank_nicolson(av, T5[calib_idx], T20[calib_idx], T_init)
    resid  = out[wu:, OBS_NODE] - T10[calib_idx[wu:]]
    return np.sum(resid**2)

def predict_val(params, model, T5, T20, SM, val_idx):
    n  = len(val_idx)
    if model == 'M0':
        av = np.full(n, np.exp(params[0]))
    else:
        a0 = np.exp(params[0]); b = np.exp(params[1])
        av = np.maximum(a0 + b * SM[val_idx], 1e-9)
    T_init = np.linspace(T5[val_idx[0]], T20[val_idx[0]], NZ)
    out    = crank_nicolson(av, T5[val_idx], T20[val_idx], T_init)
    return out[:, OBS_NODE]

def acf1(x):
    xc = x - x.mean()
    n  = len(xc)
    if xc.std() < 1e-12 or n < 4: return np.nan
    return float(np.dot(xc[:-1], xc[1:]) / np.dot(xc, xc))

# ------------------------------------------------------------------ #
# Load data and identify episodes
# ------------------------------------------------------------------ #
st, sm = load_station('AL_Selma_13_WNW', [2019, 2020])
valid = (np.all(~np.isnan(st), axis=1) & np.all(~np.isnan(sm), axis=1)
         & np.all(st > 1.0, axis=1))
episodes = []
in_ep = False; es = 0
for i in range(len(valid)):
    if valid[i] and not in_ep:   es = i; in_ep = True
    elif not valid[i] and in_ep:
        if i-es >= 96: episodes.append((es,i))
        in_ep = False
if in_ep and len(valid)-es >= 96: episodes.append((es, len(valid)))

# ------------------------------------------------------------------ #
# Report SM ranges for Episode 4 before fitting anything
# ------------------------------------------------------------------ #
ep4s, ep4e = episodes[3]
T5_4  = st[ep4s:ep4e, 0]; T10_4 = st[ep4s:ep4e, 1]; T20_4 = st[ep4s:ep4e, 2]
SM5_4 = sm[ep4s:ep4e, 0]; SM10_4= sm[ep4s:ep4e, 1]

print("=== Episode 4 moisture — before any fitting ===")
print(f"SM at  5cm: min={SM5_4.min():.3f}  max={SM5_4.max():.3f}  range={SM5_4.max()-SM5_4.min():.3f}")
print(f"SM at 10cm: min={SM10_4.min():.3f}  max={SM10_4.max():.3f}  range={SM10_4.max()-SM10_4.min():.3f}")
print(f"\n10cm moisture range is {SM10_4.max()-SM10_4.min():.3f} m3/m3.")
print("This is very narrow. Beta fitted using SM_10cm is weakly constrained.")
print("Running M1 with SM_5cm (range 0.156) as proxy — labelled as assumption.")
print("Running M1 with SM_10cm (direct measurement) — labelled as direct but narrow.")

# Chronological split
N4 = ep4e - ep4s
CALIB_END = int(N4 * 2/3)
VAL_START  = CALIB_END
print(f"\nEpisode 4: {N4} hours. Calib=0..{CALIB_END-1} ({CALIB_END/24:.1f}d)  "
      f"Val={VAL_START}..{N4-1} ({(N4-VAL_START)/24:.1f}d)")
c_idx = np.arange(0, CALIB_END)
v_idx = np.arange(VAL_START, N4)

for sm_label, SM_ep in [('SM_5cm (proxy, 5cm range=0.156)', SM5_4),
                         ('SM_10cm (direct, 10cm range=0.032)', SM10_4)]:
    print(f"\n--- Using {sm_label} ---")
    sm_c_range = SM_ep[c_idx].max() - SM_ep[c_idx].min()
    sm_v_range = SM_ep[v_idx].max() - SM_ep[v_idx].min()
    print(f"  SM range in calibration: {sm_c_range:.3f}   validation: {sm_v_range:.3f}")
    if sm_c_range < 0.03:
        print("  WEAK CONSTRAINT: SM range in calibration < 0.03. Beta unreliable.")

    # Fit M0
    res0 = minimize(lambda p: run_and_cost(p,'M0',T5_4,T20_4,T10_4,SM_ep,c_idx,WARMUP),
                    [-13.0], method='Nelder-Mead',
                    options={'maxiter':2000,'xatol':1e-7,'fatol':1e-9})
    alpha_M0 = np.exp(res0.x[0])
    pred_M0_v = predict_val(res0.x,'M0',T5_4,T20_4,SM_ep,v_idx)
    err_M0    = pred_M0_v - T10_4[v_idx]
    rmse_M0   = np.sqrt(np.mean(err_M0**2))

    # Fit M1
    res1 = minimize(lambda p: run_and_cost(p,'M1',T5_4,T20_4,T10_4,SM_ep,c_idx,WARMUP),
                    [-13.0,-15.0], method='Nelder-Mead',
                    options={'maxiter':3000,'xatol':1e-7,'fatol':1e-9})
    a0_M1 = np.exp(res1.x[0]); b_M1 = np.exp(res1.x[1])
    pred_M1_v = predict_val(res1.x,'M1',T5_4,T20_4,SM_ep,v_idx)
    err_M1    = pred_M1_v - T10_4[v_idx]
    rmse_M1   = np.sqrt(np.mean(err_M1**2))

    print(f"  M0: alpha={alpha_M0:.3e} m2/s  val-RMSE={rmse_M0:.4f} C  acf1={acf1(err_M0):.3f}")
    print(f"  M1: alpha0={a0_M1:.3e}  beta={b_M1:.3e}  val-RMSE={rmse_M1:.4f} C  acf1={acf1(err_M1):.3f}")
    print(f"  RMSE improvement (M0-M1): {rmse_M0-rmse_M1:.4f} C")
    print(f"  M1 alpha range in val: {(a0_M1+b_M1*SM_ep[v_idx]).min():.3e} to "
          f"{(a0_M1+b_M1*SM_ep[v_idx]).max():.3e}")

    # Diurnal amplitude comparison
    from numpy.fft import fft, fftfreq
    nv = len(v_idx)
    freqs = fftfreq(nv, d=1.0)
    idx_day = np.argmin(np.abs(freqs - 1/24.0))
    amp_obs = 2*abs(fft(T10_4[v_idx])[idx_day])/nv
    amp_M0  = 2*abs(fft(pred_M0_v)[idx_day])/nv
    amp_M1  = 2*abs(fft(pred_M1_v)[idx_day])/nv
    print(f"  Diurnal amplitude at 10cm (val): obs={amp_obs:.3f}  M0={amp_M0:.3f}  M1={amp_M1:.3f} C")

    # Rounding sensitivity for M0
    delta_pairs = [(+0.1,0.0),(-0.1,0.0),(0.0,+0.1),(0.0,-0.1)]
    alphas_perturbed = []
    for dt5, dt20 in delta_pairs:
        T5p = T5_4+dt5; T20p = T20_4+dt20
        def cost_p(p):
            a = np.exp(p[0])
            T_init = np.linspace(T5p[c_idx[0]], T20p[c_idx[0]], NZ)
            out = crank_nicolson(np.full(len(c_idx),a), T5p[c_idx], T20p[c_idx], T_init)
            return np.sum((out[WARMUP:,OBS_NODE]-T10_4[c_idx[WARMUP:]])**2)
        rp = minimize(cost_p,[-13.0],method='Nelder-Mead',
                      options={'maxiter':1000,'xatol':1e-5,'fatol':1e-7})
        alphas_perturbed.append(np.exp(rp.x[0]))
    pct_changes = [100*(a/alpha_M0-1) for a in alphas_perturbed]
    print(f"  Rounding sensitivity (M0 alpha % change per +/-0.1C on boundary):")
    labels = ['+0.1 T5','-0.1 T5','+0.1 T20','-0.1 T20']
    for lab, pct in zip(labels, pct_changes):
        print(f"    {lab}: {pct:+.1f}%")

# ------------------------------------------------------------------ #
# Screen all episodes using SM_5cm (larger range proxy)
# ------------------------------------------------------------------ #
print("\n=== EPISODE SCREEN (all episodes >=6 days, SM_5cm proxy) ===")
print(f"{'Ep':>3}  {'dur(h)':>7}  {'SM5_rng_c':>10}  {'alpha_M0':>10}  "
      f"{'RMSE_M0':>8}  {'RMSE_M1':>8}  {'M0-M1':>7}  {'note'}")
for ep_i, (es, ee) in enumerate(episodes):
    n_ep = ee-es
    if n_ep < 144: continue
    T5e=st[es:ee,0]; T10e=st[es:ee,1]; T20e=st[es:ee,2]
    SM5e=sm[es:ee,0]
    c_end = int(n_ep*2/3); wu=min(48,c_end//4)
    ci=np.arange(0,c_end); vi=np.arange(c_end,n_ep)
    sm_rc = SM5e[ci].max()-SM5e[ci].min()
    note = 'weak_SM' if sm_rc < 0.05 else ''
    try:
        r0=minimize(lambda p: run_and_cost(p,'M0',T5e,T20e,T10e,SM5e,ci,wu),
                    [-13.0],method='Nelder-Mead',
                    options={'maxiter':1500,'xatol':1e-5,'fatol':1e-7})
        a0=np.exp(r0.x[0])
        pv0=predict_val(r0.x,'M0',T5e,T20e,SM5e,vi)
        rm0=np.sqrt(np.mean((pv0-T10e[vi])**2))
        r1=minimize(lambda p: run_and_cost(p,'M1',T5e,T20e,T10e,SM5e,ci,wu),
                    [-13.0,-15.0],method='Nelder-Mead',
                    options={'maxiter':2000,'xatol':1e-5,'fatol':1e-7})
        pv1=predict_val(r1.x,'M1',T5e,T20e,SM5e,vi)
        rm1=np.sqrt(np.mean((pv1-T10e[vi])**2))
        print(f"{ep_i+1:>3}  {n_ep:>7}  {sm_rc:>10.3f}  {a0:>10.3e}  "
              f"{rm0:>8.4f}  {rm1:>8.4f}  {rm0-rm1:>7.4f}  {note}")
    except Exception as ex:
        print(f"{ep_i+1:>3}  {n_ep:>7}  {sm_rc:>10.3f}  {'ERROR':>10}  {str(ex)[:40]}")

print("\n=== PILOT SCOPE REMINDER ===")
print("This is an exploratory conditional reconstruction test, not a forecast.")
print("Boundaries (T5, T20) are measured contemporaneously.")
print("Results do not establish literature gap, physical mechanism, or PINO justification.")
