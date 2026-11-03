# Soil Heat Forecasting (USCRN)

Question: can ML use the preceding week of soil temperature, rainfall and moisture to improve 1-72 h soil-temperature forecasts (primary 20 cm, secondary 50 cm) over persistence and a 1D conduction model, and does moisture history add information?

This repository is an **organised copy** of `C:\Users\jtani\.gemini\antigravity\scratch\soil` plus the reports written during the project. The originals were not modified.

## Layout

| Folder | Contents |
|---|---|
| `src/` | Shared libraries: `heatsolver.py` (Crank-Nicolson solver), `pilotA_estimator.py` (diffusivity estimator), `layeredsolver.py`, `forecastlib.py` (competitors B1/B2/C1/C2/C3/RECON) |
| `scripts/` | Numbered scripts grouped by project stage (below) |
| `specs/` | Frozen specifications and pre-registrations |
| `data/` | All data, see `data/README.md` (715 MB) |
| `results/` | Script outputs (CSV/TXT/NPZ), grouped by stage |
| `reports/` | Written reports by theme, plus `figures/` |
| `literature/` | Not in the repository (private literature review); shared separately with the team |
| `docs/` | Syntheses and USCRN documentation |
| `ENVIRONMENT.txt`, `_build_log.json` | Package versions and download date; copy log |

## Project stages

| # | Scripts | Results | What happened |
|---|---|---|---|
| 01 | `01-04b` | `results/01_early_pilots_and_audits` | Stillwater inventory, episode audit, single-station pilot |
| 02 | `09-12` | same | Diurnal-amplitude diffusivity, windowed alpha, four-model rerun |
| 03 | `13-17` | same | Multistation download, contrast audit, QC, pilot |
| 04 | `18-26` | `results/02_soil_properties` | SoilSIP / SDA probes, soil-lab data, Wilson 2016 table |
| 05 | `27-30, 34-38, 41-43` | not in repository | PDF extraction, citation search, literature screening (private) |
| 06 | `31-33, 35, 39, 40, 44` | `results/03_phase3_events_and_pilotA` | 39-station event inventory, solver check, pilot A |
| 07 | `45-53` | `results/04_*`, `results/05_*` | Layered and identifiability diagnostics (rain-property question closed as unresolved) |
| 08 | `54-57` | `results/06_forecast_benchmark` | Causal 72 h forecast benchmark, RECON diagnostic |

Start with `reports/06_overview/soil_project_complete_narrative.md`, then `reports/04_forecast_benchmark/forecast_audit_and_ai_spec.md`.

## Headline numbers (validation, 716 events, 99 clusters)

Median event MAE over hours 1-72 (`results/06_forecast_benchmark/forecast_bootstrap.csv`):

| | B1 | B2 | C1 | C2 | C3 | RECON (diagnostic) |
|---|---|---|---|---|---|---|
| 20 cm | 0.740 | 0.708 | 0.704 | 0.673 | 0.704 | 0.262 |
| 50 cm | 0.274 | 0.352 | 0.333 | 0.316 | 0.334 | 0.198 |

RECON uses observed future 5 and 100 cm temperatures; it is not a forecaster. Events: 1,907 detected, 1,689 in the common set (973 dev, 716 val).

## Status

- Baselines and verification checks: done.
- AI spec (GRU + gradient-boosted trees, moisture ablation): written, not trained.
- Rain-property experiment: closed as unresolved.

## Running code

```
pip install -r requirements.txt
python setup_workspace.py        # rebuilds the flat layout the scripts expect in ./workspace
python reproduce_check.py        # reruns inventory + scoring, compares with shipped results
```

Scripts resolve their old absolute root to `workspace/` via `src/config.py` and never write over `results/` or `data/`. Full order and the status of every stage: `RUN_ORDER.md`.

**Reproducibility, tested:** rerunning `54_forecast_inventory.py` and `56_forecast_scores.py` from this repo reproduced `issue_inventory.csv` (1,907 rows) and `forecast_scores.csv` (1,689 rows) with max numeric difference 0.0, and `55_forecast_verification.py` passes all checks. Earlier-stage scripts 01-53 were also executed (`stage_run_log.md`); offline-runnable ones reproduce the shipped outputs byte-for-byte (`stage_output_comparison.md`). Scripts that need the network or files outside the project are listed in `RUN_ORDER.md`. See `docs/PROJECT_HISTORY.md` for the chronological story.

## Ampacity extension (`proposal/` and `SoilSens_Ampacity_Dataset/`)

Connects soil temperature and moisture to buried-cable ampacity (Neher-McGrath-style steady-state model).

| Folder | Contents |
|---|---|
| `proposal/PROPOSAL_DRAFT_v3.md`, `proposal/V4_CLARIFICATION_RESPONSE.md` | Latest proposal draft and the audit of what is implemented, what needs correction and what is proposed |
| `proposal/code/` | Cable model, Johansen soil model, Darmstadt validation scripts, depth interpolation, dynamic-ampacity pipeline, sensitivity analysis |
| `proposal/results/` | Summaries of the 13-station runs (original depths and PG&E-derived depths), Darmstadt validation outputs, sensitivity tables |
| `proposal/notes/` | Validation findings, workbook audit (literature surveys kept private) |
| `SoilSens_Ampacity_Dataset/` | Cleaned CSV dataset package with data dictionary, quality flags, source manifest, Excel overview and rebuild scripts (see its own README) |

**Read `proposal/V4_CLARIFICATION_RESPONSE.md` before using any ampacity number.** The static-versus-dynamic comparison uses unmatched assumptions, the MF_III and SF V+VI Darmstadt validations contain mapping errors, and the ampacity results are historical calculations, not forecasts.

## Data and files not included in the repository

Excluded for size or copyright; regenerate or download as noted.

| Excluded | How to get it |
|---|---|
| `data/phase3_processed_hourly/` (574 MB), `data/uscrn_soil_sip/` | `scripts/06_phase3_events_and_pilotA/31_phase3_download.py`; `scripts/04_soil_properties_wilson/` (network) |
| Per-station ampacity time series and plots | `python proposal/code/05_dynamic_ampacity/run_all_stations.py`; `run_corrected_depth.py` |
| Darmstadt workbook (CC BY-NC 4.0, non-commercial) | TUdatalib, DOI 10.48328/tudatalib-665 |
| Paper PDFs, standards (PG&E, Southwire, SnoPUD) and full-text extractions | See DOIs and document numbers in `proposal/notes/` and `SoilSens_Ampacity_Dataset/Source_Manifest.csv` |
| Dataset ZIPs | Built from `SoilSens_Ampacity_Dataset/` |

No licence file has been added yet; choose one before making the repository public. The Darmstadt data are non-commercial only.
