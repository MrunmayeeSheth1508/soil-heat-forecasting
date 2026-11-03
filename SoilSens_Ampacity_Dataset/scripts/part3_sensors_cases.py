"""
Part 3 - Sensor_Metadata.csv, Experimental_Cases.csv, Reference_Cases.csv
Counts, durations and sampling steps are computed from the cleaned CSVs, not asserted.
Reference cases are *selected assessment cases* (station x installation x loading). They contain NO calculated results.
"""
import numpy as np, pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
C1, C2, C3, C4 = (ROOT / d for d in ("01_Soil_and_Climate", "02_Electricity_and_Cables", "03_Installation_and_Materials", "04_Assessment_Cases"))
C4.mkdir(exist_ok=True)
ENC = "utf-8-sig"
PAPER = "Verschaffel-Drefke et al. 2021, Energies 14(23):7189"

L = pd.read_csv(C2 / "Experimental_Loading.csv", low_memory=False)
T = pd.read_csv(C2 / "Experimental_Temperatures.csv", low_memory=False)
M = pd.read_csv(C1 / "Darmstadt_Soil_Moisture.csv", low_memory=False)

def step_min(df):
    d = np.diff(np.sort(df["elapsed_time_d"].dropna().unique())) * 24 * 60
    return round(float(np.median(d)), 2) if len(d) else np.nan

# ------------------------------------------------------------ Sensor metadata
rows = []
for sid, g in L.groupby("sensor_id"):
    rows.append(dict(sensor_id=sid, experiment_id=g.experiment_id.iloc[0], installation_id=g.installation_id.iloc[0],
                     sensor_domain="electrical", sensor_type="current (circuit load)", measured_variable="electrical_load_A",
                     bedding_material="", unit="A", sensor_hardware="AHR 500 B10 current transducer, true RMS, 1% accuracy (paper Sec 2.1.3)",
                     location_description="Cable loop current, single-phase induction loop", depth_m="",
                     n_records=len(g), median_step_min=step_min(g)))
for sid, g in T.groupby("sensor_id"):
    kind = g.sensor_type.iloc[0]
    rows.append(dict(sensor_id=sid, experiment_id=g.experiment_id.iloc[0], installation_id=g.installation_id.iloc[0],
                     sensor_domain="cable temperature", sensor_type=f"Pt100 on {kind.replace('_', ' ')}", measured_variable="temperature_C",
                     bedding_material=g.bedding_material.iloc[0] if pd.notna(g.bedding_material.iloc[0]) else "", unit="degC",
                     sensor_hardware="Pt100, class 1/10 DIN B (paper Sec 2.1.4)",
                     location_description={"conductor": "On the conductor, in the named bedding section", "sheath": "On the outer sheath, in the named bedding section (conductor sensors not available in all beddings for config II)",
                                           "protection_pipe": "Outer surface of the protection duct"}.get(kind, ""),
                     depth_m="", n_records=len(g), median_step_min=step_min(g)))
for sid, g in M.groupby("sensor_id"):
    und = "undisturbed" in sid
    rows.append(dict(sensor_id=sid, experiment_id=g.experiment_id.iloc[0], installation_id=g.installation_id.iloc[0],
                     sensor_domain="bedding moisture", sensor_type="FDR volumetric water content", measured_variable="volumetric_water_content_pct",
                     bedding_material=g.bedding_material.iloc[0], unit="%", sensor_hardware="METER ECH2O EC-5, +-3% VWC (paper Sec 2.1.4)",
                     location_description=("Undisturbed reference, >= 2.5 m horizontal distance from the cables" if und else "About 10 cm from the trefoils, between the two trefoils (config II)"),
                     depth_m="", n_records=len(g), median_step_min=step_min(g)))
for sid, var, unit, loc in [("DARM_WX_AIR", "air_temperature_C", "degC", "Weather station (paper Sec 2.1.4)"),
                            ("DARM_WX_SOIL_0p8m", "soil_temperature_0p8m_C", "degC", "Undisturbed soil at the weather station, not at the cables"),
                            ("DARM_WX_SOIL_0p2m", "soil_temperature_0p2m_C", "degC", "Undisturbed soil at the weather station (long-term file only)"),
                            ("DARM_WX_PRECIP", "precipitation_mm_per_h", "mm/h", "Weather station")]:
    rows.append(dict(sensor_id=sid, experiment_id="all (weather block)", installation_id="", sensor_domain="weather", sensor_type="weather station",
                     measured_variable=var, bedding_material="", unit=unit, sensor_hardware="not stated in paper", location_description=loc,
                     depth_m={"DARM_WX_SOIL_0p8m": 0.8, "DARM_WX_SOIL_0p2m": 0.2}.get(sid, ""), n_records="", median_step_min=""))
SM = pd.DataFrame(rows)
SM["source_reference"] = PAPER + "; workbook column headers; counts and steps computed from the cleaned CSVs"
SM["notes"] = "Sensor coordinates are not published in text (Fig 2/4 only); depth left blank unless stated."
SM.to_csv(C3 / "Sensor_Metadata.csv", index=False, encoding=ENC)
print("Sensor_Metadata", SM.shape)

# ------------------------------------------------------------ Experimental cases
def stats(exp, cfg=None):
    l = L[(L.experiment_id == exp) & ((L.circuit_config == cfg) if cfg else True)]
    t = T[(T.experiment_id == exp) & ((T.circuit_config == cfg) if cfg else True)]
    return dict(duration_d=round(l.elapsed_time_d.max() - l.elapsed_time_d.min(), 3), n_load_records=len(l), median_step_min=step_min(l),
                load_min_A=round(l.electrical_load_A.min(), 2), load_max_A=round(l.electrical_load_A.max(), 2),
                temp_sensors=len(t.sensor_id.unique()), n_temp_records=len(t))

C = [
 ("DARM_CASE_MF_IV_CL", "MF_IV_CL", "IV", "DARM_MV150_NA2XS(F)2Y_1x150", "silt; sand; fluidized_backfill; loam", "DARMSTADT_CONSTANT", "conductor temperature",
  "Last 5.5 weeks of the constant-load phase (paper Fig 7). Day 0 is not a steady state (conductor already 32-83 C)."),
 ("DARM_CASE_MF_IV_EVU", "MF_IV_EVU", "IV", "DARM_MV150_NA2XS(F)2Y_1x150", "silt; sand; fluidized_backfill; loam", "DARMSTADT_EVU", "conductor temperature",
  "Paper Fig 8 left (3 weeks); the workbook holds only the span shown in the data (see duration_d). Peak set to IEC 60853 value; amperes are in the loading file."),
 ("DARM_CASE_MF_IV_PV", "MF_IV_PV", "IV", "DARM_MV150_NA2XS(F)2Y_1x150", "silt; sand; fluidized_backfill; loam", "DARMSTADT_PV", "conductor temperature",
  "Paper Fig 8 right; workbook span only (see duration_d)."),
 ("DARM_CASE_MF_III_CL", "MF_III_CL", "II", "DARM_MV150_NA2XS(F)2Y_1x150 (two trefoils); DARM_LV_NAY2Y-J_4x150", "silt; sand; fluidized_backfill; loam", "DARMSTADT_CONSTANT", "sheath temperature",
  "Config II long-term run (paper Sec 3.3 / Fig 11); SHEATH not conductor temperature; 75 C sheath control limit. Sheet name refers to field section III. Companion FDR moisture in Darmstadt_Soil_Moisture.csv."),
 ("DARM_CASE_SF_V", "SF_V_VI", "V", "DARM_MV150_NA2XS(F)2Y_1x150", "natural sand; air-filled PVC duct", "see source (300 A for 18 d then control to ~90 C; then utility-profile phases)", "conductor and protection-pipe temperature",
  "Load starts at ~0 A (noise incl. a negative value). Do not mix with conductor temperatures of other cases."),
 ("DARM_CASE_SF_VI", "SF_V_VI", "VI", "DARM_MV150_NA2XS(F)2Y_1x150", "natural sand; grout-filled PVC duct", "see source (same phases as V; grouted load chosen to match conductor temperatures)", "conductor and protection-pipe temperature",
  "As SF_V."),
]
rows = []
for cid, exp, cfg, cab, bed, prof, tgt, cav in C:
    s = stats(exp, cfg)
    rows.append(dict(case_id=cid, case_type="experimental (measured)", experiment_id=exp, installation_id=f"DARM_CFG_{cfg}", cable_ids=cab,
                     bedding_materials=bed, load_profile_id=prof, target_variable=tgt, **s,
                     environment_inputs="Darmstadt_Experiment_Weather.csv (air T, soil T at 0.8 m, precipitation) - elapsed days, no calendar date",
                     material_ids="DARM_SILT; DARM_SAND; DARM_FBF; DARM_LOAM" + ("; DARM_GROUT" if exp == "SF_V_VI" else ""),
                     evaluation_use="Validation target for a cable thermal model driven by recorded current and Darmstadt boundary conditions. No train / validation / holdout split is defined in this package.",
                     caveats=cav, source_reference=PAPER + "; workbook sheet for " + exp))
EC = pd.DataFrame(rows)
EC.to_csv(C4 / "Experimental_Cases.csv", index=False, encoding=ENC)
print("Experimental_Cases", EC.shape)

# ------------------------------------------------------------ Reference cases (selected scenarios)
ST = pd.read_csv(C1 / "Stations.csv")
RI = pd.read_csv(C3 / "Reference_Installations.csv")
rows = []
n = 0
for _, s in ST.iterrows():
    for _, r in RI.iterrows():
        n += 1
        rows.append(dict(
            case_id=f"REF_CASE_{n:02d}", case_type="reference scenario (selected, not measured)", station_id=s.station_id, climate_zone=s.climate_zone,
            installation_id=r.installation_id, cable_id=r.cable_id, loading_profile_id="REF_LF_0.66 (dynamic); REF_LF_1.00 (static design baseline)",
            soil_property_basis="Johansen model with default parameters (quartz 0.50, saturated water content 0.40, dry density 1550 kg/m3) - Wilson T1 NOT used in this run",
            wilson_t1_available=bool(s.in_wilson_t1), wilson_key=s.wilson_key if pd.notna(s.wilson_key) else "",
            soil_timeseries_file=f"01_Soil_and_Climate/USCRN_Hourly/{s.station_id}.csv", soil_depths_used_cm="50 and 100 (interpolated to the model cable depth)",
            pipeline_model_depth_m=r.pipeline_model_depth_m, depth_caveat="Model depth is the nominal inch label, passed as depth to cable centre (see Reference_Installations.csv)",
            issue_time_lst="n/a - hourly series over the whole period", period_covered=s.period_covered,
            measured_cable_temperature_available=False,
            pointer_to_calculated_results="proposal/results/dynamic_ampacity/multistation_summary.csv (not part of this package)",
            notes="USCRN soil conditions combined with a selected installation and cable. This pairing is a scenario; there is no measured conductor temperature or utility load for it."))
RC = pd.DataFrame(rows)
RC.to_csv(C4 / "Reference_Cases.csv", index=False, encoding=ENC)
print("Reference_Cases", RC.shape)
print(EC[["case_id", "duration_d", "n_load_records", "median_step_min", "load_min_A", "load_max_A"]].to_string())
