import os as _o, sys as _s
_p = _o.path.dirname(_o.path.abspath(__file__))
while not _o.path.exists(_o.path.join(_p, 'src', 'config.py')): _p = _o.path.dirname(_p)
_s.path.insert(0, _o.path.join(_p, 'src'))
from config import WS_ROOT  # PATH-PATCH: was an absolute path to the original working directory
"""
Small conventional multi-station pilot: does within-station moisture change improve excluded 10 cm temperature
predictions after station differences and temperature are accounted for?

PRE-SPECIFIED DESIGN (fixed before any result)
 Stations: pilot_stations.txt (5 selected by rule in 16_reconcile_qc_select.py + Selma reference).
 Development period: 2019-2021. Final evaluation period: 2022, not downloaded or inspected until models are frozen (FINAL=False here).
 Forward model: 1D conduction, 5-20 cm, 7 nodes, CN, dt 1 h. T5 and T20 measured boundaries. T10 target only, never an input.
 Segments: continuous hours with T5, T10, T20, SM10 valid and all three temperatures > 1 C, cut into 336 h pieces (min 168 h).
 Scored hours: exclude first 24 h of each segment (warm-up) and hours with > 1 mm precipitation in the preceding 24 h.
 Inputs: theta = measured 10 cm moisture (representative-layer assumption). Tin = trailing 24 h mean of (T5+T20)/2 (boundaries only).
 Separation of station differences from within-station change:
   theta_bar_s, T_bar_s = station means over the data used to calibrate that station. Moisture and temperature enter only as departures.
   Station mean differences are absorbed by the station intercept a_s; the between-station moisture effect is therefore NOT tested here.
 Models (b, c shared across stations, signed):
   M_T : log alpha = a_s + c (Tin - T_bar_s)/10
   M_TM: log alpha = a_s + b (theta - theta_bar_s)/0.1 + c (Tin - T_bar_s)/10
 Unseen station (local-calibration design): leave-one-station-out. b, c fitted on the other 5 stations.
   At the held-out station only a_s is fitted, on its first 25% of development segments (chronological); theta_bar_s and T_bar_s also
   from that calibration block only. Scored on its remaining 75%. Identical allowance for M_T and M_TM.
 Uncertainty and observation checks:
   segment block bootstrap within stations (100 resamples) for pooled b, c and corr(b, c);
   refits with +/-0.1 C offsets on T5 or on T20 (reporting resolution and bias scenario);
   moisture calibration scale error of +/-20% rescales b by 1/(1 +/- 0.2) and cannot flip its sign (stated, not refitted);
   station-specific fits (a_s, b_s, c_s) to show heterogeneity.
 Decision rule (development), all required:
   D1 M_TM lower RMSE than M_T at >= 5 of 6 held-out stations
   D2 station-averaged improvement, bootstrap 95% CI (segments resampled within stations) excludes 0
   D3 b has the same sign in all 6 LOSO folds and the pooled bootstrap 95% interval for b excludes 0
   D4 sign of pooled b unchanged under all four boundary offsets
"""
import sys, io, os, warnings
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
warnings.filterwarnings('ignore')
import numpy as np
from numba import njit
from scipy.optimize import least_squares

SO = WS_ROOT; IN = os.path.join(SO, 'multi')
STN = [s.strip() for s in open(os.path.join(SO, 'pilot_stations.txt')) if s.strip()]
SEGLEN, MINLEN, WU = 336, 168, 24
rng = np.random.default_rng(1)

@njit(cache=True)
def sim(T5, T20, la):
    N = len(T5); NZ = 7; ni = 5; dz2 = 0.025 ** 2
    T = np.empty(NZ)
    for i in range(NZ): T[i] = T5[0] + (T20[0] - T5[0]) * i / (NZ - 1)
    out = np.empty(N); out[0] = T[2]
    d = np.empty(ni); cp = np.empty(ni); dp = np.empty(ni)
    for n in range(1, N):
        a = np.exp(min(max(la[n], -20.7), -9.2))
        r = a * 3600.0 / dz2
        for i in range(ni): d[i] = (r / 2) * T[i] + (1 - r) * T[i + 1] + (r / 2) * T[i + 2]
        d[0] += (r / 2) * T5[n]; d[ni - 1] += (r / 2) * T20[n]
        lo = -r / 2; di = 1 + r; up = -r / 2
        cp[0] = up / di; dp[0] = d[0] / di
        for i in range(1, ni):
            m = di - lo * cp[i - 1]; cp[i] = up / m; dp[i] = (d[i] - lo * dp[i - 1]) / m
        T[ni] = dp[ni - 1]
        for i in range(ni - 2, -1, -1): T[i + 1] = dp[i] - cp[i] * T[i + 2]
        T[0] = T5[n]; T[NZ - 1] = T20[n]; out[n] = T[2]
    return out

def build(stn, years=(2019, 2020, 2021)):
    ps = [np.load(os.path.join(IN, f'{stn}_{y}.npz')) for y in years]
    P = np.concatenate([p['P'] for p in ps]); SM = np.concatenate([p['SM'] for p in ps]); ST = np.concatenate([p['ST'] for p in ps])
    T5, T10, T20, th = ST[:, 0].astype(float), ST[:, 1].astype(float), ST[:, 2].astype(float), SM[:, 1].astype(float)
    ok = ~np.isnan(T5) & ~np.isnan(T10) & ~np.isnan(T20) & ~np.isnan(th) & (np.minimum(np.minimum(T5, T10), T20) > 1.0)
    Pr = np.nan_to_num(P.astype(float)); P24 = np.convolve(Pr, np.ones(24), 'full')[:len(Pr)]
    segs = []; s0 = None
    for i in range(len(ok) + 1):
        v = ok[i] if i < len(ok) else False
        if v and s0 is None: s0 = i
        if not v and s0 is not None:
            for a in range(s0, i, SEGLEN):
                b = min(a + SEGLEN, i)
                if b - a >= MINLEN:
                    tb = 0.5 * (T5[a:b] + T20[a:b]); cs = np.cumsum(np.insert(tb, 0, 0)); idx = np.arange(b - a)
                    lo = np.maximum(0, idx - 23); tin = (cs[idx + 1] - cs[lo]) / (idx + 1 - lo)
                    m = np.zeros(b - a, bool); m[WU:] = True; m &= P24[a:b] <= 1.0
                    if m.sum() >= 48: segs.append(dict(T5=T5[a:b], T10=T10[a:b], T20=T20[a:b], th=th[a:b], tin=tin, m=m, start=a))
            s0 = None
    return segs

DATA = {s: build(s) for s in STN}
print('Stations and development segments (336 h pieces, 2019-2021):')
for s in STN:
    sg = DATA[s]; th = np.concatenate([g['th'][g['m']] for g in sg]); tin = np.concatenate([g['tin'][g['m']] for g in sg])
    print(f'  {s:28s} segments {len(sg):3d}  scored hours {sum(g["m"].sum() for g in sg):6d}  theta {th.min():.3f}-{th.max():.3f} (IQR {np.percentile(th, 25):.3f}-{np.percentile(th, 75):.3f})  r(theta,Tin) {np.corrcoef(th, tin)[0, 1]:+.2f}')

def means(segs):
    th = np.concatenate([g['th'] for g in segs]); ti = np.concatenate([g['tin'] for g in segs]); return th.mean(), ti.mean()

def seg_pred(g, a, b, c, thb, Tb, dT5=0.0, dT20=0.0):
    la = a + b * (g['th'] - thb) / 0.1 + c * (g['tin'] - Tb) / 10.0
    return sim(g['T5'] + dT5, g['T20'] + dT20, la)

def fit_shared(model, sdict, start=None, dT5=0.0, dT20=0.0):
    """sdict: station -> list of segments. Fits a_s per station + shared b (if M_TM) + c. Equal weight per station."""
    names = list(sdict); K = len(names); cen = {s: means(sdict[s]) for s in names}
    nh = {s: sum(g['m'].sum() for g in sdict[s]) for s in names}
    def unpack(p):
        a = p[:K]; b = p[K] if model == 'M_TM' else 0.0; c = p[-1]; return a, b, c
    def res(p):
        a, b, c = unpack(p); out = []
        for k, s in enumerate(names):
            w = 1 / np.sqrt(nh[s])
            for g in sdict[s]:
                pr = seg_pred(g, a[k], b, c, *cen[s], dT5, dT20); out.append(w * (pr[g['m']] - g['T10'][g['m']]))
        return np.concatenate(out)
    npar = K + (2 if model == 'M_TM' else 1)
    p0 = np.r_[np.full(K, -14.8), ([0.0] if model == 'M_TM' else []), [0.0]] if start is None else start
    lb = np.r_[np.full(K, -20.0), np.full(npar - K, -5.0)]; ub = np.r_[np.full(K, -9.5), np.full(npar - K, 5.0)]
    r = least_squares(res, p0, bounds=(lb, ub), diff_step=1e-3, max_nfev=200)
    a, b, c = unpack(r.x); return dict(a=dict(zip(names, a)), b=b, c=c, cen=cen, x=r.x)

def fit_intercept(segs, b, c, thb, Tb):
    def res(p): return np.concatenate([seg_pred(g, p[0], b, c, thb, Tb)[g['m']] - g['T10'][g['m']] for g in segs])
    return least_squares(res, [-14.8], bounds=([-20], [-9.5]), diff_step=1e-3).x[0]

def seg_errors(segs, a, b, c, thb, Tb):
    return [np.mean((seg_pred(g, a, b, c, thb, Tb)[g['m']] - g['T10'][g['m']]) ** 2) for g in segs], [g['m'].sum() for g in segs]

# ---------------- pooled fit on all 6 stations ----------------
print('\n=== POOLED FIT, all stations, all development data ===')
FIT = {}
for m in ('M_T', 'M_TM'):
    FIT[m] = fit_shared(m, DATA)
    print(f'{m}: c = {FIT[m]["c"]:+.3f} per 10 C' + (f', b = {FIT[m]["b"]:+.3f} per 0.1 m3/m3' if m == 'M_TM' else '') +
          '  intercepts: ' + ', '.join(f'{s.split("_")[0]}_{s.split("_")[1][:6]} {np.exp(v):.2e}' for s, v in FIT[m]['a'].items()))

# ---------------- LOSO with local calibration ----------------
print('\n=== LEAVE-ONE-STATION-OUT, local calibration on first 25% of held-out segments ===')
rows = []; bfold = []
for h in STN:
    train = {s: DATA[s] for s in STN if s != h}
    segs = DATA[h]; nc = max(1, int(round(0.25 * len(segs)))); cal, tst = segs[:nc], segs[nc:]
    thb, Tb = means(cal); res_h = {}
    for m in ('M_T', 'M_TM'):
        F = fit_shared(m, train); b = F['b']; c = F['c']
        a = fit_intercept(cal, b, c, thb, Tb)
        e, n = seg_errors(tst, a, b, c, thb, Tb); res_h[m] = (np.array(e), np.array(n), b, c)
        if m == 'M_TM': bfold.append(b)
    eT, n, _, cT = res_h['M_T']; eM, _, bM, cM = res_h['M_TM']
    rT = np.sqrt(np.average(eT, weights=n)); rM = np.sqrt(np.average(eM, weights=n))
    rows.append(dict(st=h, rT=rT, rM=rM, eT=eT, eM=eM, n=n, b=bM, cT=cT, cM=cM, ncal=nc, ntest=len(tst)))
    print(f'  held out {h:28s} cal {nc:3d} seg / test {len(tst):3d} seg   RMSE M_T {rT:.4f}  M_TM {rM:.4f}  diff {rT - rM:+.4f}   fold b {bM:+.3f}  c(M_T) {cT:+.3f}  c(M_TM) {cM:+.3f}')
better = sum(r['rM'] < r['rT'] for r in rows)
imp = np.array([r['rT'] - r['rM'] for r in rows])
bs = []
for _ in range(2000):
    v = []
    for r in rows:
        i = rng.integers(0, len(r['n']), len(r['n']))
        v.append(np.sqrt(np.average(r['eT'][i], weights=r['n'][i])) - np.sqrt(np.average(r['eM'][i], weights=r['n'][i])))
    bs.append(np.mean(v))
ci = np.percentile(bs, [2.5, 97.5])
print(f'M_TM better at {better}/{len(rows)} held-out stations; station-averaged improvement {imp.mean():+.4f} C, bootstrap 95% CI [{ci[0]:+.4f}, {ci[1]:+.4f}]')
print('LOSO fold b values:', np.round(bfold, 3))

# ---------------- bootstrap of pooled b, c ----------------
print('\n=== SEGMENT BLOCK BOOTSTRAP WITHIN STATIONS (100), pooled M_TM ===')
B = []
for k in range(100):
    sd = {s: [DATA[s][i] for i in rng.integers(0, len(DATA[s]), len(DATA[s]))] for s in STN}
    F = fit_shared('M_TM', sd, start=FIT['M_TM']['x']); B.append((F['b'], F['c']))
B = np.array(B)
bci = np.percentile(B[:, 0], [2.5, 97.5]); cci = np.percentile(B[:, 1], [2.5, 97.5])
print(f'b median {np.median(B[:, 0]):+.3f}, 95% [{bci[0]:+.3f}, {bci[1]:+.3f}];  c median {np.median(B[:, 1]):+.3f}, 95% [{cci[0]:+.3f}, {cci[1]:+.3f}];  corr(b,c) {np.corrcoef(B.T)[0, 1]:+.3f}')
print('Note: segments within a station are autocorrelated in season; this bootstrap understates uncertainty.')

# ---------------- observation offsets ----------------
print('\n=== BOUNDARY OFFSET SENSITIVITY (pooled M_TM refit) ===')
offs = []
for dT5, dT20 in [(0.1, 0), (-0.1, 0), (0, 0.1), (0, -0.1)]:
    F = fit_shared('M_TM', DATA, start=FIT['M_TM']['x'], dT5=dT5, dT20=dT20); offs.append(F['b'])
    print(f'  T5 {dT5:+.1f}  T20 {dT20:+.1f}:  b {F["b"]:+.3f}   c {F["c"]:+.3f}')
print(f'  Moisture scale error +/-20%: b would become {FIT["M_TM"]["b"] / 1.2:+.3f} to {FIT["M_TM"]["b"] / 0.8:+.3f} (sign unchanged)')

# ---------------- station-specific fits ----------------
print('\n=== STATION-SPECIFIC FITS (a_s, b_s, c_s on each station alone) ===')
for s in STN:
    F = fit_shared('M_TM', {s: DATA[s]}); bb = []
    for _ in range(30):
        sg = [DATA[s][i] for i in rng.integers(0, len(DATA[s]), len(DATA[s]))]
        bb.append(fit_shared('M_TM', {s: sg}, start=F['x'])['b'])
    print(f'  {s:28s} b_s {F["b"]:+.3f} (bootstrap 95% {np.percentile(bb, 2.5):+.3f} to {np.percentile(bb, 97.5):+.3f})  c_s {F["c"]:+.3f}  alpha {np.exp(F["a"][s]):.2e}')

# ---------------- decision ----------------
D1 = better >= 5; D2 = ci[0] > 0; D3 = (all(np.sign(bfold) == np.sign(bfold[0])) and (bci[0] > 0 or bci[1] < 0))
D4 = all(np.sign(offs) == np.sign(FIT['M_TM']['b']))
print('\n=== PRE-SPECIFIED DECISION (development) ===')
print(f'D1 better at >=5/6 held-out stations: {better}/6 -> {D1}')
print(f'D2 improvement CI excludes 0: [{ci[0]:+.4f}, {ci[1]:+.4f}] -> {D2}')
print(f'D3 b same sign in all folds and bootstrap CI excludes 0: folds {np.round(bfold, 3)}, CI [{bci[0]:+.3f}, {bci[1]:+.3f}] -> {D3}')
print(f'D4 sign of b robust to boundary offsets: {np.round(offs, 3)} -> {D4}')
print('VERDICT:', 'moisture supported in development; proceed to frozen 2022 test' if (D1 and D2 and D3 and D4) else 'moisture contribution NOT established in development')
