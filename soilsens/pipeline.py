"""One call that runs a full assessment case. This is what the UI talks to."""
from __future__ import annotations

from dataclasses import dataclass, field, asdict

import numpy as np
import pandas as pd

from . import config, data, provenance as P, rating
from .forecast.base import get_forecast, interp_depth
from .physics import radial, soil
from .physics.cable import CABLES, BEDDINGS, Installation


@dataclass
class Case:
    station: str
    issue: str                                  # ISO timestamp, LST
    method: str = "persistence"                 # persistence | diurnal | gbt | gru
    stage: int = 3                              # GBT ablation stage
    cable: str = "Southwire 350 kcmil Cu, EPR, PVC jacket"
    depth_m: float = 0.819
    in_duct: bool = True
    bedding: str = "FTB (fluidized thermal backfill)"
    bedding_radius_m: float = 0.15
    moisture_mode: str = "background only"      # or "critical-isotherm drying"
    t_crit: float = 50.0
    prior_current: float = 300.0                # A, held over the 168 h history
    future_current: float = 400.0               # A, planned base load
    future_shape: str = "flat"                  # flat | daily cycle
    t_max_override: float | None = None
    n_uncertainty: int = 0                      # error-trajectory resamples (0 = off)

    def installation(self) -> Installation:
        return Installation(self.depth_m, self.in_duct, self.bedding, self.bedding_radius_m)


def future_profile(case: Case, nh=config.HORIZON_H):
    if case.future_shape == "daily cycle":
        h = np.arange(1, nh + 1)
        issue_hour = pd.Timestamp(case.issue).hour
        hod = (issue_hour + h) % 24
        shape = 0.7 + 0.3 * np.clip(np.sin(np.pi * (hod - 6) / 16), 0, None)  # evening peak
        return case.future_current * shape
    return np.full(nh, case.future_current)


def _cable(case):
    c = CABLES[case.cable]
    if case.t_max_override:
        from dataclasses import replace
        c = replace(c, t_max=case.t_max_override)
    return c


def assess(case: Case) -> dict:
    cable = _cable(case)
    inst = case.installation()
    drying = case.moisture_mode == "critical-isotherm drying"
    s = data.load_station(case.station)
    issue = pd.Timestamp(case.issue)
    hist, fut = data.window(s, issue)

    # 1. background forecast and its value at cable depth
    fc = get_forecast(case.station, issue, case.method, case.stage)
    t_bg, th_bg = fc.at_depth(case.depth_m)
    t_bg = pd.Series(t_bg).ffill().bfill().to_numpy()
    th_bg = pd.Series(th_bg).ffill().bfill().fillna(0.2).to_numpy()

    hT = interp_depth(hist[[f"T{d}" for d in config.DEPTHS_CM]].to_numpy(float), case.depth_m)
    hM = interp_depth(hist[[f"M{d}" for d in config.DEPTHS_CM]].to_numpy(float), case.depth_m)
    hT = pd.Series(hT).ffill().bfill().to_numpy()
    hM = pd.Series(hM).ffill().bfill().fillna(0.2).to_numpy()

    # 2. initial state from the prior load over the observed history
    warm, mesh = rating.warm_up(cable, inst, hT, hM, case.prior_current, drying, case.t_crit)
    T0 = warm.final_state

    # 3. conductor temperature under the planned load
    prof = future_profile(case)
    planned = radial.simulate(cable, inst, t_bg, th_bg, prof, T0=T0, drying=drying,
                              t_crit=case.t_crit, mesh=mesh)

    # 4. whole-horizon permissible current (flat) and load multiplier (planned profile)
    flat = rating.search(cable, inst, t_bg, th_bg, T0, None, drying, case.t_crit, mesh=mesh)
    mult = rating.search(cable, inst, t_bg, th_bg, T0, prof, drying, case.t_crit, mesh=mesh)

    # 5. same thing with the OBSERVED background (forecast-driven vs observed-environment)
    obs = None
    if fc.truth_temp is not None:
        oT, oM = fc.at_depth(case.depth_m, which="obs")
        if np.isfinite(oT).mean() > 0.8:
            oT = pd.Series(oT).ffill().bfill().to_numpy()
            oM = pd.Series(oM).ffill().bfill().fillna(0.2).to_numpy()
            obs = rating.search(cable, inst, oT, oM, T0, None, drying, case.t_crit, mesh=mesh)
            obs_bg = (oT, oM)

    # 6. optional uncertainty: add past forecast-error trajectories of persistence
    unc = None
    if case.n_uncertainty > 0:
        unc = _uncertainty(case, cable, inst, t_bg, th_bg, T0, drying, mesh, s, issue)

    steady = radial.steady_ampacity(cable, inst, t_bg[0], th_bg[0])

    times = fc.times
    traj = pd.DataFrame({
        "lead_h": np.arange(1, len(times) + 1),
        "T_background_fc": t_bg, "theta_background_fc": th_bg,
        "k_native_W_mK": planned.k_native,
        "planned_current_A": prof,
        "T_conductor_planned": planned.t_conductor,
        "T_cable_surface_planned": planned.t_surface,
        "T_bedding_edge_planned": planned.t_bedding_edge,
        "q_surface_W_m": planned.q_surface,
        "margin_K": cable.t_max - planned.t_conductor,
        "T_conductor_at_limit": flat.t_conductor,
    }, index=times)
    if obs is not None:
        traj["T_background_obs"], traj["theta_background_obs"] = obs_bg

    summary = {
        "permissible_current_A": P.tag(round(flat.multiplier, 1), P.CALCULATED,
                                       "rating.search, flat 72 h"),
        "load_multiplier": P.tag(round(mult.multiplier, 3), P.CALCULATED,
                                 "rating.search on planned profile"),
        "peak_T_conductor_planned_C": P.tag(round(float(planned.t_conductor.max()), 2), P.CALCULATED),
        "min_margin_K": P.tag(round(float(traj["margin_K"].min()), 2), P.CALCULATED),
        "binding_lead_h": P.tag(flat.binding_hour, P.CALCULATED),
        "T_max_C": P.tag(cable.t_max, P.SPECIFIED, cable.source),
        "T_conductor_at_issue_C": P.tag(round(float(warm.t_conductor[-1]), 2), P.CALCULATED,
                                        "warm-up with prior load over observed 168 h"),
        "steady_state_current_A": P.tag(round(steady, 1), P.CALCULATED,
                                        "analytic, background at lead 1 (sanity check)"),
        "background_T_lead1_C": P.tag(round(float(t_bg[0]), 2), fc.provenance, fc.method),
        "background_theta_lead1": P.tag(round(float(th_bg[0]), 3), fc.provenance, fc.method),
        "native_k_lead1_W_mK": P.tag(round(float(planned.k_native[0]), 3), P.ESTIMATED,
                                     "Johansen, default params"),
    }
    if obs is not None:
        summary["permissible_current_obs_bg_A"] = P.tag(
            round(obs.multiplier, 1), P.CALCULATED, "same search, observed background (hindcast)")
        summary["forecast_effect_A"] = P.tag(round(flat.multiplier - obs.multiplier, 1),
                                             P.CALCULATED, "forecast-driven minus observed-driven")
    if unc is not None:
        summary["permissible_current_p10_p90_A"] = P.tag(
            [round(float(x), 1) for x in np.percentile(unc, [10, 90])], P.CALCULATED,
            f"{len(unc)} resampled persistence error trajectories")

    support = {
        "geometry": "single cable, equivalent radial (Kennelly 2h boundary)",
        "moisture": ("reduced rule: soil above T_crit takes dry conductivity (scenario)"
                     if drying else "background moisture only, no local redistribution"),
        "not_supported": ["multiple cables / mutual heating", "2D cross-section",
                          "moisture transport (liquid/vapour)", "trench/duct-bank geometry"],
    }
    return {"case": asdict(case), "forecast": fc, "trajectory": traj, "summary": summary,
            "support": support, "warmup": warm, "history_bg": (hist.index, hT, hM)}


def _uncertainty(case, cable, inst, t_bg, th_bg, T0, drying, mesh, s, issue, seed=0):
    """Resample past (pre-issue) persistence error trajectories at cable depth."""
    rng = np.random.default_rng(seed)
    past = data.valid_issue_times(s)
    past = past[past < issue - pd.Timedelta(hours=config.HORIZON_H)]
    if len(past) < 10:
        return None
    df = s.frame()
    errs = []
    for iss in rng.choice(past, size=min(len(past), 5 * case.n_uncertainty), replace=False):
        i = s.time.get_loc(iss)
        blk = df.iloc[i:i + 1 + config.HORIZON_H]
        z = interp_depth(blk[[f"T{d}" for d in config.DEPTHS_CM]].to_numpy(float), case.depth_m)
        if np.isfinite(z).all():
            errs.append(z[1:] - z[0])
        if len(errs) >= case.n_uncertainty:
            break
    out = []
    for e in errs:
        r = rating.search(cable, inst, t_bg + e, th_bg, T0, None, drying, case.t_crit,
                          mesh=mesh, tol=2.0)
        out.append(r.multiplier)
    return np.array(out) if out else None


def compare(base: Case, **changes) -> pd.DataFrame:
    """Matched comparison: change ONE thing, keep load, limits, initial history identical."""
    from dataclasses import replace
    rows = []
    for label, c in [("base", base)] + [(f"{k}={v}", replace(base, **{k: v})) for k, v in changes.items()]:
        r = assess(c)
        s = r["summary"]
        rows.append({"case": label,
                     "permissible_current_A": s["permissible_current_A"]["value"],
                     "peak_T_conductor_C": s["peak_T_conductor_planned_C"]["value"],
                     "min_margin_K": s["min_margin_K"]["value"]})
    return pd.DataFrame(rows)
