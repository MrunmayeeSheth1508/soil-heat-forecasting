"""Solver verification (pre-registered, run BEFORE any event data is used).
Semi-infinite medium with periodic surface: T = A exp(-z/d) cos(w t - z/d), d = sqrt(2 alpha / w).
Boundaries and initial condition are taken from the analytic solution at 5 and 100 cm; the interior is compared at 10, 20, 50 cm.
Also: grid/time-step refinement. Acceptance (pre-registered): amplitude error <= 3%, phase error <= 0.3 h at 24 h period for alpha 2e-7..2e-6."""
import sys, io, numpy as np
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, r'C:\Users\jtani\.gemini\antigravity\scratch\soil')
from heatsolver import simulate, make_grid, sample
P = 24 * 3600.0; w = 2 * np.pi / P; A = 8.0
def exact(zz, t, alpha):
    d = np.sqrt(2 * alpha / w); return A * np.exp(-zz / d) * np.cos(w * t - zz / d)
def run(alpha, nint, dt, ndays=12):
    z, dz = make_grid(0.05, 1.0, nint); ns = int(ndays * 86400 / dt) + 1; t = np.arange(ns) * dt
    sim = simulate(alpha, exact(0.05, t, alpha), exact(1.0, t, alpha), z, exact(z, 0.0, alpha), dt)
    return z, t, sim
def fit_amp_phase(y, t):
    X = np.vstack([np.cos(w * t), np.sin(w * t), np.ones_like(t)]).T; c, *_ = np.linalg.lstsq(X, y, rcond=None)
    return np.hypot(c[0], c[1]), np.arctan2(c[1], c[0])
rows = []; ok = True
print('alpha      depth  amp_exact amp_num  amp_err%  phase_err_h')
for alpha in (2e-7, 5e-7, 1e-6, 2e-6):
    z, t, sim = run(alpha, 38, 3600.0)
    sel = t >= 6 * 86400.0
    for zz in (0.10, 0.20, 0.50):
        yn = sample(sim, z, [zz])[:, 0][sel]; ye = exact(zz, t[sel], alpha)
        an, pn = fit_amp_phase(yn, t[sel]); ae, pe = fit_amp_phase(ye, t[sel])
        if ae < 0.01 * A: print(f'{alpha:.0e}  {zz*100:4.0f}  amplitude {ae:.3g} < 1% of surface: skipped'); continue
        aerr = 100 * (an / ae - 1); perr = ((pn - pe + np.pi) % (2 * np.pi) - np.pi) / w / 3600.0
        print(f'{alpha:.0e}  {zz*100:4.0f}  {ae:8.4f} {an:8.4f} {aerr:8.2f}  {perr:8.3f}')
        ok &= (abs(aerr) <= 3.0 and abs(perr) <= 0.3)
print('\nRefinement (alpha 1e-6): amplitude at 20 cm for (nint, dt)')
for nint, dt in [(38, 3600.0), (76, 3600.0), (38, 900.0), (76, 900.0)]:
    z, t, sim = run(1e-6, nint, dt); sel = t >= 6 * 86400.0
    an, pn = fit_amp_phase(sample(sim, z, [0.2])[:, 0][sel], t[sel]); print(f'  nint {nint:3d} dt {dt:6.0f}s amp {an:.4f} phase {pn:.4f}')
print('\nACCEPTANCE (amp err <= 3%, phase err <= 0.3 h):', 'PASS' if ok else 'FAIL')
