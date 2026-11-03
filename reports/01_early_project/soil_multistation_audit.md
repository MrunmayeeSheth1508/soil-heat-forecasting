# Soil Heat: Multi-Station Contrast Audit (before any AI fitting)

Scripts: `soil/13_multistation_download.py`, `soil/14_contrast_audit.py` (criteria fixed in its header before results), `soil/15_coverage.py`.
Outputs: `audit_out.txt`, `coverage_out.txt`, `audit_station_table.csv`, `audit_dry_days.csv`.

## Data

USCRN hourly02, all lower-48 stations, 2019-2021: 131 stations, 393 station-years requested. Kept soil temperature (5 depths), soil moisture (5 depths), precipitation.

**Dry informative day** (local standard time): all 24 hours valid for T5, T10, T20 and 10 cm moisture; no temperature at or below 1 C; 5 cm diurnal amplitude of at least 1 C; precipitation of 1 mm or less that day and the day before.
Per day: theta = mean 10 cm moisture, Tin = mean of (T5 + T20)/2 (boundary temperatures only, same input as the model).

## Result 1: how many stations have usable contrast

| Item | Count |
|---|---|
| Stations with 30 or more dry informative days | 89 |
| Stations meeting the pre-specified rule (200+ dry days, 3+ two-state bins, residual moisture SD after temperature + season of 0.03 or more, sane sensor) | **39** |
| Within-site day pairs at the same 1 C temperature with moisture differing by 0.10 or more | 52,337 over 39 stations (heavily dependent; not an effective sample size) |

A two-state bin is a 3 C temperature bin with at least 5 days in the station's driest quarter and at least 5 in its wettest quarter.

## Result 2: different climates do not reverse the confound

Within-site correlation of theta and Tin on dry informative days, all 89 stations:

| r range | Stations |
|---|---|
| below -0.5 | 48 |
| -0.5 to -0.2 | 34 |
| -0.2 to +0.2 | 7 |
| above +0.2 | **0** |

Every climate in the network has wet-means-cool on dry days. No station has the opposite sign, so pooling sites cannot cancel the confound by sign.

Pooled over the 39 qualifying stations with site means removed: **r = -0.44** (variance inflation 1.24), against **-0.61 at Selma** (2019-2021 dry days, variance inflation 1.59). Pooling reduces collinearity modestly; it does not remove it.

Caveat: excluding rain days may remove warm-wet days (for example summer monsoon). That was a deliberate choice to limit infiltration heat transport, and it may bias this sign count.

## Result 3: Selma passes the contrast rule but samples the wrong moisture range

Selma qualifies (6 two-state bins, 12 to 30 C). **So within-site contrast at matched temperature existed at Selma, yet the rerun could not identify a moisture effect.** The contrast rule alone does not predict identifiability.

What distinguishes Selma is its moisture range. On dry informative days:

| | 5th percentile theta | 95th percentile theta |
|---|---|---|
| Selma | 0.277 | 0.539 |
| Qualifying stations, range of 5th percentiles | 0.017 to 0.277 | |

Selma is the **wettest** of the 39 qualifying stations and never drops below about 0.28. **28 of 39 qualifying stations reach theta below 0.15.**

Expectation, not tested here: soil thermal diffusivity is commonly reported to rise steeply from dry to moderately moist soil and to flatten or decline near saturation. If so, Selma sampled the range where the moisture effect should be smallest. This is a hypothesis for the next step, not a finding. The position of that plateau depends on texture, which I have not checked.

## Result 4: pooled coverage of moisture at fixed temperature

Across qualifying stations, every 3 C bin from 3 to 27 C contains 20 to 39 stations and spans 10 cm moisture of roughly 0.05 to 0.40. The joint (moisture, temperature) space is well covered between stations. Most of that span is **between-site**, so it carries site effects (texture, vegetation, sensor installation) unless a site term absorbs them.

## Data-quality flags (not yet resolved)

- Some stations report 10 cm moisture near 0.02 (Port Aransas 5th percentile 0.017; Yosemite 25th percentile 0.042). These may be real sandy soils or sensor problems. Needs a per-station check.
- Selma's 95th percentile of 0.54 is high for mineral soil and may reflect calibration.
- Soil texture and bulk density per station not retrieved yet. They are needed as the "site characteristics" in the matched model pair.
- Same 0.1 C reporting resolution and multi-probe aggregation at every station.

## Literature check

The research subagent was blocked from network access and returned unverified leads only. I fetched one paper directly.

| Paper | Status |
|---|---|
| Huang, Heaney, van Reeuwijk 2026, GMD 19, 8801 | Abstract read: physics-based forward model in an ML library, no training; synthetic soil temperature plus one urban flux tower; two depths needed; latent and sensible heat not separable; no subsurface moisture model |
| Peng et al. 2024, Random forest approach to estimate soil thermal diffusivity, Soil & Tillage Research, DOI 10.1016/j.still.2024.106233 | **Exists** (reference verified by you from publisher record). Full methods not yet read by me |
| Xie et al. 2024, Simulating field soil temperature variations with physics-informed neural networks, Soil & Tillage Research 244, 106236 | **Exists** (verified by you). Full methods not yet read by me |
| Wang et al. 2023, Multiphysics-informed neural networks for coupled soil hydrothermal modeling, DOI 10.1029/2022WR031960 | **Exists** (verified by you). Per your reading of the primary text, it uses moisture observations to improve temperature modelling and thermal-conductivity estimation |

**Correction:** my earlier "not found / possibly fabricated" labels were wrong. The other environment could not reach the sources; that was an access failure, not evidence about the papers. Coupled AI inference of soil thermal relationships from moisture and temperature observations is existing work (Wang 2023). No gap can be claimed until the full methods of all three are compared with this design.

## Verdict for this gate

| Question | Answer |
|---|---|
| Are there stations with contrasting moisture at overlapping temperatures? | **Yes**, 39 stations, and 28 of them reach dry soil that Selma never samples |
| Do different climates break the moisture-temperature confound? | **No by sign** (0 of 89 positive); **modestly by magnitude** (pooled -0.44 vs -0.61) |
| Is contrast at matched temperature sufficient for identifiability? | **No.** Selma had it and failed |
| Is a small probabilistic relationship inside the solver now justified? | **Conditionally.** Only for a design that includes stations reaching dry soil and holds out whole stations |

## Proposed next step (needs your decision)

1. Resolve the data-quality flags and retrieve per-station soil texture (USCRN site soil characterisations).
2. Pre-register a stratified set of about 12 to 16 stations: half reaching theta below 0.15, half always moist, spread across climates.
3. Conventional baseline first: within the 5-20 cm solver, compare (temperature + site term) against (temperature + site term + moisture), each with the existing log-linear form. Hold out whole stations and a final untouched period.
4. Only then replace the log-linear moisture term with a small Gaussian-process function of moisture (and temperature), fitted through the solver with site terms, and test whether it transfers to held-out stations better than the log-linear form.
