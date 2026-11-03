"""
validate_mf_iv.py — validate the N-M cable thermal model against the
Darmstadt MF_IV_CL (constant load, 4 beddings) dataset.

Primary validation target per proposal WP2.
Expected performance per Bates (2021) [V]: mean error within ±10%,
consistent with CYMCAP -3%±15.4% and ETAP -4%±14.6% [V Table 10.6].

Run from proposal/ root:
    python code/03_darmstadt_validation/validate_mf_iv.py
"""
import numpy as np
import pandas as pd
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "code" / "01_cable_thermal_model"))
sys.path.insert(0, str(ROOT / "code" / "02_soil_thermal_properties"))
sys.path.insert(0, str(ROOT / "code" / "03_darmstadt_validation"))

from neher_mcgrath import (
    dc_resistance_at_temp, ys_factor, yp_factor,
    T_insulation, T_jacket, T_soil, conductor_temperature
)
from johansen import johansen_lambda, lambda_to_rho_Ccm_per_W
from load_darmstadt import load_mf_iv_cl, load_weather
from cable_params import DarmstadtMV150Al, ThermalRho


# ---------------------------------------------------------------------------
# Darmstadt MV150 Al cable parameters [V survey_darmstadt_2021.md]
# ---------------------------------------------------------------------------
CABLE = DarmstadtMV150Al()

# Bedding thermal resistivity values (wet, from workbook TH sheet)
# These will be loaded dynamically from the workbook; fallback defaults
# are taken from the survey notes [V darmstadt_workbook_audit.md].
BEDDING_RHO_WET_Ccm_W = {
    "sand" :  65.0,   # [I from workbook conductivity curve ~1.54 W/(m·K)]
    "loam" : 100.0,   # [I]
    "FTB"  :  80.0,   # [I; FTB spec: ≤60–75 °C·cm/W at 3% MC per EDS 038193]
    "silt" :  90.0,   # [I]
}

# Cable geometry (trefoil, bundle bottom at 0.650 m)
# [V notes/survey_darmstadt_2021.md — figure-based interpretation]
LOWER_CONDUCTOR_DEPTH_M = CABLE.lower_conductor_depth_m   # 0.633 m [I]
UPPER_CONDUCTOR_DEPTH_M = CABLE.upper_conductor_depth_m   # 0.604 m [I]
CENTROID_DEPTH_M        = CABLE.centroid_depth_m           # 0.623 m [I]

# Validation uses Darmstadt's own boundary conditions (soil temp at -0.8 m),
# NOT USCRN interpolation. [Per user instruction 4 Nov 2026]
AMBIENT_DEPTH_M = 0.80   # soil temp sensor depth in Darmstadt weather sheet [V]


def compute_model_conductor_temp(
    current_A: float,
    ambient_temp_C: float,
    rho_e_Ccm_W: float,
    burial_depth_m: float = CENTROID_DEPTH_M,
    load_factor: float = 1.0,
) -> float:
    """
    Compute predicted conductor temperature for one operating point.
    Uses N-M steady-state with load factor correction.
    [V neher_mcgrath.py; Bates 2021 Ch 9]
    """
    rdc = dc_resistance_at_temp(CABLE.rdc_20C_ohm_per_m, T_ref=20.0, T_oper=70.0)
    Ycs = ys_factor(rdc)
    Ycp = yp_factor(rdc, CABLE.overall_od_m, CABLE.overall_od_m * 2.0)
    Y_c = Ycs + Ycp

    Ti = T_insulation(ThermalRho.EPR_INSULATION,
                      CABLE.overall_od_m - CABLE.sheath_thickness_m * 2,
                      CABLE.overall_od_m - CABLE.sheath_thickness_m * 2
                      - CABLE.insulation_thickness_m * 2)
    Tj = 0.0   # sheath modelled as thin conductor, thermal R negligible [I]
    Te = T_soil(rho_e_Ccm_W, burial_depth_m, CABLE.overall_od_m,
                n_cables=3, load_factor=load_factor)
    R_ca = Ti + Tj + Te

    return conductor_temperature(current_A, ambient_temp_C, 0.0, rdc, Y_c, R_ca)


def run_validation(bedding: str = "sand") -> pd.DataFrame:
    """
    Run model vs measured comparison for a given bedding type.
    Returns DataFrame with columns: time_d, I_A, T_ambient_C,
    T_measured_C, T_model_C, error_pct.
    """
    df_exp = load_mf_iv_cl()

    # Bedding name → fragment that appears in the workbook column label
    BEDDING_COL_FRAGMENT = {
        "sand": "sand",
        "loam": "loam",
        "FTB" : "fluidized",
        "silt": "silt",
    }
    bed_frag = BEDDING_COL_FRAGMENT.get(bedding, bedding).lower()

    # Identify relevant columns by name fragment — robust to encoding artefacts
    time_cols    = [c for c in df_exp.columns if c.lower().startswith("time")]
    current_cols = [c for c in df_exp.columns
                    if "electrical load" in c.lower() or "current" in c.lower()]
    temp_cols    = [c for c in df_exp.columns
                    if bed_frag in c.lower() and "conductor" in c.lower()]
    amb_cols     = [c for c in df_exp.columns
                    if ("soil" in c.lower() and "0.8" in c) or "ambient" in c.lower()]

    if not time_cols or not current_cols or not temp_cols:
        print(f"[WARNING] Could not identify columns for bedding={bedding}.")
        print(f"  Available columns: {list(df_exp.columns)}")
        return pd.DataFrame()

    time_col    = time_cols[0]
    current_col = current_cols[0]
    temp_col    = temp_cols[0]
    amb_col     = amb_cols[0] if amb_cols else None

    sub = df_exp[[time_col, current_col, temp_col]].copy()
    if amb_col:
        sub["T_ambient_C"] = df_exp[amb_col]
    else:
        sub["T_ambient_C"] = 20.0   # fallback [I]
        print("[WARNING] No ambient column found; using 20°C fallback.")

    sub.columns = ["time_d", "I_A", "T_measured_C", "T_ambient_C"]
    sub = sub.dropna()

    rho = BEDDING_RHO_WET_Ccm_W.get(bedding, 90.0)
    sub["T_model_C"] = sub.apply(
        lambda r: compute_model_conductor_temp(r.I_A, r.T_ambient_C, rho),
        axis=1
    )
    sub["error_pct"] = (sub["T_model_C"] - sub["T_measured_C"]) / sub["T_measured_C"] * 100.0

    return sub


def print_summary(results: dict):
    """Print mean error and 90% CI per bedding, following Bates (2021) style."""
    print("\n=== Darmstadt MF_IV_CL Validation Summary ===")
    print(f"{'Bedding':8s}  {'n':>5s}  {'Mean err%':>10s}  {'Std%':>7s}  {'90% CI':>20s}")
    print("-" * 60)
    for bedding, df in results.items():
        if df.empty:
            print(f"{bedding:8s}  -- no data --")
            continue
        e = df["error_pct"].dropna()
        lo = np.percentile(e, 5)
        hi = np.percentile(e, 95)
        print(f"{bedding:8s}  {len(e):5d}  {e.mean():+10.1f}  {e.std():7.1f}"
              f"  [{lo:+.1f}%, {hi:+.1f}%]")
    print("\nNegative error = model overestimates temperature (conservative).")
    print("Target: mean within ±10% [V Bates 2021 Table 10.6]")


if __name__ == "__main__":
    results = {}
    for bed in ["sand", "loam", "FTB", "silt"]:
        print(f"Running validation for bedding: {bed} ...")
        results[bed] = run_validation(bed)

    print_summary(results)

    # Save per-bedding results
    out_dir = ROOT / "results" / "darmstadt_validation"
    out_dir.mkdir(parents=True, exist_ok=True)
    for bed, df in results.items():
        if not df.empty:
            df.to_csv(out_dir / f"mf_iv_cl_{bed}.csv", index=False)
    print(f"\nResults saved to {out_dir}/")
