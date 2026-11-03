"""
Part 2a - Darmstadt (Verschaffel-Drefke et al. 2021, TUdatalib-665) workbook -> readable CSVs.

Outputs
  02_Electricity_and_Cables/Experimental_Loading.csv
  02_Electricity_and_Cables/Experimental_Temperatures.csv
  02_Electricity_and_Cables/Load_Profiles.csv      (experimental profiles only here; reference scenarios added in part 2b)
  01_Soil_and_Climate/Darmstadt_Site_Weather.csv
  01_Soil_and_Climate/Darmstadt_Soil_Moisture.csv
  03_Installation_and_Materials/Material_Properties.csv  (Darmstadt materials; part 2b appends others)
  03_Installation_and_Materials/Material_Curves.csv

Nothing is interpolated or filled. Time in the workbook is elapsed days ('d'); both days and hours are kept.
"""
import numpy as np, pandas as pd, openpyxl
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
XLSX = ROOT.parent / "proposal" / "data" / "Data_CableTestSite_VerschaffelDrefkeetal2021.xlsx"
SRC = "Verschaffel-Drefke et al. 2021, Energies 14(23):7 (TUdatalib-665), workbook sheet "
ENC = "utf-8-sig"

NOTE = "Workbook sheet is named MF_III_CL (field section III) and its load header reads '(IV)'; paper Sec 3.3 / Fig 11 attribute this run to configuration II (two MV trefoils). Treated as config II."

wb = openpyxl.load_workbook(XLSX, read_only=True, data_only=True)

def rows(sheet, min_row=5):
    return [r for r in wb[sheet].iter_rows(min_row=min_row, values_only=True)]

def num(x):
    return float(x) if isinstance(x, (int, float)) and not isinstance(x, bool) else np.nan

# ---- sheet layouts (0-based column index in the sheet row; verified against header rows) ----
# (experiment_id, sheet, time_col, [(load_sensor, col, ...)], [(temp sensor...)], weather cols, moisture cols)
SILT, SAND, FBF, LOAM = "silt", "sand", "fluidized_backfill", "loam"
EXPS = {
 "MF_IV_CL": dict(sheet="Experiment - Data - MF_IV_CL", t=1,
                  loads=[("LOAD_IV", 2, "IV")],
                  temps=[(3, SILT), (4, SAND), (5, FBF), (6, LOAM)], temp_type="conductor",
                  wx=(9, 10, 11, 12, 13), profile="continuous (CL)"),
 "MF_IV_EVU": dict(sheet="Experiment - Data - MF_IV_EVU", t=1,
                  loads=[("LOAD_IV", 2, "IV")],
                  temps=[(3, SILT), (4, SAND), (5, FBF), (6, LOAM)], temp_type="conductor",
                  wx=(9, 10, 11, 12, 13), profile="EVU (utility) profile"),
 "MF_IV_PV": dict(sheet="Experiment - Data - MF_IV_PV", t=1,
                  loads=[("LOAD_IV", 2, "IV")],
                  temps=[(3, SILT), (4, SAND), (5, FBF), (6, LOAM)], temp_type="conductor",
                  wx=(9, 10, 11, 12, 13), profile="PV profile"),
 "MF_III_CL": dict(sheet="Experiment - Data - MF_III_CL", t=1,
                  loads=[("LOAD_II", 2, "II")],
                  temps=[(3, SILT), (4, SAND), (5, FBF), (6, LOAM)], temp_type="sheath",
                  wx=(18, 19, 20, 21, 22), profile="continuous (CL)",
                  moist=[(10, "silt"), (11, "silt_undisturbed"), (12, "sand"), (13, "sand_undisturbed"),
                         (14, "loam"), (15, "loam_undisturbed")], moist_t=9),
 "SF_V_VI": dict(sheet="Experiment - Data - SF_V+VI", t=1,
                  loads=[("LOAD_V", 2, "V"), ("LOAD_VI", 3, "VI")],
                  temps=[(4, "config_V|conductor"), (5, "config_V|protection_pipe"),
                         (6, "config_VI|conductor"), (7, "config_VI|protection_pipe")], temp_type=None,
                  wx=(10, 11, 12, 13, 14), profile="see source"),
}

load_rows, temp_rows, wx_rows, moist_rows = [], [], [], []
for eid, c in EXPS.items():
    data = rows(c["sheet"])
    ref = SRC + f"'{c['sheet']}'"
    for r in data:
        t_d = num(r[c["t"]])
        if np.isnan(t_d):
            continue
        for sid, col, cfg in c["loads"]:
            v = num(r[col])
            load_rows.append((eid, f"{eid}_{sid}", cfg, t_d, t_d * 24, v, "A", ref))
        for col, label in c["temps"]:
            v = num(r[col])
            if "|" in label:
                cfg, kind = label.split("|"); mat = ""
                sensor = f"{eid}_{cfg}_{kind}"; stype = kind; cfgid = cfg.replace("config_", "")
            else:
                sensor = f"{eid}_{c['temp_type']}_{label}"; stype = c["temp_type"]; mat = label
                cfgid = c["loads"][0][2]
            temp_rows.append((eid, sensor, cfgid, stype, mat, t_d, t_d * 24, v, "degC", ref))
        # weather block (time, air, soil-0.8m, time, precip)
        tw, ta, ts, tp, pp = c["wx"]
        wx_rows.append((eid, num(r[tw]), num(r[ta]), num(r[ts]), num(r[tp]), num(r[pp])))
        if "moist" in c:
            for col, label in c["moist"]:
                moist_rows.append((eid, f"{eid}_VWC_{label}", label, num(r[c["moist_t"]]), num(r[c["moist_t"]]) * 24, num(r[col]), "%", ref))

# ---------------- write tables ----------------
out2 = ROOT / "02_Electricity_and_Cables"; out1 = ROOT / "01_Soil_and_Climate"; out3 = ROOT / "03_Installation_and_Materials"

L = pd.DataFrame(load_rows, columns=["experiment_id", "sensor_id", "circuit_config", "elapsed_time_d", "elapsed_time_h", "electrical_load_A", "unit", "source_reference"])
L.insert(2, "installation_id", "DARM_CFG_" + L["circuit_config"])
L["config_note"] = np.where(L["experiment_id"] == "MF_III_CL", NOTE, "")
L.to_csv(out2 / "Experimental_Loading.csv", index=False, encoding=ENC)

T = pd.DataFrame(temp_rows, columns=["experiment_id", "sensor_id", "circuit_config", "sensor_type", "bedding_material", "elapsed_time_d", "elapsed_time_h", "temperature_C", "unit", "source_reference"])
T.insert(2, "installation_id", "DARM_CFG_" + T["circuit_config"])
T["config_note"] = np.where(T["experiment_id"] == "MF_III_CL", NOTE, "")
T.to_csv(out2 / "Experimental_Temperatures.csv", index=False, encoding=ENC)

Wraw = pd.DataFrame(wx_rows, columns=["experiment_id", "wx_time_d", "air_temperature_C", "soil_temperature_0p8m_C", "precip_time_d", "precipitation_mm_per_h"])
parts = []
for var, tcol, unit in (("air_temperature_C", "wx_time_d", "degC"), ("soil_temperature_0p8m_C", "wx_time_d", "degC"), ("precipitation_mm_per_h", "precip_time_d", "mm/h")):
    w = Wraw[["experiment_id", tcol, var]].rename(columns={tcol: "elapsed_time_d", var: "value"}).dropna(subset=["elapsed_time_d"])
    w.insert(1, "variable", var); w["unit"] = unit
    parts.append(w)
W = pd.concat(parts, ignore_index=True)
# the workbook repeats each 30-min / 1-h weather sample on every 10-min cable row: keep one row per sample
chk = W.groupby(["experiment_id", "variable", "elapsed_time_d"])["value"].nunique(dropna=False)
assert (chk <= 1).all(), "same weather sample time with different values"
W = W.drop_duplicates(["experiment_id", "variable", "elapsed_time_d"]).sort_values(["experiment_id", "variable", "elapsed_time_d"])
W["elapsed_time_h"] = W["elapsed_time_d"] * 24
W["source_reference"] = SRC + "(weather block of each experiment sheet)"
W.to_csv(out1 / "Darmstadt_Experiment_Weather.csv", index=False, encoding=ENC)

M = pd.DataFrame(moist_rows, columns=["experiment_id", "sensor_id", "bedding_material", "elapsed_time_d", "elapsed_time_h", "volumetric_water_content_pct", "unit", "source_reference"])
M = M.dropna(subset=["elapsed_time_d"]).drop_duplicates(["sensor_id", "elapsed_time_d"])
M.insert(2, "installation_id", "DARM_CFG_II")
M["config_note"] = NOTE
M.to_csv(out1 / "Darmstadt_Soil_Moisture.csv", index=False, encoding=ENC)

print("loading", L.shape, "temps", T.shape, "weather(long)", W.shape, "moisture", M.shape)

# long-term site weather
sw = []
for r in rows("Weather - Data - Temp", min_row=3):
    if r[1] is None:
        continue
    sw.append((r[1], num(r[2]), num(r[3]), num(r[4])))
SW = pd.DataFrame(sw, columns=["timestamp_local", "air_temperature_C", "soil_temperature_0p2m_C", "soil_temperature_0p8m_C"])
SW["source_reference"] = SRC + "'Weather - Data - Temp' (timezone not stated in workbook)"
SW.to_csv(out1 / "Darmstadt_Site_Weather.csv", index=False, encoding=ENC)
print("site weather", SW.shape, SW.timestamp_local.min(), SW.timestamp_local.max())

# ---------------- load profiles (24 h relative profiles) ----------------
lp = []
for r in rows("Load Profils", min_row=4):
    if r[1] is None:
        continue
    lp.append(r)
LP = []
for r in lp:
    h = num(r[1])
    LP.append(("DARMSTADT_EVU", "experimental", h, num(r[2]), "relative load (fraction of peak)", SRC + "'Load Profils'"))
    LP.append(("DARMSTADT_PV", "experimental", h, num(r[3]), "relative load (fraction of peak)", SRC + "'Load Profils'"))
LP = pd.DataFrame(LP, columns=["profile_id", "profile_type", "time_of_day_h", "relative_load", "unit", "source_reference"])
LP.to_csv(out2 / "Load_Profiles.csv", index=False, encoding=ENC)
print("load profiles", LP.shape)

# ---------------- material properties (Basic Bedding Properties) ----------------
mats = {"Silt": "DARM_SILT", "Sand": "DARM_SAND", "Fluidized Backfill": "DARM_FBF", "Loam": "DARM_LOAM",
        "Grouting Material (cable duct)": "DARM_GROUT"}
rs = rows("Basic Bedding Properties", min_row=1)
hdr = rs[1]
cols = {hdr[i]: i for i in range(5, 10) if hdr[i]}
mp = []; g = s1 = s2 = s3 = None; unit = None
for r in rs[2:]:
    if r[0]: g, s1, s2 = r[0], None, None
    if r[1]: s1, s2 = r[1], None
    if r[2]: s2 = r[2]
    if not any(x is not None for x in r[:5]):
        continue  # footnote / blank row
    s3 = r[3]
    if r[4]: unit = r[4]
    if all(r[ci] is None for ci in cols.values()):
        continue
    prop = " | ".join(x for x in [g, s1, s2, s3] if x)
    for mname, ci in cols.items():
        v = r[ci]
        if v is None:
            continue
        n = num(v)
        mp.append((mats[mname], mname, prop, n, "" if not np.isnan(n) else str(v), unit, SRC + "'Basic Bedding Properties'"))
MP = pd.DataFrame(mp, columns=["material_id", "material_name", "property", "value", "value_text", "unit", "source_reference"])
MP.to_csv(out3 / "Material_Properties.csv", index=False, encoding=ENC)
print("material properties", MP.shape)

# ---------------- material curves (TH Bedding Characteristic) ----------------
rs = rows("TH Bedding Characteristic", min_row=1)
names = rs[0]; curves = rs[1]; params = rs[2]; units = rs[3]; body = rs[4:]
mc = []
for m_idx, mname in enumerate(["Silt", "Sand", "Fluidized Backfill", "Loam"]):
    base = 1 + 6 * m_idx
    for k, ctype in enumerate(["water_retention", "unsaturated_hydraulic_conductivity", "thermal_conductivity_dryout"]):
        xc, yc = base + 2 * k, base + 2 * k + 1
        xn, yn = params[xc], params[yc]; xu, yu = units[xc], units[yc]
        for i, r in enumerate(body):
            x, y = num(r[xc]), num(r[yc])
            if np.isnan(x) and np.isnan(y):
                continue
            mc.append((mats[mname], mname, ctype, i + 1, xn, x, xu or "", yn, y, yu or "pF (-)" if ctype == "water_retention" else (yu or ""), SRC + "'TH Bedding Characteristic'"))
MC = pd.DataFrame(mc, columns=["material_id", "material_name", "curve_type", "point_no", "x_variable", "x_value", "x_unit", "y_variable", "y_value", "y_unit", "source_reference"])
MC.to_csv(out3 / "Material_Curves.csv", index=False, encoding=ENC)
print("material curves", MC.shape)
print(MC.groupby(["material_name", "curve_type"]).size())

