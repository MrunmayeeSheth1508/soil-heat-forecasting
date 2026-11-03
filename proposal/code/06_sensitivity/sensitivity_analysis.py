"""
sensitivity_analysis.py — WP4 sensitivity study
Quantifies how ampacity varies with:
  1. Soil thermal resistivity uncertainty (Johansen texture inputs)
  2. Depth interpolation error (depth reference convention)
  3. Ambient temperature uncertainty

All bounds are derived from verified literature values.
[V] = verified from full text; sources in notes/survey_*.md

Run from proposal/ root:
    python code/06_sensitivity/sensitivity_analysis.py
"""
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "code" / "01_cable_thermal_model"))
sys.path.insert(0, str(ROOT / "code" / "02_soil_thermal_properties"))

from neher_mcgrath import (
    dc_resistance_at_temp, ys_factor, yp_factor,
    T_insulation, T_jacket, T_duct, T_soil, ampacity
)
from johansen import johansen_lambda, lambda_to_rho_Ccm_per_W, LITERATURE_RHO
from cable_params import (
    Southwire350kcmil, PGEInstallation, ThermalRho,
    BlackBooksAssumptions, inches_to_m
)

CABLE = Southwire350kcmil()
PGE   = PGEInstallation()
BB    = BlackBooksAssumptions()

_rdc_90 = dc_resistance_at_temp(CABLE.rdc_25C_ohm_per_m, 25.0, 90.0)
_Ycs    = ys_factor(_rdc_90)
_Ycp    = yp_factor(_rdc_90, CABLE.conductor_od_m, BB.CABLE_SPACING_M)
Y_C     = _Ycs + _Ycp
_Ti = T_insulation(ThermalRho.EPR_INSULATION, CABLE.od_over_insulation_m, CABLE.conductor_od_m)
_Tj = T_jacket(ThermalRho.PVC_JACKET, CABLE.overall_od_m, CABLE.od_over_shield_m)
_Td = T_duct(ThermalRho.FIBER_PVC_DUCT, PGE.conduit_od_m, PGE.conduit_id_m)

OUT_DIR = ROOT / "results" / "sensitivity"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def ampacity_for_rho_and_Ta(rho_Ccm_W, Ta_C, depth_m=None, T_c=105.0):
    """Compute ampacity for given RHO, Ta, and burial depth."""
    d = depth_m if depth_m else PGE.cable_centre_depth_m
    Te = T_soil(rho_Ccm_W, d, PGE.conduit_od_m, n_cables=1, load_factor=1.0)
    R_ca = _Ti + _Tj + _Td + Te
    return ampacity(T_c, Ta_C, 0.0, _rdc_90, Y_C, R_ca)


# ---------------------------------------------------------------------------
# 1. RHO sensitivity sweep
# From Bates (2021) [V]: field range 95–220 °C·cm/W; design range 90–408
# ---------------------------------------------------------------------------
def rho_sensitivity():
    rho_range = np.arange(50, 451, 10)
    results = []
    Ta_ref = 20.0   # Black Books ambient [V]
    for rho in rho_range:
        I = ampacity_for_rho_and_Ta(rho, Ta_ref)
        results.append({"rho_Ccm_W": rho, "I_A": I, "Ta_C": Ta_ref})

    df = pd.DataFrame(results)

    # Mark literature reference points [V Bates 2021]
    refs = {
        "NEC default (90)"      : 90.0,
        "Boulder CO mean (117)" : 117.0,
        "Boulder 95%CI (220)"   : 220.0,
        "Arizona in-situ (157)" : 157.0,
        "Arizona design (270)"  : 270.0,
        "Bates adj.max (408)"   : 408.0,
    }

    fig, ax = plt.subplots(figsize=(9, 5))
    ax.plot(df.rho_Ccm_W, df.I_A, "b-", lw=2)
    for label, rho in refs.items():
        I_ref = float(df.loc[df.rho_Ccm_W == int(round(rho)), "I_A"].values[0]
                      if int(round(rho)) in df.rho_Ccm_W.values
                      else ampacity_for_rho_and_Ta(rho, Ta_ref))
        ax.axvline(rho, ls="--", alpha=0.5)
        ax.text(rho + 3, I_ref + 2, label.split("(")[0].strip(),
                fontsize=7, rotation=0)
    ax.set_xlabel("Soil thermal resistivity ρ (°C·cm/W)")
    ax.set_ylabel("Ampacity (A)")
    ax.set_title(f"Ampacity vs Soil Thermal Resistivity (Ta={Ta_ref}°C, PG&E install)")
    fig.tight_layout()
    fig.savefig(OUT_DIR / "rho_sensitivity.png", dpi=120)
    df.to_csv(OUT_DIR / "rho_sensitivity.csv", index=False)
    print(f"[1] RHO sensitivity: saved rho_sensitivity.png + .csv")
    return df


# ---------------------------------------------------------------------------
# 2. Ambient temperature sensitivity
# From Bates (2021) [V]: SCAN 99th pctile Ta = 34.6°C (Essex 2185, AZ)
# Black Books design: Ta = 20°C; IEEE 835: Ta = 25°C
# ---------------------------------------------------------------------------
def Ta_sensitivity():
    Ta_range = np.arange(5, 41, 1)
    rho_cases = {
        "NEC default RHO=90 [V]"       : 90.0,
        "Bates in-situ mean RHO=117 [V]": 117.0,
        "Arizona in-situ RHO=157 [V]"  : 157.0,
    }
    results = []
    for Ta in Ta_range:
        for label, rho in rho_cases.items():
            I = ampacity_for_rho_and_Ta(rho, float(Ta))
            results.append({"Ta_C": float(Ta), "rho_label": label, "I_A": I})
    df = pd.DataFrame(results)

    fig, ax = plt.subplots(figsize=(9, 5))
    for label, grp in df.groupby("rho_label"):
        ax.plot(grp.Ta_C, grp.I_A, label=label)
    ax.axvline(20.0,  ls="--", color="k", alpha=0.4, label="Black Books (20°C) [V]")
    ax.axvline(25.0,  ls=":",  color="k", alpha=0.4, label="IEEE 835 (25°C) [V]")
    ax.axvline(34.6,  ls="-.", color="r", alpha=0.6, label="SCAN 99th pctile (34.6°C) [V]")
    ax.set_xlabel("Ambient soil temperature Ta (°C)")
    ax.set_ylabel("Ampacity (A)")
    ax.set_title("Ampacity vs Ambient Soil Temperature (PG&E install, Tc=105°C)")
    ax.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(OUT_DIR / "Ta_sensitivity.png", dpi=120)
    df.to_csv(OUT_DIR / "Ta_sensitivity.csv", index=False)
    print(f"[2] Ta sensitivity: saved Ta_sensitivity.png + .csv")
    return df


# ---------------------------------------------------------------------------
# 3. Darmstadt depth-reference sensitivity
# [V notes/survey_darmstadt_2021.md — 0.65 m = underside interpretation]
# Tests three conventions: underside, centre, top of trefoil bundle
# ---------------------------------------------------------------------------
def depth_reference_sensitivity():
    depth_cases = {
        "Underside of bundle (0.650 m) [V, fig-based]" : 0.650,
        "Lower conductor centres (0.633 m) [I]"        : 0.633,
        "Centroid of three centres (0.623 m) [I]"      : 0.623,
        "Upper conductor centre (0.604 m) [I]"         : 0.604,
        "Top of bundle (~0.587 m) [I]"                 : 0.587,
    }
    Ta = 20.0
    results = []
    for label, depth in depth_cases.items():
        for rho in [90.0, 117.0, 157.0]:
            I = ampacity_for_rho_and_Ta(rho, Ta, depth_m=depth)
            results.append({"depth_m": depth, "label": label, "rho": rho, "I_A": I})
    df = pd.DataFrame(results)

    print("\n[3] Darmstadt depth-reference sensitivity (Ta=20°C):")
    print(df.pivot_table(index="label", columns="rho", values="I_A").to_string())
    df.to_csv(OUT_DIR / "depth_reference_sensitivity.csv", index=False)
    print(f"    Saved depth_reference_sensitivity.csv")
    return df


# ---------------------------------------------------------------------------
# 4. N-M accuracy vs load factor (reproducing Bates 2021 finding)
# [V Bates 2021 Ch 9: LF=0.66 gives mean error -0.3%]
# ---------------------------------------------------------------------------
def load_factor_sensitivity():
    LFs = np.arange(0.3, 1.05, 0.05)
    # Bates measured: SS mean error -8%; with LF=0.66 mean error -0.3%
    # Here we show how ampacity scales with load factor
    results = []
    for lf in LFs:
        Te = T_soil(90.0, PGE.cable_centre_depth_m, PGE.conduit_od_m,
                    n_cables=1, load_factor=lf)
        R_ca = _Ti + _Tj + _Td + Te
        I = ampacity(105.0, 20.0, 0.0, _rdc_90, Y_C, R_ca)
        results.append({"load_factor": lf, "I_A": I})
    df = pd.DataFrame(results)

    fig, ax = plt.subplots(figsize=(7, 4))
    ax.plot(df.load_factor * 100, df.I_A, "b-o", ms=4)
    ax.axvline(66, ls="--", color="r",
               label="LF=66% (Bates: error -0.3% [V])")
    ax.axvline(100, ls=":", color="k",
               label="LF=100% (steady-state, error -8% [V])")
    ax.set_xlabel("Load factor (%)")
    ax.set_ylabel("Ampacity (A)")
    ax.set_title("Ampacity vs Daily Load Factor (PG&E install, RHO=90, Ta=20°C)")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(OUT_DIR / "load_factor_sensitivity.png", dpi=120)
    df.to_csv(OUT_DIR / "load_factor_sensitivity.csv", index=False)
    print(f"[4] Load factor sensitivity: saved load_factor_sensitivity.png + .csv")
    return df


if __name__ == "__main__":
    print("Running all sensitivity studies ...\n")
    rho_sensitivity()
    Ta_sensitivity()
    depth_reference_sensitivity()
    load_factor_sensitivity()
    print(f"\nAll outputs saved to {OUT_DIR}/")
