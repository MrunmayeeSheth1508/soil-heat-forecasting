# Code — Ampacity Pipeline

This folder contains all pipeline code for the ampacity extension.
Every module is self-contained and can be run from the `proposal/` root.
All parameter values are verified from the literature surveys in `notes/`.

---

## Structure

```
code/
├── requirements.txt                       ← pip dependencies (numpy, pandas, scipy, ...)
│
├── 00_data_audit/
│   ├── audit_workbook.py                  ← full Darmstadt Excel column audit → notes/darmstadt_workbook_audit.md
│   └── inspect_workbook.py               ← quick head-dump of every sheet → notes/darmstadt_workbook_head.txt
│
├── 01_cable_thermal_model/
│   ├── cable_params.py                    ← all verified cable + installation parameters (Southwire, PG&E, Darmstadt)
│   └── neher_mcgrath.py                  ← IEC 60287 / N-M ampacity model; self-test reproduces Bates Table 3.1
│
├── 02_soil_thermal_properties/
│   ├── johansen.py                        ← Johansen (1975) thermal conductivity + conversion to ρ (°C·cm/W)
│   └── wilson_lookup.py                  ← Wilson et al. (2016) soil texture → Johansen parameters
│
├── 03_darmstadt_validation/
│   ├── load_darmstadt.py                 ← load + clean all released Darmstadt sheets
│   ├── validate_mf_iv.py                 ← WP2: validate vs MF_IV_CL (4 beddings, primary target)
│   ├── validate_sf_v_vi.py               ← WP2: validate vs SF V+VI (PVC duct, unfilled + grouted)
│   └── validate_mf_iii.py                ← WP2: sheath temp + moisture dynamics; NHR screening
│
├── 04_depth_interpolation/
│   └── depth_interp.py                   ← Crank-Nicolson interpolation: USCRN 50/100 cm → cable depth (0.82 m)
│
├── 05_dynamic_ampacity/
│   └── dynamic_ampacity_pipeline.py      ← WP3: full pipeline — USCRN → depth interp → Johansen → N-M → dynamic rating
│
└── 06_sensitivity/
    └── sensitivity_analysis.py           ← WP4: RHO sweep, Ta sweep, depth-ref sensitivity, load factor study
```

---

## Run Order

### Step 0 — Install dependencies
```bash
pip install -r code/requirements.txt
```

### Step 1 — Audit the Darmstadt dataset
```bash
python code/00_data_audit/inspect_workbook.py   # quick look
python code/00_data_audit/audit_workbook.py     # full audit → notes/darmstadt_workbook_audit.md
```

### Step 2 — Self-test the cable model (reproduces Bates Table 3.1: ~541 A)
```bash
python code/01_cable_thermal_model/neher_mcgrath.py
```

### Step 3 — Self-test the Johansen module
```bash
python code/02_soil_thermal_properties/johansen.py
python code/02_soil_thermal_properties/wilson_lookup.py
```

### Step 4 — Darmstadt validation (WP2)
```bash
python code/03_darmstadt_validation/load_darmstadt.py      # check sheet loading
python code/03_darmstadt_validation/validate_mf_iv.py      # primary validation
python code/03_darmstadt_validation/validate_sf_v_vi.py    # duct validation
python code/03_darmstadt_validation/validate_mf_iii.py     # sheath + moisture
```
Results written to `results/darmstadt_validation/`.

### Step 5 — Depth interpolation demo
```bash
python code/04_depth_interpolation/depth_interp.py
```
Writes `results/depth_interp/depth_interp_demo.png`.

### Step 6 — Sensitivity study (WP4)
```bash
python code/06_sensitivity/sensitivity_analysis.py
```
Writes to `results/sensitivity/`.

### Step 7 — Dynamic ampacity pipeline (WP3)
First, download USCRN data for a station and place in `data/uscrn/`:
```
https://www.ncei.noaa.gov/pub/data/uscrn/products/hourly02/
```
Then:
```bash
python code/05_dynamic_ampacity/dynamic_ampacity_pipeline.py --station 53974
```
Results written to `results/dynamic_ampacity/`.

---

## Key Parameter Sources (all [V] = verified from full text)

| Parameter | Value | Source |
|---|---|---|
| Soil share of thermal resistance | 70–90% | Bates 2021 Ch 1 [V] |
| N-M SS mean error | -8% ± 8.9% | Bates 2021 Table 9.1 [V] |
| N-M transient mean error | -0.5% ± 8.1% | Bates 2021 Table 9.8 [V] |
| Validated load factor | 66% → error -0.3% | Bates 2021 Ch 9 [V] |
| PG&E cable centre depth | 0.819 m (30" + OD/2) | EDS 038193/062288 [V] |
| NEC default RHO | 90 °C·cm/W | Bates 2021 Ch 2 [V] |
| EPR insulation rho | 350 °C·cm/W | N-M Table 6 via Bates [V] |
| PVC jacket rho | 500 °C·cm/W | N-M Table 6 via Bates [V] |
| Fiber/PVC duct rho | 480 °C·cm/W | N-M Table 6 via Bates [V] |
| SCAN ambient (Arizona, 99th pctile) | 34.6°C | Bates 2021 Ch 11 [V] |
| Sand NHR (probe) | 0.1 W/cm | Bates 2021 Ch 4 [V] |
| Law of Times | Rejected at 99.995% CI | Bates 2021 Ch 6 [V] |
| Darmstadt MV150 Al OD | 34 mm | Darmstadt paper Fig 2 [V] |
| Darmstadt PVC duct ID | 147.6 mm | Darmstadt paper Fig 4 [V] |
| Grouted duct ΔT penalty | +25–35% over direct-buried | Verschaffel-Drefke 2021 [V] |

---

## Limitations and TODOs

- `neher_mcgrath.py`: skin/proximity effect uses simplified Ruck formula; full IEC 60287 lookup tables would improve accuracy for larger conductors.
- `depth_interp.py`: uses uniform α profile; Bayesian inversion (Brunetti et al. 2022) should replace this for production use.
- `validate_mf_iv.py`: column identification relies on string matching — may need adjustment if workbook column headers differ from expected.
- `dynamic_ampacity_pipeline.py`: USCRN data must be downloaded manually; a download helper script (`scripts/download_uscrn.py`) should be added for WP1.
- Wilson table: `data/wilson_T1.csv` must be created from the Wilson et al. (2016) PDF for station-level lookup (27 of 39 stations covered [V]).

---

*All code written 4 November 2026. Parameter values sourced from full-text reads documented in `notes/survey_*.md`. No values invented.*
