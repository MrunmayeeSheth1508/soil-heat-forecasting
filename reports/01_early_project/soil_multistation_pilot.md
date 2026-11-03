# Soil Heat: Data Checks and Small Multi-Station Conventional Pilot

Scripts: `soil/16_reconcile_qc_select.py`, `soil/17_multistation_pilot.py` (design and decision rule in the header, fixed before results).
Outputs: `reconcile_out.txt`, `record_checks.csv`, `pilot_stations.txt`, `multipilot_out.txt`.

## 0. Corrections to the previous audit report

- **Sign reversal is not required.** Negative moisture-temperature correlation at every site does not prevent separation. What matters is independent variation after other predictors, measurement error and model sensitivity. The variance inflation of 1.24 describes pairwise linear collinearity only.
- **Moisture ranges are observations, not regimes.** The 0.15 m3/m3 threshold does not mean the same wetness across soils (texture, porosity, density differ). "Selma sampled the wrong range" is withdrawn as a statement; it was a hypothesis.
- **Unusual values are inspection flags, not sensor failures.**
- **Literature:** Peng 2024, Xie 2024 and Wang 2023 exist (references verified by you). My earlier "not found / possibly fabricated" was an access failure. Coupled AI inference of soil thermal relationships from moisture and temperature is existing work. No gap is claimed.

## 1. Selma reconciliation (identical columns and dates)

- Pilot raw files and audit arrays: 17,544 rows each; column 29 (10 cm moisture) and 5/10/20 cm temperature identical hour by hour.
- Pilot episode mask rebuilt exactly: 14,703 hours (matches).

| Subset | 10 cm moisture p5 to p95 | Two-state bins (audit definition) | r(theta, Tin) |
|---|---|---|---|
| Audit dry days 2019-2021 | 0.277 to 0.539 | 6 (12 to 30 C) | -0.61 |
| Audit dry days 2019-2020 | 0.260 to 0.541 | 1 (27 C) | -0.67 |
| Dry days inside pilot episodes | 0.263 to 0.541 | 2 (12, 15 C) | -0.64 |
| Rerun training episodes 1-11 | | **0** | -0.64 |
| Rerun test episodes 12-14 | | **0** | -0.68 |

**Selma's audit contrast comes mainly from 2021, which the earlier pilot and rerun did not use.** The rerun training episodes contained no within-site contrast at overlapping temperatures by the audit definition. Selma passing the broader screen did not mean the earlier fitting episodes had useful contrast.

Pilot validity required all five depths; the audit required 5/10/20 cm temperature and 10 cm moisture only. That also changes which days enter.

## 2. Record checks and station selection

Checks on the 39 audit-qualifying stations (2019-2021): completeness, longest stuck run of 10 cm moisture, unexplained one-hour moisture jumps, temperature amplitude ordering 5 > 10 > 20 cm. Nine stations flagged for inspection (not rejected as faulty), for example Merced (164 unexplained jumps per year), Port Aransas (moisture constant for 9.6 days), Lafayette and Newton (amplitude ordering holds on only about half of days).

Pre-specified selection: top 5 unflagged stations by two-state bins then residual moisture SD, at most one per state, plus Selma:

| Station | Segments | 10 cm moisture IQR | r(theta, Tin) |
|---|---|---|---|
| TX Muleshoe | 68 | 0.100 to 0.155 | -0.23 |
| SC McClellanville | 58 | 0.113 to 0.255 | -0.23 |
| IL Champaign | 62 | 0.190 to 0.334 | -0.46 |
| OK Goodwell | 78 | 0.199 to 0.350 | -0.44 |
| NE Lincoln | 59 | 0.276 to 0.403 | -0.46 |
| AL Selma | 77 | 0.387 to 0.504 | -0.58 |

## 3. Pilot design (as pre-specified)

- 5-20 cm solver; T5 and T20 boundaries; T10 target only. 336 h segments; warm-up and hours after rain over 1 mm excluded from scoring.
- **Station differences separated from within-station change:** moisture and temperature enter only as departures from station means; station means absorbed by a station intercept. The between-station moisture effect is not tested.
- M_T: temperature departure. M_TM: temperature plus moisture departure. Shared signed coefficients.
- **Unseen station:** leave-one-station-out with local calibration. Shared b, c from the other 5 stations; at the held-out station only the intercept (and the centring means) estimated from its first 25% of segments; scored on the remaining 75%. Same allowance for both models.
- Final evaluation year 2022 not downloaded or inspected.

## 4. Results

**Leave-one-station-out RMSE of excluded 10 cm temperature (C):**

| Held-out station | M_T | M_TM | Change | Fold b |
|---|---|---|---|---|
| TX Muleshoe | 0.512 | 0.557 | -0.045 | -0.116 |
| SC McClellanville | 0.396 | 0.417 | -0.021 | +0.114 |
| IL Champaign | 0.142 | 0.146 | -0.004 | +0.061 |
| OK Goodwell | 0.674 | 0.674 | 0.000 | +0.046 |
| NE Lincoln | 0.989 | 0.993 | -0.004 | +0.096 |
| AL Selma | 0.359 | 0.361 | -0.002 | +0.067 |

Adding the shared moisture term made held-out prediction slightly worse at 5 stations and unchanged at one. Station-averaged change -0.0125 C, bootstrap 95% CI -0.0154 to -0.0094.

**Pooled shared coefficients:** b = +0.046 per 0.1 m3/m3 (bootstrap 95% -0.016 to +0.113); c = +0.008 per 10 C (-0.044 to +0.059); corr(b, c) = +0.23. The bootstrap resamples segments within stations and understates uncertainty because of seasonal dependence.

**Observation sensitivity:** b ranges +0.043 to +0.050 under +/-0.1 C offsets on either boundary; a +/-20% moisture scale error rescales b without changing its sign.

**Station-specific fits (each station alone):**

| Station | b_s per 0.1 m3/m3 (bootstrap 95%) | c_s per 10 C | alpha |
|---|---|---|---|
| TX Muleshoe | **+0.459** (+0.378 to +0.585) | -0.007 | 1.8e-7 |
| OK Goodwell | **+0.172** (+0.060 to +0.345) | +0.354 | 1.9e-6 |
| AL Selma | -0.022 (-0.076 to +0.065) | +0.099 | 3.8e-7 |
| IL Champaign | **-0.055** (-0.091 to -0.017) | +0.019 | 3.7e-7 |
| NE Lincoln | -0.075 (-0.178 to +0.010) | +0.065 | 1.3e-7 |
| SC McClellanville | **-0.230** (-0.320 to -0.078) | -0.165 | 5.3e-7 |

## 5. Pre-specified decision

| Criterion | Result |
|---|---|
| D1 M_TM better at 5 or more of 6 held-out stations | 1/6 (the one is a tie): **fail** |
| D2 improvement CI excludes 0 (in favour of M_TM) | CI excludes 0 **against** M_TM: **fail** |
| D3 fold b same sign and pooled interval excludes 0 | signs differ (Muleshoe fold negative); interval spans 0: **fail** |
| D4 sign of b robust to boundary offsets | **pass** |

**Verdict: a shared within-station moisture contribution is not established, and it does not transfer.** The 2022 final test was not run; it remains untouched.

## 6. Interpretation

**Supported by these computations:**
- A single shared log-linear moisture coefficient does not transfer between these stations. The Muleshoe fold shows this directly: coefficients learned elsewhere (b = -0.116) degraded Muleshoe, whose own fit wants b = +0.46.
- Within individual stations, moisture coefficients are constrained under the (optimistic) bootstrap, but they differ in sign across stations.
- The Selma-only temperature effect does not appear when pooled (c near 0), and station c_s also varies in sign.
- Model differences (up to 0.05 C) are small next to station RMSEs of 0.14 to 0.99 C. Lincoln (0.99 C) and Goodwell (0.67 C; fitted alpha 1.9e-6 m2/s, high for soil) indicate base-model or observation problems larger than any moisture term.

**Not supported:**
- That the heterogeneity reflects a physical nonlinear moisture response. The two positive stations include the driest (Muleshoe), which is consistent with diffusivity rising in drier soil, but McClellanville is also dry and has the strongest negative coefficient. Six stations, unknown texture and possible station-specific observation problems cannot separate a physical response from site or sensor effects.
- Any claim about the between-station moisture effect (not tested by design).

## 7. What this means for the AI step

By the decision you set: moisture did not improve excluded predictions or yield a constrained shared relationship after site differences, temperature and observation checks. **A Gaussian process or spline is not justified by this evidence.** Fitting a flexible function to these six stations would describe their sign differences, and I have now seen these stations, so they could not test it.

What could still be done conventionally, each a separate pre-registered question:
1. **Diagnose the base-model misfit** at Lincoln and Goodwell (amplitude and phase consistency by layer, alpha plausibility) before any dependence is modelled. A moisture term cannot be interpreted while station RMSE is near 1 C.
2. **Retrieve site soil properties** (texture, porosity, bulk density) and pre-register a texture-normalised wetness variable. Test it on **new** stations not used here.
3. Read the full methods of Wang 2023, Xie 2024 and Peng 2024 before any gap statement.

## Status

| Item | Status |
|---|---|
| Data gate (usable moisture contrasts exist) | Advanced |
| Earlier Selma fitting had contrast | **No** (training episodes had none) |
| Shared, transferable within-station moisture relationship | **Not established; fails transfer** |
| Station-level moisture coefficients | Constrained individually, heterogeneous in sign; cause unknown |
| Justification for GP / spline / PINO | **None from this evidence** |
| Literature gap | Open; coupled AI soil-thermal inference is existing work |
