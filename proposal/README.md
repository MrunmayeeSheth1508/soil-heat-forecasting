# Ampacity Extension — Research Package

**Project:** Dynamic Underground Cable Ampacity Rating from Forecast Soil Conditions  
**Location:** `scratch/soil-heat-forecasting/proposal/`  
**Date assembled:** 4 November 2026  
**Status:** Pre-submission research package — all literature read, all pipeline scripts run, proposal draft v3 ready

This folder is self-contained: all papers, standards, data, extracted text, survey notes, code, results, and the proposal draft are here. Nothing needs to be retrieved from `scratch/ampacity/` (mirror only). USCRN processed NPZ data lives at `../../data/multistation_npz/` (too large to copy; 131 stations, 2019–2021).

---

## Folder Structure

```
proposal/
├── README.md                              ← this file
├── PROPOSAL_DRAFT_v3.md                   ← CURRENT — full proposal with WP3 preliminary results
├── PROPOSAL_DRAFT_v2.md                   ← superseded
├── PROPOSAL_DRAFT_v1.md                   ← superseded (assumed reader knows SoilSens)
│
├── papers/                                ← all ampacity papers, downloaded and read in full
│   ├── bates_2021_underground_cable_ampacity.pdf        13.2 MB, 252 pp
│   ├── bracale_ieee_access_2019.pdf                      8.4 MB, 17 pp
│   ├── espedal_2025_nn_ampacity_AAM.pdf                  1.1 MB (author accepted manuscript)
│   ├── verschaffel_drefke_2021_energies14_7189.pdf       7.5 MB (Darmstadt experiment)
│   ├── thermohydraulic_2022_energies15_8897.pdf          6.3 MB
│   ├── thermohydraulic_2022_cardiff_copy.pdf            24.7 MB (Cardiff open-access copy)
│   ├── temperature_field_2021_energies14_8191.pdf       12.5 MB
│   └── complex_arrangements_2021_energies14_6813.pdf     6.1 MB
│
├── standards_and_specs/                   ← utility standards, specs, paywalled standard pages
│   ├── pge_eds_038193.pdf                 ← PG&E EDS — burial depth, FTB thermal spec [V]
│   ├── pge_eds_062288.pdf                 ← PG&E EDS — PVC Sch 40 dimensions [V]
│   ├── pge_greenbook_manual_full.pdf      ← PG&E 2026 Greenbook (305 pp)
│   ├── pge_td7001m_b013_update_2026_sec7_appA.pdf
│   ├── southwire_spec_46319.pdf           ← Southwire 350 kcmil Cu cable datasheet [V]
│   ├── snopud_ftb_1002182.1.html          ← SnoPUD FTB thermal spec
│   ├── iec60287_webstore.html             ← IEC 60287 catalogue page (paywalled)
│   ├── iec60853_webstore.html             ← IEC 60853 catalogue page (paywalled)
│   └── ieee442_page.html                  ← IEEE Std 442 catalogue page (paywalled)
│
├── data/                                  ← field datasets and reference tables
│   ├── Data_CableTestSite_VerschaffelDrefkeetal2021.xlsx  ← Darmstadt (CC BY-NC 4.0, 2.7 MB)
│   ├── uscrn_HEADERS.txt                  ← USCRN hourly02 field schema (38 fields) [V]
│   ├── wilson_T1.csv                      ← Wilson et al. 2016 Table T1, tidy (70 stations, 5 depths)
│   ├── wilson_Supplemental_Table_T1.xls   ← Wilson et al. 2016 source XLS (293 KB)
│   └── wilson_candidate_coverage.csv      ← 38-station USCRN coverage with texture data [V]
│
│   NOTE: USCRN processed NPZ files (131 stations, 2019–2021) are at:
│         ../../data/multistation_npz/{STATE}_{CITY}_{YEAR}.npz
│         Keys: date(8760,), hour(8760,), P, SM(8760,5), ST(8760,5)
│         SM/ST depth indices: 0=5cm, 1=10cm, 2=20cm, 3=50cm, 4=100cm
│         72 of 131 stations have valid 50+100 cm data for cable-depth interpolation.
│
├── code/                                  ← reproducible pipeline (Python 3.12, see requirements.txt)
│   ├── README.md                          ← run instructions, dependency list, runtime status
│   ├── requirements.txt                   ← numpy scipy pandas matplotlib openpyxl
│   ├── 00_data_audit/
│   │   ├── inspect_workbook.py            ← print all Darmstadt sheet names and headers
│   │   └── audit_workbook.py              ← write darmstadt_workbook_audit.md
│   ├── 01_cable_thermal_model/
│   │   ├── cable_params.py                ← Southwire 350 kcmil + PG&E installation dataclass
│   │   └── neher_mcgrath.py               ← Neher-McGrath AC ampacity; self-tests at 90°C/105°C
│   ├── 02_soil_thermal_properties/
│   │   ├── johansen.py                    ← Johansen (1975) λ(θ) + κ_e model; self-test table
│   │   └── wilson_lookup.py               ← texture class → Johansen params via wilson_T1.csv
│   ├── 03_darmstadt_validation/
│   │   ├── load_darmstadt.py              ← load all 10 Darmstadt workbook sheets
│   │   ├── validate_mf_iv.py              ← MF_IV: 4 beddings, N-M vs measured
│   │   ├── validate_sf_v_vi.py            ← SF_V+VI: unfilled vs grouted duct
│   │   └── validate_mf_iii.py             ← MF_III: sheath T + soil moisture dynamics
│   ├── 04_depth_interpolation/
│   │   └── depth_interp.py                ← C-N 1D heat conduction, 50→target cm; demo
│   ├── 05_dynamic_ampacity/
│   │   ├── dynamic_ampacity_pipeline.py   ← NPZ loader → C-N interp → Johansen → N-M ampacity
│   │   └── run_all_stations.py            ← batch runner: 13 stations × 3 burial depths
│   └── 06_sensitivity/
│       └── sensitivity_analysis.py        ← RHO, Ta, load-factor, depth-reference sweeps
│
├── results/                               ← auto-generated by running code/ scripts
│   ├── darmstadt_validation/              ← per-bedding CSVs: mf_iv_{bedding}.csv, sf_v_vi.csv, mf_iii_cl.csv
│   ├── depth_interp/                      ← depth_interp_demo.png
│   ├── sensitivity/                       ← rho/Ta/load_factor/depth_reference CSVs + PNGs
│   └── dynamic_ampacity/                  ← [NEW] 39 station×depth combinations
│       ├── ampacity_timeseries_{station}_{depth}.csv  ← hourly ST, SM, I_dynamic, headroom_pct
│       ├── ampacity_plot_{station}_{depth}.png         ← 3-panel: temperature, moisture, ampacity
│       └── multistation_summary.csv                    ← 39 rows: all stations × depths
│
└── notes/                                 ← extracted text, survey notes, findings, gap analysis
    ├── survey_bates_2021.md               ← FULL survey, all 12 chapters + appendices
    ├── survey_bracale_2019.md
    ├── survey_darmstadt_2021.md
    ├── survey_espedal_2025.md
    ├── survey_thermohydraulic_2022.md
    ├── survey_temperature_field_2021.md
    ├── survey_complex_arrangements_2021.md
    ├── survey_pge_eds_038193_062288.md
    ├── AMPACITY_SOURCES_PARAMETERS_AND_GAPS.md  ← master parameter register + gap table
    ├── LITERATURE_MATRIX.md                      ← 10-paper cross-domain matrix
    ├── VALIDATION_FINDINGS.md                    ← [NEW] Darmstadt N-M validation statistics
    ├── DYNAMIC_AMPACITY_FINDINGS.md              ← [NEW] WP3 pipeline results, 13 stations × 3 depths
    ├── darmstadt_workbook_audit.md               ← full audit of Darmstadt Excel workbook
    ├── source_verification.md                    ← download/access log for all sources
    ├── *.txt                                     ← extracted full text of every paper
    └── img/                                      ← page images from papers (Bracale, Darmstadt)
```

---

## What Has Been Done

### Literature — All Read in Full

| Paper / Source | Survey file | Key finding |
|---|---|---|
| Bates 2021 (252 pp dissertation) | `survey_bates_2021.md` | N-M overestimates 8% SS, 0.5% transient; NHR validated; SCAN use confirmed |
| Bracale et al. 2019 | `survey_bracale_2019.md` | Moisture→ampacity chain; persistence beats ML at all horizons |
| Verschaffel-Drefke et al. 2021 | `survey_darmstadt_2021.md` | Darmstadt dataset; sand dries at cable surface in <1 day |
| Espedal et al. 2025 | `survey_espedal_2025.md` | NN tuning of cable model; marginal without soil data |
| Liu et al. 2022 (thermohydraulic) | `survey_thermohydraulic_2022.md` | Moisture dominates; no field validation |
| Ahmad et al. 2021 (temperature field) | `survey_temperature_field_2021.md` | Convection in saturated sand; cyclic heating |
| Brakelmann et al. 2021 (complex arrangements) | `survey_complex_arrangements_2021.md` | Image-source multi-cable mutual heating |
| PG&E EDS 038193 + 062288 | `survey_pge_eds_038193_062288.md` | Burial depth 0.762–0.819 m; FTB spec; PVC dims |

### Pipeline — Runtime Status (4 Nov 2026)

All 14 `.py` files syntax-clean. All run successfully:

| Script | Status | Output |
|---|---|---|
| `00_data_audit/inspect_workbook.py` | ✅ PASS | All 10 Darmstadt sheets + headers printed |
| `00_data_audit/audit_workbook.py` | ✅ PASS | `notes/darmstadt_workbook_audit.md` |
| `01_cable_thermal_model/neher_mcgrath.py` | ✅ PASS | 631 A for Southwire 350 kcmil |
| `02_soil_thermal_properties/johansen.py` | ✅ PASS | Conductivity table; sand wet λ=2.17 W/(m·K) |
| `02_soil_thermal_properties/wilson_lookup.py` | ✅ PASS | 70 rows loaded from `data/wilson_T1.csv` |
| `03_darmstadt_validation/load_darmstadt.py` | ✅ PASS | All sheets loaded; shapes confirmed |
| `03_darmstadt_validation/validate_mf_iv.py` | ✅ PASS | sand −51%, loam −51%, FTB −21%, silt −26% |
| `03_darmstadt_validation/validate_sf_v_vi.py` | ✅ PASS | Unfilled −68%, grouted −39% |
| `03_darmstadt_validation/validate_mf_iii.py` | ✅ PASS | Sheath −53%; mean rho=45.8 °C·cm/W |
| `04_depth_interpolation/depth_interp.py` | ✅ PASS | C-N interp demo; bounding verified |
| `06_sensitivity/sensitivity_analysis.py` | ✅ PASS | 4 studies; CSVs + plots in `results/sensitivity/` |
| `05_dynamic_ampacity/dynamic_ampacity_pipeline.py` | ✅ PASS | NPZ loader + C-N + N-M pipeline |
| `05_dynamic_ampacity/run_all_stations.py` | ✅ PASS | **39 combinations** (13 stations × 3 depths) |

### Key Pipeline Results [R — computed from real USCRN data 2019–2021]

**Darmstadt N-M validation** (see `notes/VALIDATION_FINDINGS.md`):

| Configuration | Mean N-M error | Interpretation |
|---|---|---|
| MF_IV sand | −51.4% ± 1.0% | Soil dried at cable surface — SS model expects wet |
| MF_IV FTB | −21.4% ± 1.7% | FTB resists drying → smaller error |
| SF_V (unfilled duct) | −67.7% ± 11.4% | Air gap worst case |
| SF_VI (grouted duct) | −39.3% ± 14.1% | FTB fill −28 pp improvement |
| MF_III sheath | −52.5% ± 2.7% | Mean rho=45.8 °C·cm/W |

**Dynamic ampacity — WP3 preliminary** (see `notes/DYNAMIC_AMPACITY_FINDINGS.md`):

Static design rating at 30" (Black Books: RHO-90, Ta=20°C, LF=1.0): **621 A**

| Climate Zone | Mean Dynamic (A) at 30" | vs Static | Headroom σ | Mean RHO (°C·cm/W) |
|---|---|---|---|---|
| Arid-SW (NM, NV, TX) | 1175–1286 | **+86–107%** | 8–12% | 94–144 |
| Mediterranean (CA) | 1370–1430 | **+121–130%** | 2–7% | 55–82 |
| Semi-arid-NW (OR) | 1421 | **+129%** | 9.5% | 74 |
| Sub-humid (OK, NE) | 1447–1452 | **+133%** | 4–11% | 54–60 |
| Humid-subtropical (AL, NC) | 1335–1453 | **+115–134%** | 3–9% | 56–73 |
| Continental (WY, MI) | 1431–1513 | **+130–144%** | 2–12% | 57–77 |

All 39 station-depth combinations: **100% of hours exceed static design rating**.  
Highest forecast value (largest σ): NV Mercury, TX Monahans, AL Fairhope (σ 9–12%).

**Sensitivity** (see `results/sensitivity/`):

| Change | Ampacity shift |
|---|---|
| RHO: 90 → 50 °C·cm/W (wet soil) | +92 A (+11%) |
| RHO: 90 → 157 °C·cm/W (AZ mean) | −99 A (−12%) |
| Ta: 20°C → 10°C (winter) | +45 A (+5%) |
| Depth reference (±4 cm) | ±7 A (<1%) |

---

## How to Reproduce

```bash
cd proposal/
pip install -r code/requirements.txt

# 1. Audit Darmstadt workbook
python code/00_data_audit/inspect_workbook.py
python code/00_data_audit/audit_workbook.py

# 2. Soil thermal model self-tests
python code/02_soil_thermal_properties/johansen.py
python code/02_soil_thermal_properties/wilson_lookup.py   # requires data/wilson_T1.csv

# 3. N-M validation against Darmstadt
python code/03_darmstadt_validation/validate_mf_iv.py
python code/03_darmstadt_validation/validate_sf_v_vi.py
python code/03_darmstadt_validation/validate_mf_iii.py

# 4. Depth interpolation demo
python code/04_depth_interpolation/depth_interp.py

# 5. Sensitivity study
python code/06_sensitivity/sensitivity_analysis.py

# 6. WP3: Dynamic ampacity — 13 stations × 3 burial depths
#    Requires USCRN NPZ data at ../../data/multistation_npz/
python code/05_dynamic_ampacity/run_all_stations.py

# Single station / single depth (e.g. 36" burial):
python code/05_dynamic_ampacity/dynamic_ampacity_pipeline.py \
    --station WY_Sundance_8_NNW --depth 0.914
```

---

## Darmstadt Geometry Note

The 0.65 m dimension in Figure 2 is the **underside of the upper-row trefoil bundle** (figure-based reading). With 34 mm cable OD (touching):

| Location | Depth |
|---|---|
| Lower conductor centres [I] | 0.633 m |
| Upper conductor centre [I] | 0.604 m |
| Centroid [I, used in validation] | 0.623 m |

Depth-reference uncertainty: ±7 A (<1%) [R] — not material.

---

## Open Items

- [ ] Target journal selection (IEEE Trans. Power Delivery / Energies / Applied Energy)
- [ ] CC BY-NC 4.0 (Darmstadt) compatibility check with target journal open-data policy
- [ ] Lock WP1 model architecture (motivate with SoilSens baseline results)
- [ ] Score moisture baseline at 50 cm (completes WP1 prerequisite)
- [ ] Wilson T1 lookup integration into dynamic ampacity pipeline (replaces default Johansen params for 27 matched stations)
- [ ] Bayesian α inversion for depth interpolation (Brunetti 2022 method — WP3 refinement)
- [ ] Richards-equation moisture coupling (WP3 deliverable, replacing linear interpolation)
- [ ] Confirm SCAN API access for climatological reference comparisons in WP3

---

## Licence Notes

| Source | Licence |
|---|---|
| Darmstadt dataset | CC BY-NC 4.0 — non-commercial use only |
| USCRN data | Public domain (NOAA) |
| Wilson et al. 2016 Supplemental Table T1 | Academic; reproduced for research use |
| Papers | Individual journal terms; PDFs for personal research use |
| PG&E EDS 038193/062288 | Utility design standard (user-supplied) |

---

*All literature claims in the proposal are traceable to survey files in `notes/`. No values invented. Tags: [V] = verified from full text, [I] = inferred, [R] = computed by pipeline.*
