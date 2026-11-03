import os as _o, sys as _s
_p = _o.path.dirname(_o.path.abspath(__file__))
while not _o.path.exists(_o.path.join(_p, 'src', 'config.py')): _p = _o.path.dirname(_p)
_s.path.insert(0, _o.path.join(_p, 'src'))
from config import WS_ROOT  # PATH-PATCH: was an absolute path to the original working directory
"""Layered-solver verification against the criteria frozen in phase3/layered_spec_frozen.md (written before this ran).
Log: the first run of this script had a sign error in the PHASE comparison (analytic phase vs fitted phase); the criteria themselves were not changed.
Criteria 2 and 3 are evaluated at the base resolution (38 intervals, 3600 s) AND at a refined resolution (76 intervals, 900 s); the generator resolution used later is chosen from these
verification results only (before any contrast is computed)."""
import sys, io, numpy as np
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, WS_ROOT)
from heatsolver import simulate, make_grid, sample
from layeredsolver import simulate_layered, element_properties
OUT = []; STATUS = {}
def say(s): OUT.append(s); print(s)
def check(key, name, ok, detail=''):
    STATUS[key] = bool(ok); say(f'[{"PASS" if ok else "FAIL"}] {name} {detail}')
P = 86400.0; w = 2 * np.pi / P

def fit_amp_phase(y, t):
    X = np.vstack([np.cos(w * t), np.sin(w * t), np.ones_like(t)]).T; c, *_ = np.linalg.lstsq(X, y, rcond=None); return np.hypot(c[0], c[1]), np.arctan2(c[1], c[0])
def phase_err_h(pn, pe):   # numerical y = A cos(wt - pn); analytic Re[phi e^{iwt}] = |phi| cos(wt + pe)  -> pn should equal -pe
    return ((pn + pe + np.pi) % (2 * np.pi) - np.pi) / w / 3600.0
def two_layer_exact(k1, C1, k2, C2, zi, z0, z1, phi0, phi1):
    s1 = np.sqrt(1j * w * C1 / k1); s2 = np.sqrt(1j * w * C2 / k2)
    M = np.zeros((4, 4), complex); r = np.zeros(4, complex)
    M[0, 0] = np.exp(s1 * z0); M[0, 1] = np.exp(-s1 * z0); r[0] = phi0
    M[1, 2] = np.exp(s2 * z1); M[1, 3] = np.exp(-s2 * z1); r[1] = phi1
    M[2, 0] = np.exp(s1 * zi); M[2, 1] = np.exp(-s1 * zi); M[2, 2] = -np.exp(s2 * zi); M[2, 3] = -np.exp(-s2 * zi)
    M[3, 0] = k1 * s1 * np.exp(s1 * zi); M[3, 1] = -k1 * s1 * np.exp(-s1 * zi); M[3, 2] = -k2 * s2 * np.exp(s2 * zi); M[3, 3] = k2 * s2 * np.exp(-s2 * zi)
    A1, B1, A2, B2 = np.linalg.solve(M, r)
    def phi(zz):
        zz = np.asarray(zz, float); return np.where(zz <= zi, A1 * np.exp(s1 * zz) + B1 * np.exp(-s1 * zz), A2 * np.exp(s2 * zz) + B2 * np.exp(-s2 * zz))
    def dphi(zz):
        zz = np.asarray(zz, float); return np.where(zz <= zi, s1 * (A1 * np.exp(s1 * zz) - B1 * np.exp(-s1 * zz)), s2 * (A2 * np.exp(s2 * zz) - B2 * np.exp(-s2 * zz)))
    return phi, dphi
def run_periodic(k1, C1, k2, C2, zi, nint, dt, ndays=14, A=8.0):
    z, dz = make_grid(0.05, 1.0, nint); ns = int(ndays * 86400 / dt) + 1; t = np.arange(ns) * dt
    phi, dphi = two_layer_exact(k1, C1, k2, C2, zi, 0.05, 1.0, A + 0j, 0.02 * A * np.exp(-1j * np.pi / 3))
    top = np.real(phi(0.05) * np.exp(1j * w * t)); bot = np.real(phi(1.0) * np.exp(1j * w * t)); T0 = np.real(phi(z))
    sim, ke, Ce = simulate_layered(z, [zi], [k1, k2], [C1, C2], top, bot, T0, dt)
    return z, dz, t, sim, ke, phi, dphi, A

# ---- 1. uniform limit equals existing solver
rng = np.random.default_rng(1); z, dz = make_grid(0.05, 1.0, 38); n = 24 * 20; tt = np.arange(n) * 3600.0
top = 15 + 6 * np.sin(w * tt) + np.cumsum(rng.normal(0, 0.05, n)); bot = 12 + 0.002 * np.arange(n) / 24 + rng.normal(0, 0.01, n).cumsum() * 0.1
T0 = 14 + 3 * np.exp(-(z - 0.05) / 0.3); mx = 0.0
for alpha in (2e-7, 4.8e-7, 2e-6):
    C = 2.5e6; k = alpha * C
    a = simulate(alpha, top, bot, z, T0); b, _, _ = simulate_layered(z, [], [k], [C], top, bot, T0); b3, _, _ = simulate_layered(z, [0.2, 0.5], [k] * 3, [C] * 3, top, bot, T0)
    mx = max(mx, float(np.abs(a - b).max()), float(np.abs(a - b3).max()))
check('c1', '1. uniform limit equals heatsolver (also as 3 identical layers)', mx <= 1e-8, f'max abs difference {mx:.2e} C (limit 1e-8)')

RES = {'base (38 intervals, 3600 s)': (38, 3600.0), 'refined (76 intervals, 900 s)': (76, 900.0)}
k1, C1 = 1.2, 2.5e6
for rname, (nint, dt) in RES.items():
    key = 'base' if nint == 38 else 'refined'
    say(f'\n--- criteria 2 and 3 at {rname}')
    ok2 = True; rows = []
    for alpha in (2e-7, 5e-7, 1e-6, 2e-6):
        C = 2.5e6; k = alpha * C
        z, dz, t, sim, ke, phi, dphi, A = run_periodic(k, C, k, C, 0.22, nint, dt); sel = t >= 8 * 86400.0
        for zz in (0.10, 0.20, 0.50):
            idx = int(np.argmin(np.abs(z - zz))); zn = z[idx]; ae, pe = abs(phi(zn)), np.angle(phi(zn))
            if ae < 0.01 * A: continue
            an, pn = fit_amp_phase(sim[:, idx][sel], t[sel]); aerr = 100 * (an / ae - 1); perr = phase_err_h(pn, pe); rows.append((alpha, zn, aerr, perr)); ok2 &= (abs(aerr) <= 3.0 and abs(perr) <= 0.3)
    say('   uniform periodic: ' + '; '.join(f'a={a:.0e} z={zz:.2f} amp {ae:+.2f}% ph {pe:+.3f} h' for a, zz, ae, pe in rows))
    check('c2_' + key, f'2. uniform periodic, amplitude <= 3%, phase <= 0.3 h [{rname}]', ok2)
    ok3 = True; ok3f = True
    for rk in (0.5, 2.0):
        for rC in (0.5, 2.0):
            z, dz, t, sim, ke, phi, dphi, A = run_periodic(k1, C1, rk * k1, rC * C1, 0.22, nint, dt); sel = t >= 8 * 86400.0; worst_a = 0.0; worst_p = 0.0; worst_depth = None
            for zz in (0.10, 0.20, 0.30, 0.40, 0.50):
                idx = int(np.argmin(np.abs(z - zz))); zn = z[idx]; ae, pe = abs(phi(zn)), np.angle(phi(zn))
                if ae < 0.01 * A: continue
                an, pn = fit_amp_phase(sim[:, idx][sel], t[sel]); ea = abs(100 * (an / ae - 1))
                if ea > worst_a: worst_a, worst_depth = ea, (zn, ae / A)
                worst_p = max(worst_p, abs(phase_err_h(pn, pe)))
            ie = int(np.searchsorted(z, 0.22)) - 1; fl_err = 0.0; fmax = 0.0
            for e in range(max(ie - 2, 0), min(ie + 3, len(z) - 1)):
                zm = 0.5 * (z[e] + z[e + 1]); flux_t = ke[e] * (sim[:, e + 1] - sim[:, e]) / dz; fa, _ = fit_amp_phase(flux_t[sel], t[sel])
                fex = abs((k1 if zm <= 0.22 else rk * k1) * dphi(zm)); fmax = max(fmax, fex); fl_err = max(fl_err, abs(fa - fex))
            rel = 100 * fl_err / fmax; ok3 &= (worst_a <= 3.0 and worst_p <= 0.3); ok3f &= (rel <= 3.0)
            say(f'   k2/k1={rk}, C2/C1={rC} (alpha2/alpha1 = {rk / rC:.2f}): worst amplitude error {worst_a:.2f}% at z={worst_depth[0]:.2f} m (relative amplitude {worst_depth[1]:.3f}), worst phase error {worst_p:.3f} h, interface flux error {rel:.2f}%')
    check('c3_' + key, f'3. two-layer periodic, interface between nodes, amplitude <= 3%, phase <= 0.3 h [{rname}]', ok3)
    check('c3f_' + key, f'3b. interface flux within 3% of analytic [{rname}]', ok3f)

# ---- 4. steady state
z, dz = make_grid(0.05, 1.0, 38); kl = [1.0, 2.0, 0.7]; Cl = [2.0e6, 2.5e6, 3.0e6]; ifc = [0.2, 0.5]
sim, ke, Ce = simulate_layered(z, ifc, kl, Cl, np.full(3000, 10.0), np.full(3000, 20.0), np.linspace(10, 20, len(z)), 86400.0)
fl = ke * (sim[-1, 1:] - sim[-1, :-1]) / dz; spread = float((fl.max() - fl.min()) / abs(fl.mean()))
res = (0.2 - 0.05) / 1.0 + (0.5 - 0.2) / 2.0 + (1.0 - 0.5) / 0.7; qex = 10.0 / res
def exact_profile(x):
    R = (x - 0.05) / 1.0 if x <= 0.2 else ((0.2 - 0.05) / 1.0 + (x - 0.2) / 2.0 if x <= 0.5 else (0.2 - 0.05) / 1.0 + (0.5 - 0.2) / 2.0 + (x - 0.5) / 0.7)
    return 10 + qex * R
err = max(abs(sim[-1, i] - exact_profile(z[i])) for i in range(len(z)))
check('c4', '4. steady state: element-flux spread <= 1e-6 and profile matches the piecewise-linear exact solution', spread <= 1e-6 and err <= 1e-6, f'(flux spread {spread:.2e}, max profile error {err:.2e} C)')

# ---- 5. convergence (k2/k1 = 0.5, C2/C1 = 2, the hardest case above)
def err_measure(nint, dt):
    z, dz, t, sim, ke, phi, dphi, A = run_periodic(k1, C1, 0.5 * k1, 2.0 * C1, 0.22, nint, dt, ndays=12); sel = t >= 8 * 86400.0; tt = t[sel]; e2 = []
    for zz in np.arange(0.10, 0.55, 0.05):
        idx = int(np.argmin(np.abs(z - zz))); zn = z[idx]; ex = np.real(phi(zn) * np.exp(1j * w * tt)); e2.append(np.sqrt(np.mean((sim[:, idx][sel] - ex) ** 2)))
    return float(np.mean(e2))
em = {(n_, d_): err_measure(n_, d_) for n_, d_ in [(38, 3600.0), (76, 3600.0), (38, 900.0), (76, 900.0), (152, 900.0)]}
say('\n5. RMS error vs analytic (C): ' + '; '.join(f'(nint {a_}, dt {b_:.0f} s) {v:.4f}' for (a_, b_), v in em.items()))
check('c5', '5. convergence: error at (76, 900 s) <= error at (38, 3600 s)', em[(76, 900.0)] <= em[(38, 3600.0)])
say(f'numerical error floor: RMS {em[(38, 3600.0)]:.3f} C (base) and {em[(76, 900.0)]:.3f} C (refined) against the analytic two-layer solution (24 h amplitude 8 C at the top)')

basic_ok = STATUS['c1'] and STATUS['c4'] and STATUS['c5']
refined_ok = STATUS['c2_refined'] and STATUS['c3_refined'] and STATUS['c3f_refined']; base_ok = STATUS['c2_base'] and STATUS['c3_base'] and STATUS['c3f_base']
gen = 'base' if (basic_ok and base_ok) else ('refined' if (basic_ok and refined_ok) else 'NONE')
say(f'\nCRITERIA PASSED AT: base={base_ok}, refined={refined_ok}, basic checks (1, 4, 5)={basic_ok}')
say(f'GENERATOR RESOLUTION SELECTED BY VERIFICATION: {gen}' + ('  -> task must STOP' if gen == 'NONE' else ''))
open((WS_ROOT + r'\phase3\layered_verification_out.txt'), 'w', encoding='utf-8').write('\n'.join(OUT))
