# V4_CLARIFICATION_RESPONSE

Prepared 2026-11-04. Method: files read, saved results re-tabulated, and single-point traces of existing functions. **No training, no simulation of new scenarios and no station-wide comparison was run for this document.** The depth-corrected ampacity rerun requested in the same message is reported separately (Section 4a) and is stored beside, not over, the historical results.

Status vocabulary: **completed**, **partially implemented**, **proposed**, **unresolved**.
Workspace root: `C:\Users\jtani\.gemini\antigravity\scratch\soil-heat-forecasting\` (abbreviated `WS\`).

> [!IMPORTANT]
> Four findings change how V4 must describe existing work. Each is detailed below.
> 1. The "dynamic" and "static" ampacity branches are **not matched** (Q4). About +109% of the +86–145% "headroom" is produced by assumptions, not soil.
> 2. The MF_III validation compares a **silt** sheath sensor and silt moisture sensor against **sand** parameters, passes moisture in **percent** to a function expecting m³/m³, and the "45.8 °C·cm/W" is an artefact of that (Q9).
> 3. The SF V+VI comparison drives **both** configurations with configuration V's current (VI has its own, larger, recorded current), pairs only 2,440 of 12,278 rows, and has a duct-depth sign error (Q9, Q10).
> 4. No GRU, boosted-tree, LSTM or hybrid model exists as code or results; only specifications. v3 says otherwise (Q2).

---

## 1. Which files represent the latest project state?

| Item | Latest file | Last modified (local) | Status |
|---|---|---|---|
| Proposal | `WS\proposal\PROPOSAL_DRAFT_v3.md` | 04-11 01:41 | completed draft; **needs the corrections in this document**; v4 not yet written |
| Forecasting specification (frozen) | `WS\specs\forecast_spec_frozen.md` (benchmark) and `WS\reports\04_forecast_benchmark\forecast_audit_and_ai_spec.md` §9 (training-ready GRU/GBT spec) | 15-10 | completed (specs) |
| Forecasting implementation | `WS\src\forecastlib.py`, `WS\src\heatsolver.py`, `WS\scripts\08_forecast_benchmark\54–57_*.py` | 03-11 21:52 / 14-10 | completed for baselines only |
| Forecast results | `WS\results\06_forecast_benchmark\` (`forecast_scores.csv`, `forecast_summary.txt`, `forecast_verification_out.txt`, `issue_inventory.csv`) | – | completed |
| Cable model | `WS\proposal\code\01_cable_thermal_model\neher_mcgrath.py`, `cable_params.py` | 04-11 | completed, with issues in Q6 |
| Ampacity pipeline | `WS\proposal\code\05_dynamic_ampacity\dynamic_ampacity_pipeline.py`, `run_all_stations.py` | 04-11 | completed; branches unmatched (Q4) |
| Ampacity results, original | `WS\proposal\results\dynamic_ampacity\multistation_summary.csv` (+ 39 timeseries) | 04-11 | preserved unchanged |
| Ampacity results, depth-corrected | `WS\proposal\results\dynamic_ampacity_corrected_depth\` | 04-11 03:38 | **new**, added alongside |
| Darmstadt validation results | `WS\proposal\results\darmstadt_validation\*.csv`; narrative `WS\proposal\notes\VALIDATION_FINDINGS.md` | 04-11 | completed code; **narrative needs correction** |
| Sensitivity | `WS\proposal\results\sensitivity\*.csv`; `notes\VALIDATION_FINDINGS.md` §4 | 04-11 | completed; denominators inconsistent (Q11) |
| Dataset package | `WS\SoilSens_Ampacity_Dataset\` (46 files), `Dataset_Overview.xlsx`, ZIP `WS\SoilSens_Ampacity_Dataset_v1.0.zip` | 04-11 03:16 | completed |
| Completion summary | `…\brain\d895d91a-…\dataset_completion_summary.md` | 04-11 03:17 | completed |

**Does the ZIP predate the corrections?** I cannot inspect the ZIP you uploaded, so I cannot give its contents. By timestamps: `PROPOSAL_DRAFT_v3.md` was last written 01:41 and `README.md` 01:43; the dataset package (LST field name `timestamp_lst`, MF_III_CL = configuration II, Southwire flag QF11, depth-scenario IDs `REF_DEPTH_*`) was built 02:00–03:16; the depth-corrected rerun finished 03:38. **Any ZIP assembled before about 03:16 predates the dataset package and all of those corrections**, and any ZIP before 03:38 lacks the corrected-depth results. Nothing older was overwritten.

**Housekeeping incident.** During this session the unpacked `SoilSens_Ampacity_Dataset\` folder was found missing from `WS\` (the ZIP was intact). I did not delete it and cannot say what removed it. I restored it by extracting the ZIP (integrity test passed, 46 entries). Contents equal the 03:16 build.

**Correction needed in v3:** none to the file list; add a "Document and data versions" line to v4 giving the files above.

---

## 2. What forecasting work is actually completed?

| Component | Implemented? | Trained? | Evaluated? | Evidence |
|---|---|---|---|---|
| Original temperature baselines B1 persistence, B2 seasonal-anomaly | **Yes** | n/a (non-parametric; development-year climatology only) | **Yes**: validation 2018–2021, 1,689 scored spells (973 development, 716 validation) | `src\forecastlib.py`; `scripts\08_forecast_benchmark\54–57`; `results\06_forecast_benchmark\forecast_summary.txt` |
| Conduction forecasters C1/C2/C3 (Crank–Nicolson, forecast boundaries) | **Yes** | one scalar diffusivity per rule, fitted on past data only (global 4.322e-7 m²/s from 48 development windows) | **Yes** | `src\heatsolver.py`, `forecastlib.py`; `forecast_verification_out.txt` (8 checks pass) |
| RECON (observed future boundaries) | Yes | – | Yes, **diagnostic only, not a forecast** | same |
| GRU | **No code** | **No** | **No** | Specified in `reports\04_forecast_benchmark\forecast_audit_and_ai_spec.md` §9.5; `requirements.txt` says torch is "only needed for the planned GRU"; no `torch` import in any project script (grep) |
| Gradient-boosted trees | **No code** | **No** | **No** | spec §9.4; xgboost/lightgbm listed in requirements but not imported |
| LSTM boundary predictor | **No** | **No** | **No** | Appears only in `PROPOSAL_DRAFT_v3.md` §2.3 and in literature-search queries |
| Differentiable NN/heat-solver hybrid | **No** | **No** | **No** | `depth_interp.py` solver is not differentiable and has no learned component; `PROPOSAL_DRAFT_v3.md` §2.3 only |
| Moisture forecaster | **No** (moisture is only an input to rain/dry strata) | No | No | `forecast_spec_frozen.md` targets are temperature only; ablations with moisture are "planned" in `PROJECT_HISTORY.md` Stage 8 |
| Temperature forecasting at 100 cm | **No as a target.** 100 cm is a *boundary* forecast by a fixed harmonic rule | – | boundary error reported separately | `forecast_spec_frozen.md` "Targets": 20 and 50 cm only |
| Intermediate-depth forecasts (cable depth 0.67–0.91 m) | **No.** `interpolate_to_depth` runs on *observed* 50/100 cm series | – | synthetic check only (Q7) | `dynamic_ampacity_pipeline.run_station` |

**Results actually obtained (validation 2018–2021, median event MAE over 72 h):** 20 cm: B1 0.740, B2 0.708, C1 0.704, **C2 0.673**, C3 0.704 °C, RECON 0.262; 50 cm: **B1 0.274**, B2 0.352, C1 0.333, C2 0.316, C3 0.334, RECON 0.198. Frozen decision rule: 20 cm "room for a fair AI trial", 50 cm "baselines adequate", **overall mixed** (`forecast_summary.txt`). These are retrospective feasibility results on years already explored, not confirmation.

**Is the LSTM/hybrid existing code, a literature-inspired proposal or a replacement for the GRU?** It is a **literature-inspired proposal** (Widyastuti 2026, Li 2022). The only *specified* AI models in the project are GRU and GBT, with 20 cm primary and 50 cm secondary. The hybrid has no spec, code or result. Treat it as a candidate architecture, not a replacement already adopted.

**Active forecasting task:** **event-triggered**, not continuous hourly. Issue time is 08:00 LST on the morning after the third hot day of a spell; one primary issue per station per spell; targets hours 1–72 at 20 and 50 cm (`forecast_spec_frozen.md`). v3 §2.1 ("forecasts … at 39 USCRN stations") does not say this and reads as continuous.

**Specific v3 contradictions to fix**
- §2.5 "Status [Completed] … Joint temperature/moisture forecast architecture implemented" is **false**. Replace with: "Baselines scored at 20 and 50 cm at 24/48/72 h on 1,689 hot-spell issues; no learned model has been trained."
- §10 open items ("Decide and lock WP1 model architecture", "Score moisture baseline") are correct; §2.3 and §2.5 contradict them.
- v3 says "persistence beats NWP-driven ML at 1–36 h" (see Q14). The project's own result is that B1 persistence is best only at 50 cm; at 20 cm C2 conduction is best.
- The "82%" headroom figure in `forecast_summary.txt` was withdrawn in the audit (`PROJECT_HISTORY.md` Stage 8) but is still printed in the file; do not quote it. The summary also prints a median MAE (0.673) next to a CI of [0.855, 1.039] which is a CI for the **mean**; they are not comparable.

---

## 3. Are the 13-station ampacity results forecasts or historical calculations?

**Historical observed-environment rating calculations.** Evidence:
- `run_station()` (`dynamic_ampacity_pipeline.py` L215–315) loads the 2019–2021 NPZ arrays via `load_npz_station`, forward/back-fills gaps, interpolates 50/100 cm observations to cable depth, and computes a rating at every hour from that hour's own observation.
- No forecast model, no issue time, no lead time and no horizon appear anywhere in the pipeline. No call into `src\forecastlib.py`.
- Status: **completed** as historical calculations; **forecast-driven ampacity: proposed**.

**Station selection.** The 13 stations are a **hard-coded list** in `run_all_stations.py` (L56–140), chosen by climate-zone coverage and checked for valid 50 + 100 cm data in the 2019–2021 NPZ set (131 stations requested; the pipeline's own docstring says 72 had valid 50 + 100 cm). They are **not** a subset selected from the forecasting study's 39 stations. Overlap with the 39 Phase-3 stations (`data\phase3_processed_hourly`) is only **4 of 13**: AL_Fairhope_3_NE, CA_Santa_Barbara_11_W, NE_Lincoln_8_ENE, WY_Sundance_8_NNW. The other 9 are not in the 39.

**13 stations × 3 depths = 39 station-depth combinations**, not 39 stations. v3 §3 ("39 climatically diverse USCRN stations") and WP3 ("39-station analysis") conflate this with the forecasting study's 39 stations. Correct to: "13 stations × 3 cable-centre depth scenarios (39 combinations); 39 stations is the separate forecasting-study set."

Station-depth rows with `n_hours_valid` below 26,304 are listed in `multistation_summary.csv`; the 72-hour solver spin-up is NaN.

---

## 4. Static versus changing-environment comparison

I read the executed code (`dynamic_ampacity_pipeline.py`) and traced one operating point. **Every difference you listed is confirmed.**

| Setting | Static branch (`I_static_d`, L296–300) | "Dynamic" branch (`compute_dynamic_ampacity_series`, L99–140) | Confirmed |
|---|---|---|---|
| Conductor limit | 90 °C | 105 °C | yes |
| Geometry diameter passed to `T_soil` | cable OD 34.09 mm | conduit OD 114.3 mm | yes |
| `n_cables` | 3 (with 7.5 in spacing) | 1 | yes |
| Duct wall `T_duct` | included | included | same |
| Loading | `load_factor=1.0`, no correction | `load_factor=0.66`, then `load_factor_correction` | yes |
| Ground | fixed ρ = 90, Ta = 20 °C | Johansen ρ(θ) with default parameters (θ_sat 0.40, ρ_dry 1550, quartz 0.50), Ta = interpolated observation | yes |
| Resistance | R_dc at 90 °C | same R_dc at 90 °C, although limit is 105 °C | yes (unintended, −2.2% at 105 °C) |

**Further finding.** With `n_cables=1`, `T_soil` returns before the `load_factor` argument is used (`neher_mcgrath.py` L159, L167). The 0.66 load factor therefore acts **only** through `load_factor_correction`, which divides by √(LF²) = 0.66.

**Single-point decomposition at 0.762 m, ρ = 90, Ta = 20 °C (traced, not a rerun)**

| Step | Rating (A) | Change |
|---|---|---|
| Static as coded | 621.3 | – |
| + conduit OD and 1 cable instead of cable OD and 3 cables | 776.1 | +24.9% |
| + 105 °C instead of 90 °C | 855.2 | +10.2% |
| + load-factor correction ÷ 0.66 | 1,295.8 | +51.5% |
| **Structural total** | | **+108.6%** |

The reported station range is +84.9% to +144.5% (depth-corrected run) or +85.6% to +143.5% (original). **About +109% is produced by assumption differences at constant soil conditions.** The station-to-station spread around it (roughly −24 to +36 percentage points) is where soil moisture and temperature enter, and it is further mixed with the arithmetic of Ta (6–22 °C observed against 20 °C fixed).

**Intended or inconsistency?** `neher_mcgrath.py` self-test and `sensitivity_analysis.py` both use the conduit/1-cable/105 °C form (850.4 A baseline), so the dynamic branch is one consistent "PG&E conduit, 105 °C, cyclic" case. The static branch is a different, "Black Books direct-burial trefoil, 90 °C, continuous" case. They are **two different installation cases, mislabelled as one comparison**. I found no document stating that this was intended.

**Which assumptions generated the 86–143%?** The three above plus ρ and Ta. **Attribution to soil conditions is not supported at present.** Cannot say how much of the spread is soil rather than Ta, or how much of the level is soil.

**Keep descriptive until a matched run:** `multistation_summary.csv` headroom columns, the v3 §4.5 "86–143%" claim and the worst/best-case sentences, the per-station table in `DYNAMIC_AMPACITY_FINDINGS.md`, and the `I_scan_ref_A` column (also 105 °C, ρ = 157, Ta = 34.6, 1 cable, so it is closer to the dynamic branch than to the static one).

**Matched comparison, to be run later (not run now):** same cable, conduit/1-cable geometry, limit, resistance temperature and load model in both branches; vary only ρ(θ) and Ta; report the rating in A and the change relative to the *same-assumption* fixed-soil baseline. Provide a 90 °C and a 105 °C version.

### 4a. Depth-corrected rerun (the deferred calculation) — completed, with the caveat above

`code\05_dynamic_ampacity\run_corrected_depth.py` calls the **unchanged** pipeline with cable-centre depths = cover + conduit OD/2 = **0.6667 m (24 in cover)** and **0.8192 m (30 in cover)**. 36 in has no PG&E primary cover standard and was not rerun. Output: `results\dynamic_ampacity_corrected_depth\` (26 timeseries, `multistation_summary_corrected_depth.csv`, `comparison_old_vs_corrected_depth.csv`). Original files untouched.

| | 24 in cover (0.610 → 0.667 m) | 30 in cover (0.762 → 0.819 m) |
|---|---|---|
| Static rating, all stations | 636.4 → 630.2 A (−0.96%) | 621.4 → 616.7 A (−0.75%) |
| Mean dynamic rating change | −0.06% to −1.18% (mean −0.55%) | −0.11% to −1.12% (mean −0.47%) |
| Mean "headroom" change | −0.41 to +2.09 percentage points (mean +0.93) | −0.68 to +1.39 points (mean +0.64) |
| Headroom range after correction | 86.5–141.6% | 84.9–144.5% |
| Mean cable-depth soil temperature change | ≤ 0.07 °C | ≤ 0.07 °C |

**The depth correction is now quantified: under 1.2% on the dynamic rating, about 1% on the static rating, at most about 2 percentage points on headroom.** The earlier "small effect" wording was unquantified and may now be replaced by these numbers. The 86–143% headroom claim is **not** altered materially by depth; it is dominated by the assumption mismatch above. The rerun inherits every issue in Q4–Q7 and is still "historical observed-environment" and "descriptive until matched".

---

## 5. What does the "persistence" column represent?

`I_persist_A` (L287–293) calls the same rating function on `T_shallow, th_shallow` = the **50 cm** observations (not depth-interpolated, not forward-filled) at the **same hour index i**. It does not freeze a state at an issue time and it has no horizon.

- Time indexing: element i of `I_persist` uses observation i; there is no shift.
- It differs from `I_dynamic_A` only by using 50 cm instead of the interpolated cable-depth temperature and moisture, and by not using the forward-filled gaps (NaNs propagate).
- Accurate label: **"rating from uninterpolated 50 cm observations (no depth interpolation)"**, or "shallow-observation rating". It must not be called persistence, a forecast baseline or a lead-time comparison.
- The forecasting study's persistence (B1) is a different object: value at the issue hour held for 72 h.
- Status: implemented; **mislabelled**. Rename the column and the v3 text ("persistence-driven ampacity", WP3 item 2, "RMSE vs persistence at t+24 h / t+72 h" L427, L440).

---

## 6. What cable thermal model is implemented?

| Capability | Present? | Evidence |
|---|---|---|
| 1. Instantaneous steady-state conductor temperature or rating | **Yes** | `ampacity()`, `conductor_temperature()` in `neher_mcgrath.py` |
| 2. Load-factor-adjusted rating | **Yes**, as a post-hoc divide by √(LF²) | `load_factor_correction()` L238–249 |
| 3. Transient model carrying stored heat | **No** | none |
| Thermal capacitances | **No** | none |
| Initial conductor/sheath/ground temperatures | **No** | none |
| Historical electrical loading | **No** (Darmstadt currents are used only as point-wise inputs to a steady-state formula) | `validate_*.py` |
| Time integration of cable temperatures | **No** | none |
| 72-hour temperature-constrained current search | **No — proposed** | v3 WP2/WP3 |

**Do not describe the model as IEC-compliant.** It is a Neher–McGrath-style steady-state implementation, partly validated against Bates's Table 3.1 only to 17% (Southwire cable 631 A vs Bates 541 A, header comment L254–261), and with the simplifications noted below. `neher_mcgrath.py`'s docstring "IEC 60287 / Neher–McGrath" and the claim of IEC equivalence "via Bates" should be removed. Not established: sheath/screen losses, armour losses, dielectric loss (set to zero in all runs), proximity effect for non-trefoil layouts.

**`Dx` in `T_soil()`** (L161): `Dx = sqrt(4 · α · (1/f) · (1/3600))` with α = 0.00716 m²/h and f = 60 Hz.
- Dimensions: α [m²/h] × (1/f) [s] / 3600 → m² after the unit conversion, so Dx is a length in metres (value 3.6e-4 m).
- **It is the diffusion length for the 60 Hz electrical period (0.0167 s), which has no thermal meaning.** The Neher–McGrath loss-factor correction concerns the *load-cycle* period (24 h). Using mains frequency is almost certainly an error. The expression I could verify is "cylindrical thermal diffusion length for the load cycle"; I could not identify the source equation in `bates_2021.txt` quickly and the code cites "N-M eq. 46 / Bates App A eq. 44A" without a page. **Status: unresolved; do not cite as validated.** Effect: with Dx = 3.6e-4 m the term `1 − 1/ln(Dx/(2L+De))` ≈ 1.12, so it slightly inflates the LF factor, but this branch is **never reached in the ampacity pipeline** (n_cables=1) and is reached only in validation scripts and the static branch with LF = 1.
- Units elsewhere: `depth_interp.py` uses α = 4.5e-7 m²/s (= 0.00162 m²/h) whereas `T_soil` defaults to 0.00716 m²/h (= 1.99e-6 m²/s). The two soil diffusivities differ by a factor of 4.4 within the same project and neither is sourced to a measurement.
- **Mutual-heating term** (L165): `F = ln(√(1 + (2L/S)²))`, labelled "simplified image term". It is the standard image-source form for one neighbouring cable at spacing S, applied once, not summed over the other two cables of a trefoil, and not tied to a page of the source. It is also mixed into `T_e` as `(ρ/2π)·F·LF`. **Source and approximation: unresolved.** It is an approximation of Neher–McGrath's F, not a verified implementation.

Further model simplifications that matter for validation: `Tj = 0` in MF_IV and MF_III; `Ti` computed from the paper's approximate outer diameter; R_dc taken at a fixed 70 °C regardless of the measured 40–95 °C; trefoil spacing taken from the Black Books 7.5 in default (`T_soil` default argument) rather than the Darmstadt 34 mm touching trefoil.

---

## 7. Depth interpolation

| Question | Answer | Evidence |
|---|---|---|
| Bayesian diffusivity estimation implemented? | **No** | `depth_interp.py` docstring: "Bayesian inversion … will replace this" |
| Posterior distribution exists? | **No** | – |
| Monte Carlo uncertainty propagation executed? | **No** | – |
| Diffusivity used | uniform **4.5e-7 m²/s** default; never fitted in the ampacity runs. (The forecasting study used a fitted/global 4.322e-7 m²/s, which is a different code path.) | `depth_interp.py` L76 |
| Grid | domain 0.50–1.00 m, dz = 0.01 m, 49 interior nodes | L77, L101–104 |
| Time step | 3,600 s (Crank–Nicolson) | L78 |
| Initialisation | linear profile between the first 50 cm and 100 cm values | L115 |
| Spin-up | first 72 steps returned as NaN; no equilibrium iteration | L79, L129 |
| Mapping target depth → node | `tgt_idx = round((d − 0.51)/0.01)`, nearest node: 0.667 → 0.67 m, 0.762 → 0.76 m, 0.819 → 0.82 m, 0.914 → 0.91 m (≤ 4 mm snap) | L106–108 |
| Boundary conditions | **Measured** 50 and 100 cm observations (gaps forward/back-filled inside the pipeline before the solve; NaN restored only where both are missing) | `run_station` L264–277 |
| Forecast boundaries in any application | **None** | – |
| Moisture | **Linear interpolation** between 50 and 100 cm, weight (d − 0.5)/0.5 (`interpolate_moisture_linear`). The heat solver does **not** model water movement. The Richards equation is explicitly "not yet implemented". | L135–147 |

**Numerical checks actually performed.** (a) A synthetic demonstration with sinusoidal 50 and 100 cm forcing, run once, plotted in `results\depth_interp\depth_interp_demo.png`, printing means and a visual "between and closer to 100 cm" expectation. (b) For the forecasting solver (a different file, `src\heatsolver.py`), analytic periodic check and RMS 0.0098 °C (`forecast_verification_out.txt` check 4a). **There is no field validation of the 50/100 → cable-depth interpolation**, because USCRN has no sensors between 0.50 and 1.00 m. v3 §10 "Depth interpolation — verified [R] correct bounding behaviour" should read "checked on synthetic forcing only".

---

## 8. Cable and installation parameters

| Item | Darmstadt main field (configs II, III, IV; workbook sheets MF_*) | Darmstadt protective-pipe (V, VI; sheet SF_V+VI) | US reference installation | 24/30/36 in scenario cases |
|---|---|---|---|---|
| Cable identifier | `DARM_MV150_NA2XS(F)2Y_1x150` (also `DARM_LV_NAY2Y-J_4x150` in I–III) | same MV150 | `SW_350KCMIL_CU_15KV_EPR` | same Southwire |
| Construction | Al 150 mm² RE/25, XLPE 5.5 mm, jacket 2.5 mm, OD ≈ 34 mm (approx.), 12/20 kV | same | Cu 350 kcmil compact (35 strands), NL-EPR 220 mil, Cu tape shield, PVC jacket 80 mil, OD 34.09 mm, 15 kV | same |
| Conductor resistance | 0.206 Ω/km at 20 °C | same | 0.10171 Ω/km at 25 °C DC; AC 0.14108 Ω/km at 90 °C | same |
| Temperature for resistance correction | **model: fixed 70 °C** (hard-coded) vs measured 40–95 °C | fixed 70 °C | 90 °C (R_dc at 90 °C even when limit is 105 °C) | 90 °C |
| Conductor temperature limit | 90 °C (MV); LV 70 °C | 90 °C | 105 °C (normal), dynamic branch; 90 °C, static branch | both, as in Q4 |
| Frequency, electrical arrangement | 50 Hz in Germany (the paper's loop is a single-phase induction current loop, `AHR 500 B10`); **model uses 60 Hz in `ys_factor`/`yp_factor`** | same | 60 Hz | 60 Hz |
| Conductors/circuits and spacing | II: two MV trefoils; III: 3 LV + 3 MV trefoils in a row; IV: single trefoil. Spacings only in paper Figs 2, 4 | single trefoil in one duct | 3 cables, trefoil, 7.5 in c/c in static; **1 cable** in dynamic | same |
| Cable-centre depth | **not stated in text**; paper gives "0.65–0.85 m" burial depth without reference point; 0.650 m as bundle underside is an **inferred** reading of Fig 2; model uses centroid 0.623 m [I] | 0.75 m is the **lower outer edge of the duct** (Sec 2.1.2); **model uses 0.75 + OD/2 = 0.829 m: the sign is wrong, centre should be 0.75 − 0.0786 = 0.671 m** | 0.819 m derived (cover + conduit OD/2); pipeline default 0.819 m in `PGEInstallation`, runner passed nominal values | scenario centre depths 0.610 / 0.762 / 0.914 (historical); PG&E-derived 0.667 / 0.819 / none (rerun, Q4a) |
| Cover reference | not stated | not cover, not centre | PG&E min cover 30 in primary, 24 in secondary/service, to **top of conduit** (EDS 038193) | cover 24 / 30 in; 36 in has no PG&E primary cover standard |
| Duct dimensions | n/a (direct bury in four beddings) | PVC ID 147.6 mm, wall 4.8 mm | 4 in Sch 40 PVC, OD 114.3 mm, ID 100.6 mm | same |
| Cable position inside duct | n/a | **not modelled**: no cable-to-wall region | assumed concentric / at conduit centre (labelled [I]) | same |
| Backfill and properties | four beddings: silt, sand, fluidized backfill, loam; native soil loam; measured retention/conductivity curves in workbook; model used default wet-state ρ [I] | native sand; config V air-filled, VI grouted (≈ 2.5 W/(m·K) from paper text). Model used 350 and 70 °C·cm/W proxies | "no thermal backfill modelled": Johansen ρ(θ) with default parameters | same |

**Figure 2 underside interpretation:** preserved as **inferred, not confirmed by the paper**.

**Retained decision:** 24/30/36 in are kept as **cable-centre-depth scenarios** (`REF_DEPTH_24IN/30IN/36IN`); the PG&E cover-derived installation is held separately in `Reference_Installations.csv` (`cover_to_conduit_top_m`, `conduit_centre_depth_m`, `cable_centre_depth_m`, status). That is now done in the dataset package, and the rerun in 4a is the first consistent use of the PG&E-derived depth.

**Frequency note.** Darmstadt is German, so mains is 50 Hz; the model's 60 Hz affects only the skin/proximity factors (small). Flag in v4.

---

## 9. Mapping of Darmstadt measurements

| Workbook sheet | Configuration per paper | Original header / conflict | Applied-current column | Temperature sensors | Moisture | Time axis |
|---|---|---|---|---|---|---|
| `MF_III_CL` | **II** (two MV trefoils), paper Sec 3.3 and Fig 11 caption | sheet header says "(IV)"; dataset package keeps both and records `config_note` | `LOAD_II` | Pt100 on the **outer sheath**, four beddings (fluidized backfill, loam, sand, silt); **no conductor sensors** | six VWC series (loam, sand, silt, each plus an undisturbed reference), METER EC-5, ±3% VWC, ≈ 10 cm from trefoils | elapsed days |
| `MF_IV_CL` | IV (single MV trefoil) | none | one load column | conductor temps, four beddings | in `MF_III` sheet only | elapsed days |
| `SF_V+VI` | V (unfilled duct) and VI (grouted duct) | none | **`SF_V_VI_LOAD_V` (mean 298 A, max 356 A) and `SF_V_VI_LOAD_VI` (mean 355 A, max 499 A)** | conductor temps, one for each configuration | not in this sheet | elapsed days |

**Alignment of different sampling intervals.** Cable rows are 10 min, VWC rows 30 min, weather rows 10 min in a separate block; **no alignment step exists in the validation code.** `MF_III` takes the first cable row and the first VWC value on the same row, so VWC rows are NaN for 3,432 of 5,009 cable rows and a fallback of 0.20 is substituted. For `SF_V+VI`, `T_amb_C` exists for only 2,440 of 12,278 rows.

### MF_III_CL — which beddings, which units

- **Sheath column used: silt.** `T_sheath_meas` in `mf_iii_cl.csv` has min 36.646, max 48.701, mean 46.61 °C, identical to sensor `MF_III_CL_sheath_silt` in the dataset package (sand: 43.5–75.0, loam: 54.6–75.0, fluidized backfill: 39.9–52.9).
- **Moisture column used: silt.** `theta_meas` mean 30.59 %, range 27.80–32.41, identical to `MF_III_CL_VWC_silt` (sand VWC is 4.9% mean and drops to −0.76%).
- **Parameters applied: sand** (`moisture_driven_rho(theta, bedding="sand")`, θ_sat 0.38, quartz 0.82). **The model therefore compares silt measurements against sand parameters.** The code comment says "same main-field upper row", but the bedding is not matched.
- **Units: moisture is in percent** (values ≈ 30). `johansen_lambda` takes m³/m³ and clips saturation to ≤ 1. **No conversion exists** anywhere in `validate_mf_iii.py`. For the 1,577 rows with a moisture value, saturation clipped to 1 and ρ = **39.96 °C·cm/W** (the saturated-sand value). For the other 3,432 rows the fallback θ = 0.20 gave ρ = **48.47**. Hence the saved mean ρ: (1,577 × 39.96 + 3,432 × 48.47)/5,009 = 45.79.
- **So the reported "mean resistivity of 45.8 °C·cm/W" was not derived from the correct material or units, is not a measured quantity, and should be withdrawn** (v3 L89 and L92, `VALIDATION_FINDINGS.md`). It is the mix of a saturation clip and a fallback constant. This happened *before* the Johansen step, so the saved MF_III results and the "half the NEC default → √(90/45.8) ≈ 40%" argument inherit it.
- Model also uses `n_cables=3` and a conductor-approach `Ti` for a sheath comparison (`Tj = 0` and the model sheath = conductor − insulation drop). The MF_III model does not represent two trefoils.

### SF_V+VI

- **Cable construction:** both configurations use the MV150 Al XLPE cable (`DARM_MV150_NA2XS(F)2Y_1x150`).
- **Own current used?** **No.** The code selects the first column matching "electrical load" and "v)" without "vi)" (`validate_sf_v_vi.py` L76–79), so **both V and VI are driven by configuration V's current**. Configuration VI's own recorded current (mean 355 A, max 499 A) is never used.
- **Cable-to-pipe interior region modelled?** **No.** There is no interior resistance (air gap, radiation, convection, grout).
- **`duct_fill_rho` applied to the pipe wall:** yes. `T_duct(duct_fill_rho, DUCT_OD_M, DUCT_ID_M)` computes a cylindrical layer between OD 157.2 mm and ID 147.6 mm, i.e. a 4.8 mm wall, so the "fill" resistivity acts on the pipe wall, not the interior. ln(157.2/147.6)/(2π) × ρ is ≈ 0.01 K·m/W even for ρ = 350 °C·cm/W; V and VI therefore differ by < 0.01 K·m/W, so the model cannot represent the effect it is being tested on.
- **Depth:** `DUCT_DEPTH_M = 0.75 + OD/2`. The workbook note says 0.75 m is the *lower outer edge*; the centre is 0.75 − OD/2 = 0.671 m. Sign error, +0.158 m.
- **Limitations of the saved comparison:** the V-versus-VI "28 percentage-point improvement" in `VALIDATION_FINDINGS.md` §2 comes from different measured temperatures under different currents and an unmodelled interior. It cannot be attributed to grouting by this code. Treat the saved SF numbers as a record of what the script printed, not as validation.

---

## 10. Darmstadt error statistics

Recomputed from the **saved CSVs** (no model rerun). Percentage error is `100(T_model − T_measured)/T_measured`; **negative means the model underpredicts** (the model temperature is lower than the measurement). `validate_mf_iv.py` L156 and `validate_sf_v_vi.py` L123 print "Negative error = model overestimates temperature (conservative)" and `VALIDATION_FINDINGS.md` says "underestimates conductor heat" in one place and "overestimates ampacity" in another. **Under the code's formula the latter statements are the reverse of the sign for the first.** Correct wording: negative = model temperature too low = unsafe direction for temperature, over-rating direction for ampacity.

| Result file | Quantity | Paired n | Mean signed error (°C) | MAE (°C) | RMSE (°C) | Mean % | Std % | 5th / 95th pct of residuals % | Measured mean / model mean (°C) |
|---|---|---|---|---|---|---|---|---|---|
| `mf_iv_cl_sand.csv` | conductor | 1,872 | −34.23 | 34.23 | 34.24 | −51.4 | 1.0 | −53.0 / −49.7 | 66.62 / 32.39 |
| `mf_iv_cl_loam.csv` | conductor | 1,872 | −42.15 | 42.15 | 42.16 | −51.3 | 0.8 | −52.7 / −50.1 | 82.15 / 40.00 |
| `mf_iv_cl_FTB.csv` | conductor | 1,872 | −9.68 | 9.68 | 9.72 | −21.4 | 1.7 | −24.0 / −18.4 | 45.33 / 35.65 |
| `mf_iv_cl_silt.csv` | conductor | 1,872 | −13.48 | 13.48 | 13.49 | −26.3 | 1.3 | −28.4 / −24.1 | 51.30 / 37.82 |
| `sf_v_vi.csv` config V, I > 50 A | conductor | **2,356** | −44.01 | 44.08 | 44.62 | −67.7 | 11.4 | −72.5 / −59.1 | 64.06 / 20.05 |
| `sf_v_vi.csv` config VI, I > 50 A | conductor | **2,356** | −13.48 | 13.61 | 14.29 | −39.3 | 14.1 | −50.3 / −14.2 | 32.90 / 19.42 |
| `mf_iii_cl.csv` | **silt sheath vs sand parameters** | 1,681 | −23.24 | 23.24 | 23.36 | −52.5 | 2.7 | −55.6 / −47.7 | 44.27 / 21.02 |

**Sign convention differs from Bates.** Bates (Sec 10.5) defines *negative = model temperature higher than measured* (conservative). The project's validation scripts define error as (model − measured)/measured, so *negative = model lower*. The two conventions are opposite. Numbers from the two sources must not be compared or pooled without flipping the sign.

**Corrections to the narrative**
- `VALIDATION_FINDINGS.md` and v3 report SF n = 12,194. That is the count of rows with I > 50 A in the **input** table. The paired count is **2,356** (2,440 with any ambient value) because `T_amb_C` exists for only 2,440 of 12,278 rows.
- **"±" in v3 is the standard deviation of the percent residual** (`e.std()`), not an uncertainty of the mean, and not a confidence interval. The residuals are one 10-min time series, strongly autocorrelated, so the effective sample is far smaller than n.
- **"5th–95th percentile" is the empirical distribution of residuals** (`np.percentile(e, [5, 95])`), not a CI for the mean. The code header for MF_IV calls it "90% CI" (`print_summary` L145); rename.
- **MF_III:** the −52.5% mean, and v3's "MF_III sheath −53%", compare a silt sheath to a sand model with the unit artefact above; withdraw as a validation result.
- Proposed and unproved: **drying.**
  - *Measured discrepancy:* −10 to −44 °C mean signed error (above).
  - *Proposed explanation:* the model uses wet-state ρ while the soil near the cable dried (paper Sec 3; Bates Ch 4).
  - *Evidence that isolates drying:* **none** in the project. Sand VWC at the cable shows measured drying to ≈ 0–12% (`MF_III_CL_VWC_sand`), which supports drying *occurring* in sand, but silt VWC stays at 28–32%, so drying cannot explain a −26% silt-model gap.
  - *Model-side candidates not excluded:* no sheath/screen losses, no dielectric loss, `Tj = 0`, trefoil spacing default 7.5 in rather than the touching 34 mm trefoil, R_dc at a fixed 70 °C, 60 Hz factors, a steady-state model against a 39-day transient, unmatched bedding (MF_III), unequal currents (SF), duct-depth sign error (SF), uncertain cable depth.
  - **Do not assert that drying alone caused the discrepancy, or that code/model error is excluded.**

---

## 11. Sensitivity and ampacity numbers

**Denominator problem.** The sensitivity script's baseline is **850.4 A** (PG&E conduit, 1 cable, 105 °C, ρ = 90, Ta = 20 °C, depth 0.819 m, LF = 1; `ampacity_for_rho_and_Ta`). The **621 A** quoted in v3 L342 and L433 is the *static branch* at 0.762 m (90 °C, 3 cables, cable OD), a different case (ratio 1.369). The A figures come from the sensitivity file, the denominator quoted in the text from the static case.

| Row | Reference (A) | Modified (A) | Δ (A) | % vs same-case denominator (850.4) | % if wrongly divided by 621 |
|---|---|---|---|---|---|
| ρ 90 → 50 | 850.4 | 941.8 | +91.4 | **+10.8%** | +14.7% |
| ρ 90 → 117 | 850.4 | 801.8 | −48.5 | **−5.7%** | −7.8% |
| ρ 90 → 157 | 850.4 | 743.1 | −107.2 | −12.6% | −17.3% |
| ρ 90 → 270 | 850.4 | 628.4 | −222.0 | −26.1% | −35.7% |
| Ta 20 → 10 °C (ρ 90) | 850.4 | 899.0 | +48.6 | +5.7% | +7.8% |
| Depth 0.650 → 0.587 m (spread, ρ 90) | 866.1 | 873.4 | +7.3 | +0.8% of 866.1 | – |
| Load factor 0.3 … 1.0 | 850.4 | 850.4 | 0 | **flat: function not applied** | – |

Notes: (a) `VALIDATION_FINDINGS.md` text gives "+92 A (+11%)" (✓ against 850), "−5.5%" (recomputed −5.7%), and "ρ 270 → 620 A, −27.1%" (saved CSV says 628.4 A, −26.1%); the text values were not reproduced from the saved CSVs, use the CSV. (b) The load-factor "sensitivity" is a flat line because the script never applies the correction (the findings file says so); the table is not evidence of anything. (c) The depth-reference table uses the **Southwire PG&E cable** at the *Darmstadt* depths 0.587–0.650 m; it shows that a 6 cm shift changes that cable's rating by 0.8%, which is not a statement about the Darmstadt cable. (d) The sensitivity script has no 36 in or 0.667 m rows.

**√(90/45.8) example.** The ≈ 40% (1.402) value assumes the **entire** conductor-to-ambient thermal resistance is soil. For the installation in the sensitivity script, soil is 0.381/(0.324 + 0.115 + 0.097 + 0.381) = **41.6%** of R_ca at ρ = 90. The full calculation at ρ = 45.8 gives 953.2 A, **+102.8 A, +12.1%**, not 40%. In any case the 45.8 value is an artefact (Q9). Replace the √ example with the full-model value, or delete it. The "wet vs design-dry changes ampacity by about 40%" statement in `VALIDATION_FINDINGS.md` §6 is withdrawn.

---

## 12. NHR calculation

- **Threshold source:** the code sets `NHR_CABLE_EQUIV_W_PER_CM = 0.2` and `NHR_SAND_PROBE_W_PER_CM = 0.1` and tags them "[V Bates 2021 Ch 4]". In `bates_2021.txt` the NHR is a **measured, soil-specific** quantity from a thermal-probe test (0.53 W/cm in the worked example, L1751, probe diameter 1.5875 cm, rescaled for cable diameter). The 0.1 and 0.2 W/cm figures appear **in a single worked example for a sand layer** (L1975 and L2003–2004: probe NHR 0.1, cable-equivalent 0.2 W/cm, cable heat rate 0.37 W/cm). They are example values, not a general threshold.
- **Material/experiment support:** none for Darmstadt. No NHR test was done on the Darmstadt beddings, and the 0.2 value was applied to **all** rows, whose sensors are silt (Q9), at a cable of different diameter than the Bates example.
- **One conductor or the arrangement?** The heat rate is `I² · R_dc(70 °C) · (1 + Ycs + Ycp)` **per cable** (one conductor of the trefoil), divided by 100 for W/m → W/cm. R_dc at 70 °C is hard-coded; MV150 rating is 90 °C. Mutual heating from the other cables is not considered.
- **Unit conversion:** W/m ÷ 100 = W/cm (1 m = 100 cm) — correct.
- **Result:** 42 of 5,009 rows exceed 0.2 W/cm (**0.84%**); mean 0.171, max 0.251 W/cm.
- **What it means:** a calculated heat rate compared with an **assumed** threshold borrowed from another example. **Local drying was not observed by this calculation**; the sand VWC series show drying independently. The 0.8% figure supports nothing about how often drying occurs; it supports only "heat rate seldom exceeds 0.2 W/cm in this one run".
- Do not generalise the 0.2 W/cm sand-example threshold to all Darmstadt beddings. The v3 sentence "only 0.8% of Darmstadt timesteps exceed NHR" and "consistent with Bates (2021)" should be removed or reworded as above.

---

## 13. Soil and backfill property provenance

| Category | What it is | Where it was used |
|---|---|---|
| Wilson measurements actually used in a calculation | **None.** `Reference_Cases.csv` records "Wilson T1 NOT used in this run". `wilson_loo…` and `wilson_T1.csv` exist in the proposal folder, but no ampacity or validation code reads them | – |
| Default Johansen parameters actually used | θ_sat 0.40, ρ_dry 1,550 kg/m³, quartz 0.50, coarse in **all 13 stations**; sand/loam/FTB/silt presets in `validate_mf_iii.py` (workbook "approximated" [I]) | pipeline, MF_III validation |
| Planned station-specific replacements | Wilson texture/bulk density by station and depth; Bayesian α; sensitivity bounds | proposed (v3 WP1, WP4) |
| Measured Darmstadt material curves | 3,156 curve points and 64 property values (porosity, density, heat capacity, conductivity/retention) in the dataset package | **not** used by `validate_mf_iv.py`, which hard-codes wet ρ {65, 100, 80, 90} °C·cm/W labelled [I] |
| PG&E acceptance requirements | FTB limits per EDS 038193 (text: 90 °C·cm/W dry limit, 60 at 3% moisture; see below) | specification |
| SnoPUD acceptance requirements | high-strength mix 75 °C·cm/W at 0% moisture and other limits (std 1002182.1 Rev 2) | specification |
| Assumed constants | Black Books ρ = 90, Ta = 20 °C; scenario ρ values; EPR 350, PVC 500, duct 480 °C·cm/W | assumptions |

**Wilson match.** Nine of 13 pipeline stations match Wilson T1: NM_Socorro_20_N, NM_Las_Cruces_20_N, NV_Mercury_3_SSW, TX_Monahans_6_ENE, OR_Riley_10_WSW, OK_Stillwater_2_W, NE_Lincoln_8_ENE, AL_Fairhope_3_NE, NC_Asheville_13_S. **Unmatched:** CA_Santa_Barbara_11_W, CA_Bodega_6_WSW, WY_Sundance_8_NNW, MI_Chatham_1_SE. The Wilson table carries seven properties (texture class, % sand/silt/clay, bulk density, field capacity at 33 kPa, wilting point at 1,500 kPa) over 69 stations × 5 depths; the numeric value is missing in 16.8% of station-depth-property cells (QF09). No porosity or quartz fraction is supplied, so even for matched stations, Johansen inputs would need a texture-to-quartz mapping. **v3 L222 "27 of the 39 USCRN stations from Wilson"** refers to the forecasting-study 39 stations (`PROJECT_HISTORY.md`, Stage 4); it is **not** the ampacity set (9 of 13).

**Dry-backfill limit, 75 versus 90 °C·cm/W.**
- **90 °C·cm/W:** PG&E EDS 038193 text for the dry (0% moisture) limit.
- **75 °C·cm/W:** the SnoPUD **high-strength** mix at 0% moisture (std 1002182.1).
- `cable_params.py` L49 sets `ftb_rho_at_0pct = 75.0` with comment "high-strength, ≤ 75 [V] EDS 038193" and comment-tags it as PG&E. **Wrong source attribution.** No numeric code path uses that field (grep: unused in the pipeline), so no result changes. The dataset package keeps both under their correct sources in `Backfill_Specifications.csv`. Fix pending your approval to edit `cable_params.py` (not edited here, per the earlier instruction).

---

## 14. Literature claims against primary papers

*Compiled by a separate reader from the primary texts in `notes\*.txt`; the stand-alone copy is `notes\V4_Q14_literature_section.md`. Items marked [web] come from search summaries, not publisher or repository pages, and are lower confidence. Status: ✅ confirmed, ❌ contradicted, ❓ unresolved.*

Method: primary texts in `notes/*.txt` were read directly. These are the Bracale, Espedal, Verschaffel-Drefke, Ahmad and Bates texts, plus the Darmstadt dataset page. Line numbers (`L…`) refer to those `.txt` files. Web look-ups were used only for items not on disk. They are marked **[web]** and are lower confidence, because they came from a search summary and not from the publisher or repository page.
Status key: ✅ confirmed · ❌ contradicted · ❓ unresolved.
Files: `v3` = `PROPOSAL_DRAFT_v3.md`, `LM` = `notes/LITERATURE_MATRIX.md`.

---

### 14.1 Bracale et al. 2019, *IEEE Access* 7:4709–4725

DOI 10.1109/ACCESS.2018.2888505 (the DOI carries 2018; the volume is 2019). The `survey_bracale_2019.md` header and `download_log.json` agree on this DOI.

**(a) What the primary text says**

| Aspect | Primary source |
|---|---|
| Methods | Three methods are compared. PSM is the physical-statistical method, new in this paper and intraday only. DDM-LR and DDM-RFR are data-driven regression methods adapted from overhead-line DLR practice. PM is persistence, "variables are assumed constant throughout the forecast lead time" (Sec. V). |
| Horizons | Intraday is 1–12 h and day-ahead is 13–36 h (L101–102). The PSM is "too computationally intensive to be applied to day-ahead scenarios, thus no results are reported" (Sec. V.B). **Nothing beyond 36 h is tested, so there is no 72 h evidence.** |
| Intraday conclusion | "The comparison at intraday scenarios demonstrates the superiority of the PSM, compared to the DDMs and to a persistence benchmark" (Sec. VI). |
| Day-ahead result | "The key result of the comparison is that the PM outscores both the DDM-LR and the DDM-RFR for all of the considered lead times" (Sec. V.B, 13–36 h). The authors conclude the DDMs "based on NWPs are not a preferable solution" versus PM. This applies to those two DDMs only. The PSM was not run at these horizons. |
| Soil case | Two soils (sand and clay, parameters from a soil database, Table 1). The cable is a **copper three-core LV cable** (EPR insulation, Table 2), directly buried. It is not MV. Results are reported separately for sand and clay. |
| Inputs, measured | Camborne (UK) weather for 2016, hourly: soil temperature at 10 cm and precipitation (Sec. IV.B). The load is an industrial-factory measurement. The test period is the last 3 months of 2016. |
| Inputs, forecast | ECMWF NWP, noon run, 1–36 h (Sec. IV.C). The PSM uses SVR forecasts of upper-layer soil temperature, precipitation and load, fed through a thermal-hydraulic soil model and the IEC cable-soil model (Sec. III.A). |
| Reference target | The reference DLR is computed by feeding **actual weather and load** to the thermal-hydraulic and cable-soil models: "Errors are calculated with respect to the values obtained by feeding actual weather and cable load data to the thermal-hydraulic model of the soil and to the cable-soil thermal model" (Sec. V.A). **No measured conductor temperature or measured ampacity is used, so this is model-vs-model.** |
| Soil-forecast value | "Information about forecast soil temperature and water content begin to be important only for lead times greater than 12 hours" (Sec. VI). |

**(b) Status**
- LM B2 "Persistence beats all ML at 1-36 h leads": ❌ **contradicted** for 1–12 h. The PSM beats persistence there, and the paper does not report that persistence beats the DDMs at intraday leads.
- Persistence beats the two DDMs at 13–36 h: ✅ confirmed, for this single UK site, one year, one load and two soils.
- "Persistence best at ~16 h cap": ❓ unsupported. I found no 16 h statement in the text.
- "Persistence is unbeaten" (LM line 145): ❌ **contradicted**. The PSM beats it intraday, and nobody has tested 24–72 h.
- LM's "MV cables" title and "one site" gap: the title is wrong. The paper is "Day-Ahead and Intraday Forecasts of the Dynamic Line Rating for Buried Cables", and the cable is LV. "One site" is ✅.
- v3 §1.6 says Bracale validates nothing against measured cable temperature: ✅ confirmed.
- v3 §1.6 says Bracale uses a "rain-bucket moisture model": ❓ unverified. The paper uses a thermal-hydraulic soil model driven by precipitation and upper-layer soil temperature.
- v3 §1.6 says Bracale uses "not measured multi-depth soil state": ✅ confirmed. It uses a single measured 10 cm temperature and precipitation.

**(c) Corrections**
- **LM B2.**
  - Replace the citation with: Bracale, A. et al. (2019; full author list to be copied from the PDF). Day-Ahead and Intraday Forecasts of the Dynamic Line Rating for Buried Cables. *IEEE Access* 7, 4709–4725, DOI 10.1109/ACCESS.2018.2888505. Check the full author list against the PDF.
  - Replace "Key metrics" with: "PSM (intraday, 1–12 h, physical-statistical) beats DDM-LR/RFR and persistence. At 13–36 h persistence beats DDM-LR and DDM-RFR; PSM not evaluated. LV Cu 3-core cable, sand and clay, Camborne UK 2016, targets are model-derived DLR."
  - Delete "persistence beats all ML at 1-36 h", "~16 h cap" and "MV".
- **LM line 145 (gap map).** Replace "Nobody – persistence is unbeaten [Bracale, V]" with "Not evaluated beyond 36 h; at 13–36 h Bracale's two data-driven models did not beat persistence (single UK site, model-derived targets)".
- **LM B2 line 81 and v3 (any 'must beat Bracale persistence at 24–72 h' wording).** Reword to "Persistence is a reasonable naive baseline we adopt; Bracale only tested ≤36 h, with a different target and cable".
- **v3 §9.** Change the role cell to "DLR forecasting; PSM beats persistence ≤12 h, persistence beats DDMs 13–36 h; model-vs-model" (drop "persistence baseline" as an unqualified claim).

---

### 14.2 Widyastuti et al. 2026, *Soil & Tillage Research*

**(a) What is established.** The paper is not on disk.
- The publisher record, as you relayed it, describes 33 Tasmanian sites.
- **[web]** Search summaries (unreliable on details) give the title as "Mapping spatiotemporal soil temperature using physics-informed neural networks with the heat transfer equation". They list authors Widyastuti, Minasny, Sharififar, Padarian, Webb and Taufik, and *Soil Tillage Res.* vol. 265, article 107452. Treat the volume and article number as unverified.
- Nothing I could retrieve mentions USCRN, an LSTM, or a Crank-Nicolson solver. The title indicates a **PINN with the heat-transfer equation, aimed at spatiotemporal mapping**, which is a different task.

| Item | Matrix / v3 claim | Evidence | Status |
|---|---|---|---|
| Dataset | "USCRN-style multi-depth … multiple US stations" | 33 Tasmanian sites (publisher record, per caller) | ❌ contradicted |
| Architecture | "Differentiable hybrid LSTM + Crank-Nicolson solver, end-to-end" | The title says PINN with the heat-transfer equation. No LSTM or CN is found. | ❌ likely contradicted; ❓ details unverified |
| Time resolution, depths | "5–100 cm, 24–72 h forecasts" | Not retrievable | ❓ unresolved |
| Task | "Outperforms … at 50/100 cm for 24–72 h forecasts" | The title says "mapping", which suggests spatiotemporal interpolation and not a 72 h forecast. | ❓ unresolved, leaning against |
| Support for our USCRN 72 h architecture | LM line 138 and v3 line 209 cite it as support | Different region, probably a different task | ❌ **does not support it**. Cite only as "physics-informed soil-temperature modelling" after the full text is read. |

**(c) Corrections**
- **LM A2.** Rewrite as "Widyastuti, M.T.; Minasny, B.; Sharififar, A.; Padarian, J.; Webb, M.A.; Taufik, M. (2026) *Soil Tillage Res.* – PINN + heat-transfer equation for spatiotemporal soil temperature, Tasmanian network. NOT USCRN, NOT LSTM+CN, NOT a verified 24–72 h forecast. Verify bibliographic details and task against the full text."
- **LM lines 28–32 (Method, Data, Key metrics, Relevance), line 138, and v3 line 209 plus the line 612 table row.** Remove "[V]" and "LSTM + Crank-Nicolson". Remove the claim that it "directly models the USCRN depth-temperature structure" and the claim that "72h horizon matches ampacity planning".
- **Action.** Obtain the PDF and re-read it before any use.

---

### 14.3 Espedal et al. 2025, CIRED 2025 paper 0152, pp. 411–415

DOI 10.1049/icp.2025.1508. The title is "Neural-network assisted modelling of cable ampacity for dynamic load profiles". The `survey_espedal_2025.md` agrees with the points below.

**(a) What the primary text says**

| Aspect | Primary source |
|---|---|
| Installation | A full-scale research trench. The section studied is a cable **in an air-filled pipe under an asphalt road** (Abstract, Sec. 2.1). It is not a soil-moisture case. |
| Measured quantities | Distributed temperature sensing (DTS) of screen temperature, conductor temperature (sensors drilled into the conductor), cable surface, pipe surface at top, side and bottom, and a site weather station for air temperature and rain intensity (Sec. 2.1). |
| NN architecture | Two LSTM layers plus regularisation (Sec. 2.5). Input is **48 h of history of rain, load and air temperature**. Output is **two scalar multipliers on soil thermophysical parameters** for the next 24 h (Sec. 2.3), `…fac` and `…fac` (the symbols are garbled in the text extraction). Targets are produced by a Gaussian-process optimisation against measured conductor temperature on a sliding 24 h window (Sec. 2.4). |
| Assumed future inputs | The thermal-equivalent-circuit (TEC) models are "tasked to calculate the conductor temperature in the next 24 hours **given a load, and temperature profile**" (Sec. 2.6). Future load and air temperature are **assumed known**. They are not forecast. |
| Prediction target | **Conductor temperature**, day-ahead (24 h). **No ampacity is computed or forecast.** The Discussion says "it was chosen to focus on conductor temperature as it is this temperature which limits the ampacity". |
| Result (Table 2, MAE ± SD, °C) | Step: conventional 2.82±0.15, NN 2.46±0.10. Slow: 1.03±0.24 vs 1.32±0.54 (**conventional better**). Fast: 1.09±0.16 vs 0.86±0.16. |
| Authors' interpretation | "The results were therefore deemed to be inconclusive, and further refining of the method is needed" (Abstract). "Proof-of-concept … somewhat inconclusive" (Sec. 4). The NN won 2 of 3 regimes with overlapping SDs in two. Also: "the model needs real temperature data to be trained on". |

**(b) Status**
- v3 §1.6 "tunes a cable model with an LSTM using no soil moisture data": ✅. More precisely, it uses no soil sensors at all, only rain and air temperature.
- v3 §1.6 "benefit over physics-only baseline is marginal": ✅ in spirit. Say "inconclusive, per the authors" and not "marginal", because the NN is better in one regime and worse in another.
- LM B3 title "Neural network-enhanced cable ampacity with soil factor tuning": ❌ wrong title.
- LM B3 "no ampacity computed": ✅.
- LM B3 "future load assumed known": ✅.
- LM B3 gap "No soil moisture or temperature data": partly ❌. Rain is used, and temperatures are measured on the cable and pipe. State it as "no soil moisture or soil temperature sensors".
- v3 labels this a "cable model tuned by ML". It is **not** a soil-state forecast, and the NN does not predict conductor temperature directly. It predicts correction factors for a TEC model, and the TEC model then predicts conductor temperature.

**(c) Corrections**
- **LM B3.** Use the correct title and DOI. Write the "Key metrics" as "NN-assisted TEC: MAE 2.46 vs 2.82 °C (step), 1.32 vs 1.03 °C (slow, conventional better), 0.86 vs 1.09 °C (fast); the authors call the result inconclusive".
- **v3 §1.6.** Replace the Espedal bullet with: "**Espedal et al. 2025** [V]: an LSTM predicts soil-property correction factors for a thermal-equivalent-circuit model in an air-filled-pipe road crossing. It uses assumed-known future load and air temperature, predicts day-ahead *conductor temperature* (not ampacity), and the authors report the comparison as inconclusive."
- **v3 §9.** Update the role cell accordingly.

---

### 14.4 Verschaffel-Drefke et al. 2021, *Energies* 14, 7189

Title: "Heat Dissipation in variable Underground Power Cable Beddings: Experiences from a Real Scale Field Experiment". DOI 10.3390/en14217189. The dataset is TUdatalib-665 (DOI 10.48328/tudatalib-665, CC BY-NC 4.0, deposited 2021-10-27).

**(a) What exactly the 25–35 % compares**

Abstract: "an increase in ampacity between 25% and 35% was determined for a cable system in a duct filled with an artificial grouting material **compared to a common air-filled ducted system**."

Conclusions (Sec. 5): "For the ducted systems the use of artificial grouting materials within the protection pipes leads to an increase in ampacity between 25% and 35%, which is especially pronounced for dynamic load scenarios."

| Experiment (Sec. 3.2, config V = unfilled duct, VI = grouted duct) | Number | Basis |
|---|---|---|
| Constant load, 33 days (Fig. 9) | **"up to 25%"** | First 18 days at 300 A in both ducts. Then the load was adjusted so both ran at ~90 °C. "An increase in the ampacity of up to 25% … for the grouted system (VI), compared to the air-filled protection pipe system (V)". |
| Dynamic EVU profile (Fig. 10) | **"around 35%"** | "an increase in the peak load of around 35%". The unfilled duct started at a 320 A peak, and loads were adjusted so conductor temperatures were similar. |

**(b) Status**
- LM B4 "grouted duct +25-35% over **direct-buried**": ❌ **contradicted**. The comparison is grouted duct against **unfilled air-filled duct**. The paper does not compare it against direct burial in this result. It does say an unfilled duct "might result in an increased temperature … compared to a directly buried cable" as a general statement.
- `VALIDATION_FINDINGS.md` line ~90 "paper's statement that grouting reduces conductor **temperature** by 25–35%": ❌ **contradicted**. It is an increase in ampacity or peak load at an equal ~90 °C conductor temperature, not a 25–35 % temperature reduction. It is also not the "28 percentage point" N-M error difference (−39 % vs −68 %).
- `survey_darmstadt_2021.md` L174: ✅ consistent with the paper.
- The Bates-style "sand dries completely at cable surface and rewets in a day" (LM B4): ❓ partly ✅. The text says complete drying occurred in the sand "from around day 14" (Sec. 3.3), with rewetting after rain (~50 mm in 48 h interrupts drying from ~day 28). "In a day" is not supported. Rewetting is gradual (Sec. 3.1).
- v3 §4.3 "the **only** publicly available multi-bedding real-scale dataset": ❓ unsupported (see 14.6). The dataset page confirms open access, CC BY-NC 4.0.

**(c) Corrections**
- **LM B4 "Key metrics".** Replace with "Loam hottest (>80 °C). Sand shows drying (complete from ~day 14) and rain-driven rewetting. Grouted duct vs **unfilled duct**: ampacity +up to 25 % (constant load, equal ~90 °C) and peak load +~35 % (dynamic EVU profile)". Delete "over direct-buried".
- **`VALIDATION_FINDINGS.md` line ~90.** Replace with "The grouted duct has a smaller N-M error, which is consistent with the paper's finding that grouted duct allows 25–35 % higher ampacity than an unfilled duct. The paper does not report a conductor-temperature reduction of 25–35 %".
- **v3 §1.4 last paragraph** ("quantitatively confirms the PG&E FTB design decision"). Soften to "is consistent with". The paper compares grout vs air-filled duct in a duct setting, not FTB vs native soil in a direct-buried configuration. It also uses thermal resistivity 1.0 K·m/W in IEC calculations.

---

### 14.5 Bates dissertation

**(a) Title and year**
- **Exact title (title page, L16–25): "UNDERGROUND CABLE AMPACITY: A FRESH LOOK AT ADDRESSING THE FUTURE ELECTRIC GRID"**. The author is Carson Bates, a PhD in Electrical Engineering at the Colorado School of Mines. The advisor is Dr. Pankaj Sen and the co-advisor is Dr. Keith Malmedal.
- The matrix and survey title "Underground Cable Ampacity: Soil Thermal Resistivity and Stability" appears **nowhere in the document**: ❌ wrong.
- **Year.**
  - The signature page has a blank "Date ____" (L~35).
  - The latest online-access dates in the references are **Nov 2018** (e.g. "Accessed 05-Nov-2018").
  - The experiments run 10/2016–8/2017.
  - **No "2021" appears in the text.**
  - **[web]** A secondary search summary (ResearchGate-based) gives "November 2018 (indexed ~2019)".
  - ❓ **A Mines repository or ProQuest record has not been retrieved.** I could not open one. **The year is unresolved; internal evidence points to 2018, and 2021 is unsupported.**
- **Action:** use "Bates (2018)" or "(n.d., c. 2018)" until a Mines or ProQuest record is checked. The filename `bates_2021_*` is the only source of "2021". Note also that the Mines repository file you obtained came from a mirror (`pdi2.org`), not the Mines repository.

**(b) Error sign convention and which numbers belong where**

Convention (Sec. 10.5, before Table 10.6): "Negative values indicate that the model calculated a higher temperature than the measurement". **So negative means the model overestimates temperature** (conservative). Compare ANSYS (Table 10.5): "-19% … negative indicates that the measured values is less than the ANSYS calculated value".

| Quantity | Source | Experiment / model |
|---|---|---|
| "mean error of 4% ± 10% for the 6 experiments" | Abstract | Overall summary for N-M and CYMCAP. Basis is not obvious from the abstract. |
| CYMCAP steady-state **−8% ± 8.9%**, N-M steady-state **−8% ± 7.2%**, 90 % CI −15 % to −1 % | Table 9.1/9.2 text (L~5613), Ch. 12 (L8486) | **5-day temperature (jacket)** against steady-state calculation. |
| CYMCAP transient 5-day **−0.5% ± 8.1%**, 90 % CI −7 % to 6 % | L~6384 | CYMCAP transient. Full duration is −0.4 % ± 9.3 %. |
| N-M with 66 % load factor, 5-day continuous run **−0.3 %**, CI (−1.4 %, 0.8 %); 100 % LF −8 %, CI (−14 %, −2 %) | L8493 | N-M spreadsheet |
| Sliding-window ρ (−3 % vs −8 % for CYMCAP; SD 11 % vs 8.9 %) | L8490 | Resistivity choice |
| ANSYS **−19 % ± 9 %** (5-day), −15 % ± 13 % (max) | L7348 | ANSYS FEA (**not** "−11 %", as in `survey_bates_2021.md` §13) |
| Table 10.6 per-run values vary −31 % to +20 % | Table 10.6 | Per software and per experiment |

Important qualifiers:
- The measured quantity is **jacket (cable-surface) temperature**, not conductor temperature, in a **single Boulder, CO direct-buried cable test with 6 runs**. v3 §1.2 says "overestimated **conductor** temperature" and cites "Table 9.1". ❌ It should say "jacket temperature". It is also not "even when soil resistivity was accurately measured": the −8 % uses transient-line-source ρ (as tested), and the 4 % ± 10 % abstract figure is on a different basis.
- The Arizona case is **1 kV DC combiner circuits** (not a 15 kV system). The design used ρ = **270 and 303 °C·cm/W** (270 is "the average of all the tests taken at 0% soil moisture"), a 75 °C termination limit and a 53 % load factor. The in-situ ρ was **157 °C·cm/W, 99 % CI 118–197, at a single location in February, with moisture content not measured**. Bates names the lower ρ as "the most likely explanation" but also lists cable-spacing deviation (>2 in) and other factors (L~8170–8225).
- The SCAN ambient temperature was 34.6 °C at 40 in (99th percentile), and the modeled ambient was 29 °C.
- v3's "software predicted 75–87 °C while field loggers measured 55–61 °C": ❓ not located in my grep of the text. Verify against Ch. 11 tables before keeping it.

**Site-specific conclusions that must not be universalised**
- N-M conservatism (−8 %) comes from one cable, one soil, 6 runs, Boulder, 71–120 A. Bates claims "conservative by experimentation", not a general bound.
- The Arizona overestimate depends on a design ρ that was dry-worst-case, a single in-situ test in February, and unmeasured moisture.
- Both of these are specific to that site and test: "No soil drying" occurred at Boulder at these heat rates. This does not imply drying is unimportant elsewhere (Darmstadt sand dried, per 14.4).
- v3 §6.3 "Soil drying as universal … only 0.8 % of Darmstadt timesteps exceed NHR": ✅ consistent as a Darmstadt statement. Do not extend it.

**(c) Corrections**
- **LM B1, `survey_bates_2021.md` header, v3 line 604, v3 `[Bates 2021 …]` tags throughout, and `AMPACITY_SOURCES…md`.**
  - Replace the title with "Underground Cable Ampacity: A Fresh Look at Addressing the Future Electric Grid".
  - Replace the year with "2018 (provisional; confirm via Mines/ProQuest)".
  - Remove "252 pp" unless the PDF page count is checked. The survey says 252 pages was "verified", but the text has roman-numbered front matter.
- **v3 §1.2 bullet 1.**
  - Rewrite as: "Bates (c. 2018) measured **cable-jacket** temperature in six runs on one direct-buried cable in Boulder, CO. Steady-state N-M and CYMCAP overestimated the 5-day jacket temperature by 8 % (SD 7.2–8.9 %; negative-sign convention = model higher), and a 66 % load factor reduced the N-M mean error to −0.3 %."
  - For the PV case: "At one Arizona 1 kV DC combiner site, measured cable temperatures were below the design calculation. Bates attributes this mainly to design ρ (270–303 °C·cm/W) being higher than the in-situ mean of 157 (single February test, moisture not measured), with cable spacing as another factor."
- **Fix ANSYS** to "−19 % (5-day)" in `survey_bates_2021.md` and `AMPACITY…md`.

---

### 14.6 Bibliography consistency, novelty claims, standards

**A. Bibliographic inconsistencies**

| Item | Inconsistency | Primary-source value | Fix in |
|---|---|---|---|
| **Ahmad et al. 2021** | LM B6 gives DOI `10.3390/en14248191` (issue **24**). v3, v1 and v2 give only "Energies 14, 8191" with no DOI. | The PDF text (L15, L84) gives DOI **10.3390/en14238191** (issue **23**). OpenAlex gives the same (`openalex_locations.json` L121) and the download URL is `mdpi.com/1996-1073/14/23/8191`. Published 6 Dec 2021. | LM B6, and add the DOI to v3 §9. |
| Ahmad title | LM: "Temperature field distribution around heated cylinder in sand: cyclic loading". | "Evolution of Temperature Field around Underground Power Cable for Static and Cyclic Heating". Authors: Ahmad, Rizvi, Arp, Wuttke, Tirth, Islam. It is a **laboratory** study with a cylindrical heater in sand, so "Sand temperature field" in v3 is acceptable, but "cable" is a loose analog. | LM B6, v3 §9 |
| Bracale title/cable | LM "Forecasting of dynamic line rating for buried **MV** cables", no volume or pages. | "Day-Ahead and Intraday Forecasts of the Dynamic Line Rating for Buried Cables", IEEE Access 7:4709–4725, DOI 10.1109/ACCESS.2018.2888505, **LV** cable. | LM B2, v3 §9 |
| Bates | Title and year wrong (see 14.5). | | LM B1, v3 §9 |
| Espedal | LM title wrong. Venue and DOI absent from v3. | CIRED 2025 paper 0152, DOI 10.1049/icp.2025.1508 | LM B3, v3 §9 |
| Widyastuti | See 14.2. v3 table row lists it as "[V]" although the paper is not on disk. | | LM A2, v3 §9 |
| Verschaffel-Drefke | LM omits the DOI of the dataset. | 10.48328/tudatalib-665 | LM B4 |
| LM A4 "Li et al. 2022 *(prev. miscited as Fang)*" and other A-side entries | Vol/pages "from paper". No DOI. | Not checked in this section. | Verify separately. |
| Liu et al. 2022 | Consistent: *Energies* 15, 8897, DOI 10.3390/en15238897. | | none |
| Brakelmann et al. 2021 | Consistent: *Energies* 14, 6813, DOI 10.3390/en14206813. | | none |

**B. Unsupported novelty or exclusivity claims in v3 (and LM)**

The reviewed set is only the seven ampacity items below, not a literature search. Replacement wording is scoped to what was actually searched.

| Location | Claim | Problem | Proposed replacement |
|---|---|---|---|
| v3 §1.6 line 150 | "A **complete review** of the literature – Bracale… Bates (2021) – reveals…" | Seven papers are not a complete review. | "In the seven sources we reviewed in full (Bracale 2019, Espedal 2025, Liu 2022, Ahmad 2021, Brakelmann 2021, Verschaffel-Drefke 2021, Bates c. 2018) and in a targeted web search conducted [date], we did not find…" |
| v3 §1.6 line 154 | "**No published work** provides a forecast of multi-depth measured soil temperature and moisture… as a live input to a cable thermal model validated against a field dataset, at 24–72 h" | An absence claim beyond the reviewed set. Bracale already forecasts soil conditions as thermal-model inputs at ≤36 h. | "Among the sources reviewed, we found none that combines (i) forecasts of multi-depth measured soil temperature and moisture, (ii) a cable thermal model validated against field data, and (iii) 24–72 h horizons. Bracale 2019 forecasts soil/weather inputs to a thermal-hydraulic model at ≤36 h without field validation." |
| v3 §4.3 lines 359–362 | "**the only publicly available**, multi-bedding, real-scale underground cable dataset… **No other paper in the surveyed literature** uses it" | No dataset search is documented. The second sentence is scoped but "only" is not. | "a publicly available (CC BY-NC 4.0), multi-bedding, real-scale dataset, which we identified through [search]. We found no other work in the reviewed set using it for model validation." |
| v3 §6.1 C1 (line 520) | "**The first** evaluation of multi-depth forecast soil T and moisture…" | Unsupported priority claim. | "To our knowledge, and within the reviewed literature, this is the first evaluation of… " or "We evaluate…" |
| v3 §6.1 C2 (line 526) | "we provide **the first** empirical characterisation of how static ρ… N-M underestimates by 21–68 %" | Unsupported. Bates 2018 and Darmstadt already document N-M conservatism or drying effects. The 21–68 % is also a [R] result under assumptions (wet-state default ρ, Darmstadt boundary conditions). | "We provide a quantitative characterisation on the Darmstadt data (N-M underestimates conductor temperature by 21–68 % under wet-state default ρ) …" |
| v3 §6.1 C4 (line 540) | "**the first** such network-scale analysis" | Unsupported. | "a network-scale analysis across 39 USCRN stations" |
| LM line 141 | "Real-time / forecast soil state as N-M input: **Nobody** – this is the SoilSens-Ampacity contribution" | An absence claim. Bracale 2019 forecasts soil state as a rating input. | "Not found in the reviewed set at 24–72 h with field validation." |
| LM line 145 | "**Nobody** – persistence is unbeaten [Bracale]" | Contradicted (see 14.1). | Delete. |
| LM line 155 | "**First operational link**…" | Unsupported priority claim. | "A proposed operational link…" |
| v3/LM P1254 | "**No enforceable standard exists** for in-situ soil thermal stability measurement" | Dated and incomplete (see C). | See C. |
| v3 §1.3 line 44 | "This confirms Bracale et al. (2019) and Liu et al. (2022) [V]" (moisture dominance) | Bracale is model-only on two soils. | "is consistent with" |
| v3 §1.4 | "quantitatively confirms the PG&E design decision" | See 14.4. | "is consistent with" |

Claims in v3 §6.3 that already scope themselves correctly ("does NOT claim first use of moisture", "no field validation at a USCRN site") are fine.

**C. IEEE P1254 and P3522**
- **P1254 (dated claim).**
  - Bates (text written c. 2018) says: "[IEEE P1254] … under an IEEE approved project authorization (PAR). This expired in 2016 due to difficulty in developing a consensus" (L1489–1490, Sec. 2.4). The project started in 2001.
  - This is a statement as of c. 2018. v3 §8 presents it as the present state.
- **P3522 (separately identified project).** **[web]**
  - IEEE P3522, "Guide for Thermal Stability Data Collection Through Laboratory Testing of Soil and Backfill". Reported as an **active PAR approved 26 September 2024**, with the Insulated Conductors Committee soil thermal stability working group (WG ID `C20W/P1254_WG`, chair reportedly Wael Moutassem). It covers laboratory test setups for moisture migration in soil or backfill.
  - This indicates that the P1254 effort was **revived under a new project number**, so "P1254 expired and nothing is under way" is outdated.
  - It is a laboratory-testing **guide** in development, not a published standard. It does not cover in-situ ampacity determination.
  - ❓ I have not seen the IEEE SA project page. Verify the status date, scope and title on the IEEE SA page before citing.
- **Related existing standard.** **[web]** IEEE Std 442-2017 (thermal resistivity measurement of soils and backfill) is an active standard. Bates cites the 1981 edition. So "no standard" must be limited to *thermal stability / dry-out*, not thermal resistivity measurement.
- **Corrections.**
  - **v3 §8, v3 line 620, LM line 144 and `AMPACITY…md` line 132/195.**
  - Replace with: "Bates (c. 2018) reported that the IEEE P1254 project on soil thermal stability had its PAR expire in 2016 without consensus. A new IEEE project, P3522 (laboratory testing of soil and backfill thermal stability), had an active PAR approved in September 2024 [status to be verified on IEEE SA]. As of our review we have not identified a published IEEE standard for in-situ soil thermal stability measurement for cable ampacity. IEEE Std 442 covers thermal resistivity measurement."
  - Add the date of the check next to the claim.
  - Remove "No enforceable standard exists…" and "IEEE standard gap" as a **gap asserted by this proposal**.

---

### Summary of the biggest contradictions

1. **Bracale:** the PSM beats persistence and the two data-driven models at 1–12 h. Persistence beats DDM-LR and DDM-RFR only at 13–36 h (LV cable, one UK site, model-derived targets, nothing beyond 36 h). The matrix claim that persistence beats all ML at 1–36 h, and the "unbeaten" claim, are wrong.
2. **Widyastuti 2026:** the paper concerns 33 Tasmanian sites and (per the title) a PINN for spatiotemporal mapping. It is not USCRN, not LSTM + Crank-Nicolson, and not a verified 24–72 h forecast. It does not support our USCRN architecture.
3. **Darmstadt 25–35 %:** this compares a grouted duct with an unfilled air-filled duct. It is an ampacity or peak-load gain at equal ~90 °C (25 % constant load, 35 % dynamic), and not "over direct burial" and not a temperature reduction.
4. **Bates:** the true title is "A Fresh Look at Addressing the Future Electric Grid", and "2021" appears nowhere in the text (Nov 2018 access dates; year unresolved). The error sign is negative = model hotter. The measurand is jacket temperature, and the Arizona case is a single-site 1 kV DC case with unmeasured moisture.
5. **Bibliography and novelty:** the Ahmad DOI is `10.3390/en14238191` (LM has `…248191`), and several titles are wrong. Seven unsupported "first / only / nobody / complete review" claims need rescoping. The P1254 "expired" statement is dated c. 2018, and a P3522 PAR (Sept 2024, web-sourced) exists.

---

## 15. Compiled dataset status

All paths relative to `WS\SoilSens_Ampacity_Dataset\`.

| Item | Location | Status |
|---|---|---|
| Latest workbook | `Dataset_Overview.xlsx` (16 sheets; samples are labelled as samples) | completed |
| Complete cleaned CSVs | `01_…` to `04_…` (341,952 USCRN rows in 13 files, 36,599 loading rows, 97,284 temperature rows, etc.) | completed |
| Data dictionary | `05_Documentation\Data_Dictionary.csv` (264 columns) | completed |
| Station and sensor metadata | `01_Soil_and_Climate\Stations.csv` (13), `03_…\Sensor_Metadata.csv` (36) | completed |
| Experimental and reference cases | `04_Assessment_Cases\Experimental_Cases.csv` (6), `Reference_Cases.csv` (39) | completed |
| Source manifest | `Source_Manifest.csv` (9 sources) | completed |
| Quality report | `05_Documentation\Quality_Flags.csv` (12), `Quality_Summary.csv` (31) | completed |
| Rebuild scripts | `scripts\part1…part5_*.py` and three patch scripts | completed |
| ZIP | `WS\SoilSens_Ampacity_Dataset_v1.0.zip` (6.3 MB) | completed |

**Handling:** timestamps — column `timestamp_lst` = **local standard time** (not UTC) built from the NPZ `date`/`hour` arrays; the original NPZ fields are `date` and `hour`. Missing observations are **left empty** (2 stations > 10% missing 50 cm moisture, QF08); the package does not forward-fill, the pipeline does. Negative moisture (min −0.764%, sand) kept and flagged QF01. Temperature plateau at 75.011 °C (loam, sand sheath) kept and flagged QF02 as control-limited, not clipping — *this is an inference from varying values near the limit and not confirmed by the paper*. Retention above porosity (silt 38.37% > 35.6%) kept, QF06. Southwire 750 kcmil 1.495 in diameter kept as printed, QF11. Conflicting labels: `MF_III_CL` kept, with configuration II noted and the "(IV)" header preserved. **Cleaning versus model filling:** the package does cleaning only (naming, units, de-duplication of weather/moisture blocks, flags). Interpolation and forward-filling occur only inside `run_station`.

**Package updates made after this audit (v1.1, additive; v1.0 ZIP unchanged):** the PG&E-derived-depth status in \Reference_Installations.csv\ now reads CALCULATED for 24 and 30 in with the size of the effect; \Reference_Cases.csv\ points to the depth-corrected results; \Quality_Flags.csv\ gained QF12–QF17 (unmatched branches, shallow-observation column label, MF_III bedding/unit mismatch, SF current/depth mapping, sign convention, unattributed MF_IV discrepancy); workbook rebuilt; new ZIP \SoilSens_Ampacity_Dataset_v1.1.zip\ (47 files, 6.0 MB). Re-running \part4_documentation.py\ would drop QF12–QF17 unless \patch_v11_rerun_and_audit.py\ is re-applied.

---

## 16. Synthesis-ready status summary

### Completed and supported by supplied files
- **Data:** 13 USCRN stations (2019–2021 hourly soil temperature, moisture, precipitation, local standard time) compiled into 341,952 cleaned rows; Darmstadt workbook (36,599 loading, 97,284 temperature, 10,074 moisture rows) cleaned; Wilson T1 (2,450 long-format rows); catalogues, installations, materials, sensor and case tables; data dictionary, quality flags, source manifest; workbook; ZIP.
- **Forecast benchmark (temperature, 20 and 50 cm, 24–72 h, event-triggered):** B1/B2 and C1–C3 conduction baselines scored on 1,689 hot-spell issues, 8 verification checks passed, frozen decision rule gave "mixed": room for AI at 20 cm, baselines adequate at 50 cm.
- **Cable model:** a steady-state Neher–McGrath-style rating and conductor-temperature calculator (`ampacity`, `conductor_temperature`), run for the Southwire 350 kcmil cable (static 621 A at 0.762 m; 631 A in the self-test versus Bates 541 A).
- **Historical observed-environment rating calculations:** 13 stations × 3 centre-depth scenarios, using observed 50/100 cm records, interpolated to cable depth; and now (4a) 13 × 2 with PG&E-derived depths (change < 1.2% in dynamic rating).
- **Sensitivity curves** of rating to ρ, Ta and depth (baseline 850.4 A).
- **Quantification of the depth issue** (Section 4a).

### Implemented but requiring correction or reconciliation
| Output | Problem | Present interpretation |
|---|---|---|
| `headroom_pct`, "86–143%" | unmatched branches (90 vs 105 °C, cable vs conduit OD, 3 vs 1 cable, LF 1 vs 0.66) | descriptive of two different cases; ≈ +109% is structural; do not attribute to soil |
| `I_persist_A` | contemporaneous 50 cm observation, no origin or horizon | "shallow-observation rating", not persistence |
| "39 stations" | 13 × 3 = 39 combinations; only 4 of the 13 are in the forecasting 39 | restate |
| MF_III validation, "45.8 °C·cm/W", √(90/45.8) = 40% | silt data vs sand parameters; % passed as m³/m³; fallback 0.20 for 69% of rows | withdraw |
| SF V+VI validation | VI driven by V's current; interior not modelled; fill ρ on pipe wall; depth sign error; paired n is 2,356 not 12,194 | not a validation |
| MF_IV validation | −21% to −51%; Tj = 0, no sheath/dielectric loss, default spacing, fixed 70 °C, steady vs transient | a measured model discrepancy; cause unresolved; drying plausible, not isolated |
| Error sign wording | printed descriptions reversed | negative = model temperature too low |
| NHR 0.8% | example-specific sand threshold applied to silt data | comparison with an assumed threshold only |
| `T_soil` `Dx` and mutual-heating term | 60 Hz diffusion length; unsourced "simplified image term" | unresolved; unreached in ampacity pipeline (n = 1) |
| `cable_params.py` | 75 °C·cm/W tagged PG&E | SnoPUD high-strength value; unused numerically |
| v3 §2.3/§2.5 | GRU/LSTM/hybrid "implemented" | not implemented |
| Sensitivity | text figures not reproduced from CSVs; load-factor sweep flat; 621 vs 850 denominators | use saved CSVs; relabel denominators |
| Forecast summary | withdrawn "82%" still printed; median MAE next to CI for mean | do not quote |
| Literature claims (Section 14) | Bracale "persistence unbeaten" and "beats all ML at 1–36 h"; Widyastuti described as USCRN LSTM + Crank–Nicolson; Darmstadt 25–35% called "over direct burial" or a temperature reduction; Bates title/year; Ahmad DOI; "first/only/nobody/complete review" wording; P1254 undated | rewrite per 14.1–14.6 before v4 |

### Proposed work
- **Environmental forecasting:** train GRU and GBT per `forecast_audit_and_ai_spec.md` §9 (20 cm primary, 50 cm secondary); decide about the LSTM/differentiable hybrid; moisture forecaster and moisture baseline; 100 cm and cable-depth forecasting.
- **Transient modelling:** thermal capacitances, initial conditions, a time-integrated cable model, a documented IEC-style or finite-element reference.
- **Current search:** a 72-hour temperature-constrained current search.
- **Matched-assumption comparison:** one installation, one limit, one load model; fixed-soil versus ρ(θ), Ta only; both 90 and 105 °C.
- **Validation repair:** match bedding and units in MF_III; use per-configuration current and a modelled interior in SF; add sheath/dielectric losses; model touching-trefoil spacing; align sampling intervals.
- **Property work:** use Wilson T1 for the nine matched stations, with explicit fallback and bounds for the four unmatched; Darmstadt measured curves for experimental cases.
- **Interface work:** forecast-issue-time to ampacity API; reporting of lead time.

### Replacement paragraph for v4 (status and contribution)
> **Status.** The project has (i) a cleaned, documented dataset package combining USCRN soil observations, Darmstadt cable-experiment records, cable and installation catalogues and Wilson soil properties; (ii) a scored, event-triggered temperature-forecast benchmark at 20 and 50 cm using persistence, seasonal-anomaly and conduction baselines (no learned forecaster has yet been trained); (iii) a steady-state Neher–McGrath-style rating calculator; and (iv) historical, observed-environment rating calculations for 13 USCRN stations at three cable-centre-depth scenarios. The existing ampacity comparisons use unmatched static and changing-environment assumptions and are therefore descriptive; the Darmstadt validation scripts contain bedding, unit and current-mapping errors that must be repaired before any validation claim is made. **Contribution proposed.** The work proposes to connect a forecast of soil temperature (and, later, moisture) at cable depth to a transient, temperature-constrained cable model, and to evaluate it against matched-assumption static and persistence ratings, using public observations and a public cable experiment. No claim of priority is made beyond the literature search documented in the bibliography.

---

*End of V4 clarification response. No historical result, specification or source file was overwritten; new files created in this session: `run_corrected_depth.py`, `results\dynamic_ampacity_corrected_depth\`, and this document.*
