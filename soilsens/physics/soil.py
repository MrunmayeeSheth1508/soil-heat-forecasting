"""Soil thermal properties from moisture.

Johansen (1975):  k = k_dry + Ke * (k_sat - k_dry)
Volumetric heat capacity: Cv = (1 - n) * Cs + theta * Cw
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

K_WATER, K_QUARTZ = 0.594, 7.7       # W/m/K
CV_WATER, CV_SOLID = 4.18e6, 2.0e6   # J/m3/K


@dataclass(frozen=True)
class SoilParams:
    name: str
    porosity: float = 0.40          # n
    dry_density: float = 1550.0     # kg/m3
    quartz: float = 0.50            # quartz fraction of solids
    coarse: bool = False            # Johansen Ke form (coarse vs fine)
    source: str = "default (V4 audit defaults)"


DEFAULT_NATIVE = SoilParams("Native soil (default)")
SAND = SoilParams("Sand bedding", porosity=0.38, dry_density=1650, quartz=0.9, coarse=True,
                  source="generic sand, estimated")


def k_dry(p: SoilParams) -> float:
    rd = p.dry_density
    return (0.135 * rd + 64.7) / (2700 - 0.947 * rd)


def k_sat(p: SoilParams) -> float:
    k_other = 2.0 if p.quartz > 0.2 else 3.0
    k_s = K_QUARTZ ** p.quartz * k_other ** (1 - p.quartz)
    return k_s ** (1 - p.porosity) * K_WATER ** p.porosity


def kersten(sr, coarse):
    sr = np.clip(sr, 1e-4, 1.0)
    if coarse:
        ke = 0.7 * np.log10(sr) + 1.0
    else:
        ke = np.log10(sr) + 1.0
    return np.clip(ke, 0.0, 1.0)


def conductivity(theta, p: SoilParams = DEFAULT_NATIVE):
    """W/m/K for volumetric moisture theta (m3/m3)."""
    theta = np.asarray(theta, float)
    sr = np.clip(theta / p.porosity, 0, 1)
    kd, ks = k_dry(p), k_sat(p)
    return kd + kersten(sr, p.coarse) * (ks - kd)


def heat_capacity(theta, p: SoilParams = DEFAULT_NATIVE):
    """J/m3/K."""
    theta = np.clip(np.asarray(theta, float), 0, p.porosity)
    return (1 - p.porosity) * CV_SOLID + theta * CV_WATER


def rho_ccm_per_w(k):
    """Thermal resistivity in the industry unit degC.cm/W."""
    return 100.0 / np.asarray(k, float)
