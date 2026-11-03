"""
Part 2b - static catalogues (hand-transcribed from source documents, each row cited).
Nothing is estimated here: attributes not stated in a source are left blank.

Outputs
  02_Electricity_and_Cables/Cable_Catalogue.csv
  02_Electricity_and_Cables/Load_Profile_Catalogue.csv
  03_Installation_and_Materials/Experimental_Installations.csv
  03_Installation_and_Materials/Reference_Installations.csv
  03_Installation_and_Materials/Backfill_Specifications.csv
  03_Installation_and_Materials/Material_Properties.csv   (appends REF_* rows; DARM_* rows kept)
"""
import numpy as np, pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
C2, C3 = ROOT / "02_Electricity_and_Cables", ROOT / "03_Installation_and_Materials"
ENC = "utf-8-sig"
IN = 25.4  # mm per inch (exact)

SW = "Southwire SPEC 46319 rev 1.000.009 (3 Oct 2025), Table "
DA = "Verschaffel-Drefke et al. 2021, Energies 14(23):7189, Table 1"

# ---------------------------------------------------------------- Cable catalogue
# Southwire Table 1: size, strands, d_cond_in, d_over_cond_in, d_over_ins_in(shield) ...
# columns as printed: [strands, cond_dia, dia_over_conductor(=over conductor shield?), dia_over_insulation, jacket_mil, OD, ...]
# Printed Table 1 headers: Strand count | Diameter Over Conductor | Diameter Over Insulation | Diameter Over Insulation Shield | Jacket Thickness | Approx OD | ...
# (Printed header 'Diameter Over Conductor' = bare conductor; values are listed in the 4 columns after strand count.)
sw_t1 = {  # size: (stock, strands, d_cond, d_ins, d_shield, jacket_mil, od, cu_lb, wt_lb, tension_lb, bend_in, conduit_in)
    "2":    ("669142", 7,  .268, .746, .806, 80, .986, 275, 639, 530, 11.8, 2.5),
    "1":    ("",       19, .299, .777, .837, 80, 1.017, 328, 732, 669, 12.2, 2.5),
    "1/0":  ("647203", 19, .336, .814, .874, 80, 1.054, 401, 804, 844, 12.6, 2.5),
    "2/0":  ("",       19, .376, .854, .914, 80, 1.094, 486, 937, 1064, 13.1, 2.5),
    "3/0":  ("",       19, .423, .901, .961, 80, 1.141, 597, 1077, 1342, 13.7, 3),
    "4/0":  ("640921", 19, .475, .953, 1.013, 80, 1.193, 739, 1223, 1692, 14.3, 3),
    "250":  ("",       37, .520, 1.006, 1.066, 80, 1.246, 860, 1409, 2000, 15.0, 3),
    "350":  ("647207", 35, .616, 1.102, 1.162, 80, 1.342, 1178, 1752, 2800, 16.1, 3.5),
    "500":  ("553998", 35, .736, 1.230, 1.290, 80, 1.470, 1653, 2307, 4000, 17.6, 4),
    "600":  ("",       61, .813, 1.309, 1.369, 80, 1.549, 1963, 2709, 4800, 18.6, 4),
    "750":  ("561603", 61, .908, 1.404, 1.495, 80, 1.735, 2441, 3337, 6000, 20.8, 4.5),
    "1000": ("",       61, 1.060, 1.556, 1.616, 110, 1.856, 3219, 4218, 8000, 22.3, 5),
}
sw_t2 = {  # size: (dc_R25 ohm/1000ft, ac_R90 ohm/1000ft, duct90, duct105, air90, air105)
    "2": (.162, .221, 150, 160, 165, 185), "1": (.128, .175, 170, 185, 185, 210),
    "1/0": (.102, .139, 195, 210, 215, 240), "2/0": (.082, .112, 220, 235, 245, 275),
    "3/0": (.064, .087, 250, 270, 285, 315), "4/0": (.051, .070, 285, 305, 325, 360),
    "250": (.043, .059, 310, 335, 360, 400), "350": (.031, .043, 375, 400, 435, 490),
    "500": (.021, .030, 450, 485, 535, 600), "600": (.018, .026, 488, 525, 589, 658),
    "750": (.014, .021, 545, 585, 670, 745), "1000": (.011, .018, 615, 660, 770, 860),
}
FT1000_M = 304.8
rows = []
for size, (stock, strands, dc, di, ds, jm, od, cu, wt, ten, bend, cond) in sw_t1.items():
    r1, r90, d90, d105, a90, a105 = sw_t2[size]
    note = ""
    if size == "750":
        note = ("Printed value 'diameter over insulation shield' (1.495 in) is inconsistent with the other sizes "
                "(about +0.06 in over insulation) - reproduced as printed, not corrected.")
    rows.append(dict(
        cable_id=f"SW_{size.replace('/', '_')}{'AWG' if size in ('2','1','1/0','2/0','3/0','4/0') else 'KCMIL'}_CU_15KV_EPR",
        cable_family="Southwire 15 kV NL-EPR, compact Cu, tape shield, PVC jacket (Type MV-105)",
        source_type="manufacturer datasheet", stock_number=stock, conductor_size_awg_kcmil=size,
        conductor_material="Cu (compact round stranded)", strand_count=strands,
        conductor_od_in=dc, conductor_od_mm=round(dc * IN, 2),
        insulation_material="NL-EPR 133% level", insulation_thickness_mm=round(220 * 0.0254, 3),
        od_over_insulation_in=di, od_over_insulation_mm=round(di * IN, 2),
        od_over_insulation_shield_in=ds, od_over_insulation_shield_mm=round(ds * IN, 2),
        shield="5 mil Cu tape, 25% overlap", jacket_material="PVC (SIMpull)", jacket_thickness_mil=jm, jacket_thickness_mm=round(jm * 0.0254, 3),
        overall_od_in=od, overall_od_mm=round(od * IN, 2),
        dc_resistance_ohm_per_km=round(r1 / FT1000_M * 1000, 5), dc_resistance_ref_temp_C=25,
        ac_resistance_ohm_per_km=round(r90 / FT1000_M * 1000, 5), ac_resistance_ref_temp_C=90,
        resistance_as_printed_ohm_per_1000ft=f"DC25={r1}; AC90={r90}",
        rated_voltage_kV="15 (133% insulation level)", max_conductor_temp_normal_C=105,
        max_conductor_temp_emergency_C=140, max_conductor_temp_short_circuit_C=250,
        nec_ampacity_duct_90C_A=d90, nec_ampacity_duct_105C_A=d105,
        nec_ampacity_air_90C_A=a90, nec_ampacity_air_105C_A=a105,
        used_in_pipeline=(size == "350"), source_reference=SW + "1 and 2", notes=note))

rows += [
    dict(cable_id="DARM_LV_NAY2Y-J_4x150", cable_family="Darmstadt LV cable", source_type="experiment paper",
         conductor_size_awg_kcmil="4x150 mm2 (SE)", conductor_material="Al", insulation_material="PVC",
         insulation_thickness_mm=1.8, overall_od_mm=48, dc_resistance_ohm_per_km=0.206, dc_resistance_ref_temp_C=20,
         rated_voltage_kV="0.6/1", max_conductor_temp_normal_C=70, shield="", jacket_thickness_mm=2.5,
         used_in_pipeline=False, source_reference=DA,
         notes="Designation NAY2Y-J SE 4x150. OD approximate (~48 mm). Used in main-field configs I, II, III."),
    dict(cable_id="DARM_MV150_NA2XS(F)2Y_1x150", cable_family="Darmstadt MV cable", source_type="experiment paper",
         conductor_size_awg_kcmil="150 mm2 (RE/25)", conductor_material="Al", insulation_material="XLPE",
         insulation_thickness_mm=5.5, overall_od_mm=34, dc_resistance_ohm_per_km=0.206, dc_resistance_ref_temp_C=20,
         rated_voltage_kV="12/20", max_conductor_temp_normal_C=90, jacket_thickness_mm=2.5,
         used_in_pipeline=True, source_reference=DA,
         notes="Laid as trefoil. Main-field configs II, III, IV; side-field V, VI, VIII, IX, X. Capacitance 0.24 uF/km. OD approximate (~34 mm). Used for Darmstadt validation."),
    dict(cable_id="DARM_MV400_N2XS(F)2Y_1x400", cable_family="Darmstadt MV cable", source_type="experiment paper",
         conductor_size_awg_kcmil="400 mm2 (RM/35)", conductor_material="Cu", insulation_material="XLPE",
         insulation_thickness_mm=5.5, overall_od_mm=44, dc_resistance_ohm_per_km=0.047, dc_resistance_ref_temp_C=20,
         rated_voltage_kV="12/20", max_conductor_temp_normal_C=90, jacket_thickness_mm=2.5,
         used_in_pipeline=False, source_reference=DA,
         notes="Side-field config VII only; no loaded experiment in the workbook. Capacitance 0.358 uF/km. OD approximate (~44 mm)."),
]
CC = pd.DataFrame(rows)
CC.to_csv(C2 / "Cable_Catalogue.csv", index=False, encoding=ENC)
print("Cable_Catalogue", CC.shape)

# ---------------------------------------------------------------- Load profile catalogue
LP = pd.read_csv(C2 / "Load_Profiles.csv")
cat = []
for pid, g in LP.groupby("profile_id"):
    g = g.sort_values("time_of_day_h")
    cat.append(dict(profile_id=pid, profile_type="experimental", description="Darmstadt 24 h relative load profile (workbook 'Load Profils', 30-min steps)",
                    n_points=len(g), load_factor_computed_mean_over_max=round(g.relative_load.mean() / g.relative_load.max(), 3),
                    load_factor_stated_in_paper={"DARMSTADT_EVU": 0.7, "DARMSTADT_PV": 0.4}[pid],
                    peak_basis="Relative (peak = max of column); absolute peak set per run (IEC 60853 permissible value for config IV; amperes not given in text)",
                    source_reference="Verschaffel-Drefke et al. 2021, Sec 2.2 / Fig 6; workbook sheet 'Load Profils'"))
cat.append(dict(profile_id="DARMSTADT_CONSTANT", profile_type="experimental", description="Constant load (fixed current, stepwise increases, or closed loop on a temperature limit)",
                n_points="", load_factor_computed_mean_over_max="", load_factor_stated_in_paper=1.0, peak_basis="Measured current is in Experimental_Loading.csv",
                source_reference="Verschaffel-Drefke et al. 2021, Sec 2.2"))
cat.append(dict(profile_id="REF_LF_1.00", profile_type="reference_scenario", description="Continuous full load (Black Books / IEEE 835 design basis); used for the static design rating",
                n_points="", load_factor_computed_mean_over_max="", load_factor_stated_in_paper="", load_factor_scenario=1.0,
                peak_basis="n/a - static rating", source_reference="Bates 2021 (Black Books assumptions, via proposal/code/01_cable_thermal_model/cable_params.py)"))
cat.append(dict(profile_id="REF_LF_0.66", profile_type="reference_scenario", description="Daily load factor 0.66 applied as a correction in the dynamic-ampacity pipeline",
                n_points="", load_factor_computed_mean_over_max="", load_factor_stated_in_paper="", load_factor_scenario=0.66,
                peak_basis="n/a - scalar load-factor correction, not a time series", source_reference="Bates 2021 Ch 9 (as cited in proposal/notes/DYNAMIC_AMPACITY_FINDINGS.md)"))
LPC = pd.DataFrame(cat)
LPC.to_csv(C2 / "Load_Profile_Catalogue.csv", index=False, encoding=ENC)
print(LPC[["profile_id", "load_factor_computed_mean_over_max", "load_factor_stated_in_paper"]])

# ---------------------------------------------------------------- Experimental installations
SECT = "Verschaffel-Drefke et al. 2021, Sec 2.1"
def inst(i, field, desc, cables, cfg_arr, depth_note, **kw):
    d = dict(installation_id=f"DARM_CFG_{i}", configuration=i, field=field, description=desc, cable_ids=cables,
             arrangement=cfg_arr, burial_cover_m="", conductor_centre_depth_m="", depth_range_min_m="", depth_range_max_m="",
             depth_reference_note=depth_note, bedding="", duct_inner_diameter_mm="", duct_wall_mm="", duct_lower_edge_depth_m="",
             grout_conductivity_Wmk="", in_workbook=False, workbook_sheets="", source_reference=SECT)
    d.update(kw); return d
MAIN_DEPTH = dict(depth_range_min_m=0.65, depth_range_max_m=0.85)
MAIN_NOTE = ("Paper Sec 2.1.1: burial depth 'between 0.65 m and 0.85 m' (reference point - cover vs conductor centre - not stated; "
             "per-cable depth only in Fig 2). Not a conductor-centre depth.")
ins = [
    inst("I", "main", "Single LV cable", "DARM_LV_NAY2Y-J_4x150", "single cable", MAIN_NOTE, bedding="silt | sand | fluidized backfill | loam (four 3.5 m sections in series)", **MAIN_DEPTH),
    inst("II", "main", "Two LV cables plus two MV trefoils", "DARM_LV_NAY2Y-J_4x150; DARM_MV150_NA2XS(F)2Y_1x150", "2 LV + 2 MV trefoils", MAIN_NOTE,
         bedding="silt | sand | fluidized backfill | loam", in_workbook=True, workbook_sheets="MF_III_CL (sheath temperatures + FDR moisture; long-term run)", **MAIN_DEPTH),
    inst("III", "main", "Three LV cables plus three MV trefoils in a row", "DARM_LV_NAY2Y-J_4x150; DARM_MV150_NA2XS(F)2Y_1x150", "3 LV + 3 MV trefoils in a row", MAIN_NOTE,
         bedding="silt | sand | fluidized backfill | loam", **MAIN_DEPTH),
    inst("IV", "main", "Single MV trefoil", "DARM_MV150_NA2XS(F)2Y_1x150", "single trefoil",
         MAIN_NOTE + " Trefoil bundle underside at 0.650 m is an interpretation of Fig 2 (see proposal/code cable_params.py), not a written value.",
         bedding="silt | sand | fluidized backfill | loam", in_workbook=True, workbook_sheets="MF_IV_CL; MF_IV_EVU; MF_IV_PV (conductor temperatures)", **MAIN_DEPTH),
    inst("V", "side", "MV trefoil in unfilled PVC duct", "DARM_MV150_NA2XS(F)2Y_1x150", "trefoil in air-filled duct",
         "Duct buried in natural sand; 0.75 m is lower outer duct edge to surface (Sec 2.1.2) - this is NOT cover and NOT conductor-centre depth.",
         bedding="natural sand", duct_inner_diameter_mm=147.6, duct_wall_mm=4.8, duct_lower_edge_depth_m=0.75, in_workbook=True, workbook_sheets="SF_V+VI"),
    inst("VI", "side", "MV trefoil in PVC duct filled with grouting", "DARM_MV150_NA2XS(F)2Y_1x150", "trefoil in grout-filled duct",
         "As configuration V.", bedding="natural sand", duct_inner_diameter_mm=147.6, duct_wall_mm=4.8, duct_lower_edge_depth_m=0.75,
         grout_conductivity_Wmk="around 2.5 (paper text)", in_workbook=True, workbook_sheets="SF_V+VI"),
    inst("VII", "side", "Two Cu 400 mm2 trefoils directly in natural sand, at some distance from the main field", "DARM_MV400_N2XS(F)2Y_1x400", "two trefoils in sand",
         "Paper states 0.9 m depth; reference point not stated. Not loaded in any experiment shown.", bedding="natural sand", depth_range_min_m=0.9, depth_range_max_m=0.9),
    inst("VIII", "side", "MV150 trefoil in artificial bedding with high thermal conductivity (trench)", "DARM_MV150_NA2XS(F)2Y_1x150", "trefoil at trench bottom", "Not stated in text.", bedding="artificial high-conductivity bedding"),
    inst("IX", "side", "MV150 trefoil in fluidized backfill with high thermal conductivity (trench)", "DARM_MV150_NA2XS(F)2Y_1x150", "trefoil at trench bottom", "Not stated in text.", bedding="fluidized backfill (high conductivity)"),
    inst("X", "side", "MV150 trefoil in grouting with low thermal conductivity (trench)", "DARM_MV150_NA2XS(F)2Y_1x150", "trefoil at trench bottom", "Not stated in text.", bedding="grouting (low conductivity)"),
]
EI = pd.DataFrame(ins)
EI["notes"] = "Spacings, per-cable depths, trench dimensions and sensor coordinates exist only in paper figures 2 and 4 and are not transcribed here."
EI.to_csv(C3 / "Experimental_Installations.csv", index=False, encoding=ENC)
print("Experimental_Installations", EI.shape)

# ---------------------------------------------------------------- Reference installations (selected scenarios, not measurements)
PGE = "PG&E EDS 038193 Rev16 / EDS 062288 Rev21 (June 2023)"
ref = []
for lbl, cov_in in (("24in", 24), ("30in", 30), ("36in", 36)):
    cov_m = round(cov_in * 0.0254, 3)
    ref.append(dict(
        installation_id=f"REF_PGE_PVC4_{lbl}", scenario_status="selected reference scenario (not a measured installation)",
        utility="Pacific Gas & Electric (design standard)", cable_id="SW_350KCMIL_CU_15KV_EPR",
        conduit_type="Rigid PVC Schedule 40, 4 in nominal", conduit_od_mm=114.3, conduit_id_mm=100.6,
        n_cables_modelled=3, cable_arrangement="trefoil, 7.5 in centre-to-centre spacing (Black Books assumption)",
        scenario_label_in=cov_in, pipeline_model_depth_m=cov_m,
        pipeline_depth_meaning="Value passed to the model as depth to cable centre (neher_mcgrath.py: 'depth to cable centre'); equals the nominal inch label x 0.0254",
        standard_burial_cover_m={24: 0.610, 30: 0.762, 36: ""}.get(cov_in, ""),
        standard_cover_definition={24: "PG&E secondary/service minimum cover, top of conduit to grade (EDS 038193)",
                                   30: "PG&E primary minimum cover, top of conduit to grade (EDS 038193)",
                                   36: "No PG&E primary cover value; 36 in is the Black Books depth and the PG&E duct-window entry cover (062288 Note 2)"}[cov_in],
        conductor_centre_depth_derived_m=round(cov_m + 0.1143 / 2, 3) if cov_in in (24, 30) else "",
        derivation="cover + conduit OD / 2 [inferred; single conduit, cable assumed at conduit centre]" if cov_in in (24, 30) else "",
        backfill_assumed_by_pipeline="soil thermal resistivity from measured moisture (Johansen); no thermal backfill modelled",
        source_reference=PGE + "; Southwire SPEC 46319; proposal/code/01_cable_thermal_model/cable_params.py",
        notes=("CAUTION: pipeline used the nominal cover value as the conductor-centre depth. For 30 in the PG&E-derived centre depth is about 0.819 m (+0.057 m); "
               "effect on results not yet quantified.") if cov_in == 30 else
              ("Same convention as the 30 in row." if cov_in == 24 else "Same convention; this depth is a scenario, not a PG&E primary standard.")))
RI = pd.DataFrame(ref)
RI.to_csv(C3 / "Reference_Installations.csv", index=False, encoding=ENC)
print("Reference_Installations", RI.shape)

# ---------------------------------------------------------------- Backfill specifications (limits, not measurements)
SNO = "Snohomish PUD material standard 1002182.1 Rev 2 (11 Apr 2024), Table 5.1 / 4.1"
PGB = "PG&E EDS 038193 Rev16 (June 2023), FTB / thermal backfill paragraph"
def spec(sid, mat, ptype, param, val, unit, cond, src, note=""):
    return dict(spec_id=sid, material=mat, spec_kind=ptype, parameter=param, value=val, unit=unit, condition=cond, source_reference=src, notes=note)
bs = [
 spec("SNO_LS_RHO0_MIX", "Low-strength FTB (SnoPUD)", "specification limit (maximum)", "thermal resistivity, mix design", 100, "C.cm/W", "0% moisture content", SNO),
 spec("SNO_LS_RHO0_FIELD", "Low-strength FTB (SnoPUD)", "specification limit (maximum)", "thermal resistivity, field test", 110, "C.cm/W", "0% moisture content", SNO),
 spec("SNO_LS_RHOC_MIX", "Low-strength FTB (SnoPUD)", "specification limit (maximum)", "thermal resistivity, mix design", 70, "C.cm/W", "3% moisture content (critical)", SNO),
 spec("SNO_LS_RHOC_FIELD", "Low-strength FTB (SnoPUD)", "specification limit (maximum)", "thermal resistivity, field test", 80, "C.cm/W", "3% moisture content (critical)", SNO),
 spec("SNO_HS_RHO0_MIX", "High-strength FTB (SnoPUD)", "specification limit (maximum)", "thermal resistivity, mix design", 75, "C.cm/W", "0% moisture content", SNO),
 spec("SNO_HS_RHO0_FIELD", "High-strength FTB (SnoPUD)", "specification limit (maximum)", "thermal resistivity, field test", 75, "C.cm/W", "0% moisture content", SNO),
 spec("SNO_HS_RHOC_MIX", "High-strength FTB (SnoPUD)", "specification limit (maximum)", "thermal resistivity, mix design", 60, "C.cm/W", "2% moisture content (critical)", SNO),
 spec("SNO_HS_RHOC_FIELD", "High-strength FTB (SnoPUD)", "specification limit (maximum)", "thermal resistivity, field test", 65, "C.cm/W", "2% moisture content (critical)", SNO),
 spec("SNO_HS_STR_MIN", "High-strength FTB (SnoPUD)", "specification limit (minimum)", "28-day compressive strength", 3000, "psi", "", SNO),
 spec("SNO_LS_STR_MAX_MIX", "Low-strength FTB (SnoPUD)", "specification limit (maximum)", "28-day compressive strength, mix design", 100, "psi", "", SNO),
 spec("SNO_LS_STR_MAX_FIELD", "Low-strength FTB (SnoPUD)", "specification limit (maximum)", "28-day compressive strength, field test", 150, "psi", "", SNO),
 spec("SNO_SLUMP", "FTB, both strengths (SnoPUD)", "specification limit (range)", "slump", "4 to 6", "in", "", SNO),
 spec("SNO_AIR_MAX", "FTB, both strengths (SnoPUD)", "specification limit (maximum)", "total air content", 2, "% by volume", "", SNO + " (section 4.7)"),
]
mixes = [("Medium aggregate", 1800, 1515), ("Fine aggregate", 1400, 1422), ("Fluidizer (Class F fly ash)", 300, 100),
         ("Portland cement", 50, 520), ("Water", 305, 360)]
for comp, ls, hs in mixes:
    bs.append(spec(f"SNO_MIX_LS_{comp.split()[0].upper()}", "Low-strength FTB (SnoPUD)", "approved mix design", comp, ls, "lb/yd3", "", SNO,
                   "Fine aggregate quantity 'may be adjustable for unit yield'" if comp.startswith("Fine") else ""))
    bs.append(spec(f"SNO_MIX_HS_{comp.split()[0].upper()}", "High-strength FTB (SnoPUD)", "approved mix design", comp, hs, "lb/yd3", "", SNO,
                   "Fine aggregate quantity 'may be adjustable for unit yield'" if comp.startswith("Fine") else ""))
bs += [
 spec("PGE_FTB_RHOC", "Fluidized thermal backfill (PG&E)", "specification limit (maximum)", "thermal resistivity", 60, "C.cm/W", "critical moisture content (3% for FTB)", PGB),
 spec("PGE_FTB_RHO0", "Fluidized thermal backfill (PG&E)", "specification limit (maximum)", "thermal resistivity", 90, "C.cm/W", "0% moisture content", PGB,
      "proposal/code cable_params.py lists 75 C.cm/W at 0% under an EDS 038193 tag; the PG&E text says 90 (75 is the SnoPUD high-strength value)."),
 spec("PGE_FTB_STR", "Low-strength FTB (PG&E)", "specification limit (range)", "maximum nominal compressive strength", "70 to 300", "psi", "", PGB),
 spec("PGE_SAND_FINES", "Imported bedding sand EMS-4123 (PG&E)", "specification limit (maximum)", "particles not passing #200 sieve", 20, "% of particles", "", "PG&E EDS 038193 Rev16, trench notes"),
 spec("PGE_COMPACT_PUBLIC", "Trench backfill (PG&E)", "specification limit (minimum)", "compaction, public road", 95, "% density", "", "PG&E EDS 038193 Rev16"),
 spec("PGE_COMPACT_PRIVATE", "Trench backfill (PG&E)", "specification limit (minimum)", "compaction, private", 90, "% density", "", "PG&E EDS 038193 Rev16"),
]
BS = pd.DataFrame(bs)
BS.to_csv(C3 / "Backfill_Specifications.csv", index=False, encoding=ENC)
print("Backfill_Specifications", BS.shape)

# ---------------------------------------------------------------- reference material properties appended
MP = pd.read_csv(C3 / "Material_Properties.csv")
MP = MP[MP.material_id.astype(str).str.startswith("DARM")]
B = "Bates 2021 App. A Table A.1 / Neher-McGrath Table 6 (as in proposal/code cable_params.py)"
extra = [
 ("REF_EPR", "EPR/XLPE insulation", "Thermal resistivity", 350.0, "C.cm/W", B),
 ("REF_PVC_JACKET", "PVC jacket", "Thermal resistivity", 500.0, "C.cm/W", B),
 ("REF_PVC_DUCT", "Fibre / PVC conduit", "Thermal resistivity", 480.0, "C.cm/W", B),
 ("REF_NEC_SOIL", "NEC default soil (design assumption)", "Thermal resistivity", 90.0, "C.cm/W", "Bates 2021 Ch 2 (NEC default); design assumption, not a measurement"),
]
MP = pd.concat([MP, pd.DataFrame([dict(material_id=a, material_name=b, property=c, value=d, value_text="", unit=e, source_reference=f) for a, b, c, d, e, f in extra])], ignore_index=True)
MP.to_csv(C3 / "Material_Properties.csv", index=False, encoding=ENC)
print("Material_Properties", MP.shape)
