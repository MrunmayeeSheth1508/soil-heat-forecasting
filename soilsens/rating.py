"""Whole-horizon permissible loading (slide 11, 'Rating').

Largest constant current (or load multiplier on a profile) that keeps the conductor
temperature <= T_max at EVERY hour of the 72 h horizon, starting from a state warmed
up by the stated prior load.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .physics import radial
from .physics.cable import Cable, Installation


@dataclass
class RatingResult:
    multiplier: float               # x profile (if profile is ones: amps)
    current_profile: np.ndarray     # (72,) A at the limit
    t_conductor: np.ndarray         # (72,) at the limit
    sim: radial.SimResult
    iterations: int
    binding_hour: int               # lead hour where T_max is reached


def warm_up(cable, inst, t_bg_hist, theta_bg_hist, prior_current, drying=False, t_crit=50.0):
    """Run the 168 h history with the prior load to get the issue-time state."""
    n = len(t_bg_hist)
    I = np.full(n, prior_current) if np.isscalar(prior_current) else np.asarray(prior_current)
    mesh = radial.build_mesh(cable, inst)
    # start from the steady field for the first hour, then march through the history
    sim0 = radial.simulate(cable, inst, np.full(240, t_bg_hist[0]), np.full(240, theta_bg_hist[0]),
                           np.full(240, I[0]), dt=1800, drying=drying, t_crit=t_crit, mesh=mesh)
    sim = radial.simulate(cable, inst, t_bg_hist, theta_bg_hist, I, T0=sim0.final_state,
                          drying=drying, t_crit=t_crit, mesh=mesh)
    return sim, mesh


def search(cable: Cable, inst: Installation, t_bg, theta_bg, T0, profile=None,
           drying=False, t_crit=50.0, tol=1.0, mesh=None, i_hi=None) -> RatingResult:
    """Bisection on the multiplier m so that max_t Tc(m * profile) == T_max."""
    nh = len(t_bg)
    profile = np.ones(nh) if profile is None else np.asarray(profile, float)
    scale = profile.max() if profile.max() > 0 else 1.0
    shape = profile / scale
    mesh = mesh or radial.build_mesh(cable, inst)

    def peak(m):
        s = radial.simulate(cable, inst, t_bg, theta_bg, m * shape, T0=T0, drying=drying,
                            t_crit=t_crit, mesh=mesh)
        return s.t_conductor.max(), s

    if i_hi is None:   # bracket from the analytic steady rating (transient can exceed it)
        i_hi = 4.0 * radial.steady_ampacity(cable, inst, float(np.min(t_bg)),
                                            float(np.min(theta_bg)))
    lo, hi = 0.0, i_hi
    while peak(hi)[0] <= cable.t_max and hi < 1e5:
        hi *= 2
    if peak(0.0)[0] > cable.t_max:
        s = peak(0.0)[1]
        return RatingResult(0.0, 0 * shape, s.t_conductor, s, 0, int(np.argmax(s.t_conductor)) + 1)
    it = 0
    while hi - lo > tol and it < 40:
        mid = 0.5 * (lo + hi)
        if peak(mid)[0] > cable.t_max:
            hi = mid
        else:
            lo = mid
        it += 1
    _, s = peak(lo)
    return RatingResult(lo / scale if profile is not None else lo, lo * shape, s.t_conductor, s, it,
                        int(np.argmax(s.t_conductor)) + 1)
