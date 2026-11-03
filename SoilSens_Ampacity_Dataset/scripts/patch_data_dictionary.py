"""
patch_data_dictionary.py
Adds new Reference_Installations columns to Data_Dictionary.csv and
updates the installation_id entry for the new REF_DEPTH_* naming.
"""

import csv, pathlib

DD_FILE = pathlib.Path(
    r"C:\Users\jtani\.gemini\antigravity\scratch\soil-heat-forecasting"
    r"\SoilSens_Ampacity_Dataset\05_Documentation\Data_Dictionary.csv"
)

FIELDNAMES = ['table_name', 'file', 'column_name', 'data_type', 'unit', 'description', 'missing_value_convention']
TABLE_COL  = 'table_name'
COL_COL    = 'column_name'

with open(DD_FILE, encoding="utf-8-sig") as f:
    rows = list(csv.DictReader(f))

# Remove old Reference_Installations entries that we're replacing
old_ref_cols = {
    "pipeline_depth_meaning", "standard_burial_cover_m", "standard_cover_definition",
    "conductor_centre_depth_derived_m", "derivation"
}
rows = [r for r in rows if not (r[TABLE_COL] == "Reference_Installations" and r[COL_COL] in old_ref_cols)]

# Update installation_id description for new IDs
for r in rows:
    if r[TABLE_COL] == "Reference_Installations" and r[COL_COL] == "installation_id":
        r["description"] = "Stable scenario identifier (REF_DEPTH_24IN, REF_DEPTH_30IN, REF_DEPTH_36IN)"
    if r[TABLE_COL] == "Reference_Cases" and r[COL_COL] == "installation_id":
        r["description"] = "FK to Reference_Installations.installation_id (REF_DEPTH_24IN / 30IN / 36IN)"

def dd(table, col, dtype, unit, desc, missing=""):
    return {
        "table_name": table, "file": "", "column_name": col,
        "data_type": dtype, "unit": unit, "description": desc,
        "missing_value_convention": missing,
    }

RI = "Reference_Installations"
RC = "Reference_Cases"

new_entries = [
    dd(RI, "scenario_description",    "string", "-",  "Prose explanation of what the scenario represents and which PG&E requirement it relates to, if any"),
    dd(RI, "pipeline_model_depth_m",  "float",  "m",  "Depth value passed to neher_mcgrath.py as depth to cable centre; equals nominal inch label x 0.0254"),
    dd(RI, "pipeline_depth_meaning",  "string", "-",  "Explanation of what pipeline_model_depth_m represents (cover value used as cable-centre depth)"),
    dd(RI, "cover_to_conduit_top_m",  "float",  "m",  "PG&E-specified cover depth from finished grade to top of conduit", "empty = no PG&E standard at this depth"),
    dd(RI, "pge_cover_definition",    "string", "-",  "Verbatim description of the PG&E cover requirement (standard, voltage class)"),
    dd(RI, "conduit_od_m",            "float",  "m",  "Conduit outside diameter in metres (Sched 40 PVC 4-in nominal = 0.1143 m)"),
    dd(RI, "conduit_outer_radius_m",  "float",  "m",  "conduit_od_m / 2; addend for conduit_centre_depth_m"),
    dd(RI, "conduit_centre_depth_m",  "float",  "m",  "Depth to conduit centreline = cover_to_conduit_top_m + conduit_outer_radius_m; PG&E-derived, NOT the pipeline model depth", "empty = no confirmed cover value"),
    dd(RI, "cable_position_in_conduit","string","-",  "Assumed position of cable(s) inside conduit for cable-centre depth calculation"),
    dd(RI, "geometry_assumption",     "string", "-",  "Explicit statement of the geometric assumption (concentric, no sag, etc.)"),
    dd(RI, "cable_centre_depth_m",    "float",  "m",  "Depth to conductor centre derived from PG&E cover + conduit geometry; distinct from pipeline_model_depth_m", "empty = not calculable"),
    dd(RI, "pge_derived_depth_calculation_status", "string", "-",
       "Whether ampacity has been recalculated with cable_centre_depth_m (currently: NOT YET CALCULATED for 24/30 in)"),
    dd(RC, "depth_caveat",            "string", "-",
       "Explanation of pipeline depth and PG&E-derived depth; flags NOT YET CALCULATED where applicable"),
]

existing_keys = {(r[TABLE_COL], r[COL_COL]) for r in rows}
new_entries = [e for e in new_entries if (e[TABLE_COL], e[COL_COL]) not in existing_keys]
rows.extend(new_entries)

with open(DD_FILE, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
    writer.writeheader()
    writer.writerows(rows)

print(f"Data_Dictionary: {len(rows)} entries total ({len(new_entries)} new added)")
