"""
wilson_lookup.py — load Wilson et al. (2016) soil texture table and
return Johansen parameters for a USCRN station.

Reference:
  Wilson, T.B. et al. (2016). Soil climate analysis network (SCAN) data
  including bulk density, characteristic curve, chemical, textural, and
  carbon measurements. Supplemental Table T1 (xls).
  [V notes/AMPACITY_SOURCES_PARAMETERS_AND_GAPS.md — 27 of 39 stations confirmed]

The Wilson table maps USCRN station IDs to soil texture (% sand, silt, clay),
bulk density (g/cm³), and saturated moisture content at multiple depths.
These are used to parameterise the Johansen thermal conductivity model.

Run from proposal/ root:
    python code/02_soil_thermal_properties/wilson_lookup.py
"""
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Optional, Tuple

ROOT      = Path(__file__).resolve().parents[2]
WILSON_FILE = ROOT / "data" / "wilson_noaa_45305_DS1.pdf"   # or .xls if extracted

# ---------------------------------------------------------------------------
# Fallback parameter table built from verified literature values.
# Used when Wilson table is unavailable for a station (12 of 39 stations).
# [V AMPACITY_SOURCES_PARAMETERS_AND_GAPS.md §4.1]
# Texture classes follow USDA classification.
# ---------------------------------------------------------------------------
TEXTURE_DEFAULTS = {
    # texture_class: (theta_sat, rho_dry_kg_m3, quartz_fraction, is_coarse)
    "sand"        : (0.38, 1650, 0.82, True),
    "loamy_sand"  : (0.41, 1580, 0.68, True),
    "sandy_loam"  : (0.43, 1500, 0.55, True),
    "loam"        : (0.45, 1420, 0.35, False),
    "silt_loam"   : (0.46, 1390, 0.22, False),
    "silt"        : (0.46, 1350, 0.15, False),
    "clay_loam"   : (0.48, 1300, 0.12, False),
    "silty_clay"  : (0.50, 1250, 0.08, False),
    "clay"        : (0.51, 1200, 0.06, False),
}


def texture_to_class(pct_sand: float, pct_silt: float, pct_clay: float) -> str:
    """
    USDA texture triangle classification from sand/silt/clay percentages.
    Simplified decision tree — covers the most common classes.
    """
    if pct_sand >= 85:
        return "sand"
    elif pct_sand >= 70:
        return "loamy_sand"
    elif pct_sand >= 50:
        return "sandy_loam"
    elif pct_clay >= 40:
        if pct_silt >= 40:
            return "silty_clay"
        return "clay"
    elif pct_clay >= 27:
        return "clay_loam"
    elif pct_silt >= 50:
        if pct_clay < 12:
            return "silt" if pct_silt >= 80 else "silt_loam"
        return "silt_loam"
    else:
        return "loam"


def johansen_params_from_texture(
    pct_sand: float,
    pct_silt: float,
    pct_clay: float,
    rho_dry_g_cm3: Optional[float] = None,
    theta_sat: Optional[float] = None,
) -> dict:
    """
    Return Johansen model parameters from soil texture data.
    If rho_dry and theta_sat are provided (from Wilson table), use them;
    otherwise fall back to TEXTURE_DEFAULTS.

    Returns dict: {theta_sat, rho_dry_kg_per_m3, quartz_fraction, is_coarse}
    """
    tex_class = texture_to_class(pct_sand, pct_silt, pct_clay)
    defaults  = TEXTURE_DEFAULTS[tex_class]

    # Quartz fraction: approximate from sand content
    # (quartz is the dominant sand mineral for most US soils)
    # [I — standard approximation used in Dai et al. 2019, survey_thermohydraulic_2022]
    quartz = max(0.05, min(0.90, pct_sand / 100.0 * 0.85))

    theta_sat_use = theta_sat if theta_sat is not None else defaults[0]
    rho_dry_use   = (rho_dry_g_cm3 * 1000.0
                     if rho_dry_g_cm3 is not None else defaults[1])
    is_coarse     = defaults[3]

    return {
        "theta_sat"           : theta_sat_use,
        "rho_dry_kg_per_m3"   : rho_dry_use,
        "quartz_fraction"     : quartz,
        "is_coarse"           : is_coarse,
        "texture_class"       : tex_class,
    }


def load_wilson_table() -> Optional[pd.DataFrame]:
    """
    Attempt to load the Wilson et al. (2016) supplemental table.
    Returns None if the file is not available in parsed form.

    The Wilson table is available as a PDF (wilson_noaa_45305_DS1.pdf in data/).
    A parsed CSV (wilson_T1.csv) can be placed in data/ to enable station lookup.
    """
    csv_path = ROOT / "data" / "wilson_T1.csv"
    if csv_path.exists():
        return pd.read_csv(csv_path)

    # Check for the xls version (from the project repo)
    xls_candidates = list((ROOT / "data").glob("*wilson*T1*"))
    if xls_candidates:
        try:
            return pd.read_excel(xls_candidates[0])
        except Exception:
            pass

    return None


def get_station_soil_params(
    wban_id: str,
    depth_cm: float = 50.0,
) -> Tuple[dict, bool]:
    """
    Get Johansen parameters for a USCRN station from the Wilson table.

    Parameters
    ----------
    wban_id   : USCRN station WBAN ID (string)
    depth_cm  : target depth (cm); Wilson table has data at multiple depths

    Returns
    -------
    (params_dict, from_wilson)
        params_dict : Johansen parameters
        from_wilson : True if Wilson table was used; False if fallback
    """
    df = load_wilson_table()

    if df is not None:
        # Attempt to match station; column names may vary — try common names
        id_cols = [c for c in df.columns if "wban" in c.lower() or "station" in c.lower()]
        if id_cols:
            mask = df[id_cols[0]].astype(str).str.strip() == str(wban_id).strip()
            station_rows = df[mask]
            if not station_rows.empty:
                # Find closest depth
                depth_cols = [c for c in df.columns if "depth" in c.lower()]
                if depth_cols:
                    depth_vals = pd.to_numeric(
                        station_rows[depth_cols[0]], errors="coerce"
                    )
                    idx = (depth_vals - depth_cm).abs().idxmin()
                    row = station_rows.loc[idx]
                else:
                    row = station_rows.iloc[0]

                # Extract texture percentages
                sand = pd.to_numeric(row.get("pct_sand", row.get("Sand", np.nan)),
                                     errors="coerce")
                silt = pd.to_numeric(row.get("pct_silt", row.get("Silt", np.nan)),
                                     errors="coerce")
                clay = pd.to_numeric(row.get("pct_clay", row.get("Clay", np.nan)),
                                     errors="coerce")
                rho_dry = pd.to_numeric(
                    row.get("bulk_density", row.get("BD", np.nan)), errors="coerce"
                )
                theta_sat = pd.to_numeric(
                    row.get("theta_sat", row.get("ThetaSat", np.nan)), errors="coerce"
                )

                if not any(np.isnan(v) for v in [sand, silt, clay]):
                    params = johansen_params_from_texture(
                        float(sand), float(silt), float(clay),
                        rho_dry_g_cm3=None if np.isnan(rho_dry) else float(rho_dry),
                        theta_sat=None if np.isnan(theta_sat) else float(theta_sat),
                    )
                    return params, True

    # Fallback: return a mid-range loam as default
    print(f"[wilson_lookup] Wilson table not available for station {wban_id}; "
          f"using loam fallback. [I]")
    params = johansen_params_from_texture(30.0, 40.0, 30.0)  # loam
    return params, False


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import sys, io
    if hasattr(sys.stdout, 'buffer') and sys.stdout.encoding and sys.stdout.encoding.lower() in ("cp1252", "ascii"):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    print("=== Wilson lookup self-test ===\n")

    test_cases = [
        ("Sand",       85, 10,  5),
        ("Loamy sand", 75, 15, 10),
        ("Sandy loam", 60, 25, 15),
        ("Loam",       40, 35, 25),
        ("Silt loam",  20, 60, 20),
        ("Clay",       15, 20, 65),
    ]
    for label, s, si, c in test_cases:
        p = johansen_params_from_texture(s, si, c)
        print(f"  {label:12s}  → class={p['texture_class']:12s}  "
              f"θ_sat={p['theta_sat']:.2f}  "
              f"ρ_dry={p['rho_dry_kg_per_m3']:.0f} kg/m³  "
              f"q={p['quartz_fraction']:.2f}  "
              f"coarse={p['is_coarse']}")

    print("\nWilson table status:")
    df = load_wilson_table()
    if df is not None:
        print(f"  Loaded: {len(df)} rows, columns: {list(df.columns)[:6]}...")
    else:
        print("  Not found in data/. Place wilson_T1.csv in data/ to enable station lookup.")
        print("  27 of 39 USCRN stations have Wilson data [V AMPACITY_SOURCES_PARAMETERS_AND_GAPS.md]")
