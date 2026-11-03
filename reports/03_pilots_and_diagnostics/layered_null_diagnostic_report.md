# Layered-column null diagnostic: can unchanged soil layers create the rain-linked contrast?

**Task source:** sections 17-18 of the updated synthesis. **Frozen before any simulation:** [layered_spec_frozen.md](file:///C:/Users/jtani/.gemini/antigravity/scratch/soil/phase3/layered_spec_frozen.md) (with three dated addenda). **Everything marked SIMULATED is model output, never a measurement, and was not used as training data.** No new downloads and no AI fitting were used.

## 1. Bottom line

**Within the frozen, core-based family, fixed-property layers did not reproduce the observed contrast.** The observed rain-linked contrast was +0.142 (development) and +0.141 (test) log units. SIMULATED contrasts for the same events and windows were:

| Column (all SIMULATED, fixed properties, noise-free) | Development contrast [95% cluster bootstrap] | Test contrast [95% cluster bootstrap] |
|---|---|---|
| U: uniform control | 0.000 | 0.000 |
| G_low: generic two-layer, upper layer less diffusive | +0.007 [-0.025, +0.042] | -0.030 [-0.091, +0.039] |
| G_high: generic two-layer, upper layer more diffusive | -0.022 [-0.050, +0.004] | +0.035 [-0.028, +0.083] |
| S central: station cores, three layers | -0.040 [-0.101, +0.012] | -0.010 [-0.096, +0.063] |
| S, dry reference moisture | -0.088 [-0.163, -0.020] | -0.030 [-0.175, +0.095] |
| S, wet reference moisture | -0.059 [-0.134, +0.002] | -0.020 [-0.083, +0.027] |
| S, heat capacity and particle density low / high | -0.079 / -0.056 | -0.011 / -0.025 |

Across all columns, runs and selection rules the simulated contrast ranged from **-0.15 to +0.04** and was never at or above +0.05. By the rule frozen in advance (at least 0.10 in both periods counts as "reproduces"), the answer is **does not reproduce**.

- **What this weakens:** one competing explanation, namely that fixed layered soil alone creates the apparent change in a uniform effective diffusivity.
- **What it does not do:** it does not confirm that rain causes the change, and it does not exclude water advection, evaporation, sensor effects or layering stronger than the cores imply (see section 6).
- **Also found:** the observed contrast is itself fragile to which events are kept (section 5), so the "lead" is weaker than the headline numbers suggest.

![Observed and simulated contrasts](C:/Users/jtani/.gemini/antigravity/brain/d895d91a-33a5-49bd-8d56-6a58ee64f9a6/layered_comparison.png)

*Figure: left and centre, contrast by column for development and test. SIMULATED columns are squares with bootstrap intervals; the OBSERVED archived contrast is the black line with its grey interval. Right, sensitivity of the SIMULATED contrast to run, selection and numerics (circles development, open triangles test).*

## 2. Step 1: baseline reproduction (archived results and exclusions)

- All frozen outputs were archived with hashes (`archive_pre_diag/MANIFEST.tsv`), and **the originals are unchanged** (hash re-check passed).
- The original pilot code, run unchanged with outputs redirected, reproduced every archived output **byte-for-byte** for development and test: summary text, trajectory table, window fits and formulation table.
- A verbatim copy of the estimator in my new module reproduced the archived event-level best-fit diffusivities and identification decisions: **85 of 85 development and 37 of 37 test events, 0 mismatches.**
- Development/test separation is as archived (start year 2012-2018 vs 2019-2021).

**Attrition (from the archived event-level files):**

| | Development | Test |
|---|---|---|
| Complete sequences (wetting / no wetting) | 113 (76 / 37) | 43 (28 / 15) |
| Dropped, post-window shorter than 7 days | 20 | 1 |
| Dropped, more than 10% missing | 8 | 5 |
| Usable (wet / control) | 85 (51 / 34) | 37 (23 / 14) |
| Identified in both windows (wet / control) | 53 (33 / 20) | 21 (12 / 9) |
| Not identified: stress window / post-or-control window / either | 30 / 21 / 32 | 15 / 8 / 16 |
| **Stress and post windows overlap** | **14 of 85 usable (all wetting)**; 10 among identified | **4 of 37**; wetting events |
| Clusters (usable / identified) | 56 / 41 | 24 / 14 |

**Cluster implementation:** events sorted by start date, with a new cluster whenever the gap to the previous event at any station exceeds 3 days (chained, no distance limit). Median 1 event per cluster; at most 5 events and 5 stations per cluster; longest chained span 7 days. These are operational time groups and do not guarantee independence.

**One discrepancy to note:** re-bootstrapping the observed contrast in my analysis gives development [-0.010, +0.284] and test [-0.154, +0.428], against the archived [0.002, 0.277] and [-0.143, 0.433]. The point estimates are identical. The difference is resampling noise (about 0.01) from a different random-number sequence; it means the development interval's exclusion of zero is **marginal**. The figure uses the archived intervals.

## 3. Step 2: layered solver and its verification

Conservative finite-volume solver: C(z) dT/dt = d/dz (k(z) dT/dz), with conductivity and heat capacity specified separately; flux and temperature continuous across interfaces by construction (`layeredsolver.py`; results in `layered_verification_out.txt`).

| Check | Result |
|---|---|
| Uniform limit equals the existing solver (also as three identical layers) | difference 9e-14 C (limit 1e-8) **PASS** |
| Uniform periodic analytic solution, 24 h | amplitude errors 0.01-2.5% at base, 0.01-0.5% refined; phase under 0.06 h **PASS** |
| Two-layer periodic analytic solution, interface between nodes, k ratio 0.5 and 2, C ratio 0.5 and 2 | **refined: amplitude at most 0.73%, phase at most 0.013 h, PASS. Base: amplitude 3.49% in one extreme case (limit 3%), FAIL** |
| Interface flux versus analytic | within 1.8% (refined) and 1.6% (base); limit 3% **PASS** |
| Steady state, three layers | flux spread 7.5e-13, profile error 5e-14 C **PASS** |
| Grid and time-step convergence | RMS error 0.0121 C (38 intervals, 1 h), 0.0025 C (76 intervals, 900 s), 0.0008 C (152, 900 s) **PASS** |

**Logged corrections:**
- The first run of my check had a sign error in the phase comparison (the criteria were unchanged).
- The base resolution narrowly failed one criterion. I chose the **refined resolution (76 intervals, 900 s) for the SIMULATED data generator** from the verification results alone, before any contrast existed (Amendment B). The base resolution is reported as a numerical sensitivity. The original estimator keeps its own discretisation unchanged.
- **Numerical error floor:** about 0.002 C (refined) against the analytic solution. Differences in the contrast smaller than the effects measured in section 4 (at most 0.01) should not be interpreted.

## 4. Steps 3-5: the frozen columns, and what they produce

**The family** (rules in the spec; values computed only from Wilson probe-site cores and 2012-2018 moisture, hash 5a3589e2...; `columns_frozen.csv`):
- **U:** one uniform layer, alpha 4.58e-7 m2/s (nearest grid value to the archived development median), with 2e-7 and 1e-6 sensitivities.
- **S:** three layers (5-20, 20-50, 50-100 cm) from each station's cores with Johansen conductivity and mixture heat capacity at a fixed reference moisture, plus identified-range variants. **15 of the 38 event stations qualify** (13 with development events). 11 stations lack usable bulk density at 5-20 cm (Selma, Champaign, Muleshoe, Goodwell 2 E, Pierre, Manhattan and others) and 12 are absent from the Wilson table.
- **G_low / G_high:** generic two-layer columns whose layer ratios are the 10th and 90th percentiles of the development S columns.

**An important property of the family:** it is only **weakly layered**. In the S columns, conductivity and heat capacity vary together, so diffusivity is nearly uniform with depth: median 5.2e-7, 5.2e-7 and 5.1e-7 m2/s in the three layers. The generic columns have upper-to-lower diffusivity ratios of 0.83 and 1.39. This is a finding from the core evidence, not a design choice, and it shapes the result.

**Apparent change in uniform diffusivity under fixed properties (all SIMULATED):**
- The uniform control produced **exactly zero** contrast and zero event-level change, so the estimator and initialisation do not create a contrast on their own.
- The layered columns produced small event-level changes: median 0.06 log units (one grid step is 0.058), 90th percentile 0.09-0.17, maximum 0.29. The observed identified events change much more: median 0.17 (development) and 0.23 (test), SD 0.27 and 0.32, against 0.06-0.10 simulated. **Fixed layering can explain a small part of individual-event changes, but not a group difference.**
- Event-level simulated changes depend on the change in the forcing between windows. For the generic columns the Spearman correlation with the change in the T5-T100 gradient was -0.65 and +0.33 (development), -0.71 and +0.42 (test), and the sign depends on which way the layering goes. These effects cancel in the wet-minus-control contrast because both groups have similar forcing changes on average.

**Sensitivity of the SIMULATED contrast (columns U, G_low, G_high, S central):**

| Variation | Largest change in contrast |
|---|---|
| Base grid (38 intervals, 1 h) instead of refined | 0.004 development, 0.003 test |
| Output rounded to 0.1 C | 0.009, 0.010 |
| First 24 h excluded instead of 6 h (initialisation) | 0.010, 0.007 |
| Events identified in the simulated pair vs the **observed** identification | up to 0.04 for S central (2 controls in development, 7 in test, unstable); 0.03 for G |
| All usable events | none (the simulated screen keeps 100%, so this equals the simulated selection) |

**The identification screen** passed **100% of simulated cases** (interval widths 0.06-0.12 against a limit of 0.6), against 62% (development) and 57% (test) of the real windows. So noise-free simulation cannot reproduce the selection effect of the screen. Simulations on the exact set of events the real screen kept are given in the "observed identification" selection and also show no contrast.

**Small-sample caveat:** the S columns exist for only 25 development events (19 wetting, 6 control) and 23 test events (13 / 10). On that subset the observed contrast is +0.126 and +0.100, so the comparison is like for like, but with 6-10 controls the intervals are wide.

## 5. The observed contrast is selection-fragile (exploratory, post hoc)

Descriptive recomputation from the archived observed outputs (no new fits; not in the frozen spec; `observed_selection_checks.txt`):

| Selection of the OBSERVED events | Development contrast | Test contrast |
|---|---|---|
| Identified in both windows (archived rule) | +0.142 | +0.141 |
| All usable events | +0.149 [-0.052, +0.336] | **-0.223** [-0.570, +0.213] |
| Identified, stress and post windows not overlapping | +0.181 [+0.020, +0.327] | +0.227 [-0.034, +0.482] |
| Events **not** identified | +0.191 | **-0.835** [-1.394, -0.315] |

- Overlap of the two windows does not create the effect; removing overlapping pairs increases it.
- In the test period, however, the contrast flips sign when unidentified events are included, because unidentified windows have much larger changes (median 0.64 against 0.23). The positive test contrast depends on the identification screen retaining only 21 of 37 events (12 wetting, 9 control).
- Together with the wide test interval, this makes the "reproducible positive point estimate" less secure than it appeared.

## 6. What this does and does not decide

| Question | Answer |
|---|---|
| Do plausible fixed-property layers, within this family, reproduce the contrast? | **No** (simulated -0.15 to +0.04 against +0.14). |
| Does that confirm rain-driven change in soil properties? | **No.** Rain causality is unconfirmed. Not excluded: water advection, evaporation and vapour transport, sensor and moisture-sensor effects, lateral heterogeneity, and selection effects in the real data. |
| Could stronger layering do it? | **Not tested** by design. The core evidence implies nearly uniform diffusivity (layer values within 3%), so a column with strongly contrasting diffusivity (for example a dry crust or an organic layer) would be an assumption not supported by these cores. Bounding the largest contrast any layering could produce is a model-form search and was explicitly excluded. |
| Reading the original claim | The observed rain-linked change is **not diagnostic of moisture-dependent material behaviour**, but the diagnostic also does not show it is *not* an effective-model artefact of some other kind; the observed contrast is fragile (section 5). |

**Limits:** the family is exploratory and supplies no probability distribution; layer assumptions beyond the cores (interfaces, heat capacity, particle density, quartz-as-sand, coarse/fine threshold) are flagged assumptions; the noise-free generator does not exercise the identification screen; 25 and 23 events exist for the core-based columns; the estimator's log-diffusivity grid has a step of 0.058, so contrasts below about 0.03 are within quantisation.

## 7. Test-set log (what touched the 2019-2021 data in this task)

1. Baseline reproduction: the original pilot was rerun once for test (deterministic; byte-identical to the archive).
2. The diagnostic test analysis ran **once** (marker `layered_test_RUN_ONCE.marker`: "the original test results (contrast +0.141) were already known when this diagnostic was designed").
3. Exploratory post-hoc recomputation of selection-dependence on archived observed outputs (section 5). It is descriptive and not part of the frozen decision.

## 8. Suggested next step (not done)

A **separately frozen extension to genuinely new wetting events**: the 92 unused stations and the 2009-2011 data, with the identification screen and a pre-registered rule that reports all events, including unidentified ones. No flexible fitting. A layering-strength bound would be a separate decision if you want one.

## Files (`C:\Users\jtani\.gemini\antigravity\scratch\soil\`)
Frozen spec: `phase3/layered_spec_frozen.md`; columns: `phase3/columns_frozen.csv`, `columns_frozen_summary.txt`; verified solver: `layeredsolver.py`, `48_layered_verification.py`, `phase3/layered_verification_out.txt`; estimator copy: `pilotA_estimator.py`; engine: `46_layered_diagnostic.py`; event-level outputs: `phase3/layered_event_level_all.csv`, `layered_events_{dev,test}.csv`, `layered_windows_{dev,test}.csv`; summary tables: `phase3/layered_summary.txt`, `layered_contrasts.csv`, `layered_extra_stats.txt`, `observed_selection_checks.txt`; baseline reproduction: `phase3/repro/repro_comparison.txt`; archive: `phase3/archive_pre_diag/`; figure: `phase3/layered_comparison.png`.
