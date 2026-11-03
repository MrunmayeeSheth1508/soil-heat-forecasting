"""
johansen.py — soil thermal conductivity from moisture content (Johansen 1975)
and conversion to thermal resistivity for use in the N-M ampacity model.

All equations and coefficient choices are documented with sources.
Tags: [V] = verified from source; [I] = inferred.

Primary reference:
  Johansen, O. (1975). Thermal conductivity of soils. PhD thesis,
  University of Trondheim, Norway.

As implemented and described in:
  Dai, Y. et al. (2019). JAMES. [V survey_thermohydraulic_2022]
  Bracale et al. (2019). IEEE Access. [V survey_bracale_2019]
  Wilson et al. (2016) soil texture table — Wilson_T1.xls in data/

Usage:
    from johansen import johansen_lambda, lambda_to_rho_Ccm_per_W
    lam = johansen_lambda(theta=0.20, theta_sat=0.40, rho_dry=1400,
                          quartz=0.5, is_coarse=True)
    rho_cable = lambda_to_rho_Ccm_per_W(lam)

Run self-test:
    python code/02_soil_thermal_properties/johansen.py
"""
import numpy as np


# Physical constants
LAMBDA_WATER  = 0.594    # W/(m·K) at 20°C
LAMBDA_ICE    = 2.2      # W/(m·K)
LAMBDA_AIR    = 0.025    # W/(m·K)
LAMBDA_QUARTZ = 7.7      # W/(m·K)
LAMBDA_OTHER  = 2.0      # W/(m·K) for non-quartz minerals
RHO_WATER     = 1000.0   # kg/m³
RHO_SOLID     = 2700.0   # kg/m³ (assumed grain density — standard)
C_WATER       = 4182.0   # J/(kg·K)
C_SOLID       = 800.0    # J/(kg·K) approximate mineral


def lambda_solid(quartz_fraction: float) -> float:
    """
    Geometric mean thermal conductivity of solid mineral phase.
    lambda_s = lambda_q^q * lambda_o^(1-q)
    [V Johansen 1975; Dai et al. 2019]
    """
    return LAMBDA_QUARTZ**quartz_fraction * LAMBDA_OTHER**(1.0 - quartz_fraction)


def lambda_dry(rho_dry_kg_per_m3: float) -> float:
    """
    Dry thermal conductivity from bulk dry density.
    lambda_dry = (0.135*rho_dry + 64.7) / (2700 - 0.947*rho_dry)
    Units: rho_dry in kg/m³, returns W/(m·K).
    [V Johansen 1975; Dai et al. 2019]
    """
    rd = rho_dry_kg_per_m3
    return (0.135 * rd + 64.7) / (2700.0 - 0.947 * rd)


def lambda_saturated(quartz_fraction: float, porosity: float) -> float:
    """
    Saturated thermal conductivity (geometric mean of solid and water).
    lambda_sat = lambda_s^(1-n) * lambda_w^n
    [V Johansen 1975]
    """
    ls = lambda_solid(quartz_fraction)
    return ls**(1.0 - porosity) * LAMBDA_WATER**porosity


def kersten_number(Sr: float, is_coarse: bool) -> float:
    """
    Kersten number Ke — interpolation weight between dry and saturated.
    Coarse soils (sand/gravel): Ke = 0.7*log10(Sr) + 1.0  for Sr >= 0.05
    Fine soils (silt/clay):     Ke = Sr                    (linear)
    [V Johansen 1975]
    """
    Sr = float(np.clip(Sr, 1e-6, 1.0))
    if is_coarse:
        return max(0.0, 0.7 * np.log10(Sr) + 1.0)
    else:
        return Sr


def johansen_lambda(
    theta: float,
    theta_sat: float,
    rho_dry_kg_per_m3: float,
    quartz_fraction: float,
    is_coarse: bool = True,
) -> float:
    """
    Johansen (1975) soil thermal conductivity.

    Parameters
    ----------
    theta            : volumetric water content (m³/m³, 0–1)
    theta_sat        : saturated volumetric water content = porosity (m³/m³)
    rho_dry_kg_per_m3: bulk dry density (kg/m³)
    quartz_fraction  : volume fraction of quartz in solid phase (0–1)
    is_coarse        : True for sandy/gravelly soils; False for fine (silt/clay)

    Returns
    -------
    lambda_soil : W/(m·K)
    """
    porosity = theta_sat
    Sr = theta / (porosity + 1e-9)
    Sr = float(np.clip(Sr, 0.0, 1.0))

    lam_dry = lambda_dry(rho_dry_kg_per_m3)
    lam_sat = lambda_saturated(quartz_fraction, porosity)
    Ke      = kersten_number(Sr, is_coarse)

    lam = lam_dry + Ke * (lam_sat - lam_dry)
    return float(lam)


def lambda_to_rho_Ccm_per_W(lam_W_per_mK: float) -> float:
    """
    Convert thermal conductivity λ [W/(m·K)] to thermal resistivity ρ
    in °C·cm/W (the unit used in Neher-McGrath and IEC 60287).

    ρ [°C·cm/W] = 100 / λ [W/(m·K)]
    [V Bates 2021 Ch 2; unit confirmed from N-M Table 6 values]
    """
    return 100.0 / lam_W_per_mK


def rho_Ccm_per_W_to_lambda(rho: float) -> float:
    """Inverse of lambda_to_rho_Ccm_per_W."""
    return 100.0 / rho


def volumetric_heat_capacity(
    theta: float,
    rho_dry_kg_per_m3: float,
) -> float:
    """
    Volumetric heat capacity of soil (J/(m³·K)).
    C_vol = (1 - n) * rho_solid * C_solid  +  theta * rho_water * C_water
    Note: the Darmstadt workbook stores solid-phase-only values;
          this function computes the corrected total. [V darmstadt_workbook_audit.md]
    """
    porosity = 1.0 - rho_dry_kg_per_m3 / RHO_SOLID
    c_solid  = (1.0 - porosity) * RHO_SOLID * C_SOLID
    c_water  = theta * RHO_WATER * C_WATER
    return c_solid + c_water


# ---------------------------------------------------------------------------
# Typical soil parameters from literature and Wilson table
# For use when station-level texture data is unavailable.
# [V] survey_bates_2021.md, survey_bracale_2019.md
# ---------------------------------------------------------------------------
TYPICAL_SOIL_PARAMS = {
    # (theta_sat, rho_dry, quartz, is_coarse)
    "sand"          : (0.40, 1600, 0.80, True),
    "loamy_sand"    : (0.42, 1500, 0.60, True),
    "silt_loam"     : (0.46, 1400, 0.25, False),
    "clay"          : (0.50, 1300, 0.10, False),
    "ftb_flowable"  : (0.35, 1450, 0.40, False),   # FTB (approximated)
}

# Verified design values from literature [V]
LITERATURE_RHO = {
    "boulder_co_in_situ_mean"     : 117.0,  # °C·cm/W [V Bates 2021 Table 8.5]
    "boulder_co_in_situ_95ci_upper": 220.0, # °C·cm/W [V Bates 2021 Ch 8]
    "arizona_pv_in_situ_mean"     : 157.0,  # °C·cm/W [V Bates 2021 Ch 11]
    "arizona_pv_design_used"      : 270.0,  # °C·cm/W [V Bates 2021 Ch 11]
    "nec_default"                 :  90.0,  # °C·cm/W [V Bates 2021 Ch 2]
    "bracale_clay"                :  85.0,  # °C·cm/W → 0.85 mK/W [V survey_bracale]
    "bracale_sand"                :  75.0,  # °C·cm/W → 0.75 mK/W [V survey_bracale]
    "darmstadt_sand_wet"          :  65.0,  # °C·cm/W [I from workbook conductivity curve]
    "darmstadt_sand_dry"          : 200.0,  # °C·cm/W [I from workbook conductivity curve]
}


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import sys
    if sys.stdout.encoding and sys.stdout.encoding.lower() in ("cp1252", "ascii"):
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    print("=== Johansen self-test ===")
    cases = [
        ("Sand, wet (th=0.30)",  0.30, 0.40, 1600, 0.80, True),
        ("Sand, dry (th=0.05)",  0.05, 0.40, 1600, 0.80, True),
        ("Silt, wet (th=0.35)",  0.35, 0.46, 1400, 0.25, False),
        ("Silt, dry (th=0.05)",  0.05, 0.46, 1400, 0.25, False),
        ("Clay, wet (th=0.40)",  0.40, 0.50, 1300, 0.10, False),
    ]
    for label, theta, tsat, rd, q, coarse in cases:
        lam = johansen_lambda(theta, tsat, rd, q, coarse)
        rho = lambda_to_rho_Ccm_per_W(lam)
        print(f"  {label:35s}  lam={lam:.3f} W/(m.K)  rho={rho:.1f} C.cm/W")

    print("\nLiterature reference values (°C·cm/W):")
    for k, v in LITERATURE_RHO.items():
        print(f"  {k:40s} = {v}")
