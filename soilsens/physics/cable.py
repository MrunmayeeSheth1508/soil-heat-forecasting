"""Cable catalogue, beddings and installations.

Values come from the repo's proposal/code/01_cable_thermal_model/cable_params.py
(Southwire spec 46319, PG&E EDS 038193/062288, Darmstadt paper). Anything not in
those sources is marked "estimated".
"""
from __future__ import annotations

from dataclasses import dataclass, field

from . import soil

IN = 0.0254


@dataclass(frozen=True)
class Layer:
    name: str
    r_out: float      # m
    k: float          # W/m/K
    cv: float         # J/m3/K
    provenance: str = "specified"


@dataclass(frozen=True)
class Cable:
    name: str
    layers: tuple             # conductor first; radii increasing
    r20: float                # ohm/m (AC) at 20 C
    alpha20: float            # 1/K
    t_max: float              # degC normal operating limit
    source: str = ""

    @property
    def r_outer(self):
        return self.layers[-1].r_out

    def resistance(self, t_c):
        return self.r20 * (1 + self.alpha20 * (t_c - 20.0))


# --- Southwire 350 kcmil Cu, EPR, PVC jacket (Southwire spec 46319) ---------------
# Rac at 90 C = 0.043 ohm/1000 ft -> 1.411e-4 ohm/m; back to 20 C with alpha 0.00393
_rac90 = 0.043 / 304.8
SOUTHWIRE_350 = Cable(
    name="Southwire 350 kcmil Cu, EPR, PVC jacket",
    layers=(
        Layer("Cu conductor", 0.616 / 2 * IN, 400.0, 3.45e6),
        Layer("EPR insulation + screens", 1.102 / 2 * IN, 1 / 3.5, 2.0e6),
        Layer("Cu tape shield", 1.162 / 2 * IN, 400.0, 3.45e6),
        Layer("PVC jacket", 1.342 / 2 * IN, 1 / 5.0, 1.7e6),
    ),
    r20=_rac90 / (1 + 0.00393 * 70), alpha20=0.00393, t_max=105.0,
    source="Southwire spec 46319; thermal resistivities N-M Table 6 via Bates 2021",
)

# --- Darmstadt MV150 Al (Verschaffel-Drefke et al. 2021) ----------------------------
DARMSTADT_MV150 = Cable(
    name="Darmstadt MV 150 mm2 Al (single core)",
    layers=(
        Layer("Al conductor", 0.00691, 237.0, 2.42e6, "estimated"),
        Layer("XLPE insulation", 0.00691 + 0.0055, 1 / 3.5, 2.0e6),
        Layer("Screen / bedding", 0.0145, 1 / 3.5, 2.0e6, "estimated"),
        Layer("PE sheath", 0.017, 1 / 3.5, 2.4e6),
    ),
    r20=0.206e-3, alpha20=0.00403, t_max=90.0,
    source="Darmstadt paper Fig 2 / cable_params.py; inner radii estimated (DC resistance used)",
)

CABLES = {c.name: c for c in (SOUTHWIRE_350, DARMSTADT_MV150)}


# --- Beddings (material immediately around the cable / duct) ------------------------
@dataclass(frozen=True)
class Bedding:
    name: str
    kind: str                  # "native" | "johansen" | "fixed"
    params: soil.SoilParams | None = None
    k_fixed: float | None = None
    cv_fixed: float | None = None
    k_dry: float | None = None  # used if local drying is switched on
    provenance: str = "estimated"


BEDDINGS = {
    "Native soil": Bedding("Native soil", "native"),
    "Sand": Bedding("Sand", "johansen", params=soil.SAND, provenance="estimated"),
    "FTB (fluidized thermal backfill)": Bedding(
        "FTB (fluidized thermal backfill)", "fixed", k_fixed=100 / 60.0, cv_fixed=2.0e6,
        k_dry=100 / 75.0, provenance="specified"),   # PG&E/SnoPUD: rho <= 60 (3% MC), <= 75 dry
}


# --- Installation -----------------------------------------------------------------------
@dataclass
class Installation:
    depth_m: float = 0.819                 # cable centre depth (30 in cover + conduit OD/2)
    in_duct: bool = True                   # 4 in PVC Sch 40 conduit
    bedding: str = "FTB (fluidized thermal backfill)"
    bedding_radius_m: float = 0.15         # equivalent radius of the backfill zone (estimated)
    arrangement: str = "single radial"     # only supported option today
    notes: list = field(default_factory=list)


DUCT_ID, DUCT_OD = 3.961 * IN, 4.500 * IN   # PG&E EDS 062288
K_PVC = 1 / 4.8


def duct_air_k(cable: Cable, t_mean=60.0):
    """Equivalent conductivity of the air gap inside a PVC duct, from the IEC 60287
    air-space resistance T = U / (1 + 0.1 (V + Y t_mean) De), U=5.2, V=1.4, Y=0.011."""
    import math
    de_mm = cable.r_outer * 2000
    T = 5.2 / (1 + 0.1 * (1.4 + 0.011 * t_mean) * de_mm)
    return math.log((DUCT_ID / 2) / cable.r_outer) / (2 * math.pi * T)
