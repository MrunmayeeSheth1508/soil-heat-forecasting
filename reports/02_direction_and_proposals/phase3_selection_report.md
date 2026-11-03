# Phase 3 selection report: Directions A, B and C

Companion files: [literature comparison](phase3_literature_comparison.md), [pilot report](phase3_pilotA_report.md). Rules and code are in `scratch/soil/phase3/` (`event_rules.md` frozen before any count). **No model was fitted during selection.**

## 1. Event inventory

**Data:** 39 audited USCRN stations, hourly, **2012-2021** (2022 onward not downloaded), local standard time. Files: `event_inventory.csv` (one row per hot spell, three rule variants, with dryness, coverage, recovery status), `station_flags.csv`, `historypairs_B.csv`, `event_summary.txt`.

**Independent counts (primary rules: hot day at or above local P90; at least 3 hot days; dry = at most 5 mm rain and moisture at or below local P40):**

| Step | Sequences | Synoptic clusters |
|---|---|---|
| Hot spells (all) | 1,802 | n/a |
| Hot-dry episodes | 490 | 191 |
| + no hot spell in the preceding 21 days | 306 | 148 |
| + no freezing | 244 | 128 |
| + not interrupted within 21 days | 164 | 101 |
| + at least 80% data coverage = **complete sequences** | **156** (38 stations) | **95** |
| + wetting day of at least 10 mm in follow-up | 104 | 68 |
| + shallow moisture rise detected / deeper too | 101 / 51 | n/a |

Strict (P95, 4 days) gives 61 complete sequences; relaxed (P85) gives 135. 100 of the 156 are in May-September. Different stations in the same heat wave are one cluster, so **95 clusters, not 156**, is the effective event count across stations.

**Quality and coverage flags (from `station_flags.csv`):**
- **Sensor history:** the public product has no sensor-type field. The logger version changes at a median of 4 times per station (maximum 14). **25 of 39 stations** show a step above 0.1 m3/m3 between consecutive 90-day blocks of the moisture anomaly; this could be climate or an instrument change and cannot be separated here.
- **Stuck moisture:** longest constant 10 cm moisture run is 231 h at Port Aransas, 102 h at Montrose, 88 h at Dinosaur; most stations are under 40 h.
- **Soil properties:** 27 of 39 stations are in the Wilson table; 15 have bulk density at 5/10/20 cm (14 after excluding Elgin); 102 of the 156 complete sequences are at Wilson stations. Porosity is **estimated** (assumed particle density 2.65).
- **Thermal recovery rule is weak at depth:** the anomaly at 100 cm often barely exceeds the recovery threshold (35% of sequences have a 100 cm peak at most 1.5 times the threshold), so "recovered" at 100 cm is partly a threshold effect. The pilot therefore uses half-decay and fitted diffusivity, not that rule, for interpretation.
- **Climatology** includes the event year (an event-definition choice).

## 2. Comparison

### Direction A: heat penetration and recovery

| Item | Evidence |
|---|---|
| Scientific importance | How far into the soil, and for how long, hot-dry weather reaches, and whether rain changes underground heat transfer. Consequences for roots and microbes are **not measured** here. |
| Data support | 156 complete sequences, 95 clusters; 104 with wetting (68 clusters). Anomalies of 1-4 C (peak) against a 0.1 C reporting step. Observed temperatures at 5, 10, 20, 50 and 100 cm, plus air temperature, rain and radiation. |
| Candidate innovation | Event-scale, in-situ test with observed boundary temperatures. The closest papers use reanalysis and climatological statistics (Bai 2026; Gu 2026) or shallow in-situ layers (Garcia-Garcia 2023). One closely related Tibetan field-scheme paper (Geoderma 2021, 115330) is unread, and Gu et al.'s results section was not read in detail. |
| Competing explanation | Stronger or different surface forcing; rain arriving with cooling fronts; frequency content of the forcing and soil layering giving different effective diffusivity in different windows; infiltration heat transport; sensor error. |
| AI role | None at this stage. The question is whether a conduction model with observed boundaries explains the response. A learner would be justified only if that model fails in a repeatable, structured way. |
| Smallest test | Pre-registered paired comparison of fitted effective diffusivity in a stress window vs a post-wetting window (with matched no-wetting windows as control), on development and test events. Proceed if the contrast is at least 0.15 in ln units with an interval excluding zero in both. (Run; see the pilot report.) |

### Direction B: history-dependent response

| Item | Evidence |
|---|---|
| Scientific importance | If drying or wetting history matters, models using only current moisture would be biased after dry-wet transitions. Laboratory work shows conductivity is higher after drying than after wetting at equal water content (Xu 2020; Peng 2025); field relevance is unknown. |
| Data support | 582 matching cells (same 0.03 m3/m3 moisture bin, 3 C temperature bin, season) with at least 2 independent episodes in each of a low-history and a high-history class, across 38 stations (73,360 eligible days). These are feasibility counts of **dependent** cells, not independent events. |
| Candidate innovation | No field test of history dependence of heat propagation was found. The one machine-learning history paper I could check (Li 2021, ten FLUXNET sites) was compared only with ML baselines, with no mention of initial conditions. The search was thin. |
| Competing explanation | History as a proxy for unmeasured deeper conditions, water redistribution, season or sensor drift; ordinary diffusion already carries memory through the initial temperature profile, so any learned model must not be given information withheld from the baseline. |
| AI role | Concrete (a sequence model on antecedent summaries) but not justified before a fair physical comparator is fitted. An explicit-history regression is a strong competitor. |
| Smallest test | Same physical model, same initial profile and boundaries; compare residuals between low- and high-history matched cells, then add predefined history summaries. **Not run.** It also needs the effective-diffusivity machinery that Direction A just showed identifies in only about 60% of windows. |

### Direction C: soil and vegetation recovery mismatch

| Item | Evidence |
|---|---|
| Scientific importance | High: vegetation recovery matters for water and carbon. But greenness is not photosynthesis, and carbon or evaporative-cooling claims need flux observations. |
| Data support | **No vegetation or flux observation exists at the stations.** Land cover (MCD12Q1, 2019, 5 x 5 pixels of 500 m, a ~2.3 km window around the 2-decimal station coordinate): grassland 16, savanna 5, woody savanna 4, cropland 5, crop mosaic 2, evergreen needleleaf 2, deciduous broadleaf 2, other 3. **Only 21 of 39 stations have at least 80% of the window in the central class** (median 0.84); 87 of 156 complete sequences are at those stations. MOD13Q1 NDVI is 250 m, **16-day** composites: for 10 events at 6 stations there were 52 composites, with **1-2 composites inside the 21-day follow-up**; center-pixel reliability flags were good (fraction 1.00) and the 9 x 9 NDVI spatial SD was 0.066. Finer products exist (4-day LAI, 8-day LAI/GPP/ET, daily reflectance) but were **not tested**, and GPP and ET there are model products. AmeriFlux co-location was **not checkable**: the site-list request failed. |
| Candidate innovation | Established qualitatively: recovery in flux data takes months (4.1-6.7 months across 118 towers, Shao 2024). A soil-vs-greenness difference of days or weeks is essentially guaranteed by sampling and not a finding. |
| Competing explanation | Atmospheric demand, phenology, land cover (mixed pixels at half the stations), disturbance, composite compositing artefacts. |
| AI role | None. |
| Smallest test | Would need daily or near-daily vegetation or flux data at sites colocated with soil sensors. None identified. **Not run.** |

## 3. Selection

**Direction A was selected on Phase 1 evidence, before any fitting:** the strongest data support (95 independent clusters, signals 10-40 times the reporting step), an unresolved but narrow question, and a conventional comparison that can be decided. B has weaker evidence of a measurable effect and a stack of confounders; C lacks the observations.

**B and C are not killed but not supported now.** B could be revisited if A's machinery is extended to more events; C needs different data.

**The pilot (see pilot report) then gave a suggestive, unconfirmed result.** Recommendation: **reframe**, not proceed to AI. The innovation is **modest**: the penetration pattern is already established, and the rain-linked effect is not yet confirmed.
