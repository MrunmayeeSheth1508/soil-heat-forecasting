import os as _o, sys as _s
_p = _o.path.dirname(_o.path.abspath(__file__))
while not _o.path.exists(_o.path.join(_p, 'src', 'config.py')): _p = _o.path.dirname(_p)
_s.path.insert(0, _o.path.join(_p, 'src'))
from config import WS_ROOT  # PATH-PATCH: was an absolute path to the original working directory
"""
Corrected soil rerun: four diffusivity models on identical training and excluded episodes.

PRE-SPECIFIED DESIGN (fixed before any results were seen)
 Model:    1D heat equation on 5-20 cm (7 nodes, dz 2.5 cm, dt 1 h, Crank-Nicolson), T5 and T20 are measured boundary inputs.
           T10 is NEVER an input. It is the target only (training loss, and excluded-episode scoring).
 Diffusivity: alpha_t = exp[ a + b*(theta_t - theta0)/0.1 + c*(Tin_t - T0)/10 ],  b and c SIGNED.
   A: b=c=0   B: c=0   C: b=0   D: free b and c
   theta_t = measured 10 cm soil moisture at hour t (explicit representative-layer assumption).
   Tin_t   = trailing 24 h mean of (T5+T20)/2 (boundary observations only; contains no 10 cm temperature, no validation summary).
   theta0, T0 = hourly means over TRAINING episodes only.
 Loss:     per-episode mean squared error of T10 (first 24 h of each episode discarded), averaged with EQUAL weight per episode.
 Split:    episodes sorted chronologically. Episodes 1-11 = training / model selection (leave-one-episode-out CV).
           Episodes 12-14 = final untouched test, scored once with parameters refitted on all 11 training episodes.
 Decision rule for "moisture adds reproducible information beyond temperature" (D vs C):
           (i) LOEO CV: D better than C in at least 8 of 11 held-out episodes AND bootstrap 95% CI (over episodes) of mean RMSE improvement excludes 0;
           (ii) final test: D better than C in all 3 test episodes;
           (iii) episode-bootstrap 95% interval for b excludes 0.
           Otherwise: moisture effect NOT established beyond temperature.
"""
import sys, io, warnings, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
warnings.filterwarnings('ignore')
import numpy as np
from numba import njit
from scipy.optimize import least_squares
from scipy.stats import binomtest

D = np.load((WS_ROOT + r'\episodes14.npz'), allow_pickle=True)
NEP = int(D['n'])
EP = []
for k in range(NEP):
    T = D[f'T_{k}']; S = D[f'S_{k}']
    tb = 0.5 * (T[:, 0] + T[:, 2]); cs = np.cumsum(np.insert(tb, 0, 0.0)); n = len(tb)
    tin = np.empty(n)
    for i in range(n):
        lo = max(0, i - 23); tin[i] = (cs[i + 1] - cs[lo]) / (i + 1 - lo)
    EP.append(dict(T5=T[:, 0].copy(), T10=T[:, 1].copy(), T20=T[:, 2].copy(), th=S[:, 1].copy(), tin=tin, n=n))
TRAIN = list(range(0, 11)); TEST = [11, 12, 13]
WU = 24

@njit(cache=True)
def sim(T5, T20, alpha):
    N = len(T5); NZ = 7; ni = 5; dzz = 0.025; dtt = 3600.0
    T = np.empty(NZ)
    for i in range(NZ): T[i] = T5[0] + (T20[0] - T5[0]) * i / (NZ - 1)
    out = np.empty(N); out[0] = T[2]
    d = np.empty(ni); cp = np.empty(ni); dp = np.empty(ni); x = np.empty(ni)
    for n in range(1, N):
        r = alpha[n] * dtt / dzz ** 2
        for i in range(ni):
            ig = i + 1
            d[i] = (r / 2) * T[ig - 1] + (1 - r) * T[ig] + (r / 2) * T[ig + 1]
        d[0] += (r / 2) * T5[n]; d[ni - 1] += (r / 2) * T20[n]
        lo = -r / 2; di = 1 + r; up = -r / 2
        cp[0] = up / di; dp[0] = d[0] / di
        for i in range(1, ni):
            m = di - lo * cp[i - 1]; cp[i] = up / m; dp[i] = (d[i] - lo * dp[i - 1]) / m
        x[ni - 1] = dp[ni - 1]
        for i in range(ni - 2, -1, -1): x[i] = dp[i] - cp[i] * x[i + 1]
        T[0] = T5[n]
        for i in range(ni): T[i + 1] = x[i]
        T[NZ - 1] = T20[n]; out[n] = T[2]
    return out

def alpha_series(e, a, b, c, th0, T0):
    z = a + b * (e['th'] - th0) / 0.1 + c * (e['tin'] - T0) / 10.0
    return np.clip(np.exp(z), 1e-9, 1e-4)

def predict(e, p, model, th0, T0):
    a = p[0]; b = 0.0; c = 0.0
    if model == 'B': b = p[1]
    elif model == 'C': c = p[1]
    elif model == 'D': b, c = p[1], p[2]
    return sim(e['T5'], e['T20'], alpha_series(e, a, b, c, th0, T0))

def ep_mse(e, pred): return float(np.mean((pred[WU:] - e['T10'][WU:]) ** 2))

def fit(model, eps, th0, T0):
    def resid(p):
        r = []
        for i in eps:
            e = EP[i]; pr = predict(e, p, model, th0, T0)
            r.append((pr[WU:] - e['T10'][WU:]) / np.sqrt(len(pr[WU:])))
        return np.concatenate(r)
    npar = {'A': 1, 'B': 2, 'C': 2, 'D': 3}[model]
    starts = []
    for a0 in (-15.5, -14.8, -14.2):
        base = [a0] + [0.0] * (npar - 1); starts.append(base)
    if npar == 3: starts += [[-14.8, 0.5, -0.5], [-14.8, -0.5, 0.5]]
    if npar == 2: starts += [[-14.8, 0.5], [-14.8, -0.5]]
    lb = [-20] + [-5] * (npar - 1); ub = [-8] + [5] * (npar - 1)
    best = None
    for s0 in starts:
        try:
            r = least_squares(resid, s0, bounds=(lb, ub), x_scale=[1.0] + [1.0] * (npar - 1), diff_step=1e-3, max_nfev=80)
        except Exception: continue
        if best is None or r.cost < best.cost: best = r
    return best.x, 2 * best.cost / len(eps)   # parameters, mean per-episode MSE

def centers(eps):
    th = np.concatenate([EP[i]['th'] for i in eps]); ti = np.concatenate([EP[i]['tin'] for i in eps])
    return float(th.mean()), float(ti.mean())

def amp_phase(x, y):
    n = len(x); t = np.arange(n)
    A = np.vstack([np.ones(n), t - t.mean(), np.cos(2 * np.pi * t / 24), np.sin(2 * np.pi * t / 24)]).T
    cx, *_ = np.linalg.lstsq(A, x, rcond=None); cy, *_ = np.linalg.lstsq(A, y, rcond=None)
    ax = complex(cx[2], -cx[3]); ay = complex(cy[2], -cy[3])
    return abs(ax) / abs(ay), np.angle(ax / ay) * 24 / (2 * np.pi)

MODELS = ['A', 'B', 'C', 'D']
rng = np.random.default_rng(0)

# ---------- training-set fit ----------
th0, T0 = centers(TRAIN)
allth = np.concatenate([EP[i]['th'] for i in TRAIN]); allti = np.concatenate([EP[i]['tin'] for i in TRAIN])
print(f'Training episodes {[i + 1 for i in TRAIN]}, test episodes {[i + 1 for i in TEST]}')
print(f'theta0 {th0:.3f} m3/m3, T0 {T0:.2f} C. Hourly corr(theta, Tin) in training: {np.corrcoef(allth, allti)[0, 1]:.3f}')
q = lambda x: np.percentile(x, [25, 75])
th_iqr = q(allth); ti_iqr = q(allti)
print(f'Training IQR of theta: {th_iqr[0]:.3f} to {th_iqr[1]:.3f}; of Tin: {ti_iqr[0]:.1f} to {ti_iqr[1]:.1f} C')
print('\n=== FULL TRAINING FIT (all 11 training episodes) ===')
PAR = {}
for m in MODELS:
    p, mse = fit(m, TRAIN, th0, T0); PAR[m] = p
    s = f'{m}: a={p[0]:.3f} (alpha at centre {np.exp(p[0]):.2e})'
    if m == 'B': s += f' b={p[1]:+.3f} per 0.1 m3/m3'
    if m == 'C': s += f' c={p[1]:+.3f} per 10 C'
    if m == 'D': s += f' b={p[1]:+.3f} per 0.1 m3/m3, c={p[2]:+.3f} per 10 C'
    print(s + f'   mean per-episode MSE {mse:.4f} (RMSE {np.sqrt(mse):.3f} C)')
    bb = p[1] if m in ('B', 'D') else 0.0; cc = p[2] if m == 'D' else (p[1] if m == 'C' else 0.0)
    if m in ('B', 'D'): print(f'    alpha multiplier across training IQR of theta: x{np.exp(bb * (th_iqr[1] - th_iqr[0]) / 0.1):.2f}')
    if m in ('C', 'D'): print(f'    alpha multiplier across training IQR of Tin:   x{np.exp(cc * (ti_iqr[1] - ti_iqr[0]) / 10):.2f}')

# ---------- leave-one-episode-out CV on training episodes ----------
print('\n=== LEAVE-ONE-EPISODE-OUT CV (training episodes only) : held-out RMSE of T10, C ===')
cv = {m: [] for m in MODELS}
for h in TRAIN:
    tr = [i for i in TRAIN if i != h]; t0, tt0 = centers(tr)
    for m in MODELS:
        p, _ = fit(m, tr, t0, tt0)
        cv[m].append(np.sqrt(ep_mse(EP[h], predict(EP[h], p, m, t0, tt0))))
print(f'{"held-out ep":>12} ' + ' '.join(f'{m:>7}' for m in MODELS) + f' {"hours":>7}')
for j, h in enumerate(TRAIN):
    print(f'{h + 1:12d} ' + ' '.join(f'{cv[m][j]:7.3f}' for m in MODELS) + f' {EP[h]["n"]:7d}')
print(f'{"mean":>12} ' + ' '.join(f'{np.mean(cv[m]):7.3f}' for m in MODELS))

def paired(x, y, label, B=5000):
    d = np.array(x) - np.array(y)   # positive: second model is better (lower RMSE)
    better = int((d > 0).sum()); n = len(d)
    bs = np.array([d[rng.integers(0, n, n)].mean() for _ in range(B)])
    p = binomtest(better, n, 0.5).pvalue
    print(f'  {label:<18} better in {better}/{n} episodes; mean RMSE improvement {d.mean():+.4f} C; bootstrap 95% CI [{np.percentile(bs, 2.5):+.4f}, {np.percentile(bs, 97.5):+.4f}]; sign-test p={p:.3f}')
    return better, np.percentile(bs, 2.5), np.percentile(bs, 97.5)
print('\nPaired LOEO comparisons (improvement = RMSE of first minus RMSE of second):')
paired(cv['A'], cv['B'], 'B vs A (moisture)'); paired(cv['A'], cv['C'], 'C vs A (temp)')
paired(cv['B'], cv['D'], 'D vs B (+temp)'); cdec = paired(cv['C'], cv['D'], 'D vs C (+moisture)'); paired(cv['A'], cv['D'], 'D vs A')

# ---------- episode bootstrap for parameter uncertainty ----------
print('\n=== EPISODE BOOTSTRAP (200 resamples of the 11 training episodes) ===')
BS = {'B': [], 'C': [], 'D': []}
for _ in range(200):
    sel = list(rng.choice(TRAIN, size=len(TRAIN), replace=True)); t0, tt0 = centers(sel)
    for m in ('B', 'C', 'D'):
        p, _ = fit(m, sel, t0, tt0); BS[m].append(p)
for m in ('B', 'C', 'D'):
    arr = np.array(BS[m])
    if m == 'B': print(f'B: b median {np.median(arr[:, 1]):+.3f}, 95% [{np.percentile(arr[:, 1], 2.5):+.3f}, {np.percentile(arr[:, 1], 97.5):+.3f}], P(b<0) = {(arr[:, 1] < 0).mean():.2f}')
    if m == 'C': print(f'C: c median {np.median(arr[:, 1]):+.3f}, 95% [{np.percentile(arr[:, 1], 2.5):+.3f}, {np.percentile(arr[:, 1], 97.5):+.3f}], P(c>0) = {(arr[:, 1] > 0).mean():.2f}')
    if m == 'D':
        print(f'D: b median {np.median(arr[:, 1]):+.3f}, 95% [{np.percentile(arr[:, 1], 2.5):+.3f}, {np.percentile(arr[:, 1], 97.5):+.3f}], P(b<0) = {(arr[:, 1] < 0).mean():.2f}')
        print(f'D: c median {np.median(arr[:, 2]):+.3f}, 95% [{np.percentile(arr[:, 2], 2.5):+.3f}, {np.percentile(arr[:, 2], 97.5):+.3f}], P(c>0) = {(arr[:, 2] > 0).mean():.2f}')
        print(f'D: bootstrap correlation corr(b, c) = {np.corrcoef(arr[:, 1], arr[:, 2])[0, 1]:+.3f}')
b_lo = np.percentile(np.array(BS['D'])[:, 1], 2.5); b_hi = np.percentile(np.array(BS['D'])[:, 1], 97.5)

# ---------- final untouched test ----------
print('\n=== FINAL UNTOUCHED TEST (refit on all 11 training episodes, scored once on episodes 12-14) ===')
te = {m: [] for m in MODELS}; ampr = {m: [] for m in MODELS}; phs = {m: [] for m in MODELS}
for h in TEST:
    e = EP[h]
    for m in MODELS:
        pr = predict(e, PAR[m], m, th0, T0); te[m].append(np.sqrt(ep_mse(e, pr)))
        r, ph = amp_phase(pr[WU:], e['T10'][WU:]); ampr[m].append(r); phs[m].append(ph)
print(f'{"test ep":>8} ' + ' '.join(f'{m:>7}' for m in MODELS) + f' {"hours":>7}')
for j, h in enumerate(TEST): print(f'{h + 1:8d} ' + ' '.join(f'{te[m][j]:7.3f}' for m in MODELS) + f' {EP[h]["n"]:7d}')
print('Amplitude ratio model/obs (A B C D):', {h + 1: [round(ampr[m][j], 3) for m in MODELS] for j, h in enumerate(TEST)})
print('Phase error h (A B C D):           ', {h + 1: [round(phs[m][j], 2) for m in MODELS] for j, h in enumerate(TEST)})
print('Paired test comparisons (improvement = first RMSE minus second):')
for (x, y, lab) in [('A', 'B', 'B vs A'), ('A', 'C', 'C vs A'), ('B', 'D', 'D vs B'), ('C', 'D', 'D vs C'), ('A', 'D', 'D vs A')]:
    d = np.array(te[x]) - np.array(te[y]); print(f'  {lab:<8} better in {int((d > 0).sum())}/3 episodes; mean improvement {d.mean():+.4f} C')
dc = np.array(te['C']) - np.array(te['D'])

# ---------- decision rule ----------
print('\n=== PRE-SPECIFIED DECISION RULE (D vs C) ===')
c1 = cdec[0] >= 8 and cdec[1] > 0
c2 = int((dc > 0).sum()) == 3
c3 = (b_lo > 0) or (b_hi < 0)
print(f'(i)  LOEO: D better than C in {cdec[0]}/11 and CI excludes 0 -> {c1}')
print(f'(ii) test: D better than C in {int((dc > 0).sum())}/3 -> {c2}')
print(f'(iii) bootstrap 95% interval for b excludes 0 ([{b_lo:+.3f}, {b_hi:+.3f}]) -> {c3}')
print('VERDICT:', 'moisture adds reproducible information beyond temperature' if (c1 and c2 and c3) else 'moisture effect NOT established beyond temperature')
