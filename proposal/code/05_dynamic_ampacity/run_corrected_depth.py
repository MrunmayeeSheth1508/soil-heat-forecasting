"""
run_corrected_depth.py - deferred rerun with PG&E-derived cable-centre depths.

Calls the UNCHANGED pipeline (run_station) with
    cable_centre_depth = cover + conduit_OD/2   (concentric assumption)
for the 24 in and 30 in cover cases. 36 in has no PG&E primary cover
standard, so it is not rerun (its original 0.914 m centre-depth scenario stands).

Outputs go to results/dynamic_ampacity_corrected_depth/ ; the original
results/dynamic_ampacity/ folder is NOT modified.
"""
import sys
from pathlib import Path
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from run_all_stations import STATIONS, station_stats, ROOT
from dynamic_ampacity_pipeline import run_station

CONDUIT_OD_M = 4.500 * 0.0254   # as in cable_params.PGEInstallation (0.1143 m)
CASES = {
    "cover24in": 24 * 0.0254 + CONDUIT_OD_M / 2,   # 0.667 m
    "cover30in": 30 * 0.0254 + CONDUIT_OD_M / 2,   # 0.819 m
}

out = ROOT / "results" / "dynamic_ampacity_corrected_depth"
out.mkdir(parents=True, exist_ok=True)
rows = []
for meta in STATIONS:
    for label, d in CASES.items():
        df = run_station(meta["name"], burial_depth_m=d)
        df.to_csv(out / f"ampacity_timeseries_{meta['name']}_{label}.csv", index=False)
        r = station_stats(df, meta, label, d)
        rows.append(r)
        print(meta["name"], label, round(d, 4), round(r["mean_dynamic_A"], 1),
              round(r["I_static_A"], 1), round(r["mean_headroom_pct"], 1), flush=True)
pd.DataFrame(rows).to_csv(out / "multistation_summary_corrected_depth.csv",
                          index=False, float_format="%.2f")
print("done")
