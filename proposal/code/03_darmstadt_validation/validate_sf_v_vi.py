"""
validate_sf_v_vi.py — validate N-M cable model against Darmstadt SF V+VI
(PVC duct configurations: V = unfilled, VI = grouted).

51-day experiment. Directly relevant to PG&E 4-inch PVC Sch 40 installation.
[V survey_darmstadt_2021.md; V darmstadt_workbook_audit.md]

Run from proposal/ root:
    python code/03_darmstadt_validation/validate_sf_v_vi.py
"""
import numpy as np
import pandas as pd
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "code" / "01_cable_thermal_model"))
sys.path.insert(0, str(ROOT / "code" / "03_darmstadt_validation"))

from neher_mcgrath import (
    dc_resistance_at_temp, ys_factor, yp_factor,
    T_insulation, T_jacket, T_duct, T_soil, conductor_temperature
)
from load_darmstadt import load_sf_v_vi
from cable_params import DarmstadtMV150Al, ThermalRho

CABLE = DarmstadtMV150Al()

# Darmstadt duct geometry [V survey_darmstadt_2021.md, Fig 4]
# PVC duct: inner diameter 147.6 mm, wall 4.8 mm
# Duct outer edge to surface: 0.75 m; spacing 1.5 m
DUCT_ID_M  = 0.1476
DUCT_OD_M  = DUCT_ID_M + 2 * 0.0048
DUCT_DEPTH_M = 0.75 + DUCT_OD_M / 2.0    # centre of duct ≈ 0.824 m [I]

# Grouted duct: FTB fills the duct; treat as FTB thermal rho [V EDS 038193]
GROUTED_RHO_Ccm_W  = 70.0    # FTB high-strength ≤ 75 at 0% MC [V]
UNFILLED_RHO_Ccm_W = 350.0   # air-filled duct ≈ EPR rho as proxy [I]

# Native soil at Darmstadt (loam dominant) [V workbook audit]
NATIVE_SOIL_RHO_Ccm_W = 100.0   # [I from workbook TH curves]


def compute_temp_duct(
    current_A: float,
    ambient_C: float,
    duct_fill_rho: float,
    burial_depth_m: float = DUCT_DEPTH_M,
    load_factor: float = 1.0,
) -> float:
    rdc = dc_resistance_at_temp(CABLE.rdc_20C_ohm_per_m, T_ref=20.0, T_oper=70.0)
    Ycs = ys_factor(rdc)
    Ycp = yp_factor(rdc, CABLE.overall_od_m, CABLE.overall_od_m * 2.5)
    Y_c = Ycs + Ycp

    Ti = T_insulation(ThermalRho.EPR_INSULATION,
                      CABLE.overall_od_m - CABLE.sheath_thickness_m * 2,
                      CABLE.overall_od_m - CABLE.sheath_thickness_m * 2
                      - CABLE.insulation_thickness_m * 2)
    Td_fill = T_duct(duct_fill_rho, DUCT_OD_M, DUCT_ID_M)
    Te = T_soil(NATIVE_SOIL_RHO_Ccm_W, burial_depth_m, DUCT_OD_M,
                n_cables=1, load_factor=load_factor)
    R_ca = Ti + Td_fill + Te

    return conductor_temperature(current_A, ambient_C, 0.0, rdc, Y_c, R_ca)


def run_validation() -> pd.DataFrame:
    df_exp = load_sf_v_vi()
    if df_exp.empty:
        print("[WARNING] SF V+VI sheet loaded empty.")
        return pd.DataFrame()

    time_cols = [c for c in df_exp.columns if c.lower().startswith("time")]
    # Use config-specific load column; fall back to any current-like column
    curr_cols = [c for c in df_exp.columns
                 if "electrical load" in c.lower() and "v)" in c.lower()
                 and "vi)" not in c.lower()]
    curr_cols = curr_cols or [c for c in df_exp.columns if "current" in c.lower()]
    temp_v_cols = [c for c in df_exp.columns
                   if "configuration (v)" in c.lower() and "conductor" in c.lower()]
    temp_vi_cols = [c for c in df_exp.columns
                    if "configuration (vi)" in c.lower() and "conductor" in c.lower()]
    amb_cols = [c for c in df_exp.columns
                if "ambient" in c.lower() or ("soil" in c.lower() and "0.8" in c)]

    if not time_cols or not curr_cols:
        print(f"[WARNING] Cannot identify required columns.\n  Available: {list(df_exp.columns)}")
        return pd.DataFrame()

    sub = pd.DataFrame()
    sub["time_d"]  = df_exp[time_cols[0]]
    sub["I_A"]     = df_exp[curr_cols[0]] if curr_cols else np.nan
    sub["T_amb_C"] = df_exp[amb_cols[0]] if amb_cols else 20.0
    sub["T_meas_V"]  = df_exp[temp_v_cols[0]]  if temp_v_cols  else np.nan
    sub["T_meas_VI"] = df_exp[temp_vi_cols[0]] if temp_vi_cols else np.nan
    sub = sub.apply(pd.to_numeric, errors="coerce").dropna(subset=["I_A"])

    sub["T_model_V"]  = sub.apply(
        lambda r: compute_temp_duct(r.I_A, r.T_amb_C, UNFILLED_RHO_Ccm_W), axis=1)
    sub["T_model_VI"] = sub.apply(
        lambda r: compute_temp_duct(r.I_A, r.T_amb_C, GROUTED_RHO_Ccm_W),  axis=1)

    if sub["T_meas_V"].notna().any():
        sub["err_V_pct"]  = (sub.T_model_V  - sub.T_meas_V)  / sub.T_meas_V  * 100
    if sub["T_meas_VI"].notna().any():
        sub["err_VI_pct"] = (sub.T_model_VI - sub.T_meas_VI) / sub.T_meas_VI * 100

    return sub


def print_summary(df: pd.DataFrame):
    print("\n=== Darmstadt SF V+VI Validation Summary ===")
    print(f"  {'Config':12s}  {'n':>5s}  {'Mean err%':>10s}  {'Std%':>7s}")
    print("  " + "-" * 40)
    for col, label in [("err_V_pct", "Config V (unfilled)"),
                        ("err_VI_pct", "Config VI (grouted)")]:
        if col in df.columns:
            e = df[col].dropna()
            print(f"  {label:35s}  {len(e):5d}  {e.mean():+10.1f}  {e.std():7.1f}")
    print("\n  Note: grouted duct adds ~25-35% temperature over direct-buried")
    print("  per Verschaffel-Drefke et al. (2021) [V survey_darmstadt_2021.md]")
    print("  Negative error = model overestimates (conservative).")


if __name__ == "__main__":
    df = run_validation()
    print_summary(df)
    out_dir = ROOT / "results" / "darmstadt_validation"
    out_dir.mkdir(parents=True, exist_ok=True)
    if not df.empty:
        df.to_csv(out_dir / "sf_v_vi.csv", index=False)
        print(f"\nResults saved to {out_dir}/sf_v_vi.csv")
