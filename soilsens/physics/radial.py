"""Transient radial heat conduction around one buried cable.

    Cv dT/dt = (1/r) d/dr (k r dT/dr) + q        (slide 11, radial form)

Geometry: concentric layers  conductor | insulation | ... | [air gap | PVC duct] |
bedding | native soil, out to R_far = 2 * depth.  The outer surface is held at the
*background* soil temperature at cable depth (from the forecast).

Why R_far = 2h: the steady thermal resistance of a cylinder of radius r buried at
depth h under an isothermal surface (Kennelly) is  rho/(2 pi) * ln(2h/r)  for h >> r,
which equals the resistance of a soil annulus from r to 2h. So the steady state is
exact in that limit; the transient response is an approximation (labelled
"equivalent radial" in the UI). The 2D cross-section model is Phase 2 work.

Numerics: finite volumes, backward Euler, linearised I^2 R(T) source, banded solve.
Background ground is never overwritten: it only enters through the outer boundary
and the initial state (slide 11).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
try:  # scipy is faster, but some Windows policies block its DLLs
    from scipy.linalg import solve_banded as _solve_banded
except Exception:  # pragma: no cover
    _solve_banded = None


def solve_banded(lu, ab, rhs, check_finite=False):
    """Tridiagonal solve; uses scipy if available, else the Thomas algorithm."""
    if _solve_banded is not None:
        return _solve_banded(lu, ab, rhs, check_finite=check_finite)
    a, b, c = ab[2, :-1], ab[1].copy(), ab[0, 1:]   # sub, diag, super
    d = rhs.astype(float).copy()
    n = len(d)
    for i in range(1, n):
        w = a[i - 1] / b[i - 1]
        b[i] -= w * c[i - 1]
        d[i] -= w * d[i - 1]
    x = np.empty(n)
    x[-1] = d[-1] / b[-1]
    for i in range(n - 2, -1, -1):
        x[i] = (d[i] - c[i] * x[i + 1]) / b[i]
    return x

from . import soil
from .cable import Cable, Installation, BEDDINGS, DUCT_ID, DUCT_OD, K_PVC, duct_air_k

TWO_PI = 2 * np.pi


@dataclass
class Mesh:
    r_in: np.ndarray
    r_out: np.ndarray
    region: np.ndarray        # str labels
    k_fixed: np.ndarray       # nan where k depends on moisture
    cv_fixed: np.ndarray
    r_far: float
    i_surface: int            # last cell of the cable itself
    i_bedding_end: int        # last bedding cell

    @property
    def rc(self):
        rc = np.sqrt(np.maximum(self.r_in, 1e-12) * self.r_out)
        rc[self.r_in == 0] = self.r_out[self.r_in == 0] / 2
        return rc

    @property
    def area(self):
        return np.pi * (self.r_out ** 2 - self.r_in ** 2)


def _split(r0, r1, n, geometric=False):
    if geometric and r0 > 0:
        e = np.geomspace(r0, r1, n + 1)
    else:
        e = np.linspace(r0, r1, n + 1)
    return e[:-1], e[1:]


def build_mesh(cable: Cable, inst: Installation) -> Mesh:
    rin, rout, reg, kf, cvf = [], [], [], [], []

    def add(r0, r1, n, region, k, cv, geo=False):
        a, b = _split(r0, r1, n, geo)
        rin.extend(a); rout.extend(b); reg.extend([region] * n)
        kf.extend([k] * n); cvf.extend([cv] * n)

    r = 0.0
    for j, L in enumerate(cable.layers):
        add(r, L.r_out, 3 if j == 0 else 4, "conductor" if j == 0 else L.name, L.k, L.cv)
        r = L.r_out
    i_surface = len(rin) - 1

    if inst.in_duct:
        add(r, DUCT_ID / 2, 3, "air gap (duct)", duct_air_k(cable), 1.2e3)
        add(DUCT_ID / 2, DUCT_OD / 2, 2, "PVC duct", K_PVC, 1.7e6)
        r = DUCT_OD / 2

    bed = BEDDINGS[inst.bedding]
    r_bed = max(inst.bedding_radius_m, r + 0.01)
    add(r, r_bed, 12, "bedding", bed.k_fixed if bed.kind == "fixed" else np.nan,
        bed.cv_fixed if bed.kind == "fixed" else np.nan, geo=True)
    i_bed_end = len(rin) - 1

    r_far = 2 * inst.depth_m
    add(r_bed, r_far, 30, "native soil", np.nan, np.nan, geo=True)

    return Mesh(np.array(rin), np.array(rout), np.array(reg), np.array(kf, float),
                np.array(cvf, float), r_far, i_surface, i_bed_end)


def cell_properties(mesh: Mesh, inst: Installation, theta_bg: float, T: np.ndarray | None,
                    drying: bool, t_crit: float):
    """k and Cv per cell for the current background moisture (and local drying)."""
    k = mesh.k_fixed.copy()
    cv = mesh.cv_fixed.copy()
    bed = BEDDINGS[inst.bedding]
    nat = (mesh.region == "native soil")
    bd = (mesh.region == "bedding")
    k[nat] = soil.conductivity(theta_bg, soil.DEFAULT_NATIVE)
    cv[nat] = soil.heat_capacity(theta_bg, soil.DEFAULT_NATIVE)
    if bed.kind == "native":
        k[bd], cv[bd] = k[nat][0], cv[nat][0]
    elif bed.kind == "johansen":
        th = min(theta_bg, bed.params.porosity)
        k[bd] = soil.conductivity(th, bed.params)
        cv[bd] = soil.heat_capacity(th, bed.params)
    if drying and T is not None:
        # Reduced moisture rule (scenario): soil above the critical temperature dries
        # out to its dry conductivity. Not a moisture-transport model.
        hot = (T > t_crit) & (bd | nat)
        kd_nat = soil.k_dry(soil.DEFAULT_NATIVE)
        if bed.kind == "fixed":
            kd_bed = bed.k_dry
        elif bed.kind == "johansen":
            kd_bed = soil.k_dry(bed.params)
        else:
            kd_bed = kd_nat
        k[hot & nat] = kd_nat
        k[hot & bd] = kd_bed
    return k, cv


def _conductances(mesh: Mesh, k: np.ndarray):
    """Face conductances G[i] between cell i and i+1 (W/m/K per metre), and to boundary."""
    rc, ro = mesh.rc, mesh.r_out
    R_left = np.log(ro[:-1] / rc[:-1]) / (TWO_PI * k[:-1])
    R_right = np.log(rc[1:] / ro[:-1]) / (TWO_PI * k[1:])
    G = 1.0 / (R_left + R_right)
    G_bc = TWO_PI * k[-1] / np.log(mesh.r_far / rc[-1])
    return G, G_bc


@dataclass
class SimResult:
    t_conductor: np.ndarray      # (n_h,) end-of-hour, degC
    t_surface: np.ndarray        # cable outer surface
    t_bedding_edge: np.ndarray   # edge of bedding zone
    q_surface: np.ndarray        # heat leaving cable surface, W/m
    q_loss: np.ndarray           # I^2 R(T) generated, W/m
    final_state: np.ndarray
    k_native: np.ndarray         # native k used each hour


def simulate(cable: Cable, inst: Installation, t_bg, theta_bg, current, T0=None,
             dt=600.0, drying=False, t_crit=50.0, mesh: Mesh | None = None) -> SimResult:
    """Hourly forcing (piecewise constant). Returns end-of-hour diagnostics."""
    mesh = mesh or build_mesh(cable, inst)
    n = len(mesh.r_in)
    t_bg, theta_bg, current = map(lambda a: np.asarray(a, float), (t_bg, theta_bg, current))
    nh = len(t_bg)
    T = np.full(n, t_bg[0]) if T0 is None else T0.copy()
    cond = mesh.region == "conductor"
    a_cond = mesh.area[cond] / mesh.area[cond].sum()
    sub = int(round(3600 / dt))
    out = {k: np.empty(nh) for k in ("tc", "ts", "tb", "qs", "ql", "kn")}
    ab = np.zeros((3, n))
    for h in range(nh):
        k, cv = cell_properties(mesh, inst, theta_bg[h], T, drying, t_crit)
        G, G_bc = _conductances(mesh, k)
        C = cv * mesh.area / dt
        I2 = current[h] ** 2
        # q = I2 * r20 * (1 + a (T-20)) = q0 + q1 * T   (per conductor cell, area-weighted)
        q1 = I2 * cable.r20 * cable.alpha20 * a_cond
        q0 = I2 * cable.r20 * (1 - 20 * cable.alpha20) * a_cond
        diag = C.copy()
        diag[:-1] += G
        diag[1:] += G
        diag[-1] += G_bc
        diag[cond] -= q1
        ab[0, 1:] = -G
        ab[1, :] = diag
        ab[2, :-1] = -G
        runaway = False
        for _ in range(sub):
            rhs = C * T
            rhs[cond] += q0
            rhs[-1] += G_bc * t_bg[h]
            T = solve_banded((1, 1), ab, rhs, check_finite=False)
            if not np.isfinite(T).all() or T.max() > 1000 or T.min() < -100:
                runaway = True   # thermal runaway: current far above any rating
                break
        if runaway:
            for key in out:
                out[key][h:] = np.inf if key in ("tc", "ts", "tb") else np.nan
            T = np.full(n, np.inf)
            break
        tc = T[cond].mean()
        out["tc"][h] = tc
        out["ts"][h] = T[mesh.i_surface]
        out["tb"][h] = T[mesh.i_bedding_end]
        out["qs"][h] = G[mesh.i_surface] * (T[mesh.i_surface] - T[mesh.i_surface + 1])
        out["ql"][h] = I2 * cable.resistance(tc)
        out["kn"][h] = k[mesh.region == "native soil"][0]
    return SimResult(out["tc"], out["ts"], out["tb"], out["qs"], out["ql"], T, out["kn"])


def steady_rth(cable: Cable, inst: Installation, theta_bg: float) -> float:
    """Total thermal resistance conductor -> background (K.m/W), no drying."""
    mesh = build_mesh(cable, inst)
    k, _ = cell_properties(mesh, inst, theta_bg, None, False, 0)
    cond = mesh.region == "conductor"
    # series resistance from the conductor's outer radius outward
    R = 0.0
    for i in np.where(~cond)[0]:
        R += np.log(mesh.r_out[i] / mesh.r_in[i]) / (TWO_PI * k[i])
    R += 0.0  # last cell ends at its r_out; add remainder to r_far
    R += np.log(mesh.r_far / mesh.r_out[-1]) / (TWO_PI * k[-1]) if mesh.r_out[-1] < mesh.r_far else 0
    return R


def steady_ampacity(cable: Cable, inst: Installation, t_bg: float, theta_bg: float) -> float:
    """Analytic steady-state current with R(T_max): I = sqrt((Tmax - Tbg) / (R(Tmax) Rth))."""
    R = steady_rth(cable, inst, theta_bg)
    return float(np.sqrt((cable.t_max - t_bg) / (cable.resistance(cable.t_max) * R)))
