# Identification-screen sensitivity: short diagnostic

Existing outputs only; no new downloads, model families or AI. The list of diagnostics was frozen before running ([ident_diag_spec_frozen.md](file:///C:/Users/jtani/.gemini/antigravity/scratch/soil/phase3/ident_diag_spec_frozen.md)). Everything here is **exploratory sensitivity**, not a replacement confirmation test, and makes **no rain-causality claim**. Observed quantities come from the archived fits; SIMULATED quantities from the fixed-column runs. Full numbers: `phase3/ident_diag_summary.txt`.

## Conclusion

**The screen is mainly a model-misfit screen. It does not isolate a clean physical regime, and over the full set of events estimator instability prevents a reliable group comparison.**

- The archived rule is re-derived exactly from the stored interval bounds (all 122 usable pairs), so the decisions are reproducible.
- Rejection tracks poor fit of the uniform-diffusivity model, not missing data or short windows (section 1).
- The negative all-event test contrast keeps its sign under every single-unit removal, but its **magnitude** is carried by a few unstable and grid-edge estimates (section 2).
- Within the retained events the development contrast is stable at +0.14 to +0.22; in the test period it is positive but imprecise, and it drifts to about zero as the cutoff loosens (section 3).
- On core-based stations specifically, the observed and simulated contrasts cannot be told apart (section 4).

## 1. Retained vs rejected pairs (descriptive, unadjusted, dependent data)

| | Development | Test |
|---|---|---|
| Usable / retained / rejected | 85 / 53 / 32 | 37 / 21 / 16 |
| Rejection rate: wetting / control | 0.35 / 0.41 | **0.48 / 0.36** |
| Rejected because unstable (width > 0.6) | 30 | 16 |
| Rejected with a grid-edge optimum or interval | 10 (6 optimum on the edge) | 4 (1) |

What differs between rejected and retained (medians; development, then test):
- **Window length and missingness: no difference** (length 192 vs 192 h and 216 vs 228 h; missing fraction 0 in both; all p above 0.2). They do not explain rejection.
- **Fit error:** RMSE at the best diffusivity 0.64-0.74 C vs 0.21-0.22 C (development), 0.54-0.68 vs 0.21-0.28 (test). Lag-1 residual correlation 0.93-0.95 vs 0.74-0.77. Effective sample size 7-9 vs 28-34.
- **Surface variability:** rejected windows have *more* of it: SD of T5 3.2-3.5 C vs 1.9-2.3 (development), and a higher diurnal-band variance fraction (0.78-0.84 vs 0.62-0.73). In the test period the differences point the same way but are not distinguishable (p about 0.2-0.8).
- **Season:** May-September share 0.81 vs 0.57 in development (unadjusted p 0.03); 0.62 vs 0.48 in test (p 0.51).
- **Station:** rejection clusters at stations. Never or rarely retained: Los Alamos 0/6, Wolf Point 0/5, Merced 0/4, Elgin 0/4, Goodwell 0/3. Always retained: Batesville 5/0, Avondale 5/0, Oakley 4/0, Pierre 3/0, Muleshoe 3/0, Buffalo 3/0.
- Interval width correlates with residual RMSE (Spearman +0.87) and lag-1 residual correlation (+0.82), with SD of T5 (+0.25) and diurnal fraction (+0.24), and not with window length (+0.06) or missingness (+0.03). A logistic regression of rejection on information and forcing variables gives SD of T5 the dominant coefficient (+1.4 per SD, p < 0.001) but pseudo R2 only 0.20. These are descriptive; the data are clustered and dependent.

**Reading:** the interval width is built from an effective sample size that shrinks as residual autocorrelation grows, so it works as a misfit screen. Rejected windows are those where a uniform 5-100 cm conduction column fits poorly, which happens more with strong diurnal surface forcing, in summer, and at particular stations.

## 2. Influence on the all-event contrast (variants reported; none chosen)

**Test, all usable events (n 37: 23 wetting, 14 control; 24 clusters): full contrast -0.223 [-0.578, +0.197].**

| Variant | Test contrast | Development contrast (full +0.149) |
|---|---|---|
| Leave-one-event-out range | -0.288 to -0.134, no sign change | +0.129 to +0.185 |
| Leave-one-cluster-out range | -0.329 to -0.120, no sign change | +0.119 to +0.191 |
| Remove top 1 / 2 / 3 / 4 / 5 events by |change| | -0.288 / -0.199 / -0.140 / -0.183 / -0.123 | +0.185 / +0.165 / +0.145 / +0.177 / +0.160 |
| **Remove every grid-edge estimate** (4 events test, 10 development) | **-0.037** | +0.177 |
| Remove only optimum-on-edge events (1 test, 6 development) | -0.164 | +0.173 |
| Retain only identified events (the archived rule) | **+0.141** | +0.142 |
| 10% / 20% trimmed means; median difference; Hodges-Lehmann | -0.203 / -0.204; -0.204; -0.233 | +0.195 / +0.189; +0.233; +0.175 |

- **The sign of the test all-event contrast is not produced by any single event or cluster.**
- **Its magnitude is dominated by a few unstable estimates:** 13 test events change by more than 0.5, and 11 of them are rejected windows; the five largest changes carry 55% of the squared deviation from the group means; removing only the four grid-edge events moves -0.223 to -0.037.
- Among the 16 rejected test events (11 wetting, 5 control) the contrast is -0.835 [-1.394, -0.315]. The largest influences are rejected windows with intervals of 1.3-2.2 ln units, for example Wolf Point 2020-08-17 (control, change +1.40) and Yosemite 2021-01-14 (wetting, change -1.28).
- Development behaves differently: positive and stable under every variant.

## 3. Contrast vs identification-width cutoff (EXPLORATORY)

![Contrast against cutoff, with event and cluster counts](C:/Users/jtani/.gemini/antigravity/brain/d895d91a-33a5-49bd-8d56-6a58ee64f9a6/ident_sweep.png)

- **Development:** +0.14 to +0.22 at every cutoff, +0.149 for all usable events. Interval lower bounds range from -0.02 to +0.07: zero is excluded at most cutoffs up to 1.5, and included at 0.6 (archived, -0.003), 2.0 and looser.
- **Test:** +0.05 to +0.21 for cutoffs of 0.8 or less, with only 4 / 4 to 16 / 10 events, then -0.06 to -0.01 for cutoffs of 1.0-3.0 and -0.22 for all usable events. **Every test interval includes zero.**
- **Pooled:** +0.16 to +0.19 at tight cutoffs (clusters 35-64), falling to +0.04 for all usable events (80 clusters), interval [-0.145, +0.211].
- The count panels show how the selection grows: retained clusters go from 7 to 24 in test and 28 to 56 in development as the cutoff loosens.

## 4. Same events, observed vs simulated (core-based stations only)

![Observed and simulated contrasts on identical events](C:/Users/jtani/.gemini/antigravity/brain/d895d91a-33a5-49bd-8d56-6a58ee64f9a6/ident_same_subset.png)

- **Population:** 15 core-based stations; 25 usable development pairs (19 wetting, 6 control) and 23 test pairs (13, 10). The earlier report compared uniform and generic columns on all events but core-based columns on this subset; here **all columns are evaluated on exactly the same events**.
- **Observed contrast on this subset** (development): +0.271 [-0.16, +0.66] all usable, +0.126 [-0.20, +0.48] identified (12 / 2). **Test:** +0.068 [-0.41, +0.53] all usable, +0.100 [-0.35, +0.49] identified (7 / 7).
- **SIMULATED contrasts** on the same events: uniform 0.000; generic two-layer -0.04 to +0.07; core-based -0.15 to +0.05 across variants and cutoffs.
- **The observed intervals (about +/-0.4) span both zero and every simulated value.** On the core-based population, the observed contrast and the fixed-column simulations are **statistically indistinguishable**. The earlier "does not reproduce" statement rests on the larger all-station populations and on point estimates; for the population with soil cores it is underpowered (2-10 controls).
- **Event level (Spearman, descriptive, n 23-25):** observed changes correlate with the fixed generic-layer simulated changes: G_low +0.33 (development) and +0.49 (test, p 0.02); G_high -0.36 and -0.56 (test, p 0.01). The two generic columns respond in opposite directions to forcing, so this says observed event-level changes partly track the same forcing-dependent estimator response that fixed layering produces.

## 5. Post-hoc forcing check (not in the frozen list; observed fits only)

- The observed change in ln alpha correlates negatively with the change in mean |T5-T100| between windows: development -0.38, test -0.47 (rejected windows -0.56 and -0.67).
- Wetting windows show larger drops in that gradient than control windows (development -0.29 vs -0.10; test -0.19 vs -0.05).
- Adjusting the wetting coefficient for the forcing changes lowers the development all-event contrast from +0.149 to +0.083 and the retained contrast from +0.142 to +0.112 (intervals include zero except the unadjusted retained development case); test all-event goes from -0.223 to -0.287 [-0.588, +0.013] and test retained from +0.141 to +0.114. **Part of the development contrast (roughly 20-45%) co-varies with forcing character**, though the adjustment does not remove it.

## Unresolved alternatives

1. **A real physical regime in the rejected windows** (dry crust, layering stronger than the cores imply, vapour or latent heat in summer, mostly May-September) where uniform conduction fails. Comparing groups there would need a different model; the diagnostic cannot say.
2. **Station-level installation or heterogeneity effects** (Los Alamos, Wolf Point, Merced, Elgin are essentially never retained) rather than hydroclimate.
3. **A genuine rain-related difference inside the rejected subset** (the -0.835), or noise, or advection: not separable here.
4. **Forcing-character confound** (the gradient change), shown above to account for part of the development contrast.
5. **Selection by group:** rejection rates differ between wetting and control windows in the test period (0.48 vs 0.36), which can shift the retained contrast.
6. **Power:** the test period (and the core-based subset) is too small to discriminate.
7. Sensor and moisture-calibration effects are not addressed by this diagnostic.

## Notes and log
- Window descriptors (missing fraction, SD of T5, mean T5) were computed from the hourly files already on disk; no fitting was redone. The 2019-2021 data were re-examined descriptively, in addition to the three touches logged previously. Both the width sweep and the forcing check are exploratory and were not preregistered decisions.
- Files (`C:\Users\jtani\.gemini\antigravity\scratch\soil\phase3\`): `ident_diag_summary.txt`, `ident_diag_pairs.csv` (event-level covariates and flags), `ident_sweep.csv`, `ident_same_subset.csv`, `ident_diag_extra.txt`, figures `ident_sweep.png` and `ident_same_subset.png`; scripts `52_ident_diagnostic.py`, `53_ident_diag_extra.py`.

**Stopped here, as requested.**
