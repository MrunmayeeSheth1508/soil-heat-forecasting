"""Installation presets, the forecast-informed assessment, 2D field, comparisons and saved runs."""
from __future__ import annotations

import json
import math
import time
from datetime import datetime
from functools import lru_cache

from . import core, physics as ph

VERSION = "SoilSens Lite 3.0"
RUNS = core.ROOT / "runs"


# ------------------------------------------------------------------ installation presets
@lru_cache(maxsize=1)
def _ref():
    return {r["installation_id"]: r for r in json.loads(
        (core.DATA / "catalogue" / "reference_installations.json").read_text(encoding="utf-8"))}


def presets():
    r = _ref()
    sw = ph.DEFAULT_CABLE
    return {
        "PGE_30IN": dict(label="PG&E primary, 30 in cover, 4 in PVC conduit, FTB", cable=sw, arrangement="single",
                         depth_m=float(r["REF_DEPTH_30IN"]["cable_centre_depth_m"]), in_duct=True,
                         bedding="FTB (fluidized thermal backfill)", bedding_radius_m=0.15,
                         depth_ref="PG&E EDS 038193: 30 in (0.762 m) minimum cover to conduit top + conduit radius = 0.819 m to cable centre",
                         status="reference scenario (selected; not a measured installation)"),
        "PGE_24IN": dict(label="PG&E secondary, 24 in cover, 4 in PVC conduit, FTB", cable=sw, arrangement="single",
                         depth_m=float(r["REF_DEPTH_24IN"]["cable_centre_depth_m"]), in_duct=True,
                         bedding="FTB (fluidized thermal backfill)", bedding_radius_m=0.15,
                         depth_ref="PG&E EDS 038193: 24 in (0.610 m) minimum cover + conduit radius = 0.667 m to cable centre",
                         status="reference scenario (selected; not a measured installation)"),
        "SCN_36IN": dict(label="36 in to cable centre, 4 in PVC conduit, FTB (scenario)", cable=sw, arrangement="single",
                         depth_m=0.914, in_duct=True, bedding="FTB (fluidized thermal backfill)", bedding_radius_m=0.15,
                         depth_ref="Scenario depth from EDS 062288 Note 2 / Black Books; not a PG&E cover standard",
                         status="selected scenario"),
        "DIRECT_NATIVE": dict(label="Direct buried in native soil, 30 in class (scenario)", cable=sw, arrangement="single",
                              depth_m=0.819, in_duct=False, bedding="Native soil", bedding_radius_m=0.15,
                              depth_ref="Same centre depth as the 30 in preset", status="selected scenario"),
        "DARM_TREFOIL_SAND": dict(label="Darmstadt MV150 trefoil, direct buried in sand (config IV geometry)",
                                  cable="Darmstadt MV 150 mm2 Al (NA2XS(F)2Y 1x150)", arrangement="trefoil",
                                  depth_m=0.623, in_duct=False, bedding="Darmstadt sand", bedding_radius_m=0.25,
                                  depth_ref="Trefoil centroid 0.623 m, interpreted from paper Fig 2 (bundle underside 0.650 m)",
                                  status="experiment geometry used with USCRN conditions (engineering scenario)"),
    }


def install_summary(c):
    """Inputs with plain-language provenance (screen 3)."""
    cable = ph.CABLES()[c["cable"]]
    pr = presets().get(c.get("preset"), {})
    bed = ph.BEDDINGS[c["bedding"]]
    rows = [
        ("Cable construction", cable["name"], "manufacturer specification", cable["source"]),
        ("Cable layers", ", ".join(f"{L[0]} to {L[1]*2000:.1f} mm OD" for L in cable["layers"]),
         "manufacturer specification", "conductor, insulation, shield, jacket radii"),
        ("Arrangement", "touching trefoil (equivalent bundle)" if c["arrangement"] == "trefoil" else "single cable",
         "selected scenario", "trefoil = estimated equivalent-bundle approximation" if c["arrangement"] == "trefoil" else ""),
        ("Burial depth to cable centre", f"{c['depth_m']:.3f} m", "utility standard" if c.get("preset", "").startswith("PGE") else "selected scenario",
         pr.get("depth_ref", "")),
        ("Duct", "4 in Sch 40 PVC (ID 100.6 mm, OD 114.3 mm)" if c["in_duct"] else "none (direct buried)",
         "utility standard" if c["in_duct"] else "selected scenario", "PG&E EDS 062288" if c["in_duct"] else ""),
        ("Air gap in duct", "IEC 60287 air-space resistance at 60 C mean" if c["in_duct"] else "-", "derived property", ""),
        ("Backfill", c["bedding"], bed["prov"].split(" (")[0], bed["prov"]),
        ("Backfill zone", f"equivalent radius {c['bedding_radius_m']:.2f} m around the cable", "selected scenario",
         "trench drawn schematically; the radial model uses an equivalent annulus"),
        ("Native soil", "Johansen k(theta), porosity 0.40, quartz 0.50", "derived property", "moisture from the background forecast"),
        ("Previous load (168 h)", f"{c['prior_current']:.0f} A", "selected scenario", ""),
        ("Proposed future load", f"{c['future_current']:.0f} A, {c['future_shape']}", "selected scenario", ""),
        ("Conductor temperature limit", f"{c.get('t_max') or cable['t_max']:.0f} C", "manufacturer specification", "normal operating limit"),
    ]
    return [dict(zip(("input", "value", "provenance", "note"), r)) for r in rows]


# ------------------------------------------------------------------ assessment
DEFAULT_CASE = dict(station="NE_Lincoln_8_ENE", issue="2021-08-27 08:00", method="gbt", stage=3,
                    preset="PGE_30IN", moisture_mode="background only", t_crit=50.0,
                    prior_current=300.0, future_current=400.0, future_shape="flat", t_max=None,
                    environment="forecast")


def build_case(case):
    c = dict(DEFAULT_CASE, **{k: v for k, v in case.items() if v is not None})
    pr = presets().get(c["preset"])
    if pr:
        for k in ("cable", "arrangement", "depth_m", "in_duct", "bedding", "bedding_radius_m"):
            c.setdefault(k, pr[k])
            if case.get(k) is None:
                c[k] = pr[k]
    return c


def future_profile(c):
    nh = core.HOR
    if c["future_shape"] == "daily cycle":
        ih = int(c["issue"][11:13])
        return [c["future_current"] * (0.7 + 0.3 * max(math.sin(math.pi * (((ih + h) % 24) - 6) / 16), 0))
                for h in range(1, nh + 1)]
    return [c["future_current"]] * nh


def warm_up(cable, mesh, t_hist, th_hist, prior, drying, t_crit):
    pre = ph.simulate(cable, mesh, [t_hist[0]] * 240, [th_hist[0]] * 240, [prior] * 240,
                      dt=3600, drying=drying, t_crit=t_crit)
    return ph.simulate(cable, mesh, t_hist, th_hist, [prior] * len(t_hist), T0=pre["state"],
                       drying=drying, t_crit=t_crit)


def search(cable, mesh, t_bg, th_bg, T0, profile=None, drying=False, t_crit=50.0, tol=1.0, t_max=None):
    """Whole-horizon search: largest multiplier keeping T_c <= T_max at every hour."""
    nh = len(t_bg)
    profile = profile or [1.0] * nh
    scale = max(profile) or 1.0
    shape = [p / scale for p in profile]
    tmax = t_max or cable["t_max"]
    run = lambda m: ph.simulate(cable, mesh, t_bg, th_bg, [m * s for s in shape], T0=T0, drying=drying, t_crit=t_crit)
    s0 = run(0.0)
    if max(s0["tc"]) > tmax:
        return 0.0, s0, 0
    hi = 2.0 * ph.steady_ampacity(cable, mesh, min(t_bg), min(th_bg), tmax) + 1.0
    while max(run(hi)["tc"]) <= tmax and hi < 1e5:
        hi *= 2
    lo, it = 0.0, 0
    while hi - lo > tol:
        mid = 0.5 * (lo + hi)
        it += 1
        if max(run(mid)["tc"]) > tmax:
            hi = mid
        else:
            lo = mid
    return lo / scale, run(lo), it


def tag(value, prov, source=""):
    return {"value": value, "provenance": prov, "source": source}


def assess(case, save=True):
    c = build_case(case)
    cable = ph.CABLES()[c["cable"]]
    tmax = c["t_max"] or cable["t_max"]
    mesh = ph.Mesh(cable, c["depth_m"], c["in_duct"], c["bedding"], c["bedding_radius_m"], c["arrangement"])
    drying = c["moisture_mode"] == "critical-isotherm drying"
    fc = core.forecast(c["station"], c["issue"], c["method"], c["stage"])
    d = c["depth_m"]
    t_fc = core.fill(core.interp_depth(fc["T"], d), 15.0)
    th_fc = core.fill(core.interp_depth(fc["M"], d), 0.2)
    hT = core.fill(core.interp_depth(fc["histT"], d), t_fc[0])
    hM = core.fill(core.interp_depth(fc["histM"], d), th_fc[0])
    oT = oM = None
    if fc["obsT"] is not None:
        raw = core.interp_depth(fc["obsT"], d)
        if sum(not math.isnan(v) for v in raw) > 0.8 * len(raw):
            oT = core.fill(raw, t_fc[0])
            oM = core.fill(core.interp_depth(fc["obsM"], d), th_fc[0])
    # environment used for the run: forecast (default), fixed at issue, or observed (hindcast)
    env = c["environment"]
    if env == "fixed":
        t_bg, th_bg = [hT[-1]] * core.HOR, [hM[-1]] * core.HOR
    elif env == "observed" and oT is not None:
        t_bg, th_bg = oT, oM
    else:
        env, t_bg, th_bg = "forecast", t_fc, th_fc

    warm = warm_up(cable, mesh, hT, hM, c["prior_current"], drying, c["t_crit"])
    T0 = warm["state"]
    prof = future_profile(c)
    planned = ph.simulate(cable, mesh, t_bg, th_bg, prof, T0=T0, drying=drying, t_crit=c["t_crit"], keep_profiles=True)
    flat_I, flat, iters = search(cable, mesh, t_bg, th_bg, T0, None, drying, c["t_crit"], t_max=tmax)
    mult, _, _ = search(cable, mesh, t_bg, th_bg, T0, prof, drying, c["t_crit"], tol=0.5, t_max=tmax)
    obs_I = None
    if oT is not None and env != "observed":
        obs_I, _, _ = search(cable, mesh, oT, oM, T0, None, drying, c["t_crit"], t_max=tmax)
    steady = ph.steady_ampacity(cable, mesh, t_bg[0], th_bg[0], tmax)
    margin = [tmax - v for v in planned["tc"]]
    losses = sum(planned["ql"]) * 3600 / 1e3                  # kJ/m over 72 h
    to_ground = sum(planned["qs"]) * 3600 * mesh.n_cables / 1e3
    S = {
        "permissible_current_A": tag(round(flat_I, 1), "calculated", f"whole-horizon bisection, {iters} model runs"),
        "load_multiplier": tag(round(mult, 3), "calculated", "same search on the proposed profile"),
        "peak_T_conductor_C": tag(round(max(planned["tc"]), 2), "calculated", "proposed load"),
        "min_margin_K": tag(round(min(margin), 2), "calculated"),
        "T_max_C": tag(tmax, "manufacturer specification", cable["source"]),
        "T_conductor_at_issue_C": tag(round(warm["tc"][-1], 2), "calculated", "168 h warm-up at the previous load"),
        "steady_state_current_A": tag(round(steady, 1), "calculated", "analytic, sanity check"),
        "stored_heat_at_issue_kJ_m": tag(round(warm["stored"][-1] / 1e3, 1), "calculated", "cable + backfill zone, relative to the background temperature"),
        "stored_heat_end_kJ_m": tag(round(planned["stored"][-1] / 1e3, 1), "calculated"),
        "losses_72h_kJ_m": tag(round(losses, 1), "calculated", "I^2 R(T) over 72 h, all cables"),
        "heat_out_of_cables_72h_kJ_m": tag(round(to_ground, 1), "calculated", "conducted across the cable surface"),
        "background_T_lead1_C": tag(round(t_bg[0], 2), fc["provenance"], env),
        "background_theta_lead1": tag(round(th_bg[0], 3), fc["provenance"], env),
        "native_k_lead1_W_mK": tag(round(planned["kn"][0], 3), "derived property", "Johansen / material curve"),
    }
    if obs_I is not None:
        S["permissible_current_observed_env_A"] = tag(round(obs_I, 1), "calculated", "observed background (hindcast)")
        S["forecast_effect_A"] = tag(round(flat_I - obs_I, 1), "calculated", "this run minus observed-background run")
    traj = {"time": fc["times"], "T_background": t_bg, "theta_background": th_bg,
            "T_background_forecast": t_fc, "T_background_observed": oT, "k_native": planned["kn"],
            "planned_current_A": prof, "T_conductor": planned["tc"], "T_cable_surface": planned["ts"],
            "T_backfill_edge": planned["tb"], "q_surface_W_m": planned["qs"], "losses_W_m": planned["ql"],
            "stored_kJ_m": [v / 1e3 for v in planned["stored"]], "dry_radius_m": planned["dry_r"],
            "margin_K": margin, "T_conductor_at_limit": flat["tc"]}
    radial = {"r": mesh.rc, "region": mesh.region, "profiles": planned["profiles"]}
    res = {"case": c, "version": VERSION,
           "model": {"forecast": fc["method"], "stage": fc["stage"], "geometry": "equivalent radial (Kennelly 2h boundary)",
                     "arrangement": c["arrangement"], "moisture": c["moisture_mode"], "environment": env},
           "summary": S, "trajectory": traj, "radial": radial,
           "geometry": {"depth": c["depth_m"], "r_cable": mesh.r_cable, "r_bundle": mesh.r_bundle,
                        "r_bed": mesh.r_bed, "r_far": mesh.r_far, "in_duct": c["in_duct"],
                        "duct_id": ph.DUCT_ID, "duct_od": ph.DUCT_OD, "layers": cable["layers"]},
           "inputs": install_summary(c),
           "forecast": {k: fc[k] for k in ("method", "stage", "provenance", "note", "times", "T", "M", "obsT", "obsM",
                                           "hist_times", "histT", "histM", "histP", "errors")},
           "history_bg": {"time": fc["hist_times"], "T": hT, "M": hM},
           "support": {
               "geometry": "single cable or touching trefoil (equivalent bundle) in an equivalent radial domain",
               "moisture": ("reduced rule: backfill/soil above T_crit takes its dry conductivity (scenario); no transport"
                            if drying else "local moisture held at the background value; no redistribution"),
               "not_supported": ["several separate circuits / mutual heating between ducts", "full 2D finite-element cross-section",
                                 "liquid and vapour moisture transport", "explicit trench geometry"]}}
    if save:
        res["run_id"] = save_run(res)
    return res


# ------------------------------------------------------------------ 2D temperature map
def field(res, hour, nx=97, nz=65, half_w=1.5, depth_max=2.0):
    """Quasi-steady cross-section at one hour: background profile varying with depth, the radial
    solution inside the backfill zone, and the Kennelly image-method field outside it (isothermal
    ground surface). Estimated visualisation of the radial model, not a 2D solve."""
    g = res["geometry"]
    h, r_bed = g["depth"], g["r_bed"]
    k = min(max(hour, 1), len(res["radial"]["profiles"])) - 1
    prof = res["radial"]["profiles"][k]
    rc = res["radial"]["r"]
    fcT = res["forecast"]["T"][k]
    t_bg_h = res["trajectory"]["T_background"][k]

    def bg(z):
        v = core.interp_depth([fcT], max(z, 0.05))[0]
        return v if not math.isnan(v) else t_bg_h

    def radial_T(r):
        if r <= rc[0]:
            return prof[0]
        for i in range(1, len(rc)):
            if rc[i] >= r:
                f = (r - rc[i - 1]) / (rc[i] - rc[i - 1])
                return prof[i - 1] + f * (prof[i] - prof[i - 1])
        return prof[-1]
    t_edge = radial_T(r_bed)
    d_edge = 2 * h
    xs = [-half_w + 2 * half_w * i / (nx - 1) for i in range(nx)]
    zs = [depth_max * j / (nz - 1) for j in range(nz)]
    grid = []
    for z in zs:
        row = []
        for x in xs:
            d = math.hypot(x, z - h)
            dp = math.hypot(x, z + h)
            if d <= r_bed:
                row.append(round(radial_T(d) + (bg(z) - t_bg_h), 2))
            else:
                rise = (t_edge - t_bg_h) * math.log(dp / d) / math.log(d_edge / r_bed)
                row.append(round(bg(z) + rise, 2))
        grid.append(row)
    return {"x": xs, "z": zs, "T": grid, "hour": k + 1, "time": res["trajectory"]["time"][k],
            "cable_depth": h, "r_bed": r_bed, "t_edge": round(t_edge, 2)}


# ------------------------------------------------------------------ comparisons and runs
def compare(base, what):
    c0 = build_case(base)
    alts = []
    if what == "depth":
        for key in ("PGE_24IN", "PGE_30IN", "SCN_36IN"):
            alts.append((f"{presets()[key]['depth_m']:.3f} m", dict(c0, depth_m=presets()[key]["depth_m"])))
    elif what == "backfill":
        for b in ("Native soil", "Sand (generic)", "FTB (fluidized thermal backfill)"):
            alts.append((b, dict(c0, bedding=b)))
    elif what == "environment":
        for e, lab in (("fixed", "Fixed at issue"), ("forecast", "Forecast"), ("observed", "Observed (hindcast)")):
            alts.append((lab, dict(c0, environment=e)))
    elif what == "moisture":
        for m in ("background only", "critical-isotherm drying"):
            alts.append((m, dict(c0, moisture_mode=m)))
    elif what == "cable":
        for name in ("Southwire 250 kcmil Cu 15 kV EPR, PVC jacket", ph.DEFAULT_CABLE,
                     "Southwire 500 kcmil Cu 15 kV EPR, PVC jacket", "Southwire 750 kcmil Cu 15 kV EPR, PVC jacket"):
            alts.append((name.replace(" Cu 15 kV EPR, PVC jacket", ""), dict(c0, cable=name)))
    elif what == "duct":
        alts = [("In 4 in PVC duct", dict(c0, in_duct=True)), ("Direct buried", dict(c0, in_duct=False))]
    elif what == "method":
        for m, lab in (("persistence", "Persistence"), ("seasonal", "Seasonal baseline"),
                       ("gbt", "Trees (config 3)"), ("gru", "GRU")):
            alts.append((lab, dict(c0, method=m, stage=3)))
    rows = []
    for lab, c in alts:
        c["preset"] = "custom"
        try:
            r = assess(c, save=False)
            s = r["summary"]
            rows.append({"option": lab, "permissible_current_A": s["permissible_current_A"]["value"],
                         "peak_T_conductor_C": s["peak_T_conductor_C"]["value"], "min_margin_K": s["min_margin_K"]["value"],
                         "T_conductor_at_issue_C": s["T_conductor_at_issue_C"]["value"]})
        except Exception as e:
            rows.append({"option": lab, "error": str(e)})
    out = {"what": what, "base": c0, "rows": rows, "version": VERSION,
           "saved_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
    RUNS.mkdir(exist_ok=True)
    p = RUNS / f"compare_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{what}.json"
    p.write_text(json.dumps(out, default=str), encoding="utf-8")
    out["saved_as"] = p.name
    return out


def save_run(res):
    RUNS.mkdir(exist_ok=True)
    rid = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{int(time.time()*1000)%1000:03d}_{res['case']['station']}"
    res = dict(res, run_id=rid, saved_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    (RUNS / f"run_{rid}.json").write_text(json.dumps(res, default=lambda o: None), encoding="utf-8")
    return rid


def list_runs(limit=50):
    out = []
    for p in sorted(RUNS.glob("run_*.json"), reverse=True)[:limit]:
        try:
            r = json.loads(p.read_text(encoding="utf-8"))
            out.append({"run_id": r["run_id"], "saved_at": r.get("saved_at"), "station": r["case"]["station"],
                        "issue": r["case"]["issue"], "method": r["case"]["method"], "preset": r["case"].get("preset"),
                        "permissible_current_A": r["summary"]["permissible_current_A"]["value"]})
        except Exception:
            continue
    return out


def load_run(rid):
    p = RUNS / f"run_{rid}.json"
    if not p.exists() or "/" in rid or ".." in rid:
        raise FileNotFoundError(rid)
    return json.loads(p.read_text(encoding="utf-8"))
