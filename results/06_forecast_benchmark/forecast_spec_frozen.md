# Forecasting-feasibility study (Direction A): frozen specification

Written before the issue-time inventory, the baseline code or any score existed. Task source: Chapters 19-20 and the closing instruction of the supplied synthesis. **The rain-property experiment is closed as unresolved and is not revisited.** Original experiments and archives are untouched; this is a new, separate study (`phase3/forecast/`). No new downloads, no AI training, no search over arbitrary model forms. The 2012-2021 archive was explored in earlier phases, so every result here is **retrospective feasibility evidence, not confirmation**.

## Question
Do the existing observations support predicting soil temperature at 20 and 50 cm over the next 24-72 hours, using only information available at the forecast issue time, and is there room for a fair AI trial beyond simple and physical baselines?

## Data and split
Hourly USCRN files already on disk (`phase3/data`, 39 audited stations, 2012-2021, local standard time). **Development years 2012-2017** (everything fitted: hot-day thresholds, climatology, alpha references). **Validation years 2018-2021** (primary scoring). Climatology, thresholds and parameters use development years only, so no validation-year value enters any fitted quantity. No held-out-station experiment is run in this task (no station-specific learned quantity is used by the baselines beyond development-year medians).

## Hot day and issue time (no hindsight)
- Daily maximum air temperature = maximum of the hourly T_MAX over the local-standard-time day, valid with at least 20 hours.
- **Hot day** = daily maximum at or above the station's calendar-day 90th percentile, pooled over day of year +/-7 days across development years only.
- **Spell, evaluated in real time:** a spell begins on a hot day when the previous 3 days were not all non-hot, i.e. non-hot gaps of at most 2 days continue a spell; after 3 consecutive non-hot days the next hot day starts a new spell. The spell is "detected" on its **third hot day**.
- **Issue time = 08:00 local standard time on the morning after the third hot day.** One primary issue per station per spell. Only observations with time stamps up to the issue hour may be used. The spell end is never used.
- Later rain, continuing heat, a following spell and any other future event are **recorded as outcomes and never used to filter issues.**
- Past-only descriptive strata (all pre-specified): season (May-Sep vs other), dry at issue (rain over the previous 7 days at most 5 mm and 10 cm moisture at or below the development-year 40th percentile for that day of year), non-freezing (daily 5 cm temperature above 1 C throughout the previous 7 days). **The primary evaluation set is all detected spells**; strata are secondary.

## Valid issue (common set for all competitors)
1. All five depth temperatures (5, 10, 20, 50, 100 cm) observed at the issue hour (last valid value within the previous 3 hours allowed).
2. Over the previous 168 hours, at least 80% valid hours at each of the five depths.
3. At least 18 valid hours of the 20 and 50 cm temperature in the trailing 24 hours (for the anomaly baseline).
4. Outcome valid at a depth: at least 90% of the 72 target hours observed at that depth. The **primary common set requires both depths.**
Attrition is reported stage by stage and identically for all competitors.

## Targets and metrics
Hourly soil temperature at 20 and 50 cm for hours 1-72 after the issue. **Primary outcome: mean absolute error over hours 1-72** at each depth (per event, then summarised). Secondary: the same over hours 1-24 and 1-48, signed mean error, performance per event, per station and per stratum. **Events (not hours) are the unit of replication**; uncertainty by cluster bootstrap (2000 resamples) over operational date clusters (issue dates within 3 days chained across stations; geographic extent unrestricted, documented, not guaranteed independent). The 0.1 C reporting increment is **not** used as a threshold.

## Competitors (equal information: observations up to issue; no future weather, no future boundary temperatures)
- **B1 persistence:** forecast = the value at the issue hour, held constant.
- **B2 seasonal expectation with current anomaly:** development-year day-of-year (+/-7 d) median of daily mean temperature at that depth; anomaly = trailing 24-hour mean at issue minus the climatology of the corresponding days; forecast = climatology at the target day + that anomaly, held constant.
- **B3 conduction forecast (primary conduction variant C2):** the existing verified uniform-diffusivity solver on 5-100 cm, initial profile = observed five-depth profile at issue (PCHIP), boundaries forecast from past observations by one fixed rule: **level = trailing 24-hour mean; plus a 24-hour harmonic fitted to the preceding 168 hours after removing the daily means**; the boundary at the issue hour equals the observed value. Effective diffusivity: **C2 (primary)** = fitted on the preceding 168 hours with the archived estimator (80-value grid, six-hour exclusion), used only if identified under the archived rule, otherwise the development global value. **C1** = the development global value (median identified stress-window alpha from archived pilot fits with start year at most 2017). **C3** = station median of those archived development fits if at least 2 identified windows, else the global value.
- **Reconstruction diagnostic (not a forecast):** the same solver and C2 diffusivity driven by the **observed future** 5 and 100 cm temperatures. It shows how much error is due to unknown future boundaries.
Boundary-forecast error (5 and 100 cm) is reported separately from interior error. No extra tuning, no model search.

## Verification (run before any score is read)
1. **Information-set test:** replacing all observations after the issue hour by large offsets must leave every forecast of every competitor unchanged.
2. **Leakage test:** changing validation-year data must not change the thresholds, climatologies or alpha references.
3. **Alignment test:** hour 1 of every forecast corresponds to the first hour after the issue; checked on synthetic series with known answers.
4. **Solver:** the conduction forecast with exact synthetic boundaries and the exact periodic solution reproduces the analytic result (existing verification, re-run through the forecast code path).
5. **Boundary rule:** on a perfectly periodic synthetic series the rule's error is essentially zero.
If a check fails, the affected claim is dropped and reported.

## Secondary item omitted by design
Recovery-time prediction is omitted: the issue is during the spell, so recovery inside a 72-hour horizon is mostly unobserved, and the thresholds would need new freezing. The continuous trajectory is the outcome.

## Decision rule (heuristics fixed now; not statistical tests)
1. **Insufficient support** if the validation set has fewer than 40 clusters or fewer than 80 clusters exist in development.
2. Otherwise **baselines already adequate** if, at **both** depths, the best simple or physical baseline has 72-hour MAE below 0.30 C, **or** the headroom (best baseline MAE minus reconstruction-diagnostic MAE) is below 25% of the best baseline MAE, **or** its cluster-bootstrap interval includes zero.
3. Otherwise **sufficient data and meaningful room for a fair AI trial**: baselines leave at least 0.30 C of error at a depth and headroom of at least 25% with an interval excluding zero at that depth. Headroom is an upper bound that assumes perfectly known boundaries; it does not prove an AI model can recover the missing information.
Results are reported by depth; a mixed outcome is stated as mixed.

## Outputs
Short report; this specification; the issue-time inventory (`issue_inventory.csv`); verified code; event-level scores (`forecast_scores.csv`); one forecast-versus-observation figure.
