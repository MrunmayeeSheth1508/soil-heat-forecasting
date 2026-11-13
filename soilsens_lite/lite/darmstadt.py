"""Darmstadt experiment reconstruction (screen 5A).

Case MF_IV_CL: one MV150 Al trefoil (configuration IV) under a near-constant load for
39 days, four bedding sections (silt, sand, fluidized backfill, loam), measured conductor
temperatures. The model is driven by the experiment's own recorded current and the
recorded soil temperature at 0.8 m (far-field boundary).

Assumptions (all shown in the app):
  - geometry: touching trefoil, equivalent bundle, centroid depth 0.623 m (interpreted
    from paper Fig 2), whole domain filled with the bedding material (trench not transcribed)
  - bedding conductivity from the measured dry-out curve k(theta) at a prescribed moisture
  - initial state: 20 days at the first recorded current (Day 0 is not a steady state)
Case MF_III_CL (configuration II: two trefoils + LV cables) is shown as measured data only.
"""
from __future__ import annotations

import json
import math
from functools import lru_cache

from . import core, physics as ph

CABLE = "Darmstadt MV 150 mm2 Al (NA2XS(F)2Y 1x150)"
DEPTH = 0.623
BEDS = {"silt": ("Darmstadt silt", "DARM_SILT"), "sand": ("Darmstadt sand", "DARM_SAND"),
        "fluidized_backfill": ("Darmstadt fluidized backfill", "DARM_FBF"), "loam": ("Darmstadt loam", "DARM_LOAM")}


@lru_cache(maxsize=1)
def experiments():
    return json.loads((core.DATA / "darmstadt" / "experiments.json").read_text(encoding="utf-8"))


def _median(v):
    v = sorted(x for x in v if x is not None)
    return v[len(v) // 2] if v else None


def moisture_options():
    """Prescribed moisture per bedding (m3/m3) from the MF_III FDR sensors."""
    m = experiments()["MF_III_CL"]["moisture_pct"]
    out = {}
    for b in BEDS:
        near, und = _median(m.get(b, [])), _median(m.get(f"{b}_undisturbed", []))
        out[b] = {"near_cable": near / 100 if near is not None else None,
                  "undisturbed": und / 100 if und is not None else None}
    out["fluidized_backfill"] = {"near_cable": None, "undisturbed": None, "assumed": 0.20}
    return out


def theta_for(bedding, mode):
    o = moisture_options()[bedding]
    if mode == "near_cable" and o.get("near_cable") is not None:
        return o["near_cable"], "measured near cable (MF_III median)"
    if o.get("undisturbed") is not None:
        return o["undisturbed"], "measured undisturbed (MF_III median)"
    return o.get("assumed", 0.20), "assumed 0.20 (no moisture sensor for this material)"


def reconstruct(bedding="sand", moisture="undisturbed", drying=False, t_crit=50.0):
    ex = experiments()["MF_IV_CL"]
    cable = ph.CABLES()[CABLE]
    bed_name, _ = BEDS[bedding]
    theta, theta_src = theta_for(bedding, moisture)
    mesh = ph.Mesh(cable, DEPTH, False, bed_name, arrangement="trefoil", uniform=True, theta_bed=theta)
    I = core.fill([v if v is not None else float("nan") for v in ex["current_A"]], 300.0)
    Tb = core.fill([v if v is not None else float("nan") for v in ex["weather"]["soil_temperature_0p8m_C"]], 12.0)
    th = [theta] * len(I)
    pre = ph.simulate(cable, mesh, [Tb[0]] * 480, [theta] * 480, [I[0]] * 480, dt=3600, drying=drying, t_crit=t_crit)
    sim = ph.simulate(cable, mesh, Tb, th, I, T0=pre["state"], dt=900, drying=drying, t_crit=t_crit)
    meas = ex["temps"][bedding]
    pairs = [(m, c) for m, c in zip(meas, sim["tc"]) if m is not None and math.isfinite(c)]
    err = [c - m for m, c in pairs]
    n_meas = sum(m is not None for m in meas)
    stats = {
        "n_hours": len(I), "n_compared": len(pairs),
        "coverage": round(len(pairs) / len(I), 3) if I else 0,
        "mae_K": round(sum(abs(e) for e in err) / len(err), 2) if err else None,
        "bias_K": round(sum(err) / len(err), 2) if err else None,
        "within_5K": round(sum(abs(e) <= 5 for e in err) / len(err), 3) if err else None,
        "measured_mean_C": round(sum(m for m, _ in pairs) / len(pairs), 2) if pairs else None,
        "model_mean_C": round(sum(c for _, c in pairs) / len(pairs), 2) if pairs else None,
        "n_measured": n_meas,
    }
    return {"case": "DARM_CASE_MF_IV_CL", "bedding": bedding, "moisture": moisture, "theta": theta,
            "theta_source": theta_src, "drying": drying, "t_crit": t_crit,
            "k_bedding_W_mK": round(ph.curve_k(BEDS[bedding][1], theta), 3),
            "hours": ex["hours"], "current_A": ex["current_A"], "soil_0p8m_C": ex["weather"]["soil_temperature_0p8m_C"],
            "air_C": ex["weather"]["air_temperature_C"], "measured_C": meas,
            "model_C": [round(v, 2) if math.isfinite(v) else None for v in sim["tc"]],
            "stats": stats, "sensor": "conductor",
            "assumptions": ["Touching trefoil, equivalent-bundle approximation (estimated)",
                            "Centroid depth 0.623 m, interpreted from paper Fig 2",
                            "Whole model domain filled with the bedding material (trench and native soil not transcribed)",
                            f"Bedding moisture {theta:.3f} m3/m3: {theta_src}",
                            "Far-field boundary = recorded soil temperature at 0.8 m",
                            "Initial state: 20 days at the first recorded current (Day 0 is not steady)"]}


@lru_cache(maxsize=1)
def saved():
    p = core.DATA / "darmstadt" / "saved_runs.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def mf3_moisture():
    ex = experiments()["MF_III_CL"]
    return {"hours": ex["hours"], "moisture_pct": ex["moisture_pct"], "sheath_C": ex["temps"],
            "current_A": ex["current_A"], "sensor": "sheath",
            "note": ("Configuration II (two MV trefoils plus LV cables). Shown as measured data only: the "
                     "multi-circuit geometry is not supported by the radial model, and the repo's V4 audit found "
                     "mapping errors in an earlier attempt.")}
