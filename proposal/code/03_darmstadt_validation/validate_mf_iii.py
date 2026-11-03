"""
validate_mf_iii.py — validate sheath temperature and analyse soil moisture
dynamics at the cable surface using Darmstadt MF_III_CL dataset.

35-day experiment. Primary source for:
  - Moisture drying/rewetting timescales at cable surface
  - Sheath temperature accuracy of N-M model
  - Cross-reference with NHR analysis (Bates 2021 Ch 4 [V])

Key finding from Verschaffel-Drefke et al. 2021 [V]:
  Sand dries completely at cable surface and rewets within a single day.
  This is the key soil-moisture-ampacity dynamic SoilSens must capture.

Run from proposal/ root:
    python code/03_darmstadt_validation/validate_mf_iii.py
"""
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
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
from load_darmstadt import load_mf_iii_cl
from cable_params import DarmstadtMV150Al, ThermalRho

CABLE = DarmstadtMV150Al()

# Depth for MF_III: same main-field upper row as MF_IV [V]
CONDUCTOR_CENTROID_DEPTH_M = CABLE.centroid_depth_m   # 0.623 m [I]

# NHR check parameters [V Bates 2021 Ch 4]
# Typical cable heat rate range: 0.2–0.4 W/cm [V]
# Sand NHR (probe 3/4"): 0.1 W/cm [V]; cable equivalent: ~0.2 W/cm [V]
NHR_SAND_PROBE_W_PER_CM    = 0.1    # [V Bates 2021 Ch 4]
NHR_CABLE_EQUIV_W_PER_CM   = 0.2    # [V Bates 2021 Ch 4]
TYPICAL_CABLE_HEATRATE_MIN  = 0.2   # W/cm [V]
TYPICAL_CABLE_HEATRATE_MAX  = 0.4   # W/cm [V]


def cable_heat_rate_W_per_cm(current_A: float) -> float:
    """
    Total cable heat dissipation per unit length in W/cm.
    W_total = I² * Rac (W/m) / 100 (cm/m)
    [V Bates 2021 Appendix A Table A.1: W_total = 0.38 W/cm at 541 A]
    """
    rdc = dc_resistance_at_temp(CABLE.rdc_20C_ohm_per_m, T_ref=20.0, T_oper=70.0)
    Ycs = ys_factor(rdc)
    Ycp = yp_factor(rdc, CABLE.overall_od_m, CABLE.overall_od_m * 2.0)
    Y_c = Ycs + Ycp
    W_per_m = current_A**2 * rdc * (1.0 + Y_c)
    return W_per_m / 100.0   # W/cm


def moisture_driven_rho(theta: float, bedding: str = "sand") -> float:
    """
    Thermal resistivity from volumetric moisture content via Johansen.
    Parameters approximated from Darmstadt workbook TH curves. [I from workbook]
    """
    params = {
        "sand" : dict(theta_sat=0.38, rho_dry_kg_per_m3=1650, quartz_fraction=0.82, is_coarse=True),
        "loam" : dict(theta_sat=0.45, rho_dry_kg_per_m3=1420, quartz_fraction=0.35, is_coarse=False),
        "FTB"  : dict(theta_sat=0.36, rho_dry_kg_per_m3=1450, quartz_fraction=0.40, is_coarse=False),
        "silt" : dict(theta_sat=0.46, rho_dry_kg_per_m3=1380, quartz_fraction=0.20, is_coarse=False),
    }
    p = params.get(bedding, params["sand"])
    lam = johansen_lambda(theta=theta, **p)
    return lambda_to_rho_Ccm_per_W(lam)


def run_validation() -> pd.DataFrame:
    df_exp = load_mf_iii_cl()
    if df_exp.empty:
        print("[WARNING] MF_III_CL sheet loaded empty.")
        return pd.DataFrame()

    time_cols     = [c for c in df_exp.columns if c.lower().startswith("time")]
    curr_cols     = [c for c in df_exp.columns
                     if "electrical load" in c.lower() or "current" in c.lower()]
    sheath_cols   = [c for c in df_exp.columns if "sheat" in c.lower()]
    moisture_cols = [c for c in df_exp.columns
                     if "water content" in c.lower() or "moisture" in c.lower()
                     or "vwc" in c.lower()]
    amb_cols      = [c for c in df_exp.columns
                     if "ambient" in c.lower() or ("soil" in c.lower() and "0.8" in c)]

    if not time_cols or not curr_cols:
        print(f"[WARNING] Cannot identify required columns.\n  Available: {list(df_exp.columns)}")
        return pd.DataFrame()

    sub = pd.DataFrame()
    sub["time_d"]        = df_exp[time_cols[0]]
    sub["I_A"]           = df_exp[curr_cols[0]] if curr_cols else np.nan
    sub["T_sheath_meas"] = df_exp[sheath_cols[0]] if sheath_cols else np.nan
    sub["theta_meas"]    = df_exp[moisture_cols[0]] if moisture_cols else np.nan
    sub["T_amb_C"]       = df_exp[amb_cols[0]] if amb_cols else 20.0
    sub = sub.apply(pd.to_numeric, errors="coerce").dropna(subset=["I_A"])

    # Compute model sheath temperature using moisture-dependent RHO
    results = []
    for _, row in sub.iterrows():
        theta = row.theta_meas if not np.isnan(row.theta_meas) else 0.20  # fallback
        rho = moisture_driven_rho(theta, bedding="sand")

        rdc = dc_resistance_at_temp(CABLE.rdc_20C_ohm_per_m, T_ref=20.0, T_oper=70.0)
        Ycs = ys_factor(rdc)
        Y_c = Ycs
        Ti  = T_insulation(ThermalRho.EPR_INSULATION,
                           CABLE.overall_od_m - CABLE.sheath_thickness_m*2,
                           CABLE.overall_od_m - CABLE.sheath_thickness_m*2
                           - CABLE.insulation_thickness_m*2)
        Te  = T_soil(rho, CONDUCTOR_CENTROID_DEPTH_M, CABLE.overall_od_m, n_cables=3)
        R_ca = Ti + Te

        T_c_model = conductor_temperature(row.I_A, row.T_amb_C, 0.0, rdc, Y_c, R_ca)
        T_sheath_model = T_c_model - row.I_A**2 * rdc * Ti  # sheath ≈ conductor - insulation drop

        results.append({
            "time_d"         : row.time_d,
            "I_A"            : row.I_A,
            "theta_meas"     : row.theta_meas,
            "rho_Ccm_W"      : rho,
            "heat_rate_W_cm" : cable_heat_rate_W_per_cm(row.I_A),
            "T_sheath_meas"  : row.T_sheath_meas,
            "T_sheath_model" : T_sheath_model,
            "T_amb_C"        : row.T_amb_C,
        })

    df_out = pd.DataFrame(results)
    if df_out["T_sheath_meas"].notna().any():
        df_out["err_pct"] = (
            (df_out.T_sheath_model - df_out.T_sheath_meas)
            / df_out.T_sheath_meas * 100
        )
    return df_out


def print_nhk_check(df: pd.DataFrame):
    """
    NHR screening: compare cable heat rate against Bates NHR thresholds.
    [V Bates 2021 Ch 4, 8]
    """
    print("\n=== NHR Soil Drying Screening ===")
    print(f"  Sand NHR (probe 3/4\"):    {NHR_SAND_PROBE_W_PER_CM:.1f} W/cm [V Bates Ch 4]")
    print(f"  Cable equiv. NHR:          {NHR_CABLE_EQUIV_W_PER_CM:.1f} W/cm [V Bates Ch 4]")
    print(f"  Typical cable heat range:  {TYPICAL_CABLE_HEATRATE_MIN:.1f}–"
          f"{TYPICAL_CABLE_HEATRATE_MAX:.1f} W/cm [V Bates Ch 4]")

    if "heat_rate_W_cm" in df.columns:
        hr = df["heat_rate_W_cm"].dropna()
        print(f"\n  Darmstadt MF_III heat rates:")
        print(f"    Mean  = {hr.mean():.3f} W/cm")
        print(f"    Max   = {hr.max():.3f} W/cm")
        pct_above_nhr = (hr > NHR_CABLE_EQUIV_W_PER_CM).mean() * 100
        print(f"    Fraction above NHR ({NHR_CABLE_EQUIV_W_PER_CM} W/cm): "
              f"{pct_above_nhr:.1f}%")
        if pct_above_nhr > 0:
            print(f"    [WARNING] Some timesteps exceed NHR — soil drying may occur.")
        else:
            print(f"    [OK] All heat rates below NHR — soil drying unlikely [V Bates Ch 8].")


def plot_moisture_dynamics(df: pd.DataFrame, out_dir: Path):
    """Plot moisture and sheath temperature time series."""
    if df.empty or "theta_meas" not in df.columns:
        return
    fig, axes = plt.subplots(3, 1, figsize=(12, 9), sharex=True)
    x = df["time_d"].values

    axes[0].plot(x, df["theta_meas"], label="VWC at cable surface")
    axes[0].set_ylabel("Vol. moisture (m³/m³)")
    axes[0].set_title("Darmstadt MF_III_CL — Moisture and Sheath Temperature")
    axes[0].legend()

    axes[1].plot(x, df["rho_Ccm_W"], color="orange",
                 label="Thermal resistivity ρ(θ) [Johansen]")
    axes[1].set_ylabel("ρ (°C·cm/W)")
    axes[1].legend()

    axes[2].plot(x, df["T_sheath_meas"], label="Measured sheath T")
    axes[2].plot(x, df["T_sheath_model"], label="N-M model sheath T", ls="--")
    axes[2].set_ylabel("Sheath temp (°C)")
    axes[2].set_xlabel("Time (days)")
    axes[2].legend()

    fig.tight_layout()
    fname = out_dir / "mf_iii_cl_moisture_dynamics.png"
    fig.savefig(fname, dpi=120)
    print(f"\nPlot saved to {fname}")


if __name__ == "__main__":
    df = run_validation()

    if not df.empty:
        if "err_pct" in df.columns:
            e = df["err_pct"].dropna()
            print(f"\n=== MF_III_CL Sheath Temperature Validation ===")
            print(f"  n={len(e)}  mean error={e.mean():+.1f}%  std={e.std():.1f}%")

        print_nhk_check(df)

        out_dir = ROOT / "results" / "darmstadt_validation"
        out_dir.mkdir(parents=True, exist_ok=True)
        df.to_csv(out_dir / "mf_iii_cl.csv", index=False)
        plot_moisture_dynamics(df, out_dir)
        print(f"\nResults saved to {out_dir}/mf_iii_cl.csv")
