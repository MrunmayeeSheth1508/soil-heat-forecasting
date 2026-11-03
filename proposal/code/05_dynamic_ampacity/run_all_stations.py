"""
run_all_stations.py — batch dynamic-ampacity runner

Loops over a set of USCRN stations with valid 50+100 cm soil sensor data
(required to bracket standard cable burial depths 24"–36"), calls
dynamic_ampacity_pipeline.run_station() at each burial depth, and writes:
  - per-station/depth timeseries CSVs + plots  (handled by pipeline)
  - results/dynamic_ampacity/multistation_summary.csv  (this script)

Stations are selected to cover diverse NOAA climate zones.
Stations without 50+100 cm sensor data are excluded — shallow-sensor
stations (e.g. AZ Yuma, CO Boulder with only 5/10 cm) cannot bracket
cable burial depths of 0.61–0.91 m.

Burial depths simulated [V NEC Table 300.5 / PG&E EDS 038193]:
  24" = 0.610 m — NEC minimum, direct-buried conduit
  30" = 0.762 m — PG&E primary cable standard [V EDS 038193]
  36" = 0.914 m — heavy-traffic routes / transmission cables

Run from proposal/ root:
    python code/05_dynamic_ampacity/run_all_stations.py
    python code/05_dynamic_ampacity/run_all_stations.py --list
    python code/05_dynamic_ampacity/run_all_stations.py --depths 30
"""
import argparse
import sys
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "code" / "01_cable_thermal_model"))
sys.path.insert(0, str(ROOT / "code" / "02_soil_thermal_properties"))
sys.path.insert(0, str(ROOT / "code" / "04_depth_interpolation"))

from dynamic_ampacity_pipeline import (
    run_station, print_summary, plot_series, I_STATIC, I_SCAN
)
from johansen import johansen_lambda, lambda_to_rho_Ccm_per_W

# ---------------------------------------------------------------------------
# Burial depths to simulate [V NEC Table 300.5 / PG&E EDS 038193]
# All must be within [0.50, 1.00] m for C-N interpolation between
# 50 cm and 100 cm USCRN sensor BCs.
# ---------------------------------------------------------------------------
BURIAL_DEPTHS_M = {
    "24in": 0.610,   # 0.610 m = 24"
    "30in": 0.762,   # 0.762 m = 30" (PG&E primary reference)
    "36in": 0.914,   # 0.914 m = 36"
}

# ---------------------------------------------------------------------------
# Station registry: diverse climate zones, all with valid 50+100 cm data
# [I — NOAA climate regions; confirmed via NaN-rate check on NPZ dataset]
# ---------------------------------------------------------------------------
STATIONS = [
    # --- Arid / Semi-arid West ---
    {
        "name"         : "NM_Socorro_20_N",
        "climate_zone" : "Arid-SW",
        "state"        : "NM",
        "description"  : "Socorro, NM — hot desert; PG&E-analogous arid SW",
    },
    {
        "name"         : "NM_Las_Cruces_20_N",
        "climate_zone" : "Arid-SW",
        "state"        : "NM",
        "description"  : "Las Cruces, NM — Chihuahuan desert; low annual moisture",
    },
    {
        "name"         : "NV_Mercury_3_SSW",
        "climate_zone" : "Arid-SW",
        "state"        : "NV",
        "description"  : "Mercury, NV — Mojave; very low moisture, hot summer",
    },
    {
        "name"         : "TX_Monahans_6_ENE",
        "climate_zone" : "Arid-SW",
        "state"        : "TX",
        "description"  : "Monahans, TX — Permian Basin; hot/dry, high RHO",
    },
    # --- Semi-arid / Mediterranean West (CA relevance) ---
    {
        "name"         : "CA_Santa_Barbara_11_W",
        "climate_zone" : "Mediterranean",
        "state"        : "CA",
        "description"  : "Santa Barbara, CA — PG&E service territory; Mediterranean",
    },
    {
        "name"         : "CA_Bodega_6_WSW",
        "climate_zone" : "Mediterranean",
        "state"        : "CA",
        "description"  : "Bodega Bay, CA — coastal CA; cool/moist year-round",
    },
    {
        "name"         : "OR_Riley_10_WSW",
        "climate_zone" : "Semi-arid-NW",
        "state"        : "OR",
        "description"  : "Riley, OR — high desert; cold dry winters",
    },
    # --- Sub-humid / Great Plains ---
    {
        "name"         : "OK_Stillwater_2_W",
        "climate_zone" : "Sub-humid",
        "state"        : "OK",
        "description"  : "Stillwater, OK — sub-humid; Bates 2021 reference region [V]",
    },
    {
        "name"         : "NE_Lincoln_8_ENE",
        "climate_zone" : "Sub-humid",
        "state"        : "NE",
        "description"  : "Lincoln, NE — sub-humid; mixed soil texture",
    },
    # --- Humid / Eastern US ---
    {
        "name"         : "AL_Fairhope_3_NE",
        "climate_zone" : "Humid-subtropical",
        "state"        : "AL",
        "description"  : "Fairhope, AL — humid subtropical; Wilson T1 matched [V]",
    },
    {
        "name"         : "NC_Asheville_13_S",
        "climate_zone" : "Humid-subtropical",
        "state"        : "NC",
        "description"  : "Asheville, NC — humid Appalachian; moderate temp",
    },
    # --- Continental ---
    {
        "name"         : "WY_Sundance_8_NNW",
        "climate_zone" : "Continental",
        "state"        : "WY",
        "description"  : "Sundance, WY — cold continental; large seasonal swing",
    },
    {
        "name"         : "MI_Chatham_1_SE",
        "climate_zone" : "Continental",
        "state"        : "MI",
        "description"  : "Chatham, MI — Great Lakes continental; cold winters",
    },
]


def station_stats(df: pd.DataFrame, station_meta: dict,
                  depth_label: str, depth_m: float) -> dict:
    """Compute summary statistics for one station/depth result DataFrame."""
    valid = df.dropna(subset=["I_dynamic_A"])
    hw    = valid["headroom_pct"]
    i_static = df["I_static_A"].iloc[0]
    rho_series = valid["SM_cable"].apply(
        lambda th: _theta_to_rho(th) if not np.isnan(th) else np.nan
    )
    return {
        "station"            : station_meta["name"],
        "climate_zone"       : station_meta["climate_zone"],
        "state"              : station_meta["state"],
        "burial_depth_label" : depth_label,
        "burial_depth_m"     : depth_m,
        "n_hours_valid"      : len(valid),
        "mean_dynamic_A"     : valid["I_dynamic_A"].mean(),
        "min_dynamic_A"      : valid["I_dynamic_A"].min(),
        "max_dynamic_A"      : valid["I_dynamic_A"].max(),
        "I_static_A"         : i_static,
        "mean_headroom_pct"  : hw.mean(),
        "std_headroom_pct"   : hw.std(),
        "frac_gt5pct"        : (hw > 5.0).mean() * 100,
        "frac_below_static"  : (hw < 0.0).mean() * 100,
        "mean_Ta_C"          : valid["ST_cable_C"].mean(),
        "max_Ta_C"           : valid["ST_cable_C"].max(),
        "mean_SM_cable"      : valid["SM_cable"].mean(),
        "mean_rho_Ccm_W"     : rho_series.mean(),
        "I_scan_ref_A"       : I_SCAN,
    }


def _theta_to_rho(theta: float) -> float:
    """Approximate Johansen lambda->rho for summary stats (default params)."""
    lam = johansen_lambda(
        theta=theta,
        theta_sat=0.40,
        rho_dry_kg_per_m3=1550.0,
        quartz_fraction=0.50,
        is_coarse=True,
    )
    return lambda_to_rho_Ccm_per_W(lam)


def main():
    parser = argparse.ArgumentParser(
        description="Batch dynamic ampacity across climate zones and burial depths."
    )
    parser.add_argument("--list", action="store_true",
                        help="List stations and exit")
    parser.add_argument("--stations", nargs="+", default=None,
                        help="Run only these stations (by name)")
    parser.add_argument("--depths", nargs="+", default=list(BURIAL_DEPTHS_M.keys()),
                        choices=list(BURIAL_DEPTHS_M.keys()),
                        help="Burial depths to run (default: all three)")
    args = parser.parse_args()

    if args.list:
        print("Stations (all have valid 50+100 cm sensor data):")
        for s in STATIONS:
            print(f"  {s['name']:35s}  {s['climate_zone']:22s}  {s['description']}")
        print("\nBurial depths:")
        for label, depth in BURIAL_DEPTHS_M.items():
            print(f"  {label}: {depth:.3f} m")
        return

    out_dir = ROOT / "results" / "dynamic_ampacity"
    out_dir.mkdir(parents=True, exist_ok=True)

    target_stations = STATIONS
    if args.stations:
        target_stations = [s for s in STATIONS if s["name"] in args.stations]

    target_depths = {k: BURIAL_DEPTHS_M[k] for k in args.depths}

    rows = []
    for meta in target_stations:
        name = meta["name"]
        print(f"\n{'='*65}")
        print(f"Station: {name}  [{meta['climate_zone']}]")
        print(f"{'='*65}")

        for depth_label, depth_m in target_depths.items():
            print(f"\n  -- Burial depth: {depth_label} ({depth_m:.3f} m) --")
            try:
                df = run_station(name, burial_depth_m=depth_m)
            except FileNotFoundError as e:
                print(f"  [SKIP] {e}")
                break
            except Exception as e:
                print(f"  [ERROR] {name} @ {depth_label}: {e}")
                import traceback; traceback.print_exc()
                continue

            tag = f"{name}_{depth_label}"
            print_summary(df, tag)
            plot_series(df, tag, out_dir)
            df.to_csv(out_dir / f"ampacity_timeseries_{tag}.csv", index=False)

            rows.append(station_stats(df, meta, depth_label, depth_m))

    if rows:
        summary_df = pd.DataFrame(rows)
        out_path = out_dir / "multistation_summary.csv"
        summary_df.to_csv(out_path, index=False, float_format="%.2f")
        print(f"\n{'='*65}")
        print(f"Multi-station summary -> {out_path}")
        cols = ["station", "burial_depth_label", "climate_zone",
                "mean_dynamic_A", "mean_headroom_pct", "mean_rho_Ccm_W", "mean_Ta_C"]
        print(summary_df[cols].to_string(index=False))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
