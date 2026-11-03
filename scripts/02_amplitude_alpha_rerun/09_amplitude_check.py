import os as _o, sys as _s
_p = _o.path.dirname(_o.path.abspath(__file__))
while not _o.path.exists(_o.path.join(_p, 'src', 'config.py')): _p = _o.path.dirname(_p)
_s.path.insert(0, _o.path.join(_p, 'src'))
from config import WS_ROOT  # PATH-PATCH: was an absolute path to the original working directory
"""
Test of the 33 percent amplitude overprediction in the soil pilot.
Questions:
  Q1. Was D fitted? (code review: yes, per episode on calibration third, single Nelder-Mead start from log alpha=-13)
  Q2. Is the solver numerically right?  -> compare to exact analytic periodic solution
  Q3. If alpha is scanned globally and fitted IN-SAMPLE over the whole episode, does the diurnal amplitude error vanish?
  Q4. Independent of any solver: do amplitude-decay and phase-lag between 5, 10, 20 cm give the SAME thermal diffusivity?
      (classic harmonic method; homogeneous 1D conduction requires alpha_amp == alpha_phase)
"""
import sys, io, os, warnings
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
warnings.filterwarnings('ignore')
import numpy as np
from scipy.linalg import solve_banded

raw_dir = (WS_ROOT + r'\raw')
MISS_T = -9999.0; MISS_SM = -99.0
NZ = 7; OBS = 2; dz = 0.025
W = 2 * np.pi / 86400.0

def load_station(stn, years):
    rows = []
    for yr in years:
        p = os.path.join(raw_dir, f'CRNH0203-{yr}-{stn}.txt')
        if not os.path.exists(p): continue
        for line in open(p):
            s = line.split()
            if len(s) >= 38: rows.append(s)
    st = np.full((len(rows), 5), np.nan)
    for j, s in enumerate(rows):
        for k, col in enumerate([33, 34, 35, 36, 37]):
            try:
                v = float(s[col])
                if v > MISS_T + 1: st[j, k] = v
            except: pass
    return st

def cn(alpha, Ttop, Tbot, Tinit, sub=1):
    """Crank-Nicolson, constant alpha, boundaries linearly interpolated onto sub-steps. Returns node series at hourly points."""
    N = len(Ttop); dts = 3600.0 / sub
    r = alpha * dts / dz ** 2; ni = NZ - 2
    ab = np.zeros((3, ni)); ab[0, 1:] = -r / 2; ab[1, :] = 1 + r; ab[2, :-1] = -r / 2
    T = Tinit.astype(float).copy(); out = np.zeros((N, NZ)); out[0] = T
    for n in range(1, N):
        for s in range(1, sub + 1):
            f0 = (s - 1) / sub; f1 = s / sub
            top0 = Ttop[n - 1] + f0 * (Ttop[n] - Ttop[n - 1]); top1 = Ttop[n - 1] + f1 * (Ttop[n] - Ttop[n - 1])
            bot0 = Tbot[n - 1] + f0 * (Tbot[n] - Tbot[n - 1]); bot1 = Tbot[n - 1] + f1 * (Tbot[n] - Tbot[n - 1])
            T[0] = top0; T[-1] = bot0
            rhs = (r / 2) * T[:-2] + (1 - r) * T[1:-1] + (r / 2) * T[2:]
            rhs[0] += (r / 2) * top1; rhs[-1] += (r / 2) * bot1
            T[1:-1] = solve_banded((1, 1), ab, rhs); T[0] = top1; T[-1] = bot1
        out[n] = T
    return out

# ---------------- Q2: solver check against exact periodic solution ----------------
print('=== Q2. SOLVER CHECK vs exact analytic periodic solution (semi-infinite wave, boundaries at 5 and 20 cm) ===')
print(f'{"alpha m2/s":>11} {"damping depth cm":>17} {"amp err % (dt=1h)":>18} {"amp err % (sub=6)":>18} {"phase err h (1h)":>17}')
t = np.arange(24 * 12) * 3600.0
for alpha in [2e-7, 4e-7, 6e-7, 8e-7, 1.2e-6]:
    d = np.sqrt(2 * alpha / W)
    Tz = lambda z: 5.0 * np.exp(-z / d) * np.cos(W * t - z / d)
    exact = Tz(0.10)
    res = []
    for sub in (1, 6):
        init = np.linspace(Tz(0.05)[0], Tz(0.20)[0], NZ)
        o = cn(alpha, Tz(0.05), Tz(0.20), init, sub)[:, OBS]
        sl = slice(24 * 4, None)
        a_ex = np.abs(np.fft.rfft(exact[sl])[len(exact[sl]) // 24]) ; a_cn = np.abs(np.fft.rfft(o[sl])[len(o[sl]) // 24])
        ph = np.angle(np.fft.rfft(o[sl])[len(o[sl]) // 24] / np.fft.rfft(exact[sl])[len(exact[sl]) // 24]) * 24 / (2 * np.pi)
        res.append((100 * (a_cn / a_ex - 1), ph))
    print(f'{alpha:11.2e} {100 * d:17.1f} {res[0][0]:18.2f} {res[1][0]:18.2f} {res[0][1]:17.3f}')

# ---------------- load data / episodes ----------------
st = load_station('AL_Selma_13_WNW', [2019, 2020])
valid = np.all(~np.isnan(st), axis=1) & np.all(st > 1.0, axis=1)
eps = []; inep = False
for i in range(len(valid)):
    if valid[i] and not inep: es = i; inep = True
    elif not valid[i] and inep:
        if i - es >= 96: eps.append((es, i))
        inep = False
if inep and len(valid) - es >= 96: eps.append((es, len(valid)))

def harm_amp(x, k=24):
    n = len(x); tt = np.arange(n)
    A = np.vstack([np.ones(n), tt - tt.mean(), np.cos(2 * np.pi * tt / k), np.sin(2 * np.pi * tt / k)]).T
    c, *_ = np.linalg.lstsq(A, x, rcond=None)
    return complex(c[2], -c[3])          # x ~ Re[c e^{i w t}]

def metrics(model, obs, sl):
    a_m = harm_amp(model[sl]); a_o = harm_amp(obs[sl])
    ph = np.angle(a_m / a_o) * 24 / (2 * np.pi)
    rm = np.sqrt(np.mean((model[sl] - obs[sl]) ** 2))
    return abs(a_m) / abs(a_o), ph, rm, abs(a_o)

# ---------------- Q3: global alpha scan + in-sample fit, Episode 4 and all episodes ----------------
print('\n=== Q3. IS THE AMPLITUDE ERROR REMOVED BY FITTING alpha IN-SAMPLE? (whole episode, global grid) ===')
grid = np.exp(np.linspace(np.log(5e-8), np.log(8e-6), 70))
def scan(ep):
    es, ee = ep; T5, T10, T20 = st[es:ee, 0], st[es:ee, 1], st[es:ee, 2]
    init = np.linspace(T5[0], T20[0], NZ); wu = 48; out = []
    for a in grid:
        m = cn(a, T5, T20, init, 1)[:, OBS]
        r, ph, rm, ao = metrics(m, T10, slice(wu, None))
        out.append((a, rm, r, ph))
    return np.array(out), ao

ep4 = eps[3]
sc, ao = scan(ep4)
i_sse = sc[:, 1].argmin(); 
print(f'Episode 4 ({ep4[1] - ep4[0]} h), observed 10 cm diurnal amplitude (whole episode, after 48 h warm-up): {ao:.3f} C')
print(f'{"alpha":>10} {"RMSE C":>8} {"amp ratio model/obs":>20} {"phase err h":>12}')
for j in list(range(0, 70, 7)) + [i_sse]:
    print(f'{sc[j, 0]:10.2e} {sc[j, 1]:8.3f} {sc[j, 2]:20.3f} {sc[j, 3]:12.2f}' + ('   <-- minimum RMSE' if j == i_sse else ''))
# amplitude-matched alpha
ratio = sc[:, 2]
cross = np.where((ratio[:-1] - 1) * (ratio[1:] - 1) < 0)[0]
if len(cross):
    j = cross[0]; a_match = np.exp(np.interp(1.0, [ratio[j + 1], ratio[j]], [np.log(sc[j + 1, 0]), np.log(sc[j, 0])]))
    m_at = np.argmin(np.abs(grid - a_match))
    print(f'Alpha that matches the observed amplitude exactly: {a_match:.2e}; RMSE there {sc[m_at, 1]:.3f} C, phase error {sc[m_at, 3]:.2f} h; min-RMSE alpha {sc[i_sse, 0]:.2e} gives amp ratio {sc[i_sse, 2]:.3f}')
print(f'MIN-RMSE alpha {sc[i_sse, 0]:.2e}: RMSE {sc[i_sse, 1]:.3f} C, amplitude ratio {sc[i_sse, 2]:.3f}, phase err {sc[i_sse, 3]:.2f} h')

print('\nAll episodes >= 144 h, in-sample min-RMSE alpha on whole episode:')
print(f'{"ep":>3} {"hours":>6} {"alpha*":>10} {"RMSE":>7} {"amp ratio":>10} {"phase h":>8} {"obs amp10":>10}')
ratios = []
for k, ep in enumerate(eps):
    if ep[1] - ep[0] < 144: continue
    s_, ao_ = scan(ep); j = s_[:, 1].argmin(); ratios.append(s_[j, 2])
    print(f'{k + 1:3d} {ep[1] - ep[0]:6d} {s_[j, 0]:10.2e} {s_[j, 1]:7.3f} {s_[j, 2]:10.3f} {s_[j, 3]:8.2f} {ao_:10.3f}')
ratios = np.array(ratios)
print(f'Amplitude ratio at min-RMSE alpha across {len(ratios)} episodes: median {np.median(ratios):.3f}, min {ratios.min():.3f}, max {ratios.max():.3f}')

# ---------------- Q4: solver-free harmonic diagnostic ----------------
print('\n=== Q4. SOLVER-FREE CHECK: alpha from amplitude decay vs alpha from phase lag (daily 24 h windows, linear trend removed) ===')
print('Homogeneous 1D conduction requires alpha_amp = alpha_phase for every layer.')
pairs = [(0, 1, 0.05, '5-10 cm'), (1, 2, 0.10, '10-20 cm'), (0, 2, 0.15, '5-20 cm')]
agg = {p[3]: [] for p in pairs}
for ep in eps:
    es, ee = ep
    for d0 in range(es + 48, ee - 24, 24):
        c = [harm_amp(st[d0:d0 + 24, j]) for j in range(3)]
        if abs(c[0]) < 1.5: continue
        for (i, j, dzp, lab) in pairs:
            rr = c[j] / c[i]
            if abs(rr) >= 1 or abs(rr) < 0.02: continue
            lag = -np.angle(rr)
            if lag <= 0.05 or lag > np.pi: continue
            d_amp = -dzp / np.log(abs(rr)); d_ph = dzp / lag
            agg[lab].append((W * d_amp ** 2 / 2, W * d_ph ** 2 / 2, abs(rr), lag * 24 / (2 * np.pi)))
print(f'{"layer":>9} {"days":>5} {"alpha_amp median":>17} {"alpha_phase median":>19} {"median ratio amp/phase":>23} {"IQR of ratio":>16} {"median |A_lower/A_upper|":>25} {"median lag h":>13}')
for lab, v in agg.items():
    if not v: print(lab, 'no valid days'); continue
    v = np.array(v); rt = v[:, 0] / v[:, 1]
    q1, q3 = np.percentile(rt, [25, 75])
    print(f'{lab:>9} {len(v):5d} {np.median(v[:, 0]):17.2e} {np.median(v[:, 1]):19.2e} {np.median(rt):23.2f} {q1:7.2f}-{q3:5.2f} {np.median(v[:, 2]):25.3f} {np.median(v[:, 3]):13.2f}')
