# Phase 3, Direction A pilot: pre-registration (frozen before any pilot fitting)

Written before `39_pilotA_solver_check.py` and `40_pilotA_run.py` were run. No model has been fitted to the events. The event inventory (`event_inventory.csv`) and its descriptive checks already exist; they involved no fitting. Conditional reconstruction only, never forecasting.

## Question
During hot and dry episodes, how deeply does unusual warming penetrate, how long does it persist, and does rain-driven moisture replenishment coincide with a change in underground heat propagation, separated from changes in surface forcing?

## Event set
Primary-variant complete sequences from `event_inventory.csv` (156 sequences, 95 synoptic clusters). **Development: start year 2012-2018. Final test: start year 2019-2021.** The test set is touched once, after all code and rules below are fixed and development results are written. 2022 onward is not downloaded.

## Part 1 - trajectories (descriptive, no model)
Per sequence and depth (5, 10, 20, 50, 100 cm), with the anomaly defined as daily soil temperature minus the local day-of-year median:
- peak anomaly (C) over [start, end+14 d];
- peak delay = days from spell start to the peak;
- persistence = days from the peak until the anomaly first falls to <= 50% of the peak (censored if never within the window);
- anomaly burden = integral of the positive anomaly over [start, end+21 d], in degree-days (**not heat energy**).

Uncertainty: cluster bootstrap over synoptic clusters (2000 resamples). Contrasts: wetting vs no-wetting sequences; pre-event 10 cm moisture tertile (computed within station); clay tertile (stations with Wilson texture). Forcing: peak anomaly at 5 cm against the spell's mean Tmax anomaly and mean solar radiation (descriptive slope, cluster bootstrap).

## Part 2 - propagation, separated from forcing
Observed 5 cm temperature is the upper boundary and observed 100 cm temperature the lower boundary, throughout the window. The initial profile is the observed 5/10/20/50/100 cm temperatures at the window's first hour, interpolated (PCHIP) to a 2.5 cm grid, so every comparator receives the same initial profile.

Solver: uniform-diffusivity 1-D heat equation, Crank-Nicolson, dt = 1 h, nodes 5-100 cm at 2.5 cm. One diffusivity alpha per window (an **effective** value). Scored depths: 10, 20, 50 cm; the first 6 h are discarded. alpha is chosen from 80 log-spaced values between 5e-8 and 5e-6 m2/s by minimum RMSE.

**Windows** (hourly data; hot-dry complete sequences only):
- W_stress = [spell start - 2 d, spell end + 2 d].
- W_post (sequences with a wetting day) = [wetting day + 1 d, wetting day + 10 d], required length >= 7 d, clipped to the follow-up window.
- W_ctrl (sequences without a wetting day in the 21-day follow-up) = [spell end + 4 d, spell end + 14 d].

Windows with more than 10% missing hours at any used depth are excluded.

**Identifiability rule (per window):** alpha counts as identified if (i) its optimum is not at a grid edge and (ii) the approximate 68% profile interval is no wider than 0.6 in ln alpha. The interval comes from n_eff x ln(SSE/SSE_min) <= 1, with n_eff = n (1-rho)/(1+rho) from the lag-1 autocorrelation rho of the residuals. A sequence enters the pairing only if both its windows are identified.

**Outcomes:**
- Delta = ln alpha_post - ln alpha_stress (wetting sequences).
- Delta_ctrl = ln alpha_ctrl - ln alpha_stress (no-wetting sequences).
- Contrast = mean(Delta) - mean(Delta_ctrl), by cluster bootstrap. Stratified by May-Sep and all-season.

**Persistent-error scenarios (rerun every window):**
1. baseline;
2. T5 +0.1 C and T100 -0.1 C;
3. T5 -0.1 C and T100 +0.1 C;
4. upper boundary at 6 cm instead of 5 cm;
5. upper boundary at 4 cm.

These are exploratory scenarios (not measured error bounds): 0.1 C is the reporting step, not a detection threshold.

**Solver verification (before the run):** (a) against the analytic solution for a sinusoidal upper boundary and a semi-infinite medium; (b) grid and time-step refinement (dz 2.5 vs 1.25 cm; dt 1 h vs 0.25 h). Acceptance: amplitude error <= 3% and phase error <= 0.3 h over alpha from 2e-7 to 2e-6 m2/s at a 24 h period. If it fails, Part 2 is not run.

## Part 3 - established formulation vs alternatives
Predicts Delta only. A local scale factor cancels in a ratio, so every model has an equal calibration allowance (none).

Events: wetting sequences at stations with Wilson bulk density at 10 and 20 cm (the 14 audited candidates, Elgin excluded). Layer properties: bulk density and sand fraction averaged over 10 and 20 cm; estimated porosity phi = 1 - rho_b/2.65 (assumed particle density, **estimated, not measured**); window moisture = mean of 10, 20 and 50 cm moisture.

| Model | Delta_pred |
|---|---|
| M0 | 0 (constant diffusivity) |
| M_B | b x (theta_post - theta_stress); b shared, either sign, fitted leave-one-station-out on development events |
| M_J | ln[(k_J/Cv)_post / (k_J/Cv)_stress]; no fitted parameter |

M_J components:
- k_J: Johansen scheme as in Dai et al. 2019 (arXiv 1908.04579, section 2.1.1, equations 1-8). Kersten number K_e = log10 S_r + 1 for fine-grained soils (S_r > 0.1) and 0.7 log10 S_r + 1 for coarse-grained (S_r > 0.05). k_dry = (0.135 rho_d + 0.0647)/(2.7 - 0.947 rho_d), rho_d in g/cm3. k_sat = k_min_wet^(1-phi) k_w^phi, with k_min_wet = k_q^vq k_o^(1-vq), k_q = 8.8, k_o = 2.0 (vq > 0.2) or 3.0, k_w = 0.57 W/m/K.
- Assumptions NOT in Dai's text (flagged and sensitivity-tested): quartz fraction vq approximated by sand fraction; "coarse" if sand >= 50%; de Vries heat capacity Cv = (1-phi) x 2.0e6 + theta x 4.18e6 J/m3/K, with solid heat capacity varied over 1.8e6-2.4e6.

Score: mean absolute error |Delta_obs - Delta_pred| over identified events; paired differences with cluster bootstrap; sign agreement reported separately.

## Decision rules (fixed now)
- **Rain-linked change in propagation is supported** only if, in development AND test: Contrast >= 0.15 ln units with a 95% cluster-bootstrap interval excluding 0; the same sign in >= 60% of stations with >= 2 identified events; and the sign unchanged in >= 4 of the 5 error scenarios.
- **The established formulation explains the change** only if M_J has lower MAE than both M0 and M_B in development and in test, with intervals excluding 0 in both.
- If fewer than 20 identified wetting clusters exist, the result is reported as underpowered, not as a null.
- No claim of mechanism, no tipping-point language. AI is not run in this pilot; a flexible learner is considered only if both models fail with reproducible structure.

## Addendum A (written before 40_pilotA_run.py was run; solver check already passed)
- **Relative saturation above 1:** in M_J the main variant EXCLUDES events whose window-mean S_r = theta/phi_hat exceeds 1 in either window (theta above estimated porosity indicates sensor, density or particle-density error, so it is not silently capped). A sensitivity variant clips S_r at 1. The number excluded is reported.
- **Kersten number below its validity limit** (S_r <= 0.05 coarse, <= 0.1 fine): K_e = 0 (dry limit).
- **Order of work:** development events (start year 2012-2018) are analysed and written to disk first; the 2019-2021 test events are then analysed once with the frozen rules and the frozen shared parameter b from development.


## Note written after the development run and before the test run
Development results are saved in pilotA_out_dev.txt (copy: pilotA_out_dev_FROZEN_copy.txt). The decision rule did not say which stratum (all seasons or May-Sep) carries the 0.15 threshold. Both are reported; the all-season contrast is treated as the headline and May-Sep as a secondary check. Nothing in the code or rules is changed before the single test run.
