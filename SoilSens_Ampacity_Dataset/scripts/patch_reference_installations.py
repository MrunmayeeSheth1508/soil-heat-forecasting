"""
patch_reference_installations.py
Rewrites Reference_Installations.csv with an explicit split between:
  - the pipeline calculation depth (what was modelled: nominal inch x 0.0254)
  - the PG&E-derived cover specification and the conduit-geometry-derived cable-centre depth

The three rows are now labelled as cable-centre-depth scenarios, not as
PG&E primary installations. The PG&E-derived geometry is included as an
additional set of columns, clearly distinct from the scenario depth.
"""

import csv, pathlib

OUT = pathlib.Path(
    r"C:\Users\jtani\.gemini\antigravity\scratch\soil-heat-forecasting"
    r"\SoilSens_Ampacity_Dataset\03_Installation_and_Materials\Reference_Installations.csv"
)

FIELDS = [
    "installation_id",
    "scenario_status",
    "scenario_description",
    "utility",
    "cable_id",
    "conduit_type",
    "conduit_od_mm",
    "conduit_id_mm",
    "conduit_od_m",
    "n_cables_modelled",
    "cable_arrangement",
    # --- Pipeline calculation depth ---
    "scenario_label_in",
    "pipeline_model_depth_m",
    "pipeline_depth_meaning",
    # --- PG&E cover specification ---
    "cover_to_conduit_top_m",
    "pge_cover_definition",
    # --- Conduit-geometry-derived cable-centre depth (not used in existing calculations) ---
    "conduit_outer_radius_m",
    "conduit_centre_depth_m",
    "cable_position_in_conduit",
    "geometry_assumption",
    "cable_centre_depth_m",
    "pge_derived_depth_calculation_status",
    # --- Other ---
    "backfill_assumed_by_pipeline",
    "source_reference",
    "notes",
]

CONDUIT_OD_MM = 114.3    # 4-inch nominal Schedule 40 PVC OD
CONDUIT_ID_MM = 100.6
CONDUIT_OD_M  = CONDUIT_OD_MM / 1000   # 0.1143 m
CONDUIT_OD_R_M = CONDUIT_OD_M / 2      # 0.05715 m

ROWS = [
    # ---- 24-inch scenario ----
    {
        "installation_id":          "REF_DEPTH_24IN",
        "scenario_status":          "cable-centre-depth scenario (selected; not a measured installation)",
        "scenario_description":     "Depth scenario using 24 in (0.610 m) as the model depth to cable centre. "
                                    "PG&E EDS 038193 specifies 24 in as the secondary/service minimum cover to conduit top.",
        "utility":                  "Pacific Gas & Electric (design standard — cover depth only)",
        "cable_id":                 "SW_350KCMIL_CU_15KV_EPR",
        "conduit_type":             "Rigid PVC Schedule 40, 4 in nominal",
        "conduit_od_mm":            str(CONDUIT_OD_MM),
        "conduit_id_mm":            str(CONDUIT_ID_MM),
        "conduit_od_m":             f"{CONDUIT_OD_M:.4f}",
        "n_cables_modelled":        "3",
        "cable_arrangement":        "trefoil, 7.5 in centre-to-centre spacing (Black Books assumption)",
        # pipeline
        "scenario_label_in":        "24",
        "pipeline_model_depth_m":   "0.610",
        "pipeline_depth_meaning":   "Nominal inch label x 0.0254, passed as depth to cable centre in neher_mcgrath.py",
        # PG&E cover
        "cover_to_conduit_top_m":   "0.610",
        "pge_cover_definition":     "PG&E secondary/service minimum cover, top of conduit to finished grade (EDS 038193 Rev16)",
        # Derived geometry
        "conduit_outer_radius_m":   f"{CONDUIT_OD_R_M:.5f}",
        "conduit_centre_depth_m":   f"{0.610 + CONDUIT_OD_R_M:.4f}",
        "cable_position_in_conduit":"assumed at conduit centre (conservative single-cable)",
        "geometry_assumption":      "concentric positioning; cable OD << conduit ID; no cable sagging modelled",
        "cable_centre_depth_m":     f"{0.610 + CONDUIT_OD_R_M:.4f}",
        "pge_derived_depth_calculation_status":
                                    "NOT YET CALCULATED — existing results use pipeline_model_depth_m (0.610 m), "
                                    "not this PG&E-derived depth (0.667 m). Effect on ampacity not yet quantified.",
        "backfill_assumed_by_pipeline": "soil thermal resistivity from measured moisture (Johansen); no thermal backfill modelled",
        "source_reference":         "PG&E EDS 038193 Rev16 / EDS 062288 Rev21 (June 2023); Southwire SPEC 46319; "
                                    "proposal/code/01_cable_thermal_model/cable_params.py",
        "notes":                    "24 in is the nominal label used to identify this scenario. "
                                    "The model received 0.610 m as the cable-centre depth.",
    },
    # ---- 30-inch scenario ----
    {
        "installation_id":          "REF_DEPTH_30IN",
        "scenario_status":          "cable-centre-depth scenario (selected; not a measured installation)",
        "scenario_description":     "Depth scenario using 30 in (0.762 m) as the model depth to cable centre. "
                                    "PG&E EDS 038193 specifies 30 in as the primary minimum cover to conduit top.",
        "utility":                  "Pacific Gas & Electric (design standard — cover depth only)",
        "cable_id":                 "SW_350KCMIL_CU_15KV_EPR",
        "conduit_type":             "Rigid PVC Schedule 40, 4 in nominal",
        "conduit_od_mm":            str(CONDUIT_OD_MM),
        "conduit_id_mm":            str(CONDUIT_ID_MM),
        "conduit_od_m":             f"{CONDUIT_OD_M:.4f}",
        "n_cables_modelled":        "3",
        "cable_arrangement":        "trefoil, 7.5 in centre-to-centre spacing (Black Books assumption)",
        # pipeline
        "scenario_label_in":        "30",
        "pipeline_model_depth_m":   "0.762",
        "pipeline_depth_meaning":   "Nominal inch label x 0.0254, passed as depth to cable centre in neher_mcgrath.py",
        # PG&E cover
        "cover_to_conduit_top_m":   "0.762",
        "pge_cover_definition":     "PG&E primary minimum cover, top of conduit to finished grade (EDS 038193 Rev16)",
        # Derived geometry
        "conduit_outer_radius_m":   f"{CONDUIT_OD_R_M:.5f}",
        "conduit_centre_depth_m":   f"{0.762 + CONDUIT_OD_R_M:.4f}",
        "cable_position_in_conduit":"assumed at conduit centre (conservative single-cable)",
        "geometry_assumption":      "concentric positioning; cable OD << conduit ID; no cable sagging modelled",
        "cable_centre_depth_m":     f"{0.762 + CONDUIT_OD_R_M:.4f}",
        "pge_derived_depth_calculation_status":
                                    "NOT YET CALCULATED — existing results use pipeline_model_depth_m (0.762 m), "
                                    "not this PG&E-derived depth (0.819 m). Effect on ampacity not yet quantified.",
        "backfill_assumed_by_pipeline": "soil thermal resistivity from measured moisture (Johansen); no thermal backfill modelled",
        "source_reference":         "PG&E EDS 038193 Rev16 / EDS 062288 Rev21 (June 2023); Southwire SPEC 46319; "
                                    "proposal/code/01_cable_thermal_model/cable_params.py",
        "notes":                    "CAUTION: The existing calculation depth (0.762 m) is the cover value, not the "
                                    "conductor-centre depth. The PG&E-derived conductor-centre depth is 0.819 m "
                                    "(cover + conduit OD/2). These are labelled separately; do NOT equate them. "
                                    "The 30 in row was previously mislabelled as the PG&E primary installation; "
                                    "it is a scenario using the cover value as the model depth.",
    },
    # ---- 36-inch scenario ----
    {
        "installation_id":          "REF_DEPTH_36IN",
        "scenario_status":          "cable-centre-depth scenario (selected; not a measured installation)",
        "scenario_description":     "Depth scenario using 36 in (0.914 m) as the model depth to cable centre. "
                                    "36 in appears as a Black Books reference depth and as the PG&E duct-window "
                                    "entry cover (EDS 062288 Note 2); it is not a PG&E primary standard cover.",
        "utility":                  "Pacific Gas & Electric (duct-window/Black Books reference only — not a primary cover standard)",
        "cable_id":                 "SW_350KCMIL_CU_15KV_EPR",
        "conduit_type":             "Rigid PVC Schedule 40, 4 in nominal",
        "conduit_od_mm":            str(CONDUIT_OD_MM),
        "conduit_id_mm":            str(CONDUIT_ID_MM),
        "conduit_od_m":             f"{CONDUIT_OD_M:.4f}",
        "n_cables_modelled":        "3",
        "cable_arrangement":        "trefoil, 7.5 in centre-to-centre spacing (Black Books assumption)",
        # pipeline
        "scenario_label_in":        "36",
        "pipeline_model_depth_m":   "0.914",
        "pipeline_depth_meaning":   "Nominal inch label x 0.0254, passed as depth to cable centre in neher_mcgrath.py",
        # PG&E cover — no primary standard
        "cover_to_conduit_top_m":   "",
        "pge_cover_definition":     "No PG&E primary cover standard at this depth; 36 in cited in EDS 062288 Note 2 "
                                    "for duct-window entries only",
        # Derived geometry — underdetermined without a confirmed cover value
        "conduit_outer_radius_m":   f"{CONDUIT_OD_R_M:.5f}",
        "conduit_centre_depth_m":   "",
        "cable_position_in_conduit":"assumed at conduit centre (conservative single-cable)",
        "geometry_assumption":      "concentric positioning; cable OD << conduit ID; no cable sagging modelled",
        "cable_centre_depth_m":     "",
        "pge_derived_depth_calculation_status":
                                    "NOT APPLICABLE — no confirmed PG&E cover standard at 36 in. "
                                    "Scenario is a Black Books reference depth, not a PG&E primary cover case.",
        "backfill_assumed_by_pipeline": "soil thermal resistivity from measured moisture (Johansen); no thermal backfill modelled",
        "source_reference":         "PG&E EDS 038193 Rev16 / EDS 062288 Rev21 (June 2023); Southwire SPEC 46319; "
                                    "proposal/code/01_cable_thermal_model/cable_params.py",
        "notes":                    "36 in is a scenario depth, not a PG&E primary standard. "
                                    "PG&E-derived cover and cable-centre depth columns are left empty.",
    },
]

with open(OUT, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=FIELDS)
    writer.writeheader()
    writer.writerows(ROWS)

print(f"Written {len(ROWS)} rows to {OUT}")
print("Columns:", FIELDS)
