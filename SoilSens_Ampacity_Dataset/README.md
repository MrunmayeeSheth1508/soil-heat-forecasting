# SoilSens–Ampacity Dataset Package

**Version:** 1.0  
**Compiled:** 2026-11-04  
**Project:** SoilSens — Soil-heat forecasting for dynamic cable ampacity  
**Contact:** See proposal document (`PROPOSAL_DRAFT_v3.md`)

---

## Overview

This package contains the compiled, cleaned, and documented data sources for the
SoilSens project. The project develops a soil-heat forecasting system (SoilSens)
that feeds a dynamic underground cable ampacity (DUCA) model. The goal is to
compute permissible current ratings for buried power cables using real-time and
forecast soil conditions rather than worst-case static assumptions.

The package organises data from three real-world domains:

| Domain | What it contains | Role in the model |
|--------|-----------------|-------------------|
| **Soil and Climate** | USCRN soil temperature, soil moisture, precipitation; Darmstadt site weather and soil moisture; Wilson soil-property parameters | Background ground conditions; model inputs and evaluation targets |
| **Electricity and Cables** | Darmstadt experimental current records and measured cable temperatures; cable catalogue (Southwire); load profiles | Cable heating and loading; experimental validation targets |
| **Installation and Materials** | Experimental trench and sensor layout (Darmstadt); reference trench geometries (PG&E); measured thermal and hydraulic material properties; SnoPUD backfill specifications | Heat-transfer model inputs; engineering context |

An **Assessment Cases** folder links these domains into evaluation scenarios:
experimental cases use real Darmstadt measurements; reference cases are
selected—not measured—scenarios combining USCRN locations with catalogued cables
and geometries.

> **What this package is not:**  
> The package does not include raw USCRN download files, model outputs, or any
> measured data from American utility cable installations (none exist in the
> project). Reference cases are forward-analysis scenarios, not new observations.

---

## Folder Structure

```
SoilSens_Ampacity_Dataset/
│
├── README.md                        ← this file
├── Source_Manifest.csv              ← one row per original source (9 sources)
├── Dataset_Overview.xlsx            ← 16-sheet workbook for inspection
│
├── 01_Soil_and_Climate/
│   ├── Stations.csv                 ← 13 USCRN pipeline stations (lat/lon/WBAN)
│   ├── Soil_Properties.csv          ← Wilson T1 soil properties (long format, 2,450 rows)
│   ├── Darmstadt_Experiment_Weather.csv  ← Darmstadt air/surface conditions (long format, 15,773 rows)
│   ├── Darmstadt_Soil_Moisture.csv       ← Darmstadt soil moisture by depth (10,074 rows)
│   ├── Darmstadt_Site_Weather.csv        ← Darmstadt 10-min site weather (17,064 rows)
│   └── USCRN_Hourly/
│       └── <station_id>.csv         ← 13 files, 26,304 rows each (2019–2021, hourly)
│
├── 02_Electricity_and_Cables/
│   ├── Cable_Catalogue.csv          ← 15 cables: Southwire (12) + Darmstadt documented (3)
│   ├── Load_Profile_Catalogue.csv   ← 5 named loading scenarios
│   ├── Load_Profiles.csv            ← Hourly load-factor curves (98 rows)
│   ├── Experimental_Loading.csv     ← Darmstadt recorded current, 10-min (36,599 rows)
│   └── Experimental_Temperatures.csv ← Darmstadt measured cable temperatures (97,284 rows)
│
├── 03_Installation_and_Materials/
│   ├── Experimental_Installations.csv ← 10 Darmstadt cable-run descriptions
│   ├── Reference_Installations.csv    ← 3 PG&E-based reference trench geometries
│   ├── Sensor_Metadata.csv            ← 36 Darmstadt sensor descriptions
│   ├── Material_Properties.csv        ← 68 material property values (64 DARM + 4 REF)
│   ├── Material_Curves.csv            ← 3,156 measured thermal/hydraulic curve points
│   └── Backfill_Specifications.csv    ← 29 SnoPUD acceptance limits and mix definitions
│
├── 04_Assessment_Cases/
│   ├── Experimental_Cases.csv         ← 6 Darmstadt validation cases
│   └── Reference_Cases.csv            ← 39 scenario combinations (13 stations × 3 cable configs)
│
├── 05_Documentation/
│   ├── Data_Dictionary.csv            ← 258 column definitions with units and types
│   ├── Quality_Flags.csv              ← 12 flags (QF01–QF11) with affected counts
│   └── Quality_Summary.csv            ← 31 file-level coverage and missingness rows
│
└── scripts/
    ├── part1_soil_climate.py          ← Builds 01_Soil_and_Climate/
    ├── part2a_darmstadt.py            ← Builds electrical and Darmstadt climate files
    ├── part2b_catalogues.py           ← Builds catalogues and installation tables
    ├── part3_sensors_cases.py         ← Builds sensors and assessment cases
    ├── part4_documentation.py         ← Builds documentation tables
    └── part5_workbook.py              ← Assembles Dataset_Overview.xlsx
```

---

## Quick Start

**To inspect the data:**  
Open `Dataset_Overview.xlsx`. The **Start_Here** sheet explains the contents and
how the sheets relate. Use the **Data_Dictionary** sheet to look up any column.

**To use the CSV files in analysis:**  
The CSV files are UTF-8 encoded with headers. Each key table has a stable ID
column (`station_id`, `cable_id`, `installation_id`, `material_id`, `case_id`)
so tables can be joined. See the Data Dictionary and Assessment Cases folder for
join keys.

**USCRN timestamp note:**  
Timestamps in `USCRN_Hourly/*.csv` are **local standard time (LST)**, not UTC.
The column is named `timestamp_lst`. Darmstadt files use `elapsed_time_d`
(elapsed days from experiment start) — these cannot be aligned to calendar dates.

---

## Rebuilding from Source

Run the scripts in order from the `SoilSens_Ampacity_Dataset/` directory.
On Windows PowerShell, prefix each command with `$env:PYTHONIOENCODING="utf-8"`:

```powershell
cd "C:\Users\jtani\.gemini\antigravity\scratch\soil-heat-forecasting\SoilSens_Ampacity_Dataset"
$env:PYTHONIOENCODING="utf-8"
python scripts\part1_soil_climate.py      # USCRN hourly, Wilson properties
python scripts\part2a_darmstadt.py        # Darmstadt loading, temperatures, weather
python scripts\part2b_catalogues.py       # Cables, installations, materials, backfill
python scripts\part3_sensors_cases.py     # Sensors, experimental/reference cases
python scripts\part4_documentation.py     # Data dictionary, quality flags, manifest
python scripts\part5_workbook.py          # Excel workbook
```

**Prerequisites:** Python 3.9+, `numpy`, `pandas`, `openpyxl`.  
Source data must be present at the paths hard-coded in each script
(relative to the `soil-heat-forecasting` workspace root).

---

## Key Caveats and Quality Notes

### QF05 — Darmstadt elapsed-time only
Darmstadt experiment files record **elapsed days** from an undocumented experiment
start date. No calendar timestamps are available in the published workbook. These
records cannot be directly aligned to USCRN local-time observations.

### QF08 — USCRN missing soil moisture
Two stations have >10% missing 50 cm soil moisture over 2019–2021:  
`AL_Fairhope_3_NE` (14.5%) and `WY_Sundance_8_NNW` (19.7%).  
Gaps are left empty in the package; the ampacity pipeline forward-filled them
internally, but that fill is not reproduced here.

### QF10 — USCRN variables limited to compiled arrays
The compiled NPZ arrays contain only **soil temperature, soil moisture, and
precipitation**. Air temperature, solar radiation, relative humidity, and surface
temperature are **not** in the hourly CSV files. They would require re-extraction
from the raw USCRN `hourly02` flat files.

### QF11 — Southwire catalogue transcription discrepancy
The Southwire 750 kcmil listing shows "diameter over insulation shield" = 1.495 in,
which appears inconsistent with the values for neighbouring conductor sizes
(smaller sizes produce larger values). Reproduced as printed; verify against the
Southwire datasheet before use.

### Burial depth convention (Reference Installations)
`Reference_Installations.csv` lists `burial_depth_m` converted from the cover
specification in PG&E EDS 038193 (24, 30, 36 in). This depth represents
**cover to conduit top**, not depth to conductor centre.  
For the 30 in (0.762 m) case, the true conductor-centre depth is approximately
**0.819 m** (+0.057 m) when conduit OD is accounted for.  
The ampacity results in `multistation_summary.csv` use the cover depth, not the
corrected centre depth. This is flagged but not corrected in the current pipeline.

### LST vs UTC
USCRN timestamps are **local standard time** (`timestamp_lst`). No conversion to
UTC has been applied. Darmstadt data uses elapsed time only. Keep these time
references distinct in any joint analysis.

### Darmstadt MF_III_CL sheet label
The Darmstadt workbook sheet `MF_III_CL` carries the header label "(IV)", but the
published paper (Verschaffel-Drefke et al. 2021, Sec 3.3 and Fig 11 caption)
identifies this run as **configuration (II)** — two MV trefoils. The load column
in `Experimental_Loading.csv` is named `LOAD_II` and a `config_note` column
records this discrepancy.

---

## Licence and Attribution

| Source | Licence |
|--------|---------|
| USCRN data (NOAA NCEI) | Public domain — U.S. government work |
| Wilson et al. (2016) T1 | Journal publisher terms; cite the paper |
| **Darmstadt dataset (TUdatalib-665)** | **CC BY-NC 4.0 — non-commercial use only** |
| Darmstadt paper (Energies 2021) | MDPI open access (CC BY) |
| Southwire SPEC 46319 | Manufacturer datasheet; reproduce with attribution |
| PG&E EDS 038193 / EDS 062288 | PG&E publication; cite document numbers |
| SnoPUD material standard 1002182.1 | Utility publication; cite document number |
| Bates (2021) dissertation | Open copy; cite the dissertation |

> **Important:** Any redistribution or use of the Darmstadt data must comply with
> the **CC BY-NC 4.0** licence (non-commercial). The full licence text is at
> <https://creativecommons.org/licenses/by-nc/4.0/>.

---

## Citations

```
[S01] NOAA NCEI. U.S. Climate Reference Network (USCRN) hourly02 data.
      https://www.ncei.noaa.gov/pub/data/uscrn/products/hourly02/
      (Accessed 2026-10-08; 13 stations, 2019–2021.)

[S02] NOAA NCEI. USCRN station metadata.
      https://www.ncei.noaa.gov/access/crn/

[S03] Wilson, G. W., et al. (2016). "Soil water characteristic database."
      Vadose Zone Journal, 15(10). https://doi.org/10.2136/vzj2016.05.0047

[S04] Verschaffel-Drefke, C., et al. (2021). Dataset: Cable test site Darmstadt.
      TU Darmstadt TUdatalib, doi:10.48328/tudatalib-665. Licence: CC BY-NC 4.0.

[S05] Verschaffel-Drefke, C., et al. (2021). "Heat dissipation in variable
      electrical resistivity soils: Experiences from a field-scale monitoring site."
      Energies, 14(23), 7189. https://doi.org/10.3390/en14217189

[S06] Southwire Company. SPEC 46319 Rev 1.000.009 (3 Oct 2025). MV-105 15 kV
      cable specification. https://cabletechsupport.southwire.com/en/cablespec/
      download_spec/?country=US&spec=46319

[S07] Pacific Gas and Electric Company. EDS 038193 Rev 16 and EDS 062288 Rev 21
      (June 2023). Underground primary/secondary distribution design standards.

[S08] Snohomish PUD. Material standard 1002182.1 Rev 2 (11 Apr 2024).
      Fluidised thermal backfill. https://esr.snopud.com/Content/Material/
      Compounds/1002182.1.htm

[S09] Bates, E. (2021). Soil thermal resistance and cable ampacity: PhD dissertation.
      See proposal/notes/survey_bates_2021.md. Neher-McGrath constants via
      proposal/code/01_cable_thermal_model/cable_params.py.
```

---

*This package was compiled by the Antigravity agent as part of the SoilSens project.*

---

## Changelog

- **v1.1 (2026-11-04):** PG&E-derived-depth status in `Reference_Installations.csv` and the pointer in `Reference_Cases.csv` updated after the depth-corrected rerun (results are in the proposal folder, not in this package); `Quality_Flags.csv` extended with QF12-QF17 (calculation issues found in the V4 audit); workbook rebuilt. Applied by `scripts/patch_v11_rerun_and_audit.py`. **Re-running `part4_documentation.py` regenerates `Quality_Flags.csv` and removes QF12-QF17 unless the patch is re-applied afterwards.**
- **v1.0 (2026-11-04):** first release (`SoilSens_Ampacity_Dataset_v1.0.zip`, unchanged).
