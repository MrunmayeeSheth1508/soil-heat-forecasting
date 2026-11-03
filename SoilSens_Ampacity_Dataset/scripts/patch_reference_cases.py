"""
patch_reference_cases.py
Updates Reference_Cases.csv:
  - Renames installation_id from REF_PGE_PVC4_* to REF_DEPTH_*
  - Updates depth_caveat to match new explicit language
"""

import csv, pathlib

CASES_FILE = pathlib.Path(
    r"C:\Users\jtani\.gemini\antigravity\scratch\soil-heat-forecasting"
    r"\SoilSens_Ampacity_Dataset\04_Assessment_Cases\Reference_Cases.csv"
)

ID_MAP = {
    "REF_PGE_PVC4_24in": "REF_DEPTH_24IN",
    "REF_PGE_PVC4_30in": "REF_DEPTH_30IN",
    "REF_PGE_PVC4_36in": "REF_DEPTH_36IN",
}

CAVEAT_MAP = {
    "REF_DEPTH_24IN": (
        "pipeline_model_depth_m (0.610 m) = 24 in nominal cover x 0.0254, used as depth to cable centre. "
        "PG&E-derived cable-centre depth (cover + conduit OD/2) = 0.667 m. NOT YET CALCULATED with the corrected depth."
    ),
    "REF_DEPTH_30IN": (
        "pipeline_model_depth_m (0.762 m) = 30 in nominal cover x 0.0254, used as depth to cable centre. "
        "PG&E-derived cable-centre depth (cover + conduit OD/2) = 0.819 m. NOT YET CALCULATED with the corrected depth."
    ),
    "REF_DEPTH_36IN": (
        "pipeline_model_depth_m (0.914 m) = 36 in label x 0.0254, used as depth to cable centre. "
        "No PG&E primary cover standard at this depth; this is a Black Books reference depth scenario only."
    ),
}

with open(CASES_FILE, encoding="utf-8-sig") as f:
    rows = list(csv.DictReader(f))
    fieldnames = list(rows[0].keys())

updated = 0
for row in rows:
    old_id = row.get("installation_id", "")
    new_id = ID_MAP.get(old_id, old_id)
    if new_id != old_id:
        row["installation_id"] = new_id
        updated += 1
    if new_id in CAVEAT_MAP:
        row["depth_caveat"] = CAVEAT_MAP[new_id]

with open(CASES_FILE, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)

print(f"Updated {updated} installation_id values in {CASES_FILE.name}")
print(f"Total rows: {len(rows)}")
