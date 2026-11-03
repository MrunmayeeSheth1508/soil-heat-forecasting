"""
Part 1 — Build 01_Soil_and_Climate/ CSVs
  - Stations.csv          (13 pipeline stations + metadata)
  - Soil_Properties.csv   (Wilson T1 melted to long format)
  - USCRN_Hourly/*.csv    (one cleaned CSV per pipeline station, 2019-2021 concatenated)
"""

import os, sys, numpy as np, pandas as pd
from pathlib import Path

ROOT     = Path(__file__).resolve().parents[1]          # SoilSens_Ampacity_Dataset/
PROPOSAL = ROOT.parents[0] / "proposal"
NPZ_DIR  = ROOT.parents[0] / "data" / "multistation_npz"
OUT      = ROOT / "01_Soil_and_Climate"

# ------------------------------------------------------------------
# 13 pipeline stations (from run_all_stations.py)
# ------------------------------------------------------------------
PIPELINE_STATIONS = [
    # (npz_stem_prefix, climate_zone, state)
    ("NM_Socorro_20_N",        "Arid-SW",           "NM"),
    ("NM_Las_Cruces_20_N",     "Arid-SW",           "NM"),
    ("NV_Mercury_3_SSW",       "Arid-SW",           "NV"),
    ("TX_Monahans_6_ENE",      "Arid-SW",           "TX"),
    ("CA_Santa_Barbara_11_W",  "Mediterranean",      "CA"),
    ("CA_Bodega_6_WSW",        "Mediterranean",      "CA"),
    ("OR_Riley_10_WSW",        "Semi-arid-NW",       "OR"),
    ("OK_Stillwater_2_W",      "Sub-humid",          "OK"),
    ("NE_Lincoln_8_ENE",       "Sub-humid",          "NE"),
    ("AL_Fairhope_3_NE",       "Humid-subtropical",  "AL"),
    ("NC_Asheville_13_S",      "Humid-subtropical",  "NC"),
    ("WY_Sundance_8_NNW",      "Continental",        "WY"),
    ("MI_Chatham_1_SE",        "Continental",        "MI"),
]

YEARS = [2019, 2020, 2021]
DEPTHS_CM = [5, 10, 20, 50, 100]   # NPZ SM/ST indices 0-4


def norm(x):
    return str(x).upper().replace("_", "").replace(" ", "")

def load_wilson():
    return pd.read_csv(PROPOSAL / "data" / "wilson_T1.csv")

def load_station_meta():
    t = pd.read_csv(ROOT.parents[0] / "workspace" / "stations.tsv", sep="\t", dtype=str)
    t["nk"] = t["STATE"] + t["LOCATION"].str.upper().str.replace(" ", "") + t["VECTOR"].str.upper().str.replace(" ", "")
    return t.set_index("nk")

# ------------------------------------------------------------------
# Helper: load one NPZ year for a station stem
# ------------------------------------------------------------------
def load_npz(stem, year):
    fname = NPZ_DIR / f"{stem}_{year}.npz"
    if not fname.exists():
        return None
    d = np.load(fname)
    ts = pd.to_datetime(d["date"].astype(str), format="%Y%m%d") + pd.to_timedelta(d["hour"].astype(int), unit="h")
    df = pd.DataFrame({"timestamp_lst": ts})
    for j, depth in enumerate(DEPTHS_CM):
        df[f"soil_temperature_{depth}cm_C"] = d["ST"][:, j].astype(float)
        df[f"soil_moisture_{depth}cm_m3m3"] = d["SM"][:, j].astype(float)
    df["precipitation_mm"] = d["P"].astype(float)
    df["source_year"] = year
    num_cols = [c for c in df.columns if c not in ("timestamp_lst", "source_year")]
    df[num_cols] = df[num_cols].where(df[num_cols] > -999)   # USCRN sentinel -> NaN
    return df

# ------------------------------------------------------------------
# 1a. Build Stations.csv
# ------------------------------------------------------------------
def build_stations_csv():
    wil = load_wilson(); wk = {norm(k): k for k in wil["key"]}
    meta = load_station_meta()
    records = []
    for stem, climate, state in PIPELINE_STATIONS:
        nan50, nan100 = [], []
        for year in YEARS:
            f = NPZ_DIR / f"{stem}_{year}.npz"
            if f.exists():
                sm = np.load(f)["SM"]
                nan50.append(np.isnan(sm[:, 3]).mean()); nan100.append(np.isnan(sm[:, 4]).mean())
        nk = norm(stem)
        m = meta.loc[nk] if nk in meta.index else None
        records.append({
            "station_id": stem, "state": state, "climate_zone": climate,
            "wban": m["WBAN"] if m is not None else "",
            "station_name": m["NAME"] if m is not None else "",
            "latitude_deg": float(m["LATITUDE"]) if m is not None else float("nan"),
            "longitude_deg": float(m["LONGITUDE"]) if m is not None else float("nan"),
            "elevation_ft": float(m["ELEVATION"]) if m is not None else float("nan"),
            "period_covered": "2018-12-31 to 2021-12-31 (LST)",
            "n_hours": 26304,
            "missing_frac_sm_50cm": round(float(np.mean(nan50)), 4),
            "missing_frac_sm_100cm": round(float(np.mean(nan100)), 4),
            "in_pipeline_run": True,
            "in_wilson_t1": nk in wk,
            "wilson_key": wk.get(nk, ""),
        })
    df = pd.DataFrame(records)
    df.to_csv(OUT / "Stations.csv", index=False, encoding="utf-8-sig")
    print("[OK] Stations.csv", len(df), "rows;", int(df.in_wilson_t1.sum()), "in Wilson T1")
    return df

# ------------------------------------------------------------------
# 1b. Build Soil_Properties.csv  (Wilson T1 → long format)
# ------------------------------------------------------------------
def build_soil_properties_csv():
    wil = load_wilson()
    stems = {norm(f.name.rsplit("_", 1)[0]): f.name.rsplit("_", 1)[0] for f in NPZ_DIR.glob("*.npz")}
    DL = ["0.05", "0.1", "0.2", "0.5", "1.0"]
    META = {"silt": ("pct_silt", "%", "Silt fraction by mass"),
            "clay": ("pct_clay", "%", "Clay fraction by mass"),
            "sand": ("pct_sand", "%", "Sand fraction by mass"),
            "texclass": ("texture_class", "-", "Texture class as given in Wilson et al. 2016 Table T1"),
            "wp1500": ("wilting_point_1500kPa", "as published", "Water content at 1500 kPa, units as published in T1"),
            "fc33": ("field_capacity_33kPa", "as published", "Water content at 33 kPa, units as published in T1"),
            "bd": ("bulk_density", "as published", "Bulk density, units as published in T1")}
    rows = []
    for _, w in wil.iterrows():
        for dl in DL:
            for prop, (name, unit, desc) in META.items():
                v = w.get(f"{prop}_{dl}", np.nan); sd = w.get(f"{prop}_{dl}_sd", np.nan)
                num = pd.to_numeric(v, errors="coerce")
                rows.append({"wilson_key": w["key"], "uscrn_station_id": stems.get(norm(w["key"]), ""),
                             "state": w["state"], "station_label": w["wname"],
                             "latitude_deg": w["lat"], "longitude_deg": w["lon"],
                             "depth_m": float(dl), "property": name,
                             "value": num, "value_text": (str(v) if prop == "texclass" and pd.notna(v) else ""),
                             "std_dev": pd.to_numeric(sd, errors="coerce"),
                             "unit": unit, "description": desc})
    df = pd.DataFrame(rows)
    df.to_csv(OUT / "Soil_Properties.csv", index=False, encoding="utf-8-sig")
    mapped = df.groupby("wilson_key")["uscrn_station_id"].first().ne("").sum()
    print("[OK] Soil_Properties.csv", len(df), "rows;", df.wilson_key.nunique(), "stations;", mapped, "mapped to NPZ ids")
    return df

# ------------------------------------------------------------------
# 1c. Build USCRN_Hourly/<station>.csv
# ------------------------------------------------------------------
def build_uscrn_hourly():
    out_dir = OUT / "USCRN_Hourly"
    out_dir.mkdir(exist_ok=True)
    summary = []
    for stem, climate, state in PIPELINE_STATIONS:
        parts = []
        for year in YEARS:
            df_yr = load_npz(stem, year)
            if df_yr is not None:
                df_yr.insert(0, "station_id", stem)
                parts.append(df_yr)
        if not parts:
            print(f"[WARN] No NPZ data found for {stem}")
            continue
        df = pd.concat(parts, ignore_index=True).sort_values("timestamp_lst")
        csv_path = out_dir / f"{stem}.csv"
        df.to_csv(csv_path, index=False, encoding="utf-8", float_format="%.4g",
                  date_format="%Y-%m-%d %H:%M")
        n_missing_50 = df["soil_temperature_50cm_C"].isna().sum()
        print(f"[OK]  {stem}.csv  —  {len(df)} rows, {n_missing_50} NaN at 50cm")
        summary.append({"station_id": stem, "n_rows": len(df), "nan_50cm": n_missing_50})
    return summary

# ------------------------------------------------------------------
# MAIN
# ------------------------------------------------------------------
if __name__ == "__main__":
    print("=== Part 1: 01_Soil_and_Climate ===\n")
    build_stations_csv()
    build_soil_properties_csv()
    build_uscrn_hourly()
    print("\nDone.")
