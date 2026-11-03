"""
patch_v11_rerun_and_audit.py - additive update of the dataset package (v1.0 -> v1.1)
 * Reference_Installations: status of PG&E-derived depth now 'calculated' (24, 30 in) with pointer
 * Reference_Cases: pointer to the depth-corrected results (original pointer kept)
 * Quality_Flags: QF12-QF17 for calculation issues found in the V4 audit (about project calculations, not data tables)
Original v1.0 ZIP is left unchanged.
"""
import csv, pathlib
D = pathlib.Path(r"C:\Users\jtani\.gemini\antigravity\scratch\soil-heat-forecasting\SoilSens_Ampacity_Dataset")

# --- Reference_Installations
f = D / "03_Installation_and_Materials" / "Reference_Installations.csv"
rows = list(csv.DictReader(open(f, encoding="utf-8-sig")))
flds = list(rows[0].keys())
S = {
 "REF_DEPTH_24IN": "CALCULATED 2026-11-04 with cable_centre_depth_m = 0.667 m (rerun, unchanged pipeline): dynamic rating change -0.06% to -1.18% vs the 0.610 m run, static rating -0.96%. Results: proposal/results/dynamic_ampacity_corrected_depth/ (not in this package). Original 0.610 m results kept.",
 "REF_DEPTH_30IN": "CALCULATED 2026-11-04 with cable_centre_depth_m = 0.819 m (rerun, unchanged pipeline): dynamic rating change -0.11% to -1.12% vs the 0.762 m run, static rating -0.75%. Results: proposal/results/dynamic_ampacity_corrected_depth/ (not in this package). Original 0.762 m results kept.",
}
for r in rows:
    if r["installation_id"] in S:
        r["pge_derived_depth_calculation_status"] = S[r["installation_id"]]
with open(f, "w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=flds); w.writeheader(); w.writerows(rows)

# --- Reference_Cases
f = D / "04_Assessment_Cases" / "Reference_Cases.csv"
rows = list(csv.DictReader(open(f, encoding="utf-8-sig")))
flds = list(rows[0].keys())
for r in rows:
    iid = r["installation_id"]
    if iid in ("REF_DEPTH_24IN", "REF_DEPTH_30IN"):
        r["pointer_to_calculated_results"] += ("; depth-corrected rerun: proposal/results/dynamic_ampacity_corrected_depth/"
                                               "multistation_summary_corrected_depth.csv (not part of this package)")
        r["depth_caveat"] = r["depth_caveat"].replace("NOT YET CALCULATED with the corrected depth.",
                                                      "Rerun with the corrected depth completed 2026-11-04; change in dynamic rating < 1.2%.")
with open(f, "w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=flds); w.writeheader(); w.writerows(rows)

# --- Quality_Flags (append only)
f = D / "05_Documentation" / "Quality_Flags.csv"
rows = list(csv.DictReader(open(f, encoding="utf-8-sig")))
flds = list(rows[0].keys())
have = {r["flag_id"] for r in rows}
new = [
 ("QF12", "Reference_Cases / multistation_summary", "check", "Static and changing-environment ratings use different assumptions (90 vs 105 C, cable vs conduit diameter, 3 vs 1 cable, load factor 1.0 vs 0.66). Traced single-point: about +109% of the reported +85-145% headroom comes from the assumptions at constant soil.", "39", "Results kept; headroom descriptive only until a matched-assumption comparison is run"),
 ("QF13", "Reference_Cases / ampacity outputs", "info", "Column I_persist_A is the rating from uninterpolated 50 cm observations at the same hour, not a forecast baseline; no issue time or horizon.", "13", "Relabel as shallow-observation rating"),
 ("QF14", "validation scripts (MF_III_CL)", "check", "MF_III_CL validation compares silt sheath and silt moisture against sand parameters; moisture in percent was passed to a function expecting m3/m3 (saturation clipped). The reported mean rho 45.8 C.cm/W is a mix of a clipped value (39.96, 1,577 rows) and a fallback 0.20 (48.47, 3,432 rows).", "5009", "Do not use the MF_III result or the 45.8 value; repair bedding and units before reuse"),
 ("QF15", "validation scripts (SF_V+VI)", "check", "SF V+VI model drives both configurations with configuration V current (VI has its own, larger current), represents duct fill on the pipe wall only, uses duct centre depth 0.75 + OD/2 although 0.75 m is the lower outer edge, and pairs 2,440 of 12,278 rows (ambient present only there).", "12278", "Saved SF result is not a validation; repair before reuse"),
 ("QF16", "validation scripts (all)", "info", "Error sign: project formula is (model - measured)/measured, negative = model lower. Bates defines negative = model higher. Printed descriptions in scripts and notes reverse the sign in places.", "", "State the convention with every number"),
 ("QF17", "Experimental_Temperatures (MF_IV)", "info", "Model-measured conductor temperature differences of -10 to -44 C were not attributed: omitted sheath and dielectric losses, Tj = 0, default trefoil spacing, resistance fixed at 70 C and steady state against a transient are not excluded; drying is plausible but not isolated.", "7488", "Report as a measured model discrepancy with unresolved cause"),
]
for t in new:
    if t[0] not in have:
        rows.append(dict(zip(flds, t)))
with open(f, "w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=flds); w.writeheader(); w.writerows(rows)
print("Quality_Flags rows:", len(rows))

