"""Soil properties, cable catalogue, beddings and the transient radial ground model.
Pure Python (no numpy), so it runs where security policies block scientific packages.

    Cv dT/dt = (1/r) d/dr (k r dT/dr) + q

Concentric layers around ONE cable out to R_far = 2 x depth (Kennelly equivalent);
the outer surface is held at the background soil temperature at cable depth.
Finite volumes, backward Euler, linearised I^2 R(T) source, tridiagonal solve.

Arrangements
  single   one cable at the centre.
  trefoil  touching trefoil, equivalent-bundle approximation: the centre cable is
           resolved; the other two cables' losses are injected at the bundle's
           circumscribed radius (2.155 x cable radius). Estimated, not a 2D model.
"""
from __future__ import annotations

import json
import math
from functools import lru_cache
from pathlib import Path

TWO_PI = 2 * math.pi
IN = 0.0254
NAN = float("nan")
DATA = Path(__file__).resolve().parents[1] / "data"

# ------------------------------------------------------------------ soil (Johansen)
K_WATER, K_QUARTZ = 0.594, 7.7
CV_WATER, CV_SOLID = 4.18e6, 2.0e6
NATIVE = dict(name="Native soil (default)", porosity=0.40, dry_density=1550.0, quartz=0.50, coarse=False)
SAND = dict(name="Sand bedding", porosity=0.38, dry_density=1650.0, quartz=0.90, coarse=True)


def k_dry(p):
    rd = p["dry_density"]
    return (0.135 * rd + 64.7) / (2700 - 0.947 * rd)


def k_sat(p):
    k_other = 2.0 if p["quartz"] > 0.2 else 3.0
    k_s = K_QUARTZ ** p["quartz"] * k_other ** (1 - p["quartz"])
    return k_s ** (1 - p["porosity"]) * K_WATER ** p["porosity"]


def conductivity(theta, p=NATIVE):
    sr = min(max(theta / p["porosity"], 1e-4), 1.0)
    ke = (0.7 * math.log10(sr) + 1.0) if p["coarse"] else (math.log10(sr) + 1.0)
    ke = min(max(ke, 0.0), 1.0)
    kd = k_dry(p)
    return kd + ke * (k_sat(p) - kd)


def heat_capacity(theta, p=NATIVE):
    th = min(max(theta, 0.0), p["porosity"])
    return (1 - p["porosity"]) * CV_SOLID + th * CV_WATER


# ------------------------------------------------------------------ Darmstadt measured materials
@lru_cache(maxsize=1)
def darmstadt_materials():
    return json.loads((DATA / "darmstadt" / "materials.json").read_text(encoding="utf-8"))


def curve_k(material_id, theta):
    """Measured dry-out curve k(theta), theta in m3/m3 (linear interpolation)."""
    c = darmstadt_materials()["curves"][material_id]
    x, y = c["theta_pct"], c["k"]
    t = theta * 100
    if t <= x[0]:
        return y[0]
    if t >= x[-1]:
        return y[-1]
    lo, hi = 0, len(x) - 1
    while hi - lo > 1:
        mid = (lo + hi) // 2
        if x[mid] <= t:
            lo = mid
        else:
            hi = mid
    f = (t - x[lo]) / (x[hi] - x[lo]) if x[hi] > x[lo] else 0
    return y[lo] + f * (y[hi] - y[lo])


def curve_cv(material_id, theta):
    p = darmstadt_materials()["props"][material_id]
    n = (p["porosity"] or 40) / 100
    return (1 - n) * (p["cv_solid_20C"] or 2.0e6) + min(max(theta, 0), n) * CV_WATER


# ------------------------------------------------------------------ cables
def _layers_from_catalogue(r):
    mm = lambda k: float(r[k]) / 2000.0
    return [("Cu conductor", mm("conductor_od_mm"), 400.0, 3.45e6, "manufacturer specification"),
            ("EPR insulation + screens", mm("od_over_insulation_mm"), 1 / 3.5, 2.0e6, "manufacturer specification"),
            ("Cu tape shield", mm("od_over_insulation_shield_mm"), 400.0, 3.45e6, "manufacturer specification"),
            ("PVC jacket", mm("overall_od_mm"), 1 / 5.0, 1.7e6, "manufacturer specification")]


@lru_cache(maxsize=1)
def cables():
    out = {}
    cat = json.loads((DATA / "catalogue" / "cables.json").read_text(encoding="utf-8"))
    for r in cat:
        if not r["cable_id"].startswith("SW_"):
            continue
        rac = float(r["ac_resistance_ohm_per_km"]) / 1000
        tref = float(r["ac_resistance_ref_temp_C"])
        size = r["conductor_size_awg_kcmil"]
        unit = "kcmil" if size.isdigit() and int(size) >= 250 else "AWG"
        name = f"Southwire {size} {unit} Cu 15 kV EPR, PVC jacket"
        out[name] = dict(name=name, id=r["cable_id"], layers=_layers_from_catalogue(r),
                         r20=rac / (1 + 0.00393 * (tref - 20)), alpha20=0.00393,
                         t_max=float(r["max_conductor_temp_normal_C"]),
                         t_emergency=float(r["max_conductor_temp_emergency_C"] or 0) or None,
                         source="Southwire SPEC 46319 (catalogue); thermal resistivities N-M Table 6 via Bates 2021",
                         used_in_pipeline=r["used_in_pipeline"] == "True")
    out["Darmstadt MV 150 mm2 Al (NA2XS(F)2Y 1x150)"] = dict(
        name="Darmstadt MV 150 mm2 Al (NA2XS(F)2Y 1x150)", id="DARM_MV150_NA2XS(F)2Y_1x150",
        layers=[("Al conductor", 0.00691, 237.0, 2.42e6, "derived from 150 mm2 area"),
                ("XLPE insulation", 0.00691 + 0.0055, 1 / 3.5, 2.0e6, "experiment documentation"),
                ("Screen / bedding", 0.0145, 1 / 3.5, 2.0e6, "derived (inner radii estimated)"),
                ("PE sheath", 0.017, 1 / 3.5, 2.4e6, "experiment documentation")],
        r20=0.206e-3, alpha20=0.00403, t_max=90.0, t_emergency=None,
        source="Verschaffel-Drefke et al. 2021; cable_params.py (DC resistance used)", used_in_pipeline=True)
    return out


CABLES = cables
DEFAULT_CABLE = "Southwire 350 kcmil Cu 15 kV EPR, PVC jacket"


def resistance(cable, t):
    return cable["r20"] * (1 + cable["alpha20"] * (t - 20.0))


# ------------------------------------------------------------------ beddings
BEDDINGS = {
    "Native soil": dict(kind="native", prov="derived property (Johansen from background moisture)"),
    "Sand (generic)": dict(kind="johansen", params=SAND, prov="derived property (Johansen, generic sand)"),
    "FTB (fluidized thermal backfill)": dict(kind="fixed", k=100 / 60.0, cv=2.0e6, k_dry=100 / 75.0,
                                             prov="utility standard (PG&E EDS 038193: rho <= 60 at 3% MC)"),
    "Darmstadt silt": dict(kind="curve", mat="DARM_SILT", prov="experimental measurement (Darmstadt dry-out curve)"),
    "Darmstadt sand": dict(kind="curve", mat="DARM_SAND", prov="experimental measurement (Darmstadt dry-out curve)"),
    "Darmstadt fluidized backfill": dict(kind="curve", mat="DARM_FBF", prov="experimental measurement (Darmstadt dry-out curve)"),
    "Darmstadt loam": dict(kind="curve", mat="DARM_LOAM", prov="experimental measurement (Darmstadt dry-out curve)"),
}

DUCT_ID, DUCT_OD = 100.6e-3, 114.3e-3     # PG&E EDS 062288: 4 in Sch 40 PVC
K_PVC = 1 / 4.8
TREFOIL_R = 1 + 2 / math.sqrt(3)          # circumscribed radius / cable radius


def duct_air_k(r_out, t_mean=60.0):
    de_mm = r_out * 2000
    T = 5.2 / (1 + 0.1 * (1.4 + 0.011 * t_mean) * de_mm)
    return math.log((DUCT_ID / 2) / r_out) / (TWO_PI * T)


# ------------------------------------------------------------------ mesh
class Mesh:
    def __init__(self, cable, depth_m, in_duct, bedding, bedding_radius=0.15, arrangement="single",
                 uniform=False, theta_bed=None):
        rin, rout, reg, kf, cvf = [], [], [], [], []

        def add(r0, r1, n, region, k, cv, geo=False):
            if r1 <= r0:
                return
            e = ([r0 * (r1 / r0) ** (q / n) for q in range(n + 1)] if geo and r0 > 0
                 else [r0 + (r1 - r0) * q / n for q in range(n + 1)])
            for q in range(n):
                rin.append(e[q]); rout.append(e[q + 1]); reg.append(region); kf.append(k); cvf.append(cv)

        r = 0.0
        for j, (name, ro, k, cv, _p) in enumerate(cable["layers"]):
            add(r, ro, 3 if j == 0 else 4, "conductor" if j == 0 else name, k, cv)
            r = ro
        self.r_cable = r
        self.i_surface = len(rin) - 1
        self.arrangement = arrangement
        self.n_cables = 3 if arrangement == "trefoil" else 1
        self.r_bundle = r * TREFOIL_R if arrangement == "trefoil" else r
        bed = BEDDINGS[bedding]
        if in_duct:
            if self.r_bundle >= DUCT_ID / 2:
                raise ValueError("Cable bundle does not fit in a 4 in duct.")
            add(r, DUCT_ID / 2, 4, "air gap (duct)", duct_air_k(self.r_bundle), 1.2e3)
            add(DUCT_ID / 2, DUCT_OD / 2, 2, "PVC duct", K_PVC, 1.7e6)
            r = DUCT_OD / 2
        self.r_far = 2 * depth_m
        r_bed = (self.r_far * 0.999) if uniform else max(bedding_radius, r + 0.01)
        add(r, r_bed, 40 if uniform else 14, "bedding", None, None, geo=True)
        self.i_bed_end = len(rin) - 1
        add(r_bed, self.r_far, 1 if uniform else 30, "native soil", None, None, geo=True)

        self.n = len(rin)
        self.r_in, self.r_out, self.region, self.k_fixed, self.cv_fixed = rin, rout, reg, kf, cvf
        self.rc = [ro / 2 if ri == 0 else math.sqrt(ri * ro) for ri, ro in zip(rin, rout)]
        self.area = [math.pi * (ro * ro - ri * ri) for ri, ro in zip(rin, rout)]
        self.cond = [k for k, g in enumerate(reg) if g == "conductor"]
        a = sum(self.area[k] for k in self.cond)
        self.a_cond = {k: self.area[k] / a for k in self.cond}
        self.nat = [g == "native soil" for g in reg]
        self.bed = [g == "bedding" for g in reg]
        self.bedding, self.uniform, self.theta_bed = bedding, uniform, theta_bed
        self.depth, self.in_duct, self.r_bed = depth_m, in_duct, r_bed
        # cell that receives the other cables' losses (trefoil)
        self.i_inject = None
        if self.n_cables > 1:
            self.i_inject = next(i for i in range(self.n) if self.r_out[i] >= self.r_bundle)
        self.lnL = [math.log(self.r_out[i] / self.rc[i]) for i in range(self.n - 1)]
        self.lnR = [math.log(self.rc[i + 1] / self.r_out[i]) for i in range(self.n - 1)]
        self.lnBC = math.log(self.r_far / self.rc[-1])


def bed_props(mesh, theta):
    bed = BEDDINGS[mesh.bedding]
    th = mesh.theta_bed if mesh.theta_bed is not None else theta
    if bed["kind"] == "native":
        return conductivity(th), heat_capacity(th), k_dry(NATIVE)
    if bed["kind"] == "johansen":
        t = min(th, bed["params"]["porosity"])
        return conductivity(t, bed["params"]), heat_capacity(t, bed["params"]), k_dry(bed["params"])
    if bed["kind"] == "curve":
        return curve_k(bed["mat"], th), curve_cv(bed["mat"], th), curve_k(bed["mat"], 0.0)
    return bed["k"], bed["cv"], bed["k_dry"]


def cell_props(mesh, theta, T, drying, t_crit):
    kn, cn = conductivity(theta), heat_capacity(theta)
    kb, cb, kdb = bed_props(mesh, theta)
    if mesh.uniform:
        kn, cn = kb, cb
    kdn = kdb if mesh.uniform else k_dry(NATIVE)
    k, cv = [], []
    dry_r = 0.0
    for i in range(mesh.n):
        if mesh.nat[i] or mesh.bed[i]:
            nat = mesh.nat[i]
            ki, ci = (kn, cn) if nat else (kb, cb)
            if drying and T is not None and T[i] > t_crit:
                ki = kdn if nat else kdb
                dry_r = mesh.r_out[i]
        else:
            ki, ci = mesh.k_fixed[i], mesh.cv_fixed[i]
        k.append(ki); cv.append(ci)
    return k, cv, (kb if mesh.uniform else kn), dry_r


def simulate(cable, mesh, t_bg, theta_bg, current, T0=None, dt=900.0, drying=False, t_crit=50.0,
             keep_profiles=False):
    """Hourly piecewise-constant forcing. Returns dict of hourly lists + final state."""
    n = mesh.n
    nh = len(t_bg)
    T = [t_bg[0]] * n if T0 is None else list(T0)
    sub = max(1, int(round(3600 / dt)))
    r20, a20 = cable["r20"], cable["alpha20"]
    extra = mesh.n_cables - 1
    out = {k: [] for k in ("tc", "ts", "tb", "qs", "ql", "kn", "stored", "dry_r")}
    profiles = [] if keep_profiles else None
    for h in range(nh):
        k, cv, kn, dry_r = cell_props(mesh, theta_bg[h], T, drying, t_crit)
        G = [TWO_PI / (mesh.lnL[i] / k[i] + mesh.lnR[i] / k[i + 1]) for i in range(n - 1)]
        Gbc = TWO_PI * k[-1] / mesh.lnBC
        C = [cv[i] * mesh.area[i] / dt for i in range(n)]
        I2 = current[h] ** 2
        diag = list(C)
        for i in range(n - 1):
            diag[i] += G[i]
            diag[i + 1] += G[i]
        diag[-1] += Gbc
        q0 = {}
        for i in mesh.cond:
            diag[i] -= I2 * r20 * a20 * mesh.a_cond[i]
            q0[i] = I2 * r20 * (1 - 20 * a20) * mesh.a_cond[i]
        b = [0.0] * n
        w = [0.0] * n
        b[0] = diag[0]
        for i in range(1, n):
            w[i] = -G[i - 1] / b[i - 1]
            b[i] = diag[i] + w[i] * G[i - 1]
        runaway = False
        for _ in range(sub):
            d = [C[i] * T[i] for i in range(n)]
            for i in mesh.cond:
                d[i] += q0[i]
            if extra:   # other trefoil cables: same current, same conductor temperature assumed
                tc_now = sum(T[i] for i in mesh.cond) / len(mesh.cond)
                d[mesh.i_inject] += extra * I2 * resistance(cable, tc_now)
            d[-1] += Gbc * t_bg[h]
            for i in range(1, n):
                d[i] -= w[i] * d[i - 1]
            x = [0.0] * n
            x[-1] = d[-1] / b[-1]
            for i in range(n - 2, -1, -1):
                x[i] = (d[i] + G[i] * x[i + 1]) / b[i]
            T = x
            if T[0] != T[0] or T[0] > 1000 or T[0] < -100:
                runaway = True
                break
        if runaway:
            rem = nh - h
            for key in ("tc", "ts", "tb"):
                out[key] += [math.inf] * rem
            for key in ("qs", "ql", "stored", "dry_r"):
                out[key] += [NAN] * rem
            out["kn"] += [kn] * rem
            return dict(out, state=None, profiles=profiles)
        tc = sum(T[i] for i in mesh.cond) / len(mesh.cond)
        out["tc"].append(tc)
        out["ts"].append(T[mesh.i_surface])
        out["tb"].append(T[mesh.i_bed_end])
        out["qs"].append(G[mesh.i_surface] * (T[mesh.i_surface] - T[mesh.i_surface + 1]))
        out["ql"].append(mesh.n_cables * I2 * resistance(cable, tc))
        out["kn"].append(kn)
        out["stored"].append(sum(cv[i] * mesh.area[i] * (T[i] - t_bg[h]) for i in range(mesh.i_bed_end + 1)))
        out["dry_r"].append(dry_r)
        if keep_profiles:
            profiles.append([round(v, 3) for v in T])
    return dict(out, state=T, profiles=profiles)


def steady_rth(mesh, theta):
    """Conductor-to-background thermal resistance (K.m/W per cable), no drying."""
    k, _, _, _ = cell_props(mesh, theta, None, False, 0)
    R = 0.0
    for i in range(mesh.n):
        if i in mesh.a_cond:
            continue
        mult = mesh.n_cables if mesh.r_in[i] >= mesh.r_bundle - 1e-12 else 1
        R += mult * math.log(mesh.r_out[i] / mesh.r_in[i]) / (TWO_PI * k[i])
    return R


def steady_ampacity(cable, mesh, t_bg, theta, t_max=None):
    t_max = t_max or cable["t_max"]
    R = steady_rth(mesh, theta)
    return math.sqrt(max(t_max - t_bg, 0) / (resistance(cable, t_max) * R))
