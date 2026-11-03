"""
Part 5 - Dataset_Overview.xlsx (16 sheets). Reads the cleaned CSVs; samples are labelled; no values are invented.
"""
import numpy as np, pandas as pd
from pathlib import Path
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

ROOT = Path(__file__).resolve().parents[1]
rd = lambda rel: pd.read_csv(ROOT / rel, low_memory=False)

COL = {"soil": "2E75B6", "elec": "ED7D31", "inst": "548235", "case": "7030A0", "doc": "7F7F7F"}
HDR = PatternFill("solid", fgColor="D9E2F3"); NOTE = PatternFill("solid", fgColor="FFF2CC")
BOLD = Font(bold=True); thin = Side(style="thin", color="BFBFBF")

wb = Workbook(); wb.remove(wb.active)

def sheet(name, color):
    ws = wb.create_sheet(name); ws.sheet_properties.tabColor = COL[color]; return ws

def text_rows(ws, rows, widths=(34, 70, 60, 50)):
    r = 1
    for row in rows:
        for j, v in enumerate(row if isinstance(row, (list, tuple)) else [row], 1):
            c = ws.cell(r, j, v); c.alignment = Alignment(wrap_text=True, vertical="top")
        if isinstance(row, str) and row.isupper() or (isinstance(row, (list, tuple)) and len(row) == 1 and str(row[0]).isupper()):
            ws.cell(r, 1).font = Font(bold=True, size=13)
        r += 1
    for j, w in enumerate(widths, 1): ws.column_dimensions[get_column_letter(j)].width = w
    return r

def table(ws, df, r0=1, title=None, note=None, maxw=55):
    if title:
        ws.cell(r0, 1, title).font = Font(bold=True, size=12); r0 += 1
    if note:
        c = ws.cell(r0, 1, note); c.fill = NOTE; c.alignment = Alignment(wrap_text=True, vertical="top")
        ws.merge_cells(start_row=r0, start_column=1, end_row=r0, end_column=min(8, max(2, df.shape[1]))); ws.row_dimensions[r0].height = 48; r0 += 1
    for j, c in enumerate(df.columns, 1):
        x = ws.cell(r0, j, str(c)); x.font = BOLD; x.fill = HDR; x.alignment = Alignment(wrap_text=True, vertical="top")
    for i, row in enumerate(df.itertuples(index=False), r0 + 1):
        for j, v in enumerate(row, 1):
            if isinstance(v, float) and np.isnan(v): v = None
            elif isinstance(v, (np.bool_, bool)): v = bool(v)
            elif isinstance(v, (np.integer,)): v = int(v)
            elif isinstance(v, (np.floating,)): v = float(v)
            ws.cell(i, j, v)
    for j, c in enumerate(df.columns, 1):
        vals = [len(str(c))] + [len(str(v)) for v in df.iloc[:200, j - 1].dropna().tolist()]
        ws.column_dimensions[get_column_letter(j)].width = min(maxw, max(10, max(vals) + 2))
    return r0 + len(df) + 2

# ------------------------------------------------------------------ data
ST = rd("01_Soil_and_Climate/Stations.csv")
SP = rd("01_Soil_and_Climate/Soil_Properties.csv")
EC = rd("04_Assessment_Cases/Experimental_Cases.csv"); RC = rd("04_Assessment_Cases/Reference_Cases.csv")
EI = rd("03_Installation_and_Materials/Experimental_Installations.csv"); RI = rd("03_Installation_and_Materials/Reference_Installations.csv")
CC = rd("02_Electricity_and_Cables/Cable_Catalogue.csv"); MP = rd("03_Installation_and_Materials/Material_Properties.csv")
MCV = rd("03_Installation_and_Materials/Material_Curves.csv"); BS = rd("03_Installation_and_Materials/Backfill_Specifications.csv")
DD = rd("05_Documentation/Data_Dictionary.csv"); QS = rd("05_Documentation/Quality_Summary.csv"); QF = rd("05_Documentation/Quality_Flags.csv")
SM = rd("Source_Manifest.csv"); L = rd("02_Electricity_and_Cables/Experimental_Loading.csv"); T = rd("02_Electricity_and_Cables/Experimental_Temperatures.csv")
OK = rd("01_Soil_and_Climate/USCRN_Hourly/OK_Stillwater_2_W.csv")

# ------------------------------------------------------------------ 1 Start_Here
ws = sheet("Start_Here", "doc")
text_rows(ws, [
 ["SOILSENS-AMPACITY DATASET PACKAGE"],
 ["Purpose", "Readable, organised data behind the SoilSens-Ampacity proposal: ground conditions, electrical loading / cable temperatures, and installation / material properties. Original downloads are not altered; every table here is a cleaned, named-column version with a source reference."],
 ["How to use", "This workbook is for inspection (samples + complete small tables). Complete data are in the CSV files next to it (folders 01-05). Tab colours: blue = soil & climate, orange = electricity & cables, green = installation & materials, purple = assessment cases, grey = documentation."],
 ["Sheet", "What you will find"],
 ["Domain_Overview", "The three domains, their roles, and which columns enter / leave each model."],
 ["Data_Dictionary", "Every column: type, unit, meaning, missing-value convention."],
 ["Stations / Soil_Weather_Sample / Soil_Properties", "USCRN stations; a labelled sample of hourly soil data (full data: 13 CSVs, ~26,300 rows each); Wilson soil texture / hydraulic properties."],
 ["Experiment_Catalogue / Electrical_Data_Sample / Cable_Catalogue", "Darmstadt runs; a labelled sample of recorded current and cable temperatures; cable constructions."],
 ["Installations / Material_Properties / Material_Curves / Backfill_Specifications", "Experimental and reference geometry (clearly distinguished); measured and reference material constants; measured curves; specification LIMITS (not measurements)."],
 ["Assessment_Cases", "Which inputs belong together for each task, and what each is evaluated against."],
 ["Quality_Summary / Sources", "Row counts, missingness, duplicates, flagged oddities; provenance and licences."],
 ["How the pieces connect", ""],
 ["Case", "Environment data | Electrical / installation data | Outcome"],
 ["Soil forecast (future SoilSens task)", "USCRN hourly soil + precipitation (01_Soil_and_Climate)", "Not required | Forecast scored against later measured soil values in the same files. No forecasts are included."],
 ["Cable experiment (Darmstadt)", "Darmstadt weather + materials", "Recorded current, cable, configuration | Calculated temperature compared with MEASURED cable temperature (Experimental_Temperatures)."],
 ["Reference installation", "USCRN soil conditions (13 stations)", "Selected cable, installation, loading scenario | Calculated ampacity - NOT in this package; no measured cable temperature exists for these pairings."],
 ["Important", "A US station-hour is never merged with a German cable temperature. Darmstadt times are elapsed days; USCRN times are local standard time. The reference cases are selected scenarios, not observed installations."],
 ["Not included", "Measured utility loading at the USCRN stations (none exists in the sources); model outputs; train/validation/holdout split definitions; USCRN air temperature, solar radiation and humidity (not in the compiled arrays); the other 118 USCRN stations."],
], widths=(46, 90, 70, 10))

# ------------------------------------------------------------------ 2 Domain_Overview
ws = sheet("Domain_Overview", "doc")
dom = pd.DataFrame([
 ["Soil and climate", "Describe and (later) forecast the ground conditions around a cable", "USCRN_Hourly (13 stations), Stations, Soil_Properties (Wilson), Darmstadt weather + moisture", "USCRN; Wilson et al. 2016; Darmstadt", "Later measured soil temperature / moisture"],
 ["Electricity and cables", "Describe heating, loading and cable construction", "Experimental_Loading, Experimental_Temperatures, Load_Profiles, Cable_Catalogue", "Darmstadt; Southwire; Verschaffel-Drefke 2021", "Measured conductor / sheath / pipe temperature under recorded current"],
 ["Installation and materials", "Describe the cable surroundings and heat-transfer properties", "Experimental_/Reference_Installations, Sensor_Metadata, Material_Properties/Curves, Backfill_Specifications", "Darmstadt; PG&E EDS; SnoPUD", "None - these are model inputs / specification limits"],
 ["Assessment cases", "Say which of the above belong together", "Experimental_Cases, Reference_Cases", "Compiled here", "Per case (see Assessment_Cases)"],
], columns=["Domain", "Role", "Tables", "Sources", "Measured evaluation target"])
r = table(ws, dom, title="Domains")
io = pd.DataFrame([
 ["Soil forecast (future)", "soil_temperature_{5..100}cm_C, soil_moisture_{5..100}cm_m3m3, precipitation_mm", "USCRN_Hourly/<station>.csv", "Predicted soil profile + uncertainty (NOT in package)", "Later hours of the same columns"],
 ["Dynamic ampacity reference run", "Soil T and moisture at 50 and 100 cm (interpolated to model depth); cable SW_350KCMIL_CU_15KV_EPR; REF_PGE_PVC4_*; load factor REF_LF_0.66", "USCRN_Hourly; Cable_Catalogue; Reference_Installations; Load_Profile_Catalogue", "Hourly dynamic ampacity (NOT in package)", "No measured counterpart"],
 ["Soil thermal properties", "Default Johansen parameters in the run; Wilson T1 texture available for 9 of the 13 stations but not yet used", "Soil_Properties; Stations.in_wilson_t1", "Soil thermal resistivity (NOT in package)", "-"],
 ["Darmstadt validation", "electrical_load_A; air temperature; soil temperature 0.8 m; precipitation; material properties and curves; DARM_MV150 cable", "Experimental_Loading; Darmstadt_Experiment_Weather; Material_*; Cable_Catalogue", "Calculated cable temperature (NOT in package)", "temperature_C (conductor / sheath / pipe)"],
], columns=["Task", "Model inputs (columns)", "Files", "Model outputs", "Evaluation target"])
table(ws, io, r0=r, title="Model input / output map", maxw=60)

# ------------------------------------------------------------------ 3 Data_Dictionary
table(sheet("Data_Dictionary", "doc"), DD, maxw=70)

# ------------------------------------------------------------------ 4 Stations
table(sheet("Stations", "soil"), ST, note="13 USCRN stations used in the 39-case ampacity run (valid 50 cm and 100 cm sensors). Times in the hourly files are local standard time. Blank wilson_key = no match in Wilson T1.")

# ------------------------------------------------------------------ 5 Soil_Weather_Sample
s = OK.iloc[:72].copy()
table(sheet("Soil_Weather_Sample", "soil"), s,
      note="SAMPLE ONLY: first 72 hourly rows (3 days) of OK_Stillwater_2_W. Full data: 01_Soil_and_Climate/USCRN_Hourly/OK_Stillwater_2_W.csv (26,304 rows). timestamp_lst = local standard time. Empty = missing. Temperatures degC; moisture m3/m3; precipitation mm.")

# ------------------------------------------------------------------ 6 Soil_Properties
table(sheet("Soil_Properties", "soil"), SP, note="Wilson et al. 2016 Table T1, long format (70 stations x 5 depths x 7 properties). value is numeric, value_text holds texture classes. Units 'as published' follow T1. Empty = not given in T1.")

# ------------------------------------------------------------------ 7 Experiment_Catalogue
ec = EC[["case_id", "experiment_id", "installation_id", "cable_ids", "bedding_materials", "load_profile_id", "target_variable", "duration_d", "n_load_records", "median_step_min", "load_min_A", "load_max_A", "caveats"]]
table(sheet("Experiment_Catalogue", "elec"), ec, note="Darmstadt runs available in the workbook. Durations / counts / steps are computed from the data. Time is elapsed days (no calendar dates). Conductor, sheath and pipe temperatures are different quantities - do not mix them.")

# ------------------------------------------------------------------ 8 Electrical_Data_Sample
ls = L[L.experiment_id == "MF_IV_CL"][["elapsed_time_h", "electrical_load_A"]].head(72)
ts = T[T.experiment_id == "MF_IV_CL"].pivot_table(index="elapsed_time_h", columns="bedding_material", values="temperature_C").add_prefix("conductor_temperature_C_").reset_index().head(72)
es = ls.merge(ts, on="elapsed_time_h", how="left")
table(sheet("Electrical_Data_Sample", "elec"), es, note="SAMPLE ONLY: first 72 rows (12 h) of experiment MF_IV_CL (configuration IV, constant load): recorded current and MEASURED conductor temperature in four beddings. elapsed_time_h = hours since start of the sheet. Full tables: Experimental_Loading.csv, Experimental_Temperatures.csv.")

# ------------------------------------------------------------------ 9 Cable_Catalogue
cc = CC.dropna(axis=1, how="all")
table(sheet("Cable_Catalogue", "elec"), cc, note="Southwire rows are transcribed from the datasheet (inches as printed plus mm conversion). Darmstadt rows come from paper Table 1. Resistances: ohm/km converted from ohm/1000 ft.")

# ------------------------------------------------------------------ 10 Installations
ws = sheet("Installations", "inst")
e = EI.dropna(axis=1, how="all"); rr = RI.dropna(axis=1, how="all")
r = table(ws, e, title="A. EXPERIMENTAL installations (Darmstadt, real measured site)", note="Depth fields keep cover, conductor-centre depth and range separate. Blank = not stated in the paper text (geometry is in figures only).")
table(ws, rr, r0=r, title="B. REFERENCE installations (selected scenarios from design standards - NOT measured)", note="pipeline_model_depth_m is what the model used as depth to cable centre; it is the nominal inch label, which for PG&E is a cover value. See pipeline_depth_meaning and notes.")

# ------------------------------------------------------------------ 11-13 materials
table(sheet("Material_Properties", "inst"), MP, note="DARM_* = measured by the Darmstadt team (workbook 'Basic Bedding Properties'); REF_* = reference constants. Volumetric heat capacity in the source is solid-phase only (specific heat x grain density). Texts such as '0.18*' (dry raw material before hardening) are kept in value_text.")
table(sheet("Material_Curves", "inst"), MCV, note="Measured curves from the Darmstadt workbook: water retention (VWC % vs pF), unsaturated hydraulic conductivity (m/s vs VWC %), thermal-conductivity dry-out (W/m/K vs VWC %). Each curve has its own x axis; point_no is workbook order.")
table(sheet("Backfill_Specifications", "inst"), BS, note="SPECIFICATION LIMITS from PG&E and SnoPUD standards - requirements a product must meet, not measured properties. Source values differ (e.g. PG&E 90 vs SnoPUD high-strength 75 C.cm/W at 0% moisture).")

# ------------------------------------------------------------------ 14 Assessment_Cases
ws = sheet("Assessment_Cases", "case")
ecs = EC[["case_id", "case_type", "experiment_id", "installation_id", "cable_ids", "load_profile_id", "target_variable", "environment_inputs", "evaluation_use", "caveats"]]
rcs = RC[["case_id", "case_type", "station_id", "climate_zone", "installation_id", "cable_id", "loading_profile_id", "soil_property_basis", "soil_timeseries_file", "pipeline_model_depth_m", "measured_cable_temperature_available", "notes"]]
r = table(ws, ecs, title="A. Experimental cases (measured outcome exists)", note="Inputs and outcome come from the same experiment. No train / validation / holdout split is defined in this package.")
table(ws, rcs, r0=r, title="B. Reference cases (selected scenarios; no measured outcome)", note="39 = 13 USCRN stations x 3 reference installation depths. Calculated results are not part of this package.")

# ------------------------------------------------------------------ 15 Quality_Summary
ws = sheet("Quality_Summary", "doc")
r = table(ws, QS, title="Table-level summary", maxw=60)
table(ws, QF, r0=r, title="Flagged observations (kept as published unless stated)", maxw=70)

# ------------------------------------------------------------------ 16 Sources
table(sheet("Sources", "doc"), SM, maxw=70)

order = ["Start_Here", "Domain_Overview", "Data_Dictionary", "Stations", "Soil_Weather_Sample", "Soil_Properties", "Experiment_Catalogue", "Electrical_Data_Sample",
         "Cable_Catalogue", "Installations", "Material_Properties", "Material_Curves", "Backfill_Specifications", "Assessment_Cases", "Quality_Summary", "Sources"]
wb._sheets = [wb[n] for n in order]
for w in wb.worksheets:
    w.freeze_panes = "A2" if w.title not in ("Start_Here", "Domain_Overview", "Installations", "Assessment_Cases", "Quality_Summary") else None
out = ROOT / "Dataset_Overview.xlsx"
wb.save(out)
print("saved", out, [(w.title, w.max_row) for w in wb.worksheets])
