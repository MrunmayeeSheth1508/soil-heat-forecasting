"""Original uniform-diffusivity estimator copied VERBATIM from 40_pilotA_run.py (fit_window, getwin, grid, scenarios), with two numerical guards that cannot affect
windows with non-zero residual error: (i) SSE floor 1e-20 inside the log of the identification interval; (ii) NaN lag-1 autocorrelation (constant residual) -> 0.
The estimator is applied unchanged to simulated interior temperatures. Reproduction against archived real-data fits is checked in 46_layered_diagnostic.py."""
import numpy as np, pandas as pd
from heatsolver import simulate, make_grid, init_profile, sample
LA = np.linspace(np.log(5e-8), np.log(5e-6), 80); AL = np.exp(LA)
SC_BASE = dict(d5=0.0, d100=0.0, ztop=0.05)

def getwin(H, stn, t0, t1):
    h = H[stn].loc[t0:t1, ['T5', 'T10', 'T20', 'T50', 'T100']]
    if len(h) < 24 * 5: return None
    miss = h.isna().mean().max()
    if miss > 0.10: return None
    hf = h.interpolate(limit=3, limit_area='inside')
    if hf.isna().any().any(): return None
    return hf

def fit_window(hf, sc=SC_BASE, Bs=6):
    Tt = hf['T5'].values + sc['d5']; Tb = hf['T100'].values + sc['d100']
    z, dz = make_grid(sc['ztop'], 1.0, 38)
    zo = np.array([sc['ztop'], 0.10, 0.20, 0.50, 1.0]); T0 = init_profile(z, zo, [Tt[0], hf['T10'].values[0], hf['T20'].values[0], hf['T50'].values[0], Tb[0]])
    obs = hf[['T10', 'T20', 'T50']].values; sse = np.empty(len(AL))
    best = None
    for i, a in enumerate(AL):
        sim = simulate(a, Tt, Tb, z, T0); pr = sample(sim, z, [0.10, 0.20, 0.50]); res = (pr - obs)[Bs:]
        sse[i] = float((res ** 2).sum())
        if best is None or sse[i] < best[0]: best = (sse[i], i, res)
    i0 = best[1]; res = best[2]; n = res.shape[0]
    rho = float(np.mean([np.corrcoef(res[:-1, k], res[1:, k])[0, 1] for k in range(3)]))
    if not np.isfinite(rho): rho = 0.0                       # guard (ii)
    rho = min(max(rho, 0.0), 0.99)
    neff = max(n * (1 - rho) / (1 + rho), 3.0)
    s = np.maximum(sse, 1e-20)                               # guard (i)
    prof = neff * np.log(s / s[i0]); ok = np.where(prof <= 1.0)[0]
    lo, hi = LA[ok.min()], LA[ok.max()]
    ident = (0 < i0 < len(AL) - 1) and (ok.min() > 0) and (ok.max() < len(AL) - 1) and ((hi - lo) <= 0.6)
    rmse = float(np.sqrt(sse[i0] / res.size))
    return dict(lna=float(LA[i0]), lo=float(lo), hi=float(hi), ident=bool(ident), rmse=rmse, rho=rho, neff=float(neff), n=int(n))
