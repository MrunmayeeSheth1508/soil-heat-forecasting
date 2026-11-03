"""
load_darmstadt.py — load and clean the Darmstadt experimental dataset.
Returns tidy DataFrames for each released configuration.

Source: Verschaffel-Drefke et al. (2021), Energies 14, 7189.
Dataset: TUdatalib-665, CC BY-NC 4.0.
Verified sheet structure from notes/darmstadt_workbook_audit.md [V].

Released configurations:
  MF_IV_CL   — 39 days, constant load, 4 bedding types (conductor temp)
  MF_IV_EVU  — 5 days, utility load profile
  MF_IV_PV   — 5 days, PV load profile
  SF_V_VI    — 51 days, PVC duct (unfilled V + grouted VI)
  MF_III_CL  — 35 days, constant load, sheath temp + moisture

Run from proposal/ root:
    python code/03_darmstadt_validation/load_darmstadt.py
"""
import pandas as pd
import numpy as np
from pathlib import Path

ROOT      = Path(__file__).resolve().parents[2]
DATA_FILE = ROOT / "data" / "Data_CableTestSite_VerschaffelDrefkeetal2021.xlsx"


# ---------------------------------------------------------------------------
# Sheet name mapping (from workbook audit [V])
# ---------------------------------------------------------------------------
SHEET_MAP = {
    "MF_IV_CL" : "Experiment - Data - MF_IV_CL",   # constant load, 4 beddings [V inspect_workbook.py]
    "MF_IV_EVU": "Experiment - Data - MF_IV_EVU",   # EVU (utility) load profile [V]
    "MF_IV_PV" : "Experiment - Data - MF_IV_PV",    # PV load profile [V]
    "SF_V_VI"  : "Experiment - Data - SF_V+VI",     # duct configurations [V]
    "MF_III_CL": "Experiment - Data - MF_III_CL",   # sheath temp + moisture [V]
    "WEATHER"  : "Weather - Data - Temp",
    "BEDDING"  : "Basic Bedding Properties",
    "LOAD"     : "Load Profils",
    "TH"       : "TH Bedding Characteristic",
}


def _load_sheet(sheet_name: str, header_rows: int = 4) -> pd.DataFrame:
    """Load a data sheet, using rows 0..(header_rows-1) as multi-level header."""
    raw = pd.read_excel(DATA_FILE, sheet_name=sheet_name, header=None)
    # Combine header rows into a single string label
    header = raw.iloc[:header_rows].fillna("").astype(str)
    col_labels = [" / ".join(r.strip() for r in header[c] if r.strip())
                  for c in raw.columns]
    # Make column labels unique (handle empty or duplicate names)
    seen: dict = {}
    unique_labels = []
    for label in col_labels:
        if not label:
            label = "_empty_"
        if label in seen:
            seen[label] += 1
            label = f"{label}_{seen[label]}"
        else:
            seen[label] = 0
        unique_labels.append(label)
    df = raw.iloc[header_rows:].copy()
    df.columns = unique_labels
    df = df.reset_index(drop=True)
    # Drop all-NaN columns (separator columns)
    df = df.dropna(axis=1, how="all")
    # Convert remaining columns to numeric where possible
    for col in df.columns:
        if df[col].dtype == object:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def load_mf_iv_cl() -> pd.DataFrame:
    """
    MF IV constant-load experiment — primary validation target.
    39 days; conductor temperature in 4 bedding types (sand, loam, FTB, silt).
    [V darmstadt_workbook_audit.md]
    """
    df = _load_sheet(SHEET_MAP["MF_IV_CL"])
    return df


def load_mf_iv_evu() -> pd.DataFrame:
    """MF IV EVU (utility) load profile — 5 days. [V]"""
    return _load_sheet(SHEET_MAP["MF_IV_EVU"])


def load_mf_iv_pv() -> pd.DataFrame:
    """MF IV PV load profile — 5 days. [V]"""
    return _load_sheet(SHEET_MAP["MF_IV_PV"])


def load_sf_v_vi() -> pd.DataFrame:
    """
    SF V+VI — duct configurations, 51 days.
    Config V: PVC duct unfilled; Config VI: grouted.
    [V darmstadt_workbook_audit.md]
    """
    return _load_sheet(SHEET_MAP["SF_V_VI"])


def load_mf_iii_cl() -> pd.DataFrame:
    """
    MF III constant load — sheath temperature + soil moisture at cable surface.
    35 days. Primary source for moisture dynamics. [V]
    Note: MF_III sheet has 2-min resolution (SF sheet). [V audit]
    """
    return _load_sheet(SHEET_MAP["MF_III_CL"])


def load_weather() -> pd.DataFrame:
    """Calendar-dated weather sheet (2014 only, air + soil at -0.2 and -0.8 m)."""
    raw = pd.read_excel(DATA_FILE, sheet_name=SHEET_MAP["WEATHER"], header=None)
    header = raw.iloc[:2].fillna("").astype(str)
    col_labels = [" / ".join(r.strip() for r in header[c] if r.strip())
                  for c in raw.columns]
    df = raw.iloc[2:].copy()
    df.columns = col_labels
    df = df.reset_index(drop=True)
    # Parse datetime column (column index 1 in raw)
    date_col = col_labels[1]
    df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
    for col in df.columns:
        if col != date_col:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def load_bedding_properties() -> pd.DataFrame:
    """Basic bedding property table (single snapshot values)."""
    raw = pd.read_excel(DATA_FILE, sheet_name=SHEET_MAP["BEDDING"], header=None)
    return raw.dropna(how="all").dropna(axis=1, how="all").reset_index(drop=True)


def load_th_curves() -> pd.DataFrame:
    """
    Thermo-hydraulic bedding characteristic curves:
    thermal conductivity λ(θ), moisture retention, hydraulic conductivity.
    [V darmstadt_workbook_audit.md]
    Note: 'volumetric heat capacity' column is solid-phase only.
    Use johansen.volumetric_heat_capacity() for the corrected total.
    """
    return _load_sheet(SHEET_MAP["TH"], header_rows=3)


def load_load_profiles() -> pd.DataFrame:
    """EVU and PV 24-hour load profiles (relative units, 30-min resolution). [V]"""
    raw = pd.read_excel(DATA_FILE, sheet_name=SHEET_MAP["LOAD"], header=None)
    return raw.dropna(how="all").reset_index(drop=True)


# ---------------------------------------------------------------------------
# Quick summary on direct run
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    loaders = {
        "MF_IV_CL" : load_mf_iv_cl,
        "MF_IV_EVU": load_mf_iv_evu,
        "MF_IV_PV" : load_mf_iv_pv,
        "SF_V_VI"  : load_sf_v_vi,
        "MF_III_CL": load_mf_iii_cl,
        "WEATHER"  : load_weather,
        "BEDDING"  : load_bedding_properties,
        "TH_CURVES": load_th_curves,
    }
    for name, fn in loaders.items():
        df = fn()
        print(f"{name:15s}: shape={df.shape}, columns={list(df.columns)[:5]}...")
