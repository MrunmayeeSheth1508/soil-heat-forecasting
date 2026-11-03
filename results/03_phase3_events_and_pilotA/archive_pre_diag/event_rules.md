# Phase 3 event rules (frozen BEFORE any event counts were computed)

Written before running `32_event_inventory.py`; the file's modification time precedes the outputs `event_inventory.csv` and `event_summary.txt`. No model has been fitted. Data: USCRN hourly02, local standard time, **2012-2021 only**. 2022 onward is reserved and not downloaded.

## Daily variables
A day is valid for a variable only with at least 20 of 24 valid hourly values (mean for temperature, moisture and radiation; sum for rain; maximum of hourly T_MAX for daily maximum air temperature).

## Local climatology
For each station and variable: pooled over all 10 years, for the calendar day of year +/-7 days (circular window). Percentiles and medians are computed from this pool. The event year is included in its own climatology. This is an event-definition choice, **not** a reference for later model evaluation, which must use training-only climatology.

## Primary definitions
| Term | Rule |
|---|---|
| Hot day | Daily maximum air temperature >= local P90 |
| Hot spell | Hot days with gaps of at most 2 non-hot days merged; at least 3 hot days. Start = first hot day, end = last hot day |
| Dry condition | Rain total over [start-7 d, end] <= 5 mm (>= 90% of days valid) AND at least half of the spell days have 10 cm moisture <= local P40 |
| Hot-dry stress episode | Hot spell satisfying the dry condition |
| Nonfreezing | Daily mean 5 cm soil temperature > 1 C on every day from start-7 d to end+21 d |
| Clean pre-window | No hot spell (dry or not) starting in [start-21 d, start-1 d] |
| Interrupted | Another hot spell begins within 21 d after the end; follow-up is truncated to the day before it begins |
| Follow-up window | Up to 21 d after the end |
| Wetting day | First day in the follow-up window with rain >= 10 mm |
| Shallow / deeper replenishment | 5 cm / 20 cm moisture rises >= 0.02 m3/m3 within 3 d of the wetting day, relative to the minimum over the 3 d before it |
| Hydrologic recovery at depth k | After the wetting day, daily moisture >= local P40 for 2 consecutive days. No wetting day: "no_wetting" |
| Thermal anomaly at depth k | Daily soil temperature minus local day-of-year median |
| Thermal recovery at depth k | After the spell end, the anomaly <= 0.5 x (local SD of warm-season anomalies at that depth) for 2 consecutive days |
| Recovery status | observed / censored (window ended, data valid) / interrupted / unobserved (more than 30% of window days missing for that variable) / no_wetting |
| Complete sequence | Valid (>= 80% of days) for 5, 10, 20 cm temperature, 5, 10, 20 cm moisture and rain in the pre (7 d), stress and follow-up windows; nonfreezing; clean pre-window; not interrupted |

## Independence
1. Within a station, episodes with another hot spell inside 21 d before them are **not independent** (no clean pre-window).
2. **Regional clusters:** episodes at different stations whose start dates fall within +/-3 days are one synoptic cluster (the same heat wave); clusters, not episodes, are the effective count across stations.
3. Overlapping windows and matched pairs are never counted as separate events.

## Sensitivity variants (counts only)
- strict: P95, >= 4 hot days.
- relaxed: P85, >= 3 hot days.

## Direction B feasibility rule (history contrast, counted at the day level, then at the episode level)
Eligible day: nonfreezing (5 cm daily mean > 1 C), rain < 1 mm today and yesterday, all of 5/10/20 cm temperature and 10 cm moisture valid, 14 prior days >= 80% valid for 10 cm moisture. Matching cell: station x 10 cm moisture bin (0.03 m3/m3) x mean-profile-temperature bin (3 C) x day-of-year window (+/-45 d). Antecedent history = mean 10 cm moisture over the 14 prior days. A cell has a history contrast if it holds >= 2 independent episodes (contiguous day runs separated by >= 5 days) in each of a low-history class and a high-history class, with class means differing by >= 0.05 m3/m3. Counts are feasibility counts, not an effective sample size.

## Sensor-shift flags (descriptive, cannot separate climate from instrument)
- Logger version (CRX_VN) changes.
- Maximum step between consecutive 90-day medians of the moisture anomaly (relative to local day-of-year median) > 0.05 m3/m3.
- Moisture stuck constant for >= 72 h.
- Fraction of hours with moisture above estimated porosity (stations with Wilson bulk density).
