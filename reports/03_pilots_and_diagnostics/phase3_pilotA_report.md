# Direction A pilot: heat penetration, and rain-linked change in propagation

Design frozen in `phase3/pilotA_prereg.md` before fitting (plus two dated notes). Scripts: `39_pilotA_solver_check.py`, `40_pilotA_run.py`. Outputs: `phase3/pilotA_out_dev.txt`, `pilotA_out_test.txt`, `pilotA_part{1,2,3}_{dev,test}.csv`. Conditional reconstruction only, never forecasting. **No AI was run.**

## 1. Events and design

- **Event inventory:** 39 audited USCRN stations, hourly data 2012-2021 (2022 onward not downloaded). Rules are in `phase3/event_rules.md`, written before any count. Hot day = daily maximum air temperature at or above the local day-of-year P90; hot spell = at least 3 hot days (gaps of up to 2 days merged); dry = at most 5 mm rain from 7 days before the spell through its end, and half the spell days with 10 cm moisture at or below local P40.
- **Counts (primary rules):** 1,802 hot spells; 490 hot-dry episodes (191 synoptic clusters); **156 complete sequences** (95 clusters) after requiring a clean pre-window, no freezing, no interruption by another spell, and at least 80% data coverage; 104 of these have a wetting day (68 clusters); 100 fall in May-September. Stricter and looser definitions give 61 and 135 complete sequences.
- **Split:** development = start year 2012-2018 (113 sequences, 69 clusters, 36 stations); test = 2019-2021 (43 sequences, 26 clusters, 27 stations), analysed **once**.
- **Solver check (before any event data):** uniform conduction, 5-100 cm, Crank-Nicolson. Against the analytic periodic solution at a 24 h period, amplitude errors were 0.1-2.5% (largest where the amplitude is weak, at low alpha and depth) and phase errors under 0.06 h; refinement changed the 20 cm amplitude by under 0.5%. **PASS** (acceptance: 3% amplitude, 0.3 h phase). This is a uniform-diffusivity solver, so it verifies the numerics, not that real soil is uniform.

## 2. Part 1: trajectories (descriptive)

Anomaly = daily soil temperature minus the local day-of-year median. Medians with cluster-bootstrap 95% intervals.

| Depth | Peak anomaly, development (C) | Peak anomaly, test (C) | Peak delay from spell start, dev / test (days) | Half-decay after peak, dev / test (days) |
|---|---|---|---|---|
| 5 cm | 3.8 [3.5, 4.3] | 3.9 [3.2, 4.6] | 4 / 4 | 2 / 3 |
| 10 cm | 3.4 [2.9, 3.8] | 3.5 [2.8, 3.9] | 4 / 5 | 3 / 3 |
| 20 cm | 2.8 [2.2, 3.1] | 2.8 [2.2, 3.3] | 5 / 6 | 3 / 2 |
| 50 cm | 2.1 [1.5, 2.3] | 1.9 [1.6, 2.1] | 6 / 7 | 4 / 3 |
| 100 cm | 1.3 [1.0, 1.6] | 0.9 [0.5, 1.3] | 9 / 8.5 | 4 / 4 (23% / 8% censored) |

- **Penetration is large and clean:** the warm anomaly shrinks about threefold (development) to fourfold (test) from 5 to 100 cm and arrives about 4-5 days later at 100 cm. These anomalies are roughly 10-40 times the 0.1 C reporting step. This pattern is **expected from conduction and already established at climatological scale** (Bai et al. 2026); the contribution here is that it is measured event by event, in situ.
- **Persistence:** the anomaly at depth falls to half its peak within about 2-4 days of the peak. At 100 cm, 23% of development events never reach half-decay within the window (censored), so persistence there is a lower bound.
- **Anomaly burden** (degree-days above the day-of-year median, **not heat energy**): 5 cm 36 (dev) and 29 (test); 20 cm 30 and 19.
- **Forcing:** the 5 cm peak rises 0.41 C [0.31, 0.51] per C of mean Tmax anomaly in development, 0.28 [0.12, 0.45] in test. Surface forcing explains part of the shallow response.
- **Wetting vs no wetting, and moisture or clay strata:** no difference distinguishable. Intervals span zero (for example median 20 cm burden: -4.3 [-18.8, +5.9] dev; -6.9 [-12.3, +8.3] test). Higher-clay minus lower-clay 20 cm peak: -0.03 [-0.9, +0.8] dev; +0.65 [-0.3, +1.7] test. **No soil-property effect on penetration or persistence is detectable** with 26-69 clusters.

## 3. Part 2: propagation, with observed boundaries

For each hot-dry sequence, an effective diffusivity alpha was fitted in two windows: the stress window and a later window (10 days after the wetting day, or a matched no-wetting window). The 5 cm and 100 cm temperatures are observed boundaries throughout, so a change in alpha reflects the transfer between those boundaries, not a change in surface forcing. Windows were kept only if alpha was identified (interior optimum, 68% interval width at most 0.6 in ln alpha).

| | Development | Test |
|---|---|---|
| Usable sequences | 85 of 93 | 37 of 42 |
| Both windows identified | 53 (41 clusters) | 21 (14 clusters) |
| Wetting / no-wetting identified | 33 / 20 (27 / 18 clusters) | 12 / 9 (9 / 6 clusters) |
| Median alpha, stress and later window | 4.6e-7 and 4.9e-7 m2/s | 4.6e-7 and 4.6e-7 m2/s |
| Median RMSE (identified windows) | 0.22 C, 0.21 C | 0.28 C, 0.21 C |
| Mean change in ln alpha after wetting | +0.136 | +0.083 |
| Mean change without wetting | -0.006 | -0.058 |
| **Contrast (all seasons)** | **+0.142 [+0.002, +0.277]** | **+0.141 [-0.143, +0.433]** |
| Contrast, May-Sep | +0.234 [+0.053, +0.386] (21 / 9 events) | +0.189 [-0.072, +0.666] (6 / 4 events) |
| Contrast under the 5 error scenarios | +0.142, +0.180, +0.143, +0.168, +0.144 | +0.141, +0.144, +0.134, +0.128, +0.165 |
| Stations with at least 2 wetting events, share with positive change | 10 stations, 0.70 | 2 stations, 0.50 |

**Reading it:**
- In development, effective diffusivity rose about 15% after rain compared with no change in matched windows without rain (about 26% in May-September). The direction and size were **the same point estimate (+0.14) in the test period**, and the sign held across all five persistent-error scenarios in both periods.
- **The pre-registered rule is not met.** It required a contrast of at least 0.15 with an interval excluding zero in **both** development and test. Development gives 0.142 (all seasons; just under 0.15, although its interval excludes zero) and 0.234 (May-September); the test interval includes zero and has only 9 wetting clusters (the rule's minimum is 20), so the test is underpowered rather than a refutation.
- **Verdict on Part 2: suggestive, not confirmed.** The effect is small relative to per-window uncertainty (single-window intervals up to 0.6 in ln alpha) and is visible only as an average over many events.

## 4. Part 3: does an established formulation explain the change?

Johansen scheme (Dai et al. 2019, section 2.1.1 equations 1-8) with Wilson probe-site bulk density and texture, estimated porosity (assumed particle density 2.65), de Vries heat capacity; compared with constant alpha (M0) and a shared log-linear moisture term (M_B, fitted by leave-one-station-out). No local calibration enters, because the quantity is a ratio.

| | Development (12 events, 9 stations; 11 in the main comparison) | Test (7 events, 6 stations) |
|---|---|---|
| MAE of change in ln alpha: M0 / M_B / M_J | 0.270 / 0.244 / 0.265 | 0.300 / 0.352 / 0.290 |
| Sign agreement: M_B / M_J | 0.64 / 0.45 | 0.57 / 0.57 |
| MAE(M0) - MAE(M_J) [95% interval] | +0.005 [-0.010, +0.018] | +0.010 [-0.019, +0.046] |

**The established formulation is indistinguishable from constant diffusivity here, and the comparison is badly underpowered** (7-12 events; the rule needs at least 20 clusters). Of 12 development events, 1 had observed moisture above estimated porosity. The result is not sensitive to the assumed solid heat capacity (1.8e6 to 2.4e6 J/m3/K) or to clipping relative saturation. The quartz-fraction proxy (sand fraction) and the coarse/fine threshold (50% sand) are assumptions I added, not parts of the published scheme.

## 5. What we learned about the physical system

- **Well measured:** event-scale heat penetration in situ: anomaly about 3.8 C at 5 cm and about 1 C at 100 cm, peak delayed about 4-5 days at depth, persistence of days. Conduction between observed boundaries reproduces interior temperatures to about 0.2-0.3 C where alpha is identified.
- **Suggestive:** rain-linked increase in effective propagation of roughly 15% (all seasons) to 20-25% (May-September), consistent in direction with wetter soil conducting heat better, not shown with certainty.
- **Not established:** that soil properties (clay, bulk density) or an established conductivity formulation explain differences between events or stations.

## 6. What remains ambiguous (competing explanations)

1. **Frequency content and layering:** the uniform-alpha solver sees different forcing in the stress window (strong, slow synoptic warming) and the later window (smoother). A layered soil would give different effective alpha for different windows with no change in material properties. The no-wetting control reduces, but does not remove, this.
2. **Infiltration advection and latent heat** in windows starting the day after rain; the equation neglects convective heat transport.
3. **Sensor moisture error and sensor changes:** not an issue for temperature-only Part 2; matters for Part 3 (moisture enters). 25 of 39 stations show a 90-day-block step above 0.1 m3/m3 in the moisture anomaly, and logger version changes occur at a median of 4 per station; climate and sensor effects cannot be separated here.
4. **Selection:** identified windows are 62% (dev) and 57% (test) of usable sequences; identification favours windows with strong signals.
5. **Climatology** includes the event year (an event-definition choice, not used in Part 2).

## 7. Did AI help?

**No AI was run, and nothing here shows a need for it.** The relationship a learner would capture is alpha as a function of moisture and soil state, and the data cannot even separate the established formulation from a constant. With 9-27 identified wetting clusters, a flexible model would fit noise.

## 8. Conclusion: **reframe**

- **Next scientific claim (if the same design is extended):** "In situ, during hot-dry events, effective underground heat transfer between 5 and 100 cm rises by roughly 15% after wetting rain, compared with no change without rain." It needs more independent events before it can be claimed: at least about 20 identified wetting clusters in each of development and test. That is feasible: only 39 of 131 audited-or-available USCRN stations and 2012-2021 were used; the earlier 2009-2011 data and the remaining 92 stations are unused.
- **Not recommended:** adding AI, or claiming a soil-property or formulation effect, until that is shown.
- **Do not describe** any of this as a tipping point, damage or loss of buffering. The measured quantity is an effective diffusivity change of about 15%, with wide uncertainty.
