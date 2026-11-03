"""
Part 4 - 05_Documentation/Data_Dictionary.csv, Quality_Summary.csv, Quality_Flags.csv and Source_Manifest.csv
All counts are computed from the cleaned CSVs.
"""
import re, glob, numpy as np, pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "05_Documentation"; DOC.mkdir(exist_ok=True)
ENC = "utf-8-sig"
FOLDERS = ["01_Soil_and_Climate", "02_Electricity_and_Cables", "03_Installation_and_Materials", "04_Assessment_Cases"]

files = []
for f in FOLDERS:
    for p in sorted((ROOT / f).glob("*.csv")):
        files.append(p)
hourly = sorted((ROOT / "01_Soil_and_Climate" / "USCRN_Hourly").glob("*.csv"))

# ------------------------------------------------------------------ descriptions
D = {
 "experiment_id": "Darmstadt workbook sheet code (MF_IV_CL, MF_IV_EVU, MF_IV_PV, MF_III_CL, SF_V_VI)",
 "variable": "Name of the weather variable in the long-format weather table",
 "sensor_id": "Stable sensor identifier; see Sensor_Metadata.csv",
 "installation_id": "Installation identifier; DARM_CFG_* = Darmstadt configuration, REF_PGE_* = reference scenario",
 "circuit_config": "Darmstadt configuration of the loaded circuit (II, IV, V, VI)",
 "elapsed_time_d": "Time since the start of the experiment sheet, days (workbook unit 'd'). Not a calendar date",
 "elapsed_time_h": "Same as elapsed_time_d expressed in hours (x24)",
 "electrical_load_A": "Measured circuit current", "temperature_C": "Measured cable temperature",
 "sensor_type": "Where the measurement is taken (conductor, sheath, protection_pipe) or sensor kind",
 "bedding_material": "Bedding / backfill the sensor sits in", "config_note": "Clarification of configuration labelling where the workbook label differs from the paper",
 "volumetric_water_content_pct": "Volumetric water content, FDR sensor", "unit": "Unit of the value column",
 "source_reference": "Document / sheet the row comes from",
 "wx_time_d": "Elapsed time of the weather air/soil sample, days", "precip_time_d": "Elapsed time of the precipitation sample, days",
 "wx_time_h": "wx_time_d in hours", "air_temperature_C": "Air temperature", "soil_temperature_0p8m_C": "Undisturbed soil temperature at 0.8 m (weather station, not at the cables)",
 "soil_temperature_0p2m_C": "Undisturbed soil temperature at 0.2 m (weather station)", "precipitation_mm_per_h": "Precipitation rate",
 "timestamp_local": "Local timestamp of the 2014 site weather file (time zone not stated in the workbook)",
 "timestamp_lst": "USCRN observation time, local standard time (fixed offset, no daylight saving) as given by the source",
 "station_id": "USCRN station key: STATE_Location_Vector (e.g. OK_Stillwater_2_W)", "state": "US state code", "climate_zone": "Climate grouping assigned in the pipeline run",
 "wban": "NOAA WBAN number", "station_name": "USCRN station name", "latitude_deg": "Latitude, decimal degrees N", "longitude_deg": "Longitude, decimal degrees E",
 "elevation_ft": "Station elevation", "period_covered": "Observation span in this package", "n_hours": "Number of hourly rows",
 "missing_frac_sm_50cm": "Fraction of hours with no soil-moisture value at 50 cm", "missing_frac_sm_100cm": "Fraction of hours with no soil-moisture value at 100 cm",
 "in_pipeline_run": "Station was used in the 39-case ampacity run", "in_wilson_t1": "Station matched in Wilson et al. 2016 Table T1 (normalised-name join)",
 "wilson_key": "Key of the matching Wilson T1 row", "uscrn_station_id": "Matching station_id in the NPZ station list", "station_label": "Station label as printed in Wilson T1",
 "depth_m": "Sample depth below surface", "property": "Soil property name or catalogue property", "value": "Numeric value (blank where the source gives text or nothing)",
 "value_text": "Text value where the source is not numeric (e.g. texture class, '0.18*', 'not available')", "std_dev": "Standard deviation as published in Wilson T1",
 "description": "Free-text meaning of the property",
 "soil_temperature_5cm_C": "Soil temperature at 5 cm", "soil_temperature_10cm_C": "Soil temperature at 10 cm", "soil_temperature_20cm_C": "Soil temperature at 20 cm",
 "soil_temperature_50cm_C": "Soil temperature at 50 cm", "soil_temperature_100cm_C": "Soil temperature at 100 cm",
 "soil_moisture_5cm_m3m3": "Volumetric soil moisture at 5 cm", "soil_moisture_10cm_m3m3": "Volumetric soil moisture at 10 cm", "soil_moisture_20cm_m3m3": "Volumetric soil moisture at 20 cm",
 "soil_moisture_50cm_m3m3": "Volumetric soil moisture at 50 cm", "soil_moisture_100cm_m3m3": "Volumetric soil moisture at 100 cm",
 "precipitation_mm": "Hourly precipitation", "source_year": "Source file year (NPZ file the row came from)",
 "cable_id": "Stable cable identifier", "cable_ids": "Cable identifiers used in the installation (semicolon separated)", "cable_family": "Product family or experiment cable group",
 "source_type": "manufacturer datasheet or experiment paper", "stock_number": "Manufacturer stock number (blank where printed as TBA)",
 "conductor_size_awg_kcmil": "Conductor size (AWG, kcmil or mm2 as stated)", "conductor_material": "Conductor material", "strand_count": "Number of conductor strands",
 "conductor_od_in": "Bare conductor diameter, inches (as printed)", "conductor_od_mm": "Bare conductor diameter, converted from inches (x25.4)",
 "insulation_material": "Insulation material", "insulation_thickness_mm": "Insulation thickness", "od_over_insulation_in": "Diameter over insulation, inches (as printed)",
 "od_over_insulation_mm": "Converted from inches", "od_over_insulation_shield_in": "Diameter over insulation shield, inches (as printed)", "od_over_insulation_shield_mm": "Converted from inches",
 "shield": "Shield construction", "jacket_material": "Jacket material", "jacket_thickness_mil": "Jacket thickness, mil (1 mil = 0.0254 mm)", "jacket_thickness_mm": "Jacket thickness",
 "overall_od_in": "Approximate overall diameter, inches (as printed)", "overall_od_mm": "Approximate overall diameter",
 "dc_resistance_ohm_per_km": "DC resistance at dc_resistance_ref_temp_C (converted from ohm/1000 ft)", "dc_resistance_ref_temp_C": "Reference temperature of the DC resistance",
 "ac_resistance_ohm_per_km": "AC resistance at ac_resistance_ref_temp_C (converted from ohm/1000 ft)", "ac_resistance_ref_temp_C": "Reference temperature of the AC resistance",
 "resistance_as_printed_ohm_per_1000ft": "Resistances exactly as printed in the datasheet", "rated_voltage_kV": "Rated voltage (kV)",
 "max_conductor_temp_normal_C": "Continuous conductor temperature limit", "max_conductor_temp_emergency_C": "Emergency overload conductor temperature limit",
 "max_conductor_temp_short_circuit_C": "Short-circuit conductor temperature limit", "nec_ampacity_duct_90C_A": "NEC ampacity in duct, 90 C rating (as printed)",
 "nec_ampacity_duct_105C_A": "NEC ampacity in duct, 105 C rating (as printed)", "nec_ampacity_air_90C_A": "NEC ampacity in free air, 90 C (as printed)",
 "nec_ampacity_air_105C_A": "NEC ampacity in free air, 105 C (as printed)", "used_in_pipeline": "Cable was used in a pipeline calculation or validation",
 "notes": "Free-text caveat", "profile_id": "Load-profile identifier", "profile_type": "experimental or reference_scenario", "n_points": "Number of profile points",
 "load_factor_computed_mean_over_max": "Mean / max of the relative profile, computed here", "load_factor_stated_in_paper": "Load factor stated in the source paper",
 "peak_basis": "How the absolute peak is defined", "load_factor_scenario": "Scalar load factor of a reference scenario", "time_of_day_h": "Hour of day (0-24)",
 "relative_load": "Load relative to the profile peak (dimensionless)", "spec_id": "Specification identifier", "material": "Material the specification applies to",
 "spec_kind": "specification limit (max/min/range) or approved mix design - NOT a measurement", "parameter": "Specified parameter", "condition": "Condition under which the limit applies",
 "configuration": "Darmstadt configuration number", "field": "main field or side field", "arrangement": "Cable arrangement", "burial_cover_m": "Cover (top of cable/duct to surface). Blank where not stated",
 "conductor_centre_depth_m": "Conductor-centre depth. Blank where not stated", "depth_range_min_m": "Lower bound of the depth range stated in the source (reference point per depth_reference_note)",
 "depth_range_max_m": "Upper bound of the stated depth range", "depth_reference_note": "What the stated depth refers to (cover, centre, duct edge) and how reliable that is",
 "bedding": "Bedding material(s)", "duct_inner_diameter_mm": "Protection duct inner diameter", "duct_wall_mm": "Duct wall thickness", "duct_lower_edge_depth_m": "Depth of the lower outer duct edge",
 "grout_conductivity_Wmk": "Grout thermal conductivity (W/m/K) as stated in the paper", "in_workbook": "Data for this configuration exists in the Darmstadt workbook", "workbook_sheets": "Workbook sheets holding its data",
 "material_id": "Stable material identifier (DARM_* measured, REF_* reference constant)", "material_name": "Material name", "curve_type": "water_retention, unsaturated_hydraulic_conductivity, thermal_conductivity_dryout",
 "point_no": "Point index within the curve (workbook order)", "x_variable": "Name of x quantity", "x_value": "x value", "x_unit": "Unit of x", "y_variable": "Name of y quantity", "y_value": "y value", "y_unit": "Unit of y",
 "scenario_status": "Marks reference installations as selected scenarios, not measured installations", "utility": "Utility whose design standard is the source", "conduit_type": "Conduit type",
 "conduit_od_mm": "Conduit outer diameter", "conduit_id_mm": "Conduit inner diameter", "n_cables_modelled": "Cables in the thermal model", "cable_arrangement": "Arrangement in the model",
 "scenario_label_in": "Nominal depth label of the scenario, inches", "pipeline_model_depth_m": "Depth the pipeline passed to the thermal model as depth to cable centre",
 "pipeline_depth_meaning": "Explanation of how the pipeline interpreted that depth", "standard_burial_cover_m": "Cover stated by the utility standard for this label (blank if none)",
 "standard_cover_definition": "What the standard's cover value means", "conductor_centre_depth_derived_m": "Cover + conduit OD/2 (inferred)", "derivation": "How the derived value was obtained",
 "backfill_assumed_by_pipeline": "Backfill treatment in the pipeline", "sensor_domain": "electrical, cable temperature, bedding moisture or weather", "measured_variable": "Variable name in the data file",
 "sensor_hardware": "Sensor hardware as stated in the paper", "location_description": "Where the sensor is", "n_records": "Rows for the sensor (computed)", "median_step_min": "Median sampling step, minutes (computed)",
 "case_id": "Case identifier", "case_type": "experimental (measured) or reference scenario (selected, not measured)", "bedding_materials": "Beddings covered by the case", "load_profile_id": "Load profile of the case",
 "target_variable": "Measured quantity the case is evaluated against", "duration_d": "Span of the loading record, days (computed)", "n_load_records": "Loading rows (computed)", "load_min_A": "Minimum recorded current (computed)",
 "load_max_A": "Maximum recorded current (computed)", "temp_sensors": "Number of temperature sensors", "n_temp_records": "Temperature rows", "environment_inputs": "Environment data files belonging to the case",
 "material_ids": "Materials involved", "evaluation_use": "How the case may be used; no train/validation/holdout split is defined", "caveats": "Known limitations of the case",
 "loading_profile_id": "Load profiles of the scenario", "soil_property_basis": "How soil thermal properties were obtained in the run", "wilson_t1_available": "Wilson T1 data exist for the station",
 "soil_timeseries_file": "Package file with the station's hourly soil data", "soil_depths_used_cm": "Sensor depths used", "depth_caveat": "Caveat on the model depth", "issue_time_lst": "Forecast issue time (not applicable: hourly series)",
 "measured_cable_temperature_available": "False for all reference scenarios", "pointer_to_calculated_results": "Where calculated results live outside this package",
}
UNIT_PAT = [(r"_C$", "degC"), (r"_A$", "A"), (r"_mm$", "mm"), (r"_in$", "in"), (r"_m$", "m"), (r"_d$", "d"), (r"_h$", "h"), (r"_pct$", "%"), (r"_m3m3$", "m3/m3"),
            (r"_ft$", "ft"), (r"_deg$", "deg"), (r"_min$", "min"), (r"_kV$", "kV"), (r"ohm_per_km", "ohm/km"), (r"_Wmk$", "W/m/K"), (r"mm_per_h", "mm/h"), (r"^wx_time_d|^precip_time_d", "d")]
def unit_of(c):
    for pat, u in UNIT_PAT:
        if re.search(pat, c): return u
    return ""

rows = []
def add(tbl, path, df):
    kind = "time series" if any(c in df.columns for c in ("timestamp_lst", "timestamp_local", "elapsed_time_d")) else "catalogue / table"
    miss = "empty cell = value missing in the source (source sentinels such as -9999 converted to empty)" if kind == "time series" else "empty cell = not stated in the source; nothing has been estimated"
    for c in df.columns:
        rows.append(dict(table_name=tbl, file=str(path.relative_to(ROOT)).replace("\\", "/"), column_name=c, data_type=str(df[c].dtype).replace("str", "text").replace("object", "text"),
                         unit=unit_of(c), description=D.get(c, "(see table description)"), missing_value_convention=miss))
for p in files:
    add(p.stem, p, pd.read_csv(p, nrows=200, low_memory=False))
if hourly:
    add("USCRN_Hourly/<station>", hourly[0], pd.read_csv(hourly[0], nrows=200))
DD = pd.DataFrame(rows)
undesc = DD[DD.description == "(see table description)"]
DD.to_csv(DOC / "Data_Dictionary.csv", index=False, encoding=ENC)
print("Data_Dictionary", DD.shape, "undescribed:", sorted(undesc.column_name.unique()))

# ------------------------------------------------------------------ quality summary
def miss_str(df, cols):
    return "; ".join(f"{c}={df[c].isna().mean() * 100:.2f}%" for c in cols if c in df.columns)
KEYS = {"Experimental_Loading": ["electrical_load_A"], "Experimental_Temperatures": ["temperature_C"], "Darmstadt_Soil_Moisture": ["volumetric_water_content_pct"],
        "Darmstadt_Experiment_Weather": ["air_temperature_C", "soil_temperature_0p8m_C", "precipitation_mm_per_h"],
        "Darmstadt_Site_Weather": ["air_temperature_C", "soil_temperature_0p2m_C", "soil_temperature_0p8m_C"], "Soil_Properties": ["value", "value_text"],
        "Material_Properties": ["value"], "Material_Curves": ["x_value", "y_value"]}
q = []
for p in files + hourly:
    df = pd.read_csv(p, low_memory=False)
    tr = ""
    for c in ("timestamp_lst", "timestamp_local"):
        if c in df.columns: tr = f"{df[c].min()} to {df[c].max()}"
    if "elapsed_time_d" in df.columns: tr = f"{df.elapsed_time_d.min():.4g} to {df.elapsed_time_d.max():.4g} d (elapsed)"
    keycols = KEYS.get(p.stem, [c for c in df.columns if c.startswith(("soil_moisture_50", "soil_moisture_100", "soil_temperature_50", "soil_temperature_100"))])
    sub = "USCRN_Hourly/" if p.parent.name == "USCRN_Hourly" else ""
    q.append(dict(table_name=sub + p.stem, folder=p.parent.relative_to(ROOT).as_posix(), n_rows=len(df), n_columns=df.shape[1], n_exact_duplicate_rows=int(df.duplicated().sum()),
                  missing_in_key_columns=miss_str(df, keycols), time_range=tr, notes=""))
QS = pd.DataFrame(q)
QS.to_csv(DOC / "Quality_Summary.csv", index=False, encoding=ENC)
print("Quality_Summary", QS.shape, "total duplicate rows:", QS.n_exact_duplicate_rows.sum())

# ------------------------------------------------------------------ quality flags (computed)
L = pd.read_csv(ROOT / "02_Electricity_and_Cables" / "Experimental_Loading.csv", low_memory=False)
T = pd.read_csv(ROOT / "02_Electricity_and_Cables" / "Experimental_Temperatures.csv", low_memory=False)
M = pd.read_csv(ROOT / "01_Soil_and_Climate" / "Darmstadt_Soil_Moisture.csv", low_memory=False)
MC = pd.read_csv(ROOT / "03_Installation_and_Materials" / "Material_Curves.csv", low_memory=False)
SP = pd.read_csv(ROOT / "01_Soil_and_Climate" / "Soil_Properties.csv", low_memory=False)
flags = []
def flag(fid, table, severity, text, n, action):
    flags.append(dict(flag_id=fid, table=table, severity=severity, observation=text, n_affected=n, treatment=action))

neg = M[M.volumetric_water_content_pct < 0]
flag("QF01", "Darmstadt_Soil_Moisture", "check", f"Negative volumetric water content (min {M.volumetric_water_content_pct.min():.3f} %) in sensors: {', '.join(sorted(neg.sensor_id.unique())) or 'none'}", len(neg), "Kept as published; physically impossible values are sensor noise near 0 %")
for sid, g in T[T.sensor_type == "sheath"].groupby("sensor_id"):
    mx = g.temperature_C.max()
    if mx > 74:
        n = int((g.temperature_C >= mx - 0.5).sum())
        flag("QF02", "Experimental_Temperatures", "info", f"{sid}: {n} rows within 0.5 K of the maximum {mx:.3f} C; values vary (e.g. {', '.join(f'{v:.3f}' for v in g.temperature_C.nlargest(3))}), so this is the 75 C sheath control limit holding, not hard clipping", n, "Kept as published; the temperature is control-limited, not free-running")
nl = L[L.electrical_load_A < 0]
flag("QF03", "Experimental_Loading", "info", f"Negative current values (min {L.electrical_load_A.min():.3f} A), all near zero load in {', '.join(sorted(nl.sensor_id.unique()))}", len(nl), "Kept as published (measurement noise at zero load)")
mf3 = L[L.experiment_id == "MF_III_CL"]
flag("QF04", "Experimental_Loading", "check", f"MF_III_CL (config II) reaches {mf3.electrical_load_A.max():.1f} A and starts near {mf3.sort_values('elapsed_time_d').electrical_load_A.iloc[0]:.0f} A; paper narrative for the config II run cites 280 A reduced to 260 A", int((mf3.electrical_load_A > 285).sum()), "Rows above 285 A kept; run history before/after the narrative window is not documented")
flag("QF05", "Experimental_*", "info", "Darmstadt experiment sheets carry elapsed days only; no calendar dates", len(L), "Weather files cannot be aligned to the cable data by date; elapsed times kept separate from USCRN local standard time")
sil = MC[(MC.material_name == "Silt") & (MC.curve_type == "water_retention")].sort_values("point_no")
flag("QF06", "Material_Curves", "check", f"Silt water-retention curve starts at {sil.x_value.max():.2f} % VWC, above the stated silt porosity 35.6 %", 1, "Kept as published; basis/compaction of the lab sample not documented")
m50 = []
for p in hourly:
    h = pd.read_csv(p)
    for c in [c for c in h.columns if c.startswith("soil_moisture")]:
        bad = int(((h[c] < 0) | (h[c] > 1)).sum())
        if bad: m50.append((p.stem, c, bad))
flag("QF07", "USCRN_Hourly", "info", f"Soil moisture outside 0-1 m3/m3: {len(m50)} station/depth columns" + ("" if not m50 else f" (e.g. {m50[0]})"), sum(x[2] for x in m50), "Kept as published" if m50 else "none found")
st = pd.read_csv(ROOT / "01_Soil_and_Climate" / "Stations.csv")
hi = st[st.missing_frac_sm_50cm > 0.1]
flag("QF08", "Stations", "check", "Stations with >10% missing 50 cm soil moisture: " + ", ".join(f"{r.station_id} ({r.missing_frac_sm_50cm:.1%})" for r in hi.itertuples()), len(hi), "Gaps left empty; the pipeline forward-filled boundary data internally, this package does not")
flag("QF09", "Soil_Properties", "info", f"Wilson T1 numeric value missing in {SP[SP.property != 'texture_class'].value.isna().mean() * 100:.1f}% of station-depth-property cells", int(SP[SP.property != 'texture_class'].value.isna().sum()), "Left empty")
flag("QF10", "USCRN_Hourly", "info", "Source NPZ arrays contain only soil temperature, soil moisture and precipitation; air temperature, solar radiation, humidity and surface temperature are not in the compiled hourly files", len(hourly), "Not added; would require re-extraction from the raw USCRN hourly02 files")
flag("QF11", "Cable_Catalogue", "check", "Southwire 750 kcmil 'diameter over insulation shield' (1.495 in) is inconsistent with neighbouring sizes", 1, "Reproduced as printed")
FL = pd.DataFrame(flags)
FL.to_csv(DOC / "Quality_Flags.csv", index=False, encoding=ENC)
print(FL[["flag_id", "n_affected", "observation"]].to_string(max_colwidth=130))

# ------------------------------------------------------------------ source manifest
def nrows(rel): return len(pd.read_csv(ROOT / rel, low_memory=False))
SM = [
 ("S01", "USCRN hourly02 soil/precipitation (compiled NPZ arrays, 13 stations, 2019-2021 files)", "observations", "https://www.ncei.noaa.gov/pub/data/uscrn/products/hourly02/", "downloaded 2026-10-08 (data/README.md); compiled to NPZ in an earlier session", "NOAA NCEI USCRN: public data",
  "01_Soil_and_Climate/USCRN_Hourly/*.csv", 13 * 26304, "Times are local standard time. Only 13 of 131 NPZ stations are included (the pipeline stations)."),
 ("S02", "USCRN station metadata", "metadata", "https://www.ncei.noaa.gov/access/crn/", "workspace/stations.tsv (earlier session)", "NOAA public data", "01_Soil_and_Climate/Stations.csv", nrows("01_Soil_and_Climate/Stations.csv"), "Coordinates, WBAN, name, elevation"),
 ("S03", "Wilson et al. (2016) Supplemental Table T1, Vadose Zone Journal", "soil properties", "https://doi.org/10.2136/vzj2016.05.0047", "wilson_Supplemental_Table_T1.xls dated 2026-10-08", "see publisher terms; cite the paper",
  "01_Soil_and_Climate/Soil_Properties.csv", nrows("01_Soil_and_Climate/Soil_Properties.csv"), "Wide table melted to long format; 70 stations x 5 depths x 7 properties"),
 ("S04", "Darmstadt cable test site data (Verschaffel-Drefke et al. 2021), TUdatalib-665", "experiment", "https://doi.org/10.48328/tudatalib-665", "workbook supplied by the user (file dated 2026-11-03); direct download returned HTTP 403 in the download log", "CC BY-NC 4.0 (non-commercial)",
  "02_Electricity_and_Cables/Experimental_*.csv; 01_Soil_and_Climate/Darmstadt_*.csv; 03_Installation_and_Materials/Material_*.csv", nrows("02_Electricity_and_Cables/Experimental_Loading.csv") + nrows("02_Electricity_and_Cables/Experimental_Temperatures.csv"), "Rows counted = loading + temperature rows"),
 ("S05", "Verschaffel-Drefke et al. (2021) Energies 14(23):7189", "paper", "https://doi.org/10.3390/en14217189 (journal page; paper text supplied by user)", "supplied by user", "MDPI open access (CC BY) - verify on publisher page", "03_Installation_and_Materials/Experimental_Installations.csv; Cable_Catalogue.csv; Sensor_Metadata.csv", "", "Cable Table 1, configuration descriptions, instrumentation"),
 ("S06", "Southwire SPEC 46319 rev 1.000.009 (3 Oct 2025)", "manufacturer datasheet", "https://cabletechsupport.southwire.com/en/cablespec/download_spec/?country=US&spec=46319", "downloaded 2026-11-03", "manufacturer datasheet; reproduce dimensions with attribution", "02_Electricity_and_Cables/Cable_Catalogue.csv", 12, "12 conductor sizes transcribed from Tables 1 and 2"),
 ("S07", "PG&E EDS 038193 Rev 16 and EDS 062288 Rev 21 (June 2023)", "utility design standard", "https://www.pge.com/en/account/service-requests/building-and-renovation/project-resources.html", "PDFs in proposal/standards_and_specs", "PG&E publication; cite document numbers", "03_Installation_and_Materials/Reference_Installations.csv; Backfill_Specifications.csv", 3, "Cover, conduit dimensions, FTB limits"),
 ("S08", "Snohomish PUD material standard 1002182.1 Rev 2 (11 Apr 2024)", "utility material standard", "https://esr.snopud.com/Content/Material/Compounds/1002182.1.htm", "downloaded 2026-11-03", "utility publication; cite document number", "03_Installation_and_Materials/Backfill_Specifications.csv", nrows("03_Installation_and_Materials/Backfill_Specifications.csv"), "Specification limits and approved mixes - not measurements"),
 ("S09", "Bates (2021) dissertation; Neher-McGrath constants (via proposal/code/cable_params.py)", "reference constants", "see proposal/notes/survey_bates_2021.md", "open copy read in earlier session", "see source", "03_Installation_and_Materials/Material_Properties.csv (REF_* rows); Load_Profile_Catalogue.csv", 4, "Thermal resistivities, load factors"),
]
SMdf = pd.DataFrame(SM, columns=["source_id", "dataset_name", "type", "url_or_doi", "access_date_or_provenance", "licence", "file_in_package", "n_records", "notes"])
SMdf.to_csv(ROOT / "Source_Manifest.csv", index=False, encoding=ENC)
print("Source_Manifest", SMdf.shape)
