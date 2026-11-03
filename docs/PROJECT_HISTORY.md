# Project history: from the first idea to the forecast benchmark

Every stage below has its scripts in `scripts/`, its outputs in `results/`, its report in `reports/`, and what it taught us. Numbers are as reported by the executing agent at the time. Dates are 2026.

Naming: stage folders `scripts/01_…` to `scripts/08_…` follow this order.

---

## Stage 1 (8 Oct): Can the question be asked at all? Data access and a first look

**Original idea.** Does a moisture-dependent conduction description explain subsurface temperature better than a constant effective diffusivity? Neural operators were a possible later tool.

| | |
|---|---|
| Scripts | `scripts/01_data_audit_and_pilots/01_inventory.py`, `02_episode_audit.py`, `03_episode4_audit.py` |
| Results | `results/01_early_pilots_and_audits/inventory_out.txt`, `inventory_step1.txt`, `episode_out.txt`, `ep4_audit_out.txt`, `stillwater_2019.txt` |
| Data | `data/raw_uscrn_hourly_samples/` (Selma, Versailles 2019–2020) |

- 80 non-Alaska 2019 station files screened: 31 met "≥3 co-located depths, annual moisture range >0.05, >50% non-freezing", 23 had all five depths.
- Selma 2019–2020: 15,605 five-depth valid non-freezing hours (88.9%), 8 episodes. Versailles: 1 episode.
- Episode 4 (567 h, 12 Sep–5 Oct 2019) was essentially a dry-down: moisture response ≈0.002, rain 0.4 mm, within-episode moisture range 0.156.
- **Learned:** access and coverage justify an episode audit, not a conclusion that moisture is identifiable. "Gate 2 passed decisively" was withdrawn. Integer-like deep readings reflect 0.1 °C resolution, not zero information.

## Stage 2 (8 Oct): First inverse pilot, its false null, and the correction

| | |
|---|---|
| Scripts | `04_shallow_pilot.py`, `04b_shallow_pilot.py`, `09_amplitude_check.py`, `10_windowed_alpha.py`, `11_episode_table.py`, `12_four_model_rerun.py` (folders `01_…` and `02_…`) |
| Results | `pilot_out.txt`, `pilot_out2.txt`, `amp_check_out.txt`, `windowed_out.txt`, `episode_table_out.txt`, `episodes14.npz`, `rerun_out.txt` |
| Reports | `reports/01_early_project/soil_reexamination.md`, `soil_four_model_rerun.md` |

- Uniform 5–20 cm column with measured T5 and T20 boundaries, 14 Selma episodes, alpha fitted on first two-thirds and tested on the last third.
- First result: moisture coefficient collapsed to zero and a 33% amplitude excess, read as "model structurally wrong".
- **Corrections:** the moisture coefficient had been forced positive, so the null only tested a positive slope. The 33% was one transfer interval. A periodic analytic check showed solver amplitude error 0.06–1.0%, and amplitude-versus-phase diffusivity agreed near 1 at 10–20 cm (median ratio 1.01) but not at 5–10 cm (0.44).
- Four-model rerun (constant / moisture / temperature / both): moisture and temperature were strongly collinear (r = −0.59 hourly, −0.87 between episodes). Moisture alone −0.131 [−0.396, +0.048]; adding temperature flipped it to +0.147 [−0.157, +0.424]. Constant alpha won all 3 later episodes.
- **Learned:** no independent moisture effect established, and also no proof of absence. Conditional reconstruction with measured boundaries is not forecasting.

## Stage 3 (8 Oct): Do other stations behave the same?

| | |
|---|---|
| Scripts | `scripts/03_multistation_audit/13_multistation_download.py` (network), `14_contrast_audit.py`, `15_coverage.py`, `16_reconcile_qc_select.py`, `17_multistation_pilot.py` |
| Results | `audit_out.txt`, `audit_station_table.csv`, `audit_dry_days.csv`, `coverage_out.txt`, `reconcile_out.txt`, `record_checks.csv`, `multipilot_out.txt` |
| Data | `data/multistation_npz/` |
| Reports | `reports/01_early_project/soil_multistation_audit.md`, `soil_multistation_pilot.md` |

- 131 lower-48 stations requested for 2019–2021 (393 station-years); 89 had ≥30 informative days; 39 passed the full contrast criterion; 52,337 same-temperature day pairs (reused days, not independent).
- Six-station transfer (Muleshoe, McClellanville, Champaign, Goodwell, Lincoln, Selma) with local calibration: shared moisture coefficient +0.046 [−0.016, +0.113], sign changed between folds, no improvement.
- **Learned:** a shared linear moisture term does not transfer; station differences motivated looking for measured soil properties.

## Stage 4 (8 Oct): Soil properties

| | |
|---|---|
| Scripts | `scripts/04_soil_properties_wilson/18…25` (SDA / SoilSIP probes, network), `26_wilson_table.py` |
| Results | `results/02_soil_properties/` (`soil_lab_out.txt`, `soil_lab_pedons_5_20cm.csv`, `stations.tsv`, `wilson/…`), `audit15_table.csv` |
| Data | `data/uscrn_soil_sip/` |
| Reports | `reports/01_early_project/soil_property_feasibility.md`, `soil_wilson2016_retrieval.md` |

- NRCS searches found only nearby historical pedons, and "no station soil data exist" was wrong. The Wilson 2016 supplement gives 70 stations with texture, bulk density and retention at depth; 27 of the 39 later Phase 3 stations are in it.
- 15 candidate stations audited, 14 kept (Elgin depth mapping ambiguous).
- **Learned:** property-supported stations exist, but cores are ~2009–2011 and porosity vs measured moisture does not always agree (moisture sometimes exceeds the porosity estimate).

## Stage 5 (14 Oct): Literature, then a change of direction

| | |
|---|---|
| Scripts | `scripts/05_literature_tooling/` (`27…30`, `34…38`, `41…43`) |
| Texts | `literature/` (PDFs, `full_texts_verified/`, `extracted_texts/`) |
| Reports | `reports/05_literature/` (survey master, full survey, index audit), `reports/02_direction_and_proposals/` |

What each paper family changed:

| Paper family | What it showed | Effect on the project |
|---|---|---|
| Brunetti 2022 | Depth-resolved Bayesian diffusivity, works only with strong forcing, low noise, precise depths | Inverse estimation depends on forcing and geometry; thresholds are setup-specific |
| Dai 2019, Du 2020, He 2021 | Conductivity schemes already evaluated in land models and fields | Original "novel field comparison" claim weakened |
| Peng 2024 | Random forest for diffusivity on lab databases | Property regression is not field forecasting |
| Wang 2023, Xie 2024, Huang 2026, Widyastuti | PINNs / differentiable physics | Close hybrid precedents; architecture alone is not novelty; observation configuration limits identifiability |
| Xu 2020, Peng 2025 | Lab conductivity hysteresis | Motivated the history question (Direction B) |
| Li 2022 | Attention-LSTM soil temperature | Sequence precedent, no physical baseline; first author is Li, not "Fang" |
| Gu 2026, Garcia-Garcia 2023, Bai 2026 | Soil heat extremes and depth amplification | Climate motivation; titles in the old index were wrong (see index audit) |
| Shao 2024 | Ecosystem recovery at flux towers | Relevant to Direction C only |

- **Learned:** broad material-law novelty was weak. Project moved to an event-focused study (Direction A) on the same data.

## Stage 6 (14 Oct): Phase 3 events, Direction A selection and pilot A

| | |
|---|---|
| Scripts | `scripts/06_phase3_events_and_pilotA/31_phase3_download.py`, `32_event_inventory.py`, `33_thermal_check.py`, `35_c_feasibility.py`, `39_pilotA_solver_check.py`, `40_pilotA_run.py`, `44_archive_and_repro_setup.py` |
| Results | `results/03_phase3_events_and_pilotA/` (`event_inventory.csv`, `pilotA_part1/2/3_dev/test.csv`, `thermal_check.csv`, `c_*`, `archive_pre_diag/`, `repro/`) |
| Specs | `specs/event_rules.md`, `specs/pilotA_prereg.md` |
| Data | `data/phase3_processed_hourly/` (39 stations, 2012–2021) |
| Reports | `reports/02_direction_and_proposals/`, `reports/03_pilots_and_diagnostics/phase3_pilotA_report.md` |

- Directions: A (heat penetration and persistence), B (history information), C (ecosystem recovery). A selected; C parked (500 m land cover, 16-day NDVI composites, no flux co-location).
- Event definition: hot day ≥ local day-of-year P90 of Tmax; spells ≥3 hot days, merging gaps ≤2; dry = ≤5 mm rain and moisture ≤ local P40. Inventory: 490 hot-dry spells, 156 complete sequences at 38 stations (113 dev, 43 test).
- Measured profile (dev): median 5 cm peak anomaly 3.8 °C, 20 cm 2.8 °C, 100 cm 1.3 °C; peaks delayed by days with depth.
- Rain-property test (identified pairs): contrast +0.142 [0.002, 0.277] dev, +0.141 [−0.143, 0.433] test; frozen confirmation rule failed. 48 development windows with identified fits give the global alpha used later (4.322e-7 m²/s).
- **Learned:** rain-linked change not confirmed. The pilot's solver and events became the assets for the next stages.

## Stage 7 (15 Oct): Was the rain effect real? Layered and identifiability diagnostics

| | |
|---|---|
| Scripts | `scripts/07_layered_and_identifiability/45…53` |
| Results | `results/04_layered_diagnostic/`, `results/05_identifiability_diagnostic/` |
| Specs | `specs/layered_spec_frozen.md`, `specs/ident_diag_spec_frozen.md` |
| Reports | `reports/03_pilots_and_diagnostics/layered_null_diagnostic_report.md`, `ident_screen_diagnostic_report.md`, figures in `reports/figures/` |

- Fixed-layer null: simulated columns with unchanging properties, run through the same estimator and real boundaries. Weakly layered columns did not reproduce the +0.14 point contrast.
- Identification rule audit: of 122 usable pairs, 74 retained; the rule mostly retained windows the uniform model fits well (RMSE ~0.21 retained vs 0.64–0.74 rejected). Test contrast moves from +0.141 to −0.203 depending on selection.
- Same-population comparison could not decisively exclude fixed-layer explanations.
- **Learned:** the rain estimate depends on model, selection rule and forcing. Closed as unresolved.

## Stage 8 (15 Oct): Forecasting, the current project

| | |
|---|---|
| Scripts | `scripts/08_forecast_benchmark/54…57`, `src/forecastlib.py` |
| Results | `results/06_forecast_benchmark/` |
| Specs | `specs/forecast_spec_frozen.md` |
| Reports | `reports/04_forecast_benchmark/` (feasibility, audit and AI spec), `reports/06_overview/` |

- Online trigger: third consecutive relative-hot day, issue 08:00 local standard time next morning. 1,907 spells, 1,689 scored (973 dev, 716 val).
- Competitors B1 persistence, B2 seasonal anomaly, C1/C2/C3 conduction, RECON (future boundaries, diagnostic only). Validation median event MAE, 20 cm: 0.740, 0.708, 0.704, 0.673, 0.704, 0.262; 50 cm: 0.274, 0.352, 0.333, 0.316, 0.334, 0.198.
- Audit: forecasters use past-only inputs, verified by a +37 °C / 999 mm corruption test; per-event alpha uses only the preceding 168 h; 11 (not 25) stations have ≥2 identified windows; the "82% of error" statement was withdrawn.
- Current plan: GRU and boosted-tree comparator, 20 cm primary, 50 cm secondary, staged rainfall and moisture ablations (specification written, not trained).

---

## What carried forward

| From | Used in later work |
|---|---|
| Crank–Nicolson solver (`heatsolver.py`) | pilot A, layered diagnostic, forecast competitors C1–C3 and RECON |
| Uniform-diffusivity estimator | C2 per-event alpha, development alpha references |
| Event rules and station audit | forecast trigger and 39-station set |
| Wilson property table | static soil inputs for the AI models |
| Negative / inconclusive results | why the project forecasts temperatures instead of claiming a moisture law |

See `RUN_ORDER.md` for how to run each stage and `stage_run_log.md` for which earlier scripts re-execute.
