# Run order and reproducibility status

## One-time setup

```
pip install -r requirements.txt
python setup_workspace.py          # builds ./workspace (the layout the scripts expect)
```

Every script resolves its root to `workspace/` through `src/config.py` and reads/writes only there. The shipped `results/` and `data/` folders are never overwritten, so they remain the reference to compare against. Run scripts from anywhere, e.g. `python scripts\08_forecast_benchmark\55_forecast_verification.py`. To start fresh: `python setup_workspace.py --clean`.

Only the absolute-path strings in the scripts were changed (marked `# PATH-PATCH` on the injected import line). Logic and frozen parameters are unmodified.

## Forecast benchmark (the headline results): TESTED

| Step | Script | Needs | Produces (in `workspace/phase3/forecast/`) |
|---|---|---|---|
| 1 | `scripts/08_forecast_benchmark/54_forecast_inventory.py` | `phase3/data`, `phase3/stations_phase3.csv` | `issue_inventory.csv`, `inventory_summary.txt` |
| 2 | `55_forecast_verification.py` | step 1, `archive_pre_diag/pilotA_part2_dev.csv` | `forecast_verification_out.txt` (all checks must PASS) |
| 3 | `56_forecast_scores.py` | steps 1-2 | `forecast_scores.csv`, `forecast_summary.txt`, `forecast_bootstrap.csv` |
| 4 | `56b_forecast_tail.py` | step 3 | appends lead profile and decision rule to `forecast_summary.txt` |
| 5 | `57_forecast_figure.py` | step 3 | `forecast_figure.png` |

`python reproduce_check.py` runs steps 1 and 3 and compares the outputs with the shipped reference (see result below).

## Earlier stages (01-53): executed and compared

All earlier scripts were run inside `workspace/` (`python run_earlier_stages.py`; per-script status in `stage_run_log.md`) and their outputs compared byte-for-byte or value-for-value with the shipped originals (`python compare_outputs.py <unix_time>`, result in `stage_output_comparison.md`).

| Result | Scripts |
|---|---|
| Reproduced, outputs identical to shipped | 02, 03, 04b, 09, 10, 11, 12, 14, 15, 16, 17, 25, 26, 32, 33, 39, 40 `dev`, 45, 46 `dev` (85 archived fits, 0 mismatches), 47, 48, 49, 50, 51, 52, 53 |
| Need the network, not run offline | 01, 13, 18-24, 27-31, 34-38 (NCEI, USDA SDA, literature APIs). 24 and 35 failed here for that reason; 35 also crashed on a missing `center_name` column after its network step. |
| Reads files outside the project | 28, 30, 41-43 (Downloads docx/xml, conversation artifacts) |
| Not run on purpose | 44 (moves files in the frozen archive); `40 test` and `46 test` (frozen run-once test sets) |
| Original bug | 04 (array-shape error, superseded by 04b) |

Notes:
- `40` and `46` need an argument: `python scripts/06_phase3_events_and_pilotA/40_pilotA_run.py dev`.
- 49-53 read the shipped layered/ident inputs; their outputs also match when 46 `dev` is regenerated first.
- Scripts that need the network still point at the same NCEI/SDA URLs; their saved results are in `results/` and `data/`.

The table below lists the intended order for each stage.

| Stage | Order | Notes |
|---|---|---|
| 01 data audit | `01_inventory` → `02_episode_audit` → `03_episode4_audit` → `04_shallow_pilot` / `04b` | Read `raw/` |
| 02 amplitude / alpha | `09_amplitude_check` → `10_windowed_alpha` (reads `pilot_out2.txt`) → `11_episode_table` (writes `episodes14.npz`) → `12_four_model_rerun` | |
| 03 multistation | `13_multistation_download` (network) → `14_contrast_audit` → `15_coverage` → `16_reconcile_qc_select` → `17_multistation_pilot` | Uses `multi/` |
| 04 soil properties | `18-25` probes (network: SoilSIP, SDA) → `26_wilson_table` | Wilson table needs `wilson/Supplemental_Table_T1.xls` |
| 06 phase 3 | `31_phase3_download` (network) → `32_event_inventory` → `33_thermal_check` → `35_c_feasibility` → `39_pilotA_solver_check` → `40_pilotA_run` → `44_archive_and_repro_setup` | `40` is long-running; its archived outputs are in `results/03_...` |
| 07 layered / identifiability | `45_frozen_columns` → `46_layered_diagnostic` → `48_layered_verification` → `49_layered_analysis` → `50`, `51` → `52_ident_diagnostic` → `53_ident_diag_extra` | `47_compare_repro` compares against `phase3/repro` |
| 05 literature tooling | `27`, `28`, `29`, `30`, `34`, `36-38`, `41-43` | Network searches and PDF extraction |

Frozen rules: `layered_test_RUN_ONCE.marker` and the `*_frozen*` specs record single-run test sets. Do not re-run those test-set scripts expecting different outcomes.

## External inputs not included in this repo

- `C:\Users\jtani\Downloads\Soil_Project_Complete_Synthesis (1).docx` (scripts 41-43, 42 salvage).
- `C:\Users\jtani\Downloads\esurf-10-687-2022.xml` (script 28).
- Conversation-artifact paths under `...\brain\...\.system_generated\steps\...` (literature scripts).
- Live network sources: NOAA NCEI USCRN, USDA SDA, literature APIs.
- Wilson 2016 PDF: only the 443-byte access-denied stub exists; the supplemental table is included.

The first two are already reflected in `docs/syntheses/` and the literature scripts' outputs.
