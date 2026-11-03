# Forecast Feasibility Report — Direction A
**Soil Heat Penetration and Recovery · USCRN 2012–2021**
Date: 15 October 2026 | Status: **Retrospective feasibility only** — no AI training performed

> [!IMPORTANT]
> This study uses historical data from all years to set thresholds and evaluate baselines. No genuine hold-out of future time is possible from a historical archive. The decision outcome ("room for AI trial") authorises a prospective experiment only; it does not constitute a demonstrated AI improvement.

---

## 1. Question and Frozen Spec

**Question:** Do USCRN hourly multi-depth soil observations support predicting soil temperature at 20 cm (T20) and 50 cm (T50) over a 24–72 h horizon using only information available at issue time (08:00 LST), and is there headroom for an AI competitor beyond the best simple baseline?

**Frozen spec:** [`phase3/forecast/forecast_spec_frozen.md`](file:///C:/Users/jtani/.gemini/antigravity/scratch/soil/phase3/forecast/forecast_spec_frozen.md) — written and locked before any score was read.

**Decision rule (frozen):**
| Rule | Condition | Decision |
|---|---|---|
| R1 | MAE72 ≤ 0.10 °C | Insufficient signal |
| R2a | MAE72 ≤ 0.30 °C | Baselines adequate — no room for AI |
| R2b | headroom CI lower bound ≤ 0 | Baselines adequate |
| R3 | MAE72 > 0.30 °C AND headroom CI lower bound > 0 AND headroom fraction > 25% | **Room for a fair AI trial** |

---

## 2. Attrition and Inventory

| Stage | Count |
|---|---|
| Hot-dry spells detected (39 stations) | 1,907 |
| Clusters (station-groups) | 254 |
| Events in common set (all competitors scored) | **1,689** |
| Development subset (start year ≤ 2017) | 973 in 146 clusters |
| Validation subset (start year ≥ 2018) | 716 in 99 clusters |
| Stations contributing alpha (C2 archived fits) | 11 (global α = 4.322 × 10⁻⁷ m²/s) |
| C2 fitted per-event alpha available (validation) | 57% of events |

---

## 3. Verification Results

All checks run by [`55_forecast_verification.py`](file:///C:/Users/jtani/.gemini/antigravity/scratch/soil/55_forecast_verification.py). Output: [`phase3/forecast/forecast_verification_out.txt`](file:///C:/Users/jtani/.gemini/antigravity/scratch/soil/phase3/forecast/forecast_verification_out.txt).

| Check | Result |
|---|---|
| 1 — No future observations in issue features | **PASS** |
| 2 — RECON uses full profile (clearly marked diagnostic) | **PASS** |
| 3 — Development/validation split respects cluster boundaries | **PASS** |
| 4a — Solver numerical accuracy (exact grid init, RMS = 0.0098 °C) | **PASS** |
| 4b — PCHIP init limitation (informational) | Max 0.692 °C at h=0, decays to 0.040 °C RMS by h25–72; noted as limit below |
| 5 — Bootstrap cluster IDs match event clusters | **PASS** |

---

## 4. Competitors

| Label | Description | Frozen role |
|---|---|---|
| **B1** | Persistence — last observed T at depth | Primary baseline |
| **B2** | Climatological anomaly + clim mean | Primary baseline |
| **C1** | 1-D conduction, global α, surface-boundary | Primary (conduction) |
| **C2** | 1-D conduction, station-median or global α, measured T5 and T100 boundaries | **Best conduction, primary** |
| **C3** | C2 variant, PCHIP init | Sensitivity |
| **RECON** | C2 with observed interior temperatures at t=0 | Diagnostic only — not a forecaster |

---

## 5. Scores (Validation Set, n = 716)

### 5.1 MAE72 — median across events

| Competitor | T20 (20 cm) | T50 (50 cm) |
|---|---|---|
| B1 (persistence) | 0.740 °C | **0.274 °C** |
| B2 (clim+anomaly) | 0.708 °C | 0.352 °C |
| C1 (conduction, global α) | 0.704 °C | 0.333 °C |
| **C2 (best T20)** | **0.673 °C** | 0.316 °C |
| C3 (PCHIP init) | 0.704 °C | 0.334 °C |
| RECON (diagnostic only) | 0.262 °C | 0.198 °C |

### 5.2 Lead profile — best baseline, median MAE (validation)

| Lead window | T20 (C2) | T50 (B1) |
|---|---|---|
| h1–24 | 0.363 °C | 0.125 °C |
| h1–48 | 0.538 °C | 0.198 °C |
| h1–72 | 0.673 °C | 0.274 °C |

### 5.3 Boundary forecast error (validation)

| Boundary sensor | Median MAE |
|---|---|
| T5 (top, 5 cm) | 1.175 °C — poorly forecast |
| T100 (bottom, 100 cm) | 0.213 °C — well-forecast |

### 5.4 Headroom (best baseline − RECON, validation)

| Depth | Mean headroom | 95% cluster-bootstrap CI | Fraction events > 0 |
|---|---|---|---|
| **T20** | **0.552 °C** | **[0.470, 0.658]** | **82%** |
| T50 | 0.100 °C | [0.059, 0.147] | 37% |

### 5.5 Strata (validation, T20 C2 / T50 B1)

| Stratum | T20 | T50 |
|---|---|---|
| May–Sep only | 0.688 | 0.265 |
| Dry at issue | 0.717 | 0.307 |
| Non-freezing only | 0.725 | 0.290 |
| Rain ≥10 mm within 72 h | 0.824 | 0.334 |

### 5.6 Station spread (validation)

| Depth | Median | IQR | Max station |
|---|---|---|---|
| T20 (C2) | 0.651 | [0.522, 0.903] | 1.925 at CA_Merced_23_WSW |
| T50 (B1) | 0.294 | [0.207, 0.367] | 1.236 at AZ_Elgin_5_S |

### 5.7 Example events (pre-specified in frozen spec)

| Percentile | Station | Issue date | C2 MAE72 |
|---|---|---|---|
| P10 (low error) | MO_Chillicothe_22_ENE | 2021-12-26 | 0.229 °C |
| P50 (median) | SD_Sioux_Falls_14_NNE | 2020-10-10 | 0.670 °C |
| P90 (high error) | LA_Lafayette_13_SE | 2021-03-17 | 1.997 °C |

---

## 6. Decision (Frozen Rule Applied)

| Depth | MAE72 | Headroom CI lower | Headroom fraction | **Decision** |
|---|---|---|---|---|
| T20 (20 cm) | 0.673 °C > 0.30 | 0.470 > 0 | 82% > 25% | **ROOM FOR A FAIR AI TRIAL** (Rule 3) |
| T50 (50 cm) | 0.274 °C ≤ 0.30 | — | — | **BASELINES ADEQUATE** (Rule 2a) |
| **Overall** | | | | **MIXED** |

**Interpretation:**
- At 20 cm, the best baseline (C2, conduction with measured boundaries) leaves 0.55 °C mean headroom, primarily because T5 is poorly forecast 72 h ahead (median MAE 1.18 °C). A learner with better near-surface temperature prediction could propagate it downward. Rain events are hardest (0.824 °C).
- At 50 cm, B1 persistence already achieves 0.274 °C. Conduction adds nothing beyond persistence at this depth with available boundary quality. There is no practical case for an AI competitor at T50.

---

## 7. Limits

1. **Retrospective feasibility** — all years of data used; no genuine prospective test.
2. **No held-out stations** — station-level transfer not tested; station spread is large (IQR ×2 at T20).
3. **Large temporal clusters** — bootstrap CIs are conservative but cluster structure is approximate; do not over-interpret CI precision.
4. **Winter events included** — near-freezing events may be physically distinct; non-freezing stratum shows slightly worse T20 (0.725 vs 0.673 overall), suggesting winter events are not easier.
5. **Alpha from archived development fits** — C2 uses diffusivity fitted on development windows; any learner in a prospective trial must not access validation observations.
6. **No real NWP boundary forcing** — T5 and T100 are observed, not forecast. A real operational system would compound NWP error.
7. **PCHIP init error** — max 0.692 °C at h=0, decays to 0.040 °C RMS by h25–72; small effect on 24–72 h scores but non-zero.

---

## 8. Proposed AI Trial Design (T20 only, if pursued)

> [!NOTE]
> This is a design sketch only. No training was performed. Do NOT extend to PINO or operator-learning without a separate feasibility gate.

- **Target:** T20 hourly trace, h1–72, issue at 08:00 LST
- **Information set:** history of T5, T10, T20, T50, T100, soil moisture, precipitation, infrared surface temperature up to issue time; station soil properties (texture, bulk density from Wilson et al. 2016)
- **Competitors (must all be trained on development, scored on validation):**
  - Learner 1: explicit-history regression (Ridge or gradient boosting) — history lags as features, same information set
  - Learner 2: small recurrent learner (LSTM, ≤2 layers) — same information set
  - Ablation: remove moisture history; compare to full model
- **Evaluation:** cluster-bootstrap MAE72, same 716 validation events; report MAE72, headroom fraction vs C2, station-level spread
- **Hold-out stations:** reserve at least 5 stations from the development fit entirely
- **Do NOT jump to PINO** — physics-operator approaches require separate justification and a demonstrated gap in the above learners

---

## 9. Artefacts

| File | Description |
|---|---|
| [`forecast_spec_frozen.md`](file:///C:/Users/jtani/.gemini/antigravity/scratch/soil/phase3/forecast/forecast_spec_frozen.md) | Frozen spec (written before scoring) |
| [`issue_inventory.csv`](file:///C:/Users/jtani/.gemini/antigravity/scratch/soil/phase3/forecast/issue_inventory.csv) | Per-event inventory (1 689 rows) |
| [`forecast_scores.csv`](file:///C:/Users/jtani/.gemini/antigravity/scratch/soil/phase3/forecast/forecast_scores.csv) | Event-level MAE for all competitors |
| [`forecast_summary.txt`](file:///C:/Users/jtani/.gemini/antigravity/scratch/soil/phase3/forecast/forecast_summary.txt) | Full printed summary with bootstrap CIs |
| [`forecast_bootstrap.csv`](file:///C:/Users/jtani/.gemini/antigravity/scratch/soil/phase3/forecast/forecast_bootstrap.csv) | Bootstrap table |
| [`forecast_verification_out.txt`](file:///C:/Users/jtani/.gemini/antigravity/scratch/soil/phase3/forecast/forecast_verification_out.txt) | Verification log (all checks pass) |
| [`forecast_figure.png`](file:///C:/Users/jtani/.gemini/antigravity/brain/d895d91a-33a5-49bd-8d56-6a58ee64f9a6/forecast_figure.png) | Six-panel figure (traces / boxplots / lead / scatter / histogram / headroom) |
| [`55_forecast_verification.py`](file:///C:/Users/jtani/.gemini/antigravity/scratch/soil/55_forecast_verification.py) | Verification script |
| [`56_forecast_scores.py`](file:///C:/Users/jtani/.gemini/antigravity/scratch/soil/56_forecast_scores.py) | Scoring script |
| [`57_forecast_figure.py`](file:///C:/Users/jtani/.gemini/antigravity/scratch/soil/57_forecast_figure.py) | Figure script |

---

## 10. What This Study Does NOT Establish

- It does **not** demonstrate that an AI model improves on C2. It authorises trying one.
- It does **not** re-open the rain-property experiment (closed as unresolved).
- It does **not** claim rain causality, a tipping point, or ecosystem effects.
- T50 forecasting is not a productive target with available boundary quality.
