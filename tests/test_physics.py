"""Numerical checks for the ground model and rating (run: python -m pytest tests -q)."""
import numpy as np
import pytest

from soilsens.physics import radial, soil
from soilsens.physics.cable import SOUTHWIRE_350, DARMSTADT_MV150, Installation
from soilsens import rating


def test_johansen_monotonic_and_bounded():
    th = np.linspace(0, 0.4, 41)
    k = soil.conductivity(th)
    assert np.all(np.diff(k) >= -1e-12)
    assert k[0] == pytest.approx(soil.k_dry(soil.DEFAULT_NATIVE), rel=1e-6)
    assert k[-1] == pytest.approx(soil.k_sat(soil.DEFAULT_NATIVE), rel=1e-6)


@pytest.mark.parametrize("cable", [SOUTHWIRE_350, DARMSTADT_MV150])
@pytest.mark.parametrize("duct", [True, False])
def test_transient_converges_to_analytic_steady_state(cable, duct):
    inst = Installation(in_duct=duct, depth_m=0.8)
    I = radial.steady_ampacity(cable, inst, 15.0, 0.25)
    n = 24 * 200
    sim = radial.simulate(cable, inst, np.full(n, 15.0), np.full(n, 0.25), np.full(n, I), dt=3600)
    assert sim.t_conductor[-1] == pytest.approx(cable.t_max, abs=0.5)


def test_energy_balance_at_steady_state():
    inst = Installation(in_duct=True)
    n = 24 * 200
    sim = radial.simulate(SOUTHWIRE_350, inst, np.full(n, 15.0), np.full(n, 0.25),
                          np.full(n, 500.0), dt=3600)
    assert sim.q_surface[-1] == pytest.approx(sim.q_loss[-1], rel=0.01)


def test_zero_current_stays_at_background():
    inst = Installation()
    sim = radial.simulate(SOUTHWIRE_350, inst, np.full(48, 12.0), np.full(48, 0.2), np.zeros(48))
    assert np.allclose(sim.t_conductor, 12.0, atol=1e-6)


def test_rating_hits_limit():
    inst = Installation()
    tb, th = np.full(72, 20.0), np.full(72, 0.25)
    warm, mesh = rating.warm_up(SOUTHWIRE_350, inst, np.full(168, 20.0), np.full(168, 0.25), 300.0)
    r = rating.search(SOUTHWIRE_350, inst, tb, th, warm.final_state, mesh=mesh)
    assert r.t_conductor.max() <= SOUTHWIRE_350.t_max + 1e-6
    assert r.t_conductor.max() > SOUTHWIRE_350.t_max - 1.0


def test_wetter_soil_gives_higher_rating():
    inst = Installation(in_duct=False, bedding="Native soil")
    dry = radial.steady_ampacity(SOUTHWIRE_350, inst, 20, 0.05)
    wet = radial.steady_ampacity(SOUTHWIRE_350, inst, 20, 0.30)
    assert wet > dry
