# Layered-column null diagnostic: frozen specification

Written before `layeredsolver.py`, `45_frozen_columns.py` or `46_layered_diagnostic.py` existed or ran. Task source: sections 17-18 of the updated project synthesis. **Everything simulated is labelled SIMULATED and is never a measurement, never training data.** No new downloads. No AI fitting. 2022 onward is untouched.

## Question
Can **time-invariant layered soil properties**, driven by the observed 5 cm and 100 cm temperature histories, produce an apparent rain-linked change in the **uniform effective diffusivity** that the original pilot estimator reports? In the null experiment, moisture changes nothing: the same conductivity and heat capacity are used in the stress, post-wetting and control windows.

## What is held fixed from the archived pilot (unchanged)
- Event set, windows (stress, post-wetting, no-wetting control), cluster IDs, development (start year 2012-2018) / test (2019-2021) split, the six-hour exclusion, scoring depths 10/20/50 cm, the 2.5 cm grid, hourly Crank-Nicolson, the 80-value log alpha grid (5e-8 to 5e-6 m2/s), the identification rule (interior optimum, 68% interval width at most 0.6 in ln alpha, lag-1 effective sample size), the outcome (mean change in ln alpha for wetting sequences minus that for no-wetting sequences), the cluster bootstrap (2000 resamples, same seed policy), and the initial-profile rule (PCHIP through the observed 5/10/20/50/100 cm temperatures at the window's first hour).
- Observed values to compare against (archived): development all-season contrast **+0.142 [0.002, 0.277]**, test **+0.141 [-0.143, 0.433]**.

## Layered solver (to be written and verified before use)
Conservative finite-volume form: C(z) dT/dt = d/dz( k(z) dT/dz ), with k and the volumetric heat capacity C specified **separately**. Element conductivity k_e (series/harmonic over the layers an element spans), element heat capacity C_e (thickness-weighted); node heat capacity = mean of its two elements. Temperature and flux are continuous at interfaces by construction. Crank-Nicolson, Dirichlet boundaries at 5 and 100 cm from observations.

**Acceptance criteria (fixed now):**
1. Uniform-property limit equals the existing `heatsolver` to within 1e-8 C.
2. Uniform periodic analytic solution (24 h): amplitude error <= 3%, phase error <= 0.3 h at depths with amplitude >= 1% of the surface amplitude.
3. Two-layer periodic analytic solution (finite column, interface placed **between** nodes, e.g. 0.22 m) for conductivity ratios 0.5 and 2 and heat-capacity ratios 0.5 and 2: the same amplitude and phase limits, and **interface flux** (both sides) within 3% of the analytic flux amplitude.
4. Steady state: flux continuity across interfaces to within 1e-6 relative.
5. Convergence: error at (76 intervals, 900 s) <= error at (38 intervals, 3600 s).
If any criterion fails, the task stops and reports the limitation.

## Column family (parameters derived from development information only; rules fixed here)
Three layers: **L1 = 5-20 cm, L2 = 20-50 cm, L3 = 50-100 cm** (interfaces at 0.20 and 0.50 m).

| Column | Definition |
|---|---|
| **U** (control) | One uniform layer, alpha_U = the grid value nearest the archived median development stress-window alpha (4.58e-7 m2/s), C_U = 2.5e6 J/m3/K, k_U = alpha_U x C_U. Sensitivity: alpha_U = 2e-7 and 1e-6. |
| **S** (station-layered, from Wilson probe-site cores) | For each station with usable cores: layer bulk density and sand fraction = mean of the Wilson values at the depths 5/10/20 (L1), 20/50 (L2), 50/100 (L3); a layer with no value copies the nearest layer; **stations without a usable L1 bulk density are excluded and counted**. Conductivity = Johansen scheme (Dai et al. 2019, section 2.1.1 equations 1-8, as already used) and heat capacity = (1 - phi) x Cs + theta x 4.18e6 at a **fixed reference moisture** theta_ref per layer. theta_ref = median hourly moisture over non-freezing hours (5 cm temperature above 1 C) in **development years 2012-2018**: L1 = mean of the 5, 10, 20 cm sensors; L2 = mean of 20, 50; L3 = mean of 50, 100; clipped to the estimated porosity. phi = 1 - bulk density / rho_s. |
| S variants (identified uncertainty ranges, not tuning) | central (rho_s 2.65, Cs 2.0e6, theta_ref median); **dry reference** (theta_ref = development P25); **wet reference** (P75); **Cs low** (1.8e6, rho_s 2.70); **Cs high** (2.4e6, rho_s 2.60). |
| **G_low / G_high** (generic two-layer, interface 20 cm, station-independent) | From the S-central columns of development stations: r_k = k(L1) / k(L3) and r_C = C(L1) / C(L3). G_low uses r_k at the 10th percentile, G_high at the 90th, both with median r_C. Lower layer (20-100 cm): C = median C(L3) across development stations, k = alpha_U x C. Upper layer: k = r_k x k_lower, C = r_C x C_lower. |

**Assumptions not from the cited scheme (flagged):** quartz fraction proxied by sand fraction; coarse-grained if sand >= 50%; solid heat capacity and particle density as above; layer interfaces at 20 and 50 cm and averaging of Wilson depths into layers; no organic matter or gravel. Properties are held constant across all windows of a station.

## Procedure
1. Reproduce the archived baseline (event IDs, attrition, best-fit diffusivities, identification decisions, contrasts) from the original code; document any mismatch.
2. Verify the solver against the criteria above.
3. For each usable event and window, simulate each column from the observed boundaries and the same initial profile; sample at 10, 20, 50 cm (**SIMULATED**); apply the original estimator unchanged. Primary: noise-free. Secondary: rounded to the 0.1 C reporting step.
4. Compute the same contrast by column and by development/test, with cluster bootstrap 95% intervals. Selection variants: (a) events identified in the simulated pair, (b) events identified in the **observed** pair (the original selection), (c) all usable events.
5. Numerical sensitivity: refined simulation (76 intervals, 900 s) for all columns; estimator first-24 h exclusion instead of six hours (initialisation dependence); forcing-spectrum covariate for the change in ln alpha.
6. The test set is run **once**; the original test result was already known when this diagnostic was designed, and that is logged here.

## Reading rule (descriptive, fixed now)
Simulated all-season contrast >= 0.10 in both development and test: "reproduces a similar contrast"; between 0.05 and 0.10: "partly"; below 0.05: "does not". These thresholds are heuristics against the observed +0.14, not statistical tests; intervals are reported alongside. The parameter family is exploratory and supplies no probability distribution.

Results must not be described as a measurement of any physical property, and a null result for layering does not confirm rain causality.

## Amendment B (logged after the solver verification, before ANY simulated contrast existed)
- First verification run had a sign error in the PHASE comparison of my check script (criteria unchanged). Corrected run, see layered_verification_out.txt: all criteria pass at the **refined** resolution (76 intervals, 900 s); at the **base** resolution (38 intervals, 3600 s) criterion 3 misses by 0.5 percentage points in one extreme case (conductivity ratio 0.5 with heat-capacity ratio 2, amplitude error 3.49% at a depth with 5.7% of the surface amplitude).
- Decision (made from verification results only): the simulated temperatures (the SIMULATED data generator) use the **refined** resolution; the base resolution is run as a numerical sensitivity. The original estimator keeps its own discretisation (38 intervals, hourly) unchanged, as frozen. A small generator-estimator discretisation mismatch therefore exists and is quantified by the uniform control and by the base-resolution sensitivity.
- Numerical error floor to use when reading differences: RMS 0.012 C (base) and 0.002 C (refined) against the analytic two-layer solution.

## Addendum C (column family computed and frozen before any simulation)
- phase3/columns_frozen.csv, SHA-256 5a3589e207eadfe776f66aae0eb4778200d369fd360f5e94b2995b15dc079344; summary in phase3/columns_frozen_summary.txt. 15 stations have usable S columns (13 with development events); G ratios come from those 13.
- The family is only **weakly layered** (development k(L1)/k(L3) 0.76-1.27 at P10-P90; alpha_up/alpha_low 0.83 for G_low and 1.39 for G_high). A stronger-layering bound is NOT added now (that would be tuning against a result already known); it is a candidate for a separately frozen extension.
- Estimator guard: SSE is floored at 1e-20 before the log in the identification interval, which only matters for a zero-error control and does not touch any real-data window.
