# Forecasting Audit & AI Implementation Specification  
*(Corrected version — addresses all six flagged issues)*

**Source scripts audited:** `forecastlib.py`, `54_forecast_inventory.py`, `55_forecast_verification.py`, `56_forecast_scores.py`, `56b_forecast_tail.py`, `pilotA_estimator.py`  
All numbers verified from code or output files; no claims inferred from memory.

---

## 1. What the Audit Resolved

**Boundary ambiguity — resolved.**

C2 forecasts using past information only. `boundary_forecast()` extrapolates from the trailing 168 h of observed T5 and T100 using a level + 24-h harmonic rule; no observation after the issue hour is read. RECON deliberately receives future observed T5 and T100, making it a diagnostic oracle and not a forecasting competitor. C2 and RECON share the same initial five-depth profile and the same per-event diffusivity fitted from past data; their performance difference isolates the effect of replacing extrapolated boundaries with observed future boundaries *within this particular physical model*.

Verification Check 1 confirmed: corrupting every post-issue observation by +37 °C and rain 999 mm leaves all of B1, B2, C1, C2, C3 unchanged (max difference 0.0 °C). Verification Check 2 confirmed: thresholds, climatologies, and diffusivity references use development years (2012–2017) only.

---

## 2. Information Table

| Competitor | Latest timestamp of any input | Past data used |
|---|---|---|
| **B1** — persistence | Issue hour | T20, T50 at issue hour (last valid within 3 h) |
| **B2** — climatology + anomaly | Issue hour | Trailing 24 h mean of T20, T50; dev-year DOY climatology (pre-frozen) |
| **C1** — conduction, global α | Issue hour | 5-depth profile at issue; trailing 168 h of T5, T100 for boundary extrapolation |
| **C2** — conduction, per-event α | Issue hour | Same as C1 plus trailing 168 h of T5–T100 interior temperatures for α fitting |
| **C3** — conduction, station α | Issue hour | Same as C1; α from station median of dev-archive identified windows |
| **RECON** — reconstruction oracle | **Hours 1–72 future** | Same initial profile and α as C2; boundary forcing = **observed future** T5 and T100 |

Boundary temperatures at 5 and 100 cm are always predicted from past data in B1–C3. They are observed future values only in RECON.

---

## 3. Diffusivity References — Corrected Count

**Correction from prior audit:** The prior report stated "station medians for 25 stations." That was wrong.

From the archive (`pilotA_part2_dev.csv`, rows with `usable=True`, `w1_ident=True`, `start.dt.year ≤ 2017`):
- **48 identified windows** across **25 unique stations**
- Of those 25 stations, **11 have ≥ 2 identified windows** and therefore receive a station-level median
- The remaining **14 stations have exactly 1 identified window** each and fall back to the global median for C3

The `development_alphas()` function returns station medians for **11 stations**, not 25. C3 uses the station median for those 11 stations; for the other 28 stations it is numerically identical to C1.

| Parameter | Value | Source |
|---|---|---|
| Global α | 4.322 × 10⁻⁷ m²/s | Median of 48 identified windows, dev years 2012–2017 |
| Station α available | 11 stations | ≥ 2 identified windows each |
| Station α fallback | Global α | For 28 of 39 stations |
| Latest window start year in archive | 2017 | Verified by Check 2 |

---

## 4. Validation Scores (Unchanged — No Corrections Required)

Verification checks 1, 2, 3, 4a, and 6 all passed. Per-event α in validation uses a dev-frozen algorithm applied to past data; no leak. Scores stand.

| Competitor | T20 MAE h1–72 (median) | T50 MAE h1–72 (median) |
|---|---|---|
| B1 persistence | 0.740 °C | **0.274 °C** |
| B2 clim + anomaly | 0.708 °C | 0.352 °C |
| C1 conduction, global α | 0.704 °C | 0.333 °C |
| **C2 conduction, per-event α** | **0.673 °C** | 0.316 °C |
| C3 conduction, station α | 0.704 °C | 0.334 °C |
| RECON (diagnostic oracle) | 0.262 °C | 0.198 °C |

*Validation set, n = 716 events, 99 clusters, 38 stations.*

Boundary forecast errors (validation): T5 MAE h1–72 median = **1.175 °C**; T100 = **0.213 °C**.

---

## 5. Boundary-Information Sensitivity — Corrected Interpretation

**The "82% of error" statement is withdrawn.**

The paired difference C2 − RECON at T20 has mean **0.552 °C** (95% cluster-bootstrap CI [0.470, 0.658]). The C2 baseline median MAE72 is **0.673 °C**. Dividing a mean paired difference by a median absolute error does not yield an error fraction; the 82% figure is not meaningful and is removed.

**Correct statement:** When the physical solver is given observed future boundary temperatures instead of extrapolated ones, its mean per-event MAE72 at 20 cm falls by 0.552 °C (95% CI [0.470, 0.658]). This is a measure of how sensitive the solver's output is to boundary information in this dataset. It does not establish what fraction of real-world T20 forecast error comes from the boundary, and it does not indicate how much an AI can improve over C2—an AI also receives no future boundary observations.

The boundary-information sensitivity motivates testing whether learned relationships in past temperatures, moisture, and rainfall can produce better boundary estimates or better direct predictions than the harmonic extrapolation rule.

> [!NOTE]
> The statistic is now called **boundary-information sensitivity**, not "recoverable headroom" or "unexplained variance." MAE is not variance.

---

## 6. Event Count Reconciliation

**The "156 recovery sequences" arose from a different earlier analysis and is a different quantity from the forecast inventory.** The lineage is:

| Dataset | Count | Definition |
|---|---|---|
| `layered_windows_dev` + `layered_windows_test` | **156** | Earlier Direction B analysis: drying-then-wetting windows used to study hysteresis in the layered thermal model. Different trigger, different eligibility criteria, not connected to forecast issues. |
| Detected spells (forecast inventory) | **1,907** | Real-time hot-day spell detector: third consecutive hot day triggers one issue per station per spell (08:00 local time on the morning after the third hot day). Hot day = daily max ≥ station DOY 90th percentile from dev years. |
| Common set (both depths valid) | **1,689** | After 5-step attrition: (1) five-depth profile at issue, (2) ≥80% coverage in past 168 h, (3) trailing-24 h data, (4) T20 outcome ≥90% valid, (5) T50 outcome ≥90% valid. Same filter applied identically to every competitor. |
| Dev common set | **973** (146 clusters, 39 stations) | Issue years ≤ 2017 |
| Val common set | **716** (99 clusters, 38 stations) | Issue years ≥ 2018 |

**On winter events:** the 1,689 issues span all 12 months (Jan 113, …, Aug 194, …, Dec 169). This is expected: the spell trigger uses a station-specific and calendar-day-specific threshold (90th percentile of daily max T from dev years). A January issue at a southern or high-altitude station means unusually warm weather for that location and time of year, not a "warm winter" in the colloquial sense. The `mayseps` flag (54% of val events are May–September) is available as a stratum but not a filter.

---

## 7. Preprocessing and Evaluation — Corrected

**The normalisation and imputation must be fitted inside each internal fold.**

All z-score statistics (channel means and standard deviations used to normalise GRU inputs) and any imputation parameters are computed **within each training fold** using only the stations included in that fold's training data. They are then applied to the fold's internal validation stations without refitting. This prevents any information from held-out stations contaminating the standardisation.

**Clarification on "held-out stations":** the 5 stations reserved from dev training (see §9.6) serve as an **internal validation set** for early stopping and hyperparameter selection. They are not an untouched generalisation test. The primary generalisation evaluation is the fixed 716-event validation set (years ≥ 2018). Because the baseline results on those 716 events have already been examined retrospectively, any AI performance reported on them is also retrospective.

---

## 8. Finalized Decision

| Depth | Best Baseline | Median MAE72 | Decision |
|---|---|---|---|
| **T20** | C2 | 0.673 °C | ROOM FOR A FAIR AI TRIAL |
| **T50** | B1 | 0.274 °C | BASELINES ADEQUATE (secondary target, same model) |

---

## 9. Training-Ready AI Specification

### 9.1 Targets

| Target | Definition |
|---|---|
| `y_T20[h]`, h = 1…72 | Observed T20 at forecast hour h, centred by subtracting issue-hour T20 |
| `y_T50[h]`, h = 1…72 | Observed T50 at forecast hour h, centred by subtracting issue-hour T50 |

Both targets predicted by a single model. Centring removes the dominant mean-state; the model learns departures from the initial condition.

---

### 9.2 Sequence Window — Resolved Indexing

The history window is **hours −167 through 0**, where hour 0 = the issue hour. This gives 168 time steps. Hour 1 is the first forecast hour (not in the input). This matches `forecastlib.py`'s `past = df.iloc[max(i0-167, 0) : i0+1]`, where `i0 = df.index.get_loc(ts)` and the slice is inclusive of `i0`. The GRU input sequence therefore has T = 168 steps.

---

### 9.3 Feature Groups

**Group A — Issue-hour profile (always available in the common set)**

| Feature | Description |
|---|---|
| `T5_0` … `T100_0` | Temperature at each depth (5,10,20,50,100 cm) at issue hour |
| `M10_0` | 10 cm soil moisture at issue hour (mean of last 24 valid hours) |
| `doy_sin`, `doy_cos` | Day-of-year encoded cyclically (2π/365) |
| `hour_sin`, `hour_cos` | Issue hour encoded cyclically (2π/24) |
| `clim_T20`, `clim_T50` | Dev-year DOY median for this day of year (pre-frozen) |
| `alpha_log` | log(α_C2) — per-event if identified, else log(global α) |
| `alpha_fitted` | Binary: whether α was identified from past data |

**Group B — Hourly temperature history (T = 168 h)**

Lags k = 1…168 of T5, T20, T50, T100 (T10 omitted to reduce dimensionality while retaining boundary-to-target coverage). Each lag is the observed value at issue hour − k (hour 0 is included in the issue-hour profile above, not repeated in the lag series).

Four channels → 4 × 168 = 672 values.

**Group C — Moisture and rainfall history (T = 168 h)**

| Sub-group | Channels |
|---|---|
| C1 — Rainfall only | `P_lag[k]` k=1…168 (hourly precipitation mm/h), `rain7_mm` (7-day total) |
| C2 — Current moisture | `M10_0` (already in Group A), `dry_at_issue` (binary) |
| C3 — Moisture history | `M10_lag[k]` k=1…168 (hourly 10 cm moisture) |

**Group D — Static station context**

| Feature | Description | Missing value handling |
|---|---|---|
| `lat`, `lon` | Station coordinates | Always present |
| `elev` | Elevation (m) | Always present |
| `sand_pct` | Sand fraction (Wilson 2016) | 14 stations missing → fill with network median; add `soil_missing` flag |
| `clay_pct` | Clay fraction (Wilson 2016) | Same |
| `bulk_density` | Bulk density g/cm³ (Wilson 2016) | Same |

When `soil_missing = 1`, the sand/clay/bulk_density values are replaced by the development-set median. The flag is passed as an input so the model can learn to discount those features.

**Group E — C2 baseline output (optional, separate comparison only)**

The C2 72-hour forecast (2 depths × 72 h = 144 values) may be included as an additional input to test residual correction. This configuration is evaluated separately (see ablation §9.5, label "C2-assisted") and is not mixed into the standard ablation grid.

---

**Total input dimensions for GRU (Full configuration, no C2 assist):**

| Group | Channels per timestep | Notes |
|---|---|---|
| Sequence input (B + C3 + P) | 4 (T) + 1 (M10) + 1 (P) = 6 channels | 168 timesteps |
| Static context (A + D) | 16 scalars | Passed via MLP then concatenated to final hidden state |

Actual tensor shape: `[batch, 168, 6]` for the recurrent input; `[batch, 16]` for the static context.

Missing hourly values in sequence inputs are forward-filled then zero-filled; a binary mask channel (1 = valid, 0 = filled) is added per sequence channel, increasing the sequence input to `[batch, 168, 12]` (6 channels + 6 masks). Missing static soil properties use network median + `soil_missing` flag.

---

### 9.4 Model A — Gradient-Boosted Trees (GBT)

**Implementation:** XGBoost or LightGBM. LightGBM does not natively support multi-output regression in a single estimator; use `sklearn.multioutput.MultiOutputRegressor` wrapping a single-output LightGBM regressor, or train 144 separate models (72 lead hours × 2 depths). The `MultiOutputRegressor` approach is recommended: it fits one model per target using the same hyperparameters, produces output in the expected shape, and is the approach validated in the LightGBM sklearn tests.

**Input construction:** Flatten all feature groups into a fixed-length vector per event using summary statistics of the lag history:
- Mean, std, min, max over past 24 h / 72 h / 168 h for T5, T20, T50, T100, M10, P (ablation-dependent)
- Linear slope (OLS) over past 24 h for T5 and T20
- Anomaly of last-24 h mean vs. dev-year DOY climatology for T20 and T50
- All Group A scalars and Group D static features

This yields approximately 80–110 scalar features per event (ablation-dependent).

**Output:** 144 values (T20 at h1–72 and T50 at h1–72). With `MultiOutputRegressor`, 144 LightGBM models are trained; predictions are stacked.

**Hyperparameter search (station-blocked CV on dev set):**

| Parameter | Search range |
|---|---|
| `n_estimators` | 200, 500, 1000 |
| `max_depth` | 3, 4, 5 |
| `learning_rate` | 0.05, 0.10 |
| `min_data_in_leaf` | 20, 50 |
| `subsample` | 0.7, 0.9 |
| `colsample_bytree` | 0.7, 1.0 |

Cross-validation folds hold out complete stations, not randomly selected events.

---

### 9.5 Model B — GRU Sequence Model

**Architecture recommendation: GRU.** This is a starting choice; the claim that GRU is "25% faster" or "less prone to overfitting" for this specific dataset is not established. The rationale for preferring GRU over LSTM here is simpler: with 973 training events, any reduction in free parameters reduces the risk of overfit, and GRU has fewer parameters per hidden unit than LSTM (no separate cell state). Whether that advantage materialises will be visible in the training curves.

**PyTorch implementation note (PyTorch 2.x):**

A standard `torch.nn.GRU` with `num_layers=2` and a specified `hidden_size` uses the **same hidden size for all layers**. To implement 64 → 32 hidden sizes, use two separate `nn.GRU` modules:

```python
self.gru1 = nn.GRU(input_size=12, hidden_size=64, batch_first=True, dropout=0.0)
self.gru2 = nn.GRU(input_size=64, hidden_size=32, batch_first=True, dropout=0.0)
self.drop1 = nn.Dropout(0.2)
self.drop2 = nn.Dropout(0.2)
```

`nn.GRU`'s built-in `dropout` argument applies dropout **between layers only when `num_layers > 1`**, and does not apply to the final layer's output. Using separate modules with explicit dropout layers is cleaner and avoids this asymmetry.

**Full architecture:**

```python
# Recurrent path
gru1: GRU(12, 64, batch_first=True)     # input [B, 168, 12] -> output [B, 168, 64]
drop1: Dropout(0.2)
gru2: GRU(64, 32, batch_first=True)     # input [B, 168, 64] -> output [B, 168, 32], h_n [1, B, 32]
drop2: Dropout(0.2)
# Take final hidden state h_n[-1]: shape [B, 32]

# Static context path
mlp_static: Linear(16, 32) -> ReLU -> Linear(32, 32) -> ReLU
# Output: [B, 32]

# Concatenate: [B, 64]
head: Linear(64, 128) -> ReLU -> Linear(128, 144)
# Output: [B, 144]  (T20 h1-72 then T50 h1-72, centred)
```

**Training protocol:**

| Setting | Value |
|---|---|
| Loss | Huber loss, δ = 0.5 °C |
| Optimiser | Adam, lr = 1 × 10⁻³ |
| LR schedule | Cosine decay to 1 × 10⁻⁵ over 150 epochs |
| Batch size | 32 events |
| Gradient clip | Max norm 1.0 |
| Early stopping | Patience 20 epochs on internal validation stations |
| Weight initialisation | PyTorch default (Kaiming uniform for linear layers) |

**Normalisation:** Z-score each sequence channel and each static feature. Statistics are computed from **training stations in the current fold only**, then applied to internal validation stations and to the full val set at final evaluation without refitting.

---

### 9.6 Moisture Ablation — Corrected Four Configurations

The prior "No-moisture" configuration removed both M10 and rainfall together, conflating their contributions. The corrected ablation isolates each addition cleanly. All four configurations use identical model settings; only the sequence input channels differ.

| Label | Sequence channels (168-h history) | Issue-hour scalars |
|---|---|---|
| **T-only** | T5, T20, T50, T100 (+ masks) | Group A (no M10_0), Group D |
| **T + rain** | T5, T20, T50, T100, P (+ masks) | Group A (no M10_0), Group D, `rain7_mm` |
| **T + rain + M₀** | T5, T20, T50, T100, P (+ masks) | Group A (with M10_0), Group D, `rain7_mm`, `dry_at_issue` |
| **T + rain + M-history** | T5, T20, T50, T100, P, M10 (+ masks) | Group A (with M10_0), Group D, `rain7_mm`, `dry_at_issue` |

Run both GBT and GRU across all four configurations. For GBT, Group C lags are summarised into mean/std/max over 24/72/168 h windows (not raw lags). Report all four configurations; do not select the best and suppress the others.

**C2-assisted comparison (separate, not part of the moisture ablation grid):**

Run GBT-Full additionally with the 144-element C2 forecast vector appended to the feature set. This tests whether learning a correction to C2 outperforms learning from raw history directly. Evaluate identically; report alongside but labelled separately.

---

### 9.7 Evaluation Protocol

| Element | Specification |
|---|---|
| **Primary metric** | Mean MAE h1–72 for T20 (cluster-bootstrap, 2000 resamples, seed 42) |
| **Secondary metric** | Mean MAE h1–72 for T50 |
| **Val set** | 716 events, years ≥ 2018, 99 clusters, 38 stations |
| **Cluster structure** | Identical 99-cluster assignment from `issue_inventory.csv`; no recomputation |
| **Baseline comparison** | Every AI configuration compared against C2 (T20) and B1 (T50) on identical val events |
| **Internal validation (dev)** | 5 geographically spread stations withheld entirely from GRU training and GBT feature engineering; used for early stopping and hyperparameter selection only |
| **Normalisation scope** | Z-score statistics from training stations within each fold; refitted per fold; never computed on internal val stations or on the 716-event val set |
| **No separate T50 tuning** | Single model scored on both depths |
| **Reporting** | All ablation configurations reported; no post-hoc selection |

> [!WARNING]
> The 716-event validation set baseline results have already been examined. Any AI result on this set is retrospective, not prospective. Report it as such.

---

### 9.8 Comparison Summary

| Model | 168-h T history | Rain history | M10 history | C2 output | Architecture |
|---|---|---|---|---|---|
| B1 | ✗ | ✗ | ✗ | ✗ | Persistence |
| B2 | partial (24 h) | ✗ | ✗ | ✗ | Clim + anomaly |
| C2 | ✓ (via α + boundary) | ✗ | ✗ | — | Physical solver |
| GBT T-only | ✓ (summarised) | ✗ | ✗ | ✗ | XGBoost/LGBM |
| GBT T+rain | ✓ | ✓ | ✗ | ✗ | XGBoost/LGBM |
| GBT T+rain+M₀ | ✓ | ✓ | point only | ✗ | XGBoost/LGBM |
| GBT Full | ✓ | ✓ | ✓ | ✗ | XGBoost/LGBM |
| GBT C2-assist | ✓ | ✓ | ✓ | ✓ | XGBoost/LGBM |
| GRU T-only | ✓ (raw) | ✗ | ✗ | ✗ | 2-module GRU |
| GRU T+rain | ✓ | ✓ | ✗ | ✗ | 2-module GRU |
| GRU T+rain+M₀ | ✓ | ✓ | point only | ✗ | 2-module GRU |
| GRU Full | ✓ | ✓ | ✓ | ✗ | 2-module GRU |
| RECON | — | — | — | — | Oracle diagnostic |

No model receives any observation after the issue hour except RECON.

---

### 9.9 The Experiment Question

> Can AI use the preceding week of soil temperature, moisture, and rainfall to improve 1–3 day underground temperature forecasts over persistence and a conduction model — and does moisture history provide additional predictive information beyond temperature history alone?

Better prediction is a measured result. A new physical mechanism would require separate evidence.

---

*Corrected from code audit of `forecastlib.py` + scripts 54–56b + archive `pilotA_part2_dev.csv`. Six flagged issues addressed. Report date: 2026-10-15.*
