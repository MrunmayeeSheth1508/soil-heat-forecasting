# Identification-screen sensitivity diagnostic: frozen list (written before `52_ident_diagnostic.py` ran)

Inputs: archived observed fits (`archive_pre_diag/pilotA_part2_*.csv`, stored best-fit log diffusivity, profile-interval bounds, RMSE, lag-1 correlation per window), `layered_windows_*.csv`, `layered_events_*.csv` (SIMULATED), `event_inventory.csv`, and the hourly files already on disk. **No refitting, no new downloads, no new model family, no AI.** Exploratory; not a replacement confirmation test; no causal claim.

## Definitions (fixed now)
- **Retained pair** = identified in both windows under the archived rule (interior optimum, interval inside the grid, interval width at most 0.6 in ln alpha). **Rejected** = otherwise.
- **Grid-edge estimate** = best-fit at the first or last of the 80 grid values, or a 68% interval reaching either end of the grid, in either window.
- **Unstable** = interval width above 0.6 in either window (the archived rejection reason).
- Event contrast = mean change in ln alpha of wetting pairs minus that of control pairs; cluster bootstrap exactly as in the pilot (clusters defined as before).

## 1. Retained vs rejected (development, test, pooled; wetting and control separately)
By station; season (May-Sep vs other, and by month group); window lengths (hours); temperature forcing (mean Tmax anomaly and solar radiation of the spell, mean |T5-T100| and the diurnal-band variance fraction in each window, SD of T5); missingness (fraction of missing hourly values, maximum over the five depths, per window, before gap filling); fit error (RMSE at the best diffusivity, lag-1 residual correlation, effective sample size); grid-edge flags; interval widths per window. Report medians, rejection rates, and unadjusted Mann-Whitney / Fisher p-values **as descriptive only** (dependent data). Also the Spearman correlation of interval width with each signal-strength measure, and a logistic regression of rejection on the standardised covariates if a library is available.

## 2. Influence on the all-event contrast (development and test, all usable events)
Report **all** of the following, none selected afterwards: full contrast; leave-one-event-out range and leave-one-cluster-out range, with the units that move the sign; removal of the top k events by absolute change for k = 1..5 (all five reported); removal of every grid-edge estimate; removal of every unstable (rejected) event (this is the archived rule); symmetric 10% and 20% trimmed means in each group; median difference; Hodges-Lehmann style difference of group medians; list of the ten events with the largest influence, with width, grid-edge flag and change.

## 3. Contrast vs identification-width cutoff
Cutoffs 0.2, 0.3, 0.4, 0.5, 0.6 (archived), 0.8, 1.0, 1.5, 2.0, 3.0 and no width limit (interior optimum only), plus a rule using the edge test alone. For each: contrast, cluster-bootstrap 95% interval (1000 resamples), wetting and control event counts, cluster counts. Labelled exploratory.

## 4. Same-subset comparison
Core-based stations (those with S columns): usable events, observed identified events, and cutoff variants; compare OBSERVED contrast with SIMULATED U, G_low, G_high and S columns **on exactly the same events** (the earlier report compared U/G on all events and S on the subset). Event-level Spearman correlation between observed and simulated change in ln alpha on that subset.

## 5. Conclusion questions
Does the screen select a distinct physical regime (rejected and retained differ in season, forcing, soil or station in ways not explained by information content), or does estimator instability (wide profile intervals tied to weak signal, short windows, high residual correlation, missingness) prevent a reliable group comparison? Unresolved alternatives are listed explicitly.
