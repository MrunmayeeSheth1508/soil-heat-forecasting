"""
dynamic_ampacity_pipeline.py — full integration pipeline
Soil forecast → depth interpolation → Johansen resistivity → N-M ampacity

This is the WP3 integration script described in PROPOSAL_DRAFT_v2.md.
It reads USCRN data, runs depth interpolation to cable burial depth,
converts soil moisture to thermal resistivity via Johansen, then
computes dynamic ampacity and compares against:
  (1) Static design ampacity [Black Books / IEEE 835 baseline]
  (2) Persistence-driven ampacity (soil state frozen at each t)
  (3) SCAN climatological reference (99th pctile from Bates 2021 [V])

Run from proposal/ root:
    python code/05_dynamic_ampacity/dynamic_ampacity_pipeline.py --station WBANID

Outputs (results/dynamic_ampacity/):
  - ampacity_timeseries_{station}.csv
  - ampacity_summary_{station}.csv
  - ampacity_plot_{station}.png
"""
import argparse
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
sys.path.insert(0, str(ROOT / "code" / "04_depth_interpolation"))

from neher_mcgrath import (
    dc_resistance_at_temp, ys_factor, yp_factor,
    T_insulation, T_jacket, T_duct, T_soil, ampacity, load_factor_correction
)
from johansen import johansen_lambda, lambda_to_rho_Ccm_per_W
from depth_interp import interpolate_to_depth, interpolate_moisture_linear
from cable_params import (
    Southwire350kcmil, PGEInstallation, ThermalRho,
    BlackBooksAssumptions
)


# ---------------------------------------------------------------------------
# Static cable setup (PG&E reference installation)
# [V cable_params.py; all values sourced from literature]
# ---------------------------------------------------------------------------
CABLE = Southwire350kcmil()
PGE   = PGEInstallation()
BB    = BlackBooksAssumptions()

# Pre-compute cable AC loss factor at 90°C (constant for a given cable type)
_rdc_90 = dc_resistance_at_temp(CABLE.rdc_25C_ohm_per_m, T_ref=25.0, T_oper=90.0)
_Ycs    = ys_factor(_rdc_90)
_Ycp    = yp_factor(_rdc_90, CABLE.conductor_od_m,
                    BB.CABLE_SPACING_M)
Y_C     = _Ycs + _Ycp

# Thermal resistances that do not vary with soil state
_Ti = T_insulation(ThermalRho.EPR_INSULATION,
                   CABLE.od_over_insulation_m, CABLE.conductor_od_m)
_Tj = T_jacket(ThermalRho.PVC_JACKET,
               CABLE.overall_od_m, CABLE.od_over_shield_m)
_Td = T_duct(ThermalRho.FIBER_PVC_DUCT,
             PGE.conduit_od_m, PGE.conduit_id_m)

# Static design ampacity (Black Books: RHO=90, Ta=20°C) [V Bates Table 3.1]
_Te_static = T_soil(BB.SOIL_RHO_Ccm_W, BB.BURIAL_DEPTH_M,
                    CABLE.overall_od_m, n_cables=3,
                    cable_spacing_m=BB.CABLE_SPACING_M, load_factor=1.0)
I_STATIC = ampacity(90.0, BB.AMBIENT_C, 0.0, _rdc_90, Y_C,
                    _Ti + _Tj + _Td + _Te_static)

# SCAN climatological reference: soil temp 99th pctile = 34.6°C @ 40"
# [V Bates 2021 Ch 11 — Essex station 2185, San Bernardino CA]
SCAN_AMBIENT_C   = 34.6
SCAN_RHO_Ccm_W   = 157.0   # in-situ mean from Arizona [V Bates Ch 11]
_Te_scan = T_soil(SCAN_RHO_Ccm_W, PGE.cable_centre_depth_m,
                  PGE.conduit_od_m, n_cables=1, load_factor=1.0)
I_SCAN = ampacity(105.0, SCAN_AMBIENT_C, 0.0, _rdc_90, Y_C,
                  _Ti + _Tj + _Td + _Te_scan)


# ---------------------------------------------------------------------------
# Typical soil parameters for Johansen (used when Wilson table unavailable)
# [I — representative mid-range values]
# ---------------------------------------------------------------------------
DEFAULT_SOIL = dict(
    theta_sat=0.40,
    rho_dry_kg_per_m3=1550.0,
    quartz_fraction=0.50,
    is_coarse=True,
)


def compute_dynamic_ampacity_series(
    T_cable: np.ndarray,       # soil temperature at cable depth (°C)
    theta_cable: np.ndarray,   # VWC at cable depth (m³/m³)
    burial_depth_m: float,     # cable centre depth (m)
    load_factor: float = 0.66, # daily load factor [V Bates 2021 Ch 9]
    soil_params: dict = None,
) -> np.ndarray:
    """
    Compute dynamic ampacity at each timestep using Neher-McGrath.

    Parameters
    ----------
    T_cable       : hourly soil temperature at cable depth (°C) — ambient
    theta_cable   : hourly volumetric moisture content at cable depth
    burial_depth_m: cable centre depth (m); affects soil thermal resistance
    load_factor   : daily LF; applies load_factor_correction post-solve
    soil_params   : Johansen parameters; defaults to DEFAULT_SOIL if None

    Returns array of ampacity values (A). NaN where inputs are NaN.
    """
    if soil_params is None:
        soil_params = DEFAULT_SOIL
    N = len(T_cable)
    I_dyn = np.full(N, np.nan)

    for i in range(N):
        Ta = T_cable[i]
        th = theta_cable[i]
        if np.isnan(Ta) or np.isnan(th):
            continue

        lam = johansen_lambda(theta=th, **soil_params)
        rho = lambda_to_rho_Ccm_per_W(lam)

        Te = T_soil(rho, burial_depth_m, PGE.conduit_od_m,
                    n_cables=1, load_factor=load_factor)
        R_ca = _Ti + _Tj + _Td + Te

        I_ss = ampacity(105.0, Ta, 0.0, _rdc_90, Y_C, R_ca)
        I_dyn[i] = load_factor_correction(I_ss, load_factor)

    return I_dyn


def load_uscrn_station(wban_id: str) -> pd.DataFrame:
    """
    Load USCRN hourly02 text data for a station from data/uscrn/.
    Legacy path — kept for compatibility.
    [V uscrn_HEADERS.txt — 38 fields confirmed]
    """
    data_dir = ROOT / "data" / "uscrn"
    candidates = list(data_dir.glob(f"*{wban_id}*hourly02*"))
    if not candidates:
        raise FileNotFoundError(
            f"No USCRN file found for station {wban_id} in {data_dir}.\n"
            f"Download from https://www.ncei.noaa.gov/pub/data/uscrn/products/hourly02/"
        )
    df = pd.read_csv(candidates[0], sep=r"\s+", na_values=[-9999, -99, -9])
    return df


def load_npz_station(station_name: str) -> pd.DataFrame:
    """
    Load USCRN data from multistation NPZ files (2019–2021, concatenated).

    NPZ depth indices: 0=5cm, 1=10cm, 2=20cm, 3=50cm, 4=100cm [V]
    Returns columns: date, hour, ST_50cm, ST_100cm, SM_50cm, SM_100cm.

    Only stations with valid 50 cm AND 100 cm sensor data should be used
    (NaN rate < 50% at both depths). Shallow-only stations (e.g. AZ Yuma,
    CO Boulder with only 5/10 cm) are not valid for cable-depth interpolation
    — the target burial depth (0.61–0.91 m) lies outside the sensor range.
    [V multistation_npz/ dataset — 72 of 131 stations have valid 50+100 cm]
    """
    npz_dir = ROOT.parent.parent / "data" / "multistation_npz"
    if not npz_dir.exists():
        npz_dir = ROOT.parent / "data" / "multistation_npz"

    frames = []
    for yr in [2019, 2020, 2021]:
        fpath = npz_dir / f"{station_name}_{yr}.npz"
        if not fpath.exists():
            continue
        d = np.load(str(fpath), allow_pickle=True)
        sm = d["SM"]   # (N, 5)
        st = d["ST"]   # (N, 5)

        # Require 50cm (idx=3) and 100cm (idx=4) to be largely non-NaN
        for idx, label in [(3, "50 cm"), (4, "100 cm")]:
            nan_rate = np.isnan(sm[:, idx]).mean()
            if nan_rate > 0.50:
                raise ValueError(
                    f"Station '{station_name}' year {yr}: SM at {label} is "
                    f"{nan_rate:.0%} NaN — station lacks deep sensors. "
                    f"Only stations with valid 50+100 cm data are supported. "
                    f"Run 'python code/05_dynamic_ampacity/run_all_stations.py --list' "
                    f"to see valid stations."
                )

        frames.append(pd.DataFrame({
            "date"     : d["date"],
            "hour"     : d["hour"].astype(int),
            "ST_50cm"  : st[:, 3],   # 50 cm soil temperature
            "ST_100cm" : st[:, 4],   # 100 cm soil temperature
            "SM_50cm"  : sm[:, 3],   # 50 cm VWC
            "SM_100cm" : sm[:, 4],   # 100 cm VWC
        }))

    if not frames:
        raise FileNotFoundError(
            f"No NPZ files found for '{station_name}' in {npz_dir}.\n"
            f"Run 'python code/05_dynamic_ampacity/run_all_stations.py --list'"
        )
    return pd.concat(frames, ignore_index=True)


def run_station(station_id: str,
                burial_depth_m: float = None,
                load_factor: float = 0.66,
                soil_params: dict = None) -> pd.DataFrame:
    """
    Full pipeline for one USCRN station at a given burial depth.

    Parameters
    ----------
    station_id     : NPZ station name (e.g. 'NM_Socorro_20_N') or WBAN ID
    burial_depth_m : cable centre depth (m); must be in [0.50, 1.00] to stay
                     within the 50–100 cm USCRN sensor range.
                     Defaults to PGE.cable_centre_depth_m (0.762 m = 30").
    load_factor    : daily load factor [V Bates 2021 Ch 9: 0.66 validated]
    soil_params    : Johansen soil parameters; defaults to DEFAULT_SOIL

    Standard burial depths [V NEC Table 300.5 / PG&E EDS 038193]:
      24" = 0.610 m  — NEC minimum, direct-buried conduit
      30" = 0.762 m  — PG&E primary standard
      36" = 0.914 m  — heavy-traffic / transmission routes
    """
    if burial_depth_m is None:
        burial_depth_m = PGE.cable_centre_depth_m   # 0.762 m default

    if not (0.50 <= burial_depth_m <= 1.00):
        raise ValueError(
            f"burial_depth_m={burial_depth_m:.3f} m is outside [0.50, 1.00] m — "
            f"cannot interpolate between 50 cm and 100 cm USCRN sensors."
        )

    # Load station data
    if station_id.replace("_", "").replace("-", "").isdigit():
        df = load_uscrn_station(station_id)
        T_shallow  = df["SOIL_TEMP_50"].values.astype(float)
        T_deep     = df["SOIL_TEMP_100"].values.astype(float)
        th_shallow = df["SOIL_MOISTURE_50"].values.astype(float)
        th_deep    = df.get("SOIL_MOISTURE_100",
                            pd.Series(np.full(len(df), np.nan))).values.astype(float)
    else:
        df = load_npz_station(station_id)
        T_shallow  = df["ST_50cm"].values.astype(float)
        T_deep     = df["ST_100cm"].values.astype(float)
        th_shallow = df["SM_50cm"].values.astype(float)
        th_deep    = df["SM_100cm"].values.astype(float)

    # Interpolate to cable burial depth using Crank-Nicolson heat conduction
    # BCs: T_shallow = 50 cm, T_deep = 100 cm [V depth_interp.py]
    # Forward-fill NaN gaps in BCs before passing to C-N solver (gaps arise
    # from sensor outages; ffill preserves the trend across short gaps).
    T_shallow_ff  = pd.Series(T_shallow).ffill().bfill().values
    T_deep_ff     = pd.Series(T_deep).ffill().bfill().values
    th_shallow_ff = pd.Series(th_shallow).ffill().bfill().values
    th_deep_ff    = pd.Series(th_deep).ffill().bfill().values

    T_cable  = interpolate_to_depth(T_shallow_ff, T_deep_ff,
                                    target_depth_m=burial_depth_m)
    th_cable = interpolate_moisture_linear(th_shallow_ff, th_deep_ff,
                                           target_depth_m=burial_depth_m)

    # Restore NaN at timesteps where both BCs were originally NaN
    both_nan = np.isnan(T_shallow) & np.isnan(T_deep)
    T_cable[both_nan]  = np.nan
    th_cable[both_nan] = np.nan

    # Dynamic ampacity at each timestep
    I_dyn = compute_dynamic_ampacity_series(
        T_cable, th_cable,
        burial_depth_m=burial_depth_m,
        load_factor=load_factor,
        soil_params=soil_params,
    )

    # Persistence baseline: hold current shallow state constant
    I_persist = compute_dynamic_ampacity_series(
        T_shallow, th_shallow,
        burial_depth_m=burial_depth_m,
        load_factor=load_factor,
        soil_params=soil_params,
    )

    # Static reference for this burial depth
    _Te_static_d = T_soil(BB.SOIL_RHO_Ccm_W, burial_depth_m,
                          CABLE.overall_od_m, n_cables=3,
                          cable_spacing_m=BB.CABLE_SPACING_M, load_factor=1.0)
    I_static_d = ampacity(90.0, BB.AMBIENT_C, 0.0, _rdc_90, Y_C,
                          _Ti + _Tj + _Td + _Te_static_d)

    result = pd.DataFrame({
        "ST_50cm_C"    : T_shallow,
        "ST_100cm_C"   : T_deep,
        "ST_cable_C"   : T_cable,
        "SM_50cm"      : th_shallow,
        "SM_cable"     : th_cable,
        "burial_m"     : burial_depth_m,
        "I_dynamic_A"  : I_dyn,
        "I_persist_A"  : I_persist,
        "I_static_A"   : I_static_d,
        "I_scan_ref_A" : I_SCAN,
        "headroom_pct" : (I_dyn - I_static_d) / I_static_d * 100.0,
    })
    return result


def print_summary(df: pd.DataFrame, label: str):
    valid = df.dropna(subset=["I_dynamic_A"])
    hw = valid["headroom_pct"]
    depth_m = df["burial_m"].iloc[0]
    i_static = df["I_static_A"].iloc[0]
    print(f"\n=== Dynamic Ampacity — {label} (burial={depth_m:.3f} m) ===")
    print(f"  Static design ampacity (Black Books, RHO-90, Ta=20 degC): {i_static:.0f} A")
    print(f"  SCAN climatological reference (Bates 2021 [V]):           {I_SCAN:.0f} A")
    print(f"  Dynamic: mean={valid['I_dynamic_A'].mean():.0f} A  "
          f"min={valid['I_dynamic_A'].min():.0f} A  "
          f"max={valid['I_dynamic_A'].max():.0f} A")
    print(f"  Headroom vs static: mean={hw.mean():+.1f}%  std={hw.std():.1f}%")
    frac_5pct = (hw > 5.0).mean() * 100
    print(f"  Hours with >5% headroom: {frac_5pct:.1f}%  |  "
          f"Hours below static: {(hw < 0).mean()*100:.1f}%")


def plot_series(df: pd.DataFrame, label: str, out_dir: Path):
    depth_m  = df["burial_m"].iloc[0]
    i_static = df["I_static_A"].iloc[0]
    fig, axes = plt.subplots(3, 1, figsize=(14, 10), sharex=True)
    x = np.arange(len(df))

    axes[0].plot(x, df["ST_50cm_C"],  label="50 cm",  alpha=0.7)
    axes[0].plot(x, df["ST_100cm_C"], label="100 cm", alpha=0.7)
    axes[0].plot(x, df["ST_cable_C"], label=f"{depth_m*100:.0f} cm (cable)", lw=2)
    axes[0].set_ylabel("Soil temp (degC)")
    axes[0].legend(fontsize=8)
    axes[0].set_title(f"{label}  — burial depth {depth_m:.3f} m")

    axes[1].plot(x, df["SM_50cm"],  label="VWC 50 cm",  alpha=0.7)
    axes[1].plot(x, df["SM_cable"], label=f"VWC {depth_m*100:.0f} cm", lw=2)
    axes[1].set_ylabel("VWC (m3/m3)")
    axes[1].legend(fontsize=8)

    axes[2].axhline(i_static, color="r",      ls="--",
                    label=f"Static (Black Books) {i_static:.0f} A")
    axes[2].axhline(I_SCAN,   color="orange", ls=":",
                    label=f"SCAN ref {I_SCAN:.0f} A")
    axes[2].plot(x, df["I_dynamic_A"], label="Dynamic (real soil)", lw=1.5)
    axes[2].plot(x, df["I_persist_A"], label="Persistence baseline",
                 alpha=0.5, ls="--")
    axes[2].set_ylabel("Ampacity (A)")
    axes[2].set_xlabel("Hour index (3 years)")
    axes[2].legend(fontsize=8)

    fig.tight_layout()
    fname = out_dir / f"ampacity_plot_{label}.png"
    fig.savefig(fname, dpi=120)
    plt.close(fig)
    print(f"  Plot -> {fname.name}")


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(
        description="Dynamic cable ampacity from USCRN soil state (50+100 cm sensors required)."
    )
    parser.add_argument("--station", default="OK_Stillwater_2_W",
                        help="Station name (e.g. 'OK_Stillwater_2_W') or WBAN ID")
    parser.add_argument("--depth", type=float, default=None,
                        help="Burial depth in metres [0.50-1.00], default=PGE 30in=0.762m")
    parser.add_argument("--load_factor", type=float, default=0.66,
                        help="Daily load factor [V Bates 2021 Ch 9]")
    args = parser.parse_args()

    out_dir = ROOT / "results" / "dynamic_ampacity"
    out_dir.mkdir(parents=True, exist_ok=True)

    depth_m = args.depth if args.depth else PGE.cable_centre_depth_m
    label   = f"{args.station}_d{depth_m:.3f}m"

    try:
        df = run_station(args.station, burial_depth_m=depth_m,
                         load_factor=args.load_factor)
    except (FileNotFoundError, ValueError) as e:
        print(f"[ERROR] {e}")
        sys.exit(1)

    print_summary(df, label)
    df.to_csv(out_dir / f"ampacity_timeseries_{label}.csv", index=False)
    plot_series(df, label, out_dir)
    print(f"Timeseries -> results/dynamic_ampacity/ampacity_timeseries_{label}.csv")
