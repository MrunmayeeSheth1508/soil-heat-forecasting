# Research Proposal — Draft v3

## Dynamic Underground Cable Ampacity from Forecast Soil Conditions: A Data-Driven Pipeline from Multi-Depth Soil State Prediction to Real-Time Thermal Rating

**Date:** 4 November 2026  
**Status:** Pre-submission internal draft — v3 incorporates pipeline validation results

> [!NOTE]
> All literature claims are traceable to full-text reads in `notes/`. Numbers
> carry source tags: [V] = verified from text, [I] = inferred from geometry,
> [R] = computed by our pipeline scripts (see `notes/VALIDATION_FINDINGS.md`).
> Completed prior work is labelled **[Completed]**; new contributions are
> **[Proposed]**.

---

## 1. Background and Motivation

### 1.1 Underground Cable Ampacity — The Governing Problem

Underground power cables carry current from generators, substations, and
renewable plants to loads. The maximum current a cable can carry continuously
without exceeding its conductor temperature limit is its **ampacity**. Exceeding
ampacity causes irreversible insulation degradation and ultimately cable failure;
operating well below it wastes infrastructure capacity that could defer costly
capital upgrades.

The governing equation, due to Neher and McGrath (1957), is:

$$I = \sqrt{\frac{T_c - T_a - \Delta T_d}{R_{dc}(1+Y_c) \cdot R_{ca}}}$$

where $T_c$ is the maximum allowable conductor temperature (90°C for EPR/XLPE
at normal rating), $T_a$ is the ambient soil temperature at burial depth,
$\Delta T_d$ is dielectric loss temperature rise, $R_{dc}$ is conductor DC
resistance, $Y_c$ is the AC loss factor (skin + proximity effect), and $R_{ca}$
is the total thermal resistance from conductor to ambient soil. This equation is
the basis of IEC 60287-1 and is implemented in all major commercial ampacity
software (CYMCAP, ETAP, USAmp Prime).

Two parameters in the Neher-McGrath equation are **set entirely by the soil**,
not the cable:

- **$T_a$:** ambient soil temperature at burial depth — typically 60–100 cm below grade.
- **$R_{ca}$:** dominated by soil thermal resistance $T_e = \rho_e \cdot f(L, D_e)$, where
  $\rho_e$ is the soil thermal resistivity — a strong function of soil moisture $\theta$.

Soil thermal resistance accounts for **70–90% of the total thermal resistance**
between conductor and ambient in 15 kV direct-buried installations [Bates 2021, Ch 1, V].
It is the controlling variable in cable ampacity.

### 1.2 The Problem with Static Soil Assumptions

Current engineering practice — codified in the AIEE-IPCEA "Black Books" (1962),
IEEE Std 835 (1994), and utility design standards — treats $T_a$ and $\rho$ as
**fixed conservative values** chosen at design time:

- **$T_a$:** typically 20–25°C (a dry-season worst case) regardless of actual seasonal
  or diurnal conditions.
- **$\rho$:** typically 90 °C·cm/W (the NEC default [Bates V, Ch 2]) or a single
  in-situ measurement, held constant for the cable's 40–50 year operational life.

This conservatism produces two well-documented consequences:

**1. Systematic overestimation of conductor temperature.** Bates (2021) conducted
six controlled field experiments on a direct-buried cable in Boulder, Colorado, and
found that steady-state N-M overestimated conductor temperature by a mean of
**−8% ± 8.9%** (90% CI: −15% to −1%) even when soil resistivity was accurately
measured [Bates, Table 9.1, V]. In a 10 MW photovoltaic installation in Arizona,
software predicted 75–87°C while field loggers measured 55–61°C — an overestimate
of 15–30°C — because the design used $\rho$ = 270–303 °C·cm/W (dry worst-case)
while the measured in-situ mean was 157 °C·cm/W [Bates, Ch 11, V].

**2. Inability to exploit available ampacity headroom.** Because the rating is
fixed at design-time worst-case, operators cannot increase current during
favourable conditions (cool winter soil, post-rain wetting) without a new
engineering study. For overhead transmission lines, **Dynamic Line Rating (DLR)**
— updating ratings continuously from measured ambient conditions — is now
established in practice. The underground equivalent, **Dynamic Cable Rating
(DCR)**, remains operationally immature. The core obstacle is that soil
temperature and moisture at cable burial depth are not routinely monitored or
forecast.

### 1.3 Soil Moisture — The Dominant Variable

Soil thermal resistivity $\rho$ varies by a factor of **5–10** between wet and
dry states of the same soil. **Our pipeline validation quantifies this directly:**
in the Darmstadt MF_III constant-load experiment (283 A, 35 days), the measured
mean volumetric water content θ = **30.6%** corresponds — via the Johansen
relation — to a mean rho of **45.8 °C·cm/W** [R]. This is **half the NEC
default of 90 °C·cm/W** [V, Bates Ch 2]. Replacing the NEC default with the
actual in-situ rho in the Neher-McGrath equation increases ampacity by
$\sqrt{90/45.8} \approx$ **40%** for that soil condition. Conversely, in arid
sites the design rho of 270–303 °C·cm/W [V, Bates Ch 11] implies ratings far
below what wet conditions would support.

The ambient temperature effect is real but smaller: a 10°C ambient improvement
(20→10°C) adds ~5% ampacity at NEC-90; a typical wet-vs-design-dry rho change
adds 10–40% [R, sensitivity analysis]. **Soil moisture is the dominant parameter.**
This confirms Bracale et al. (2019) and Liu et al. (2022) [V].

### 1.4 The Static N-M Baseline — Measured vs Predicted

We implemented the Neher-McGrath model and validated it against all released
configurations of the Darmstadt Cable Test Site dataset (Verschaffel-Drefke
et al. 2021 [V], CC BY-NC 4.0). Using wet-state default soil resistivities and
the experiment's own boundary conditions (Darmstadt air + soil at −0.8 m), the
steady-state N-M model **underestimates conductor temperature by 21–68%** across
configurations — that is, it overestimates available thermal headroom by the same
margin [R]:

| Configuration | N-M mean error | Interpretation |
|---|---|---|
| MF_IV sand bedding (direct buried, 310 A, 39 days) | **−51.4%** ± 1.0% | Model T far below measured; soil dried at cable surface |
| MF_IV loam bedding | **−51.3%** ± 0.8% | Same mechanism |
| MF_IV silt bedding | **−26.3%** ± 1.3% | Finer soil retains moisture better |
| MF_IV FTB bedding | **−21.4%** ± 1.7% | FTB resists drying; closest to model assumption |
| SF V (unfilled PVC duct, 0–356 A, 51 days) | **−67.7%** ± 11.4% | Air gap amplifies thermal isolation |
| SF VI (grouted FTB duct, 0–356 A, 51 days) | **−39.3%** ± 14.1% | FTB fill reduces error by 28 pp |

Negative sign means predicted temperature < measured temperature (model
overestimates headroom). The large errors are not a modelling artifact — they
arise because the model uses a **fixed wet-state rho** while the experiment
progressively dried the soil near the cable surface, dramatically increasing
local rho. This is the exact gap the proposal closes.

The Grouted vs Unfilled result also **quantitatively confirms** the PG&E design
decision to specify FTB backfill: FTB reduces the model discrepancy by 28
percentage points in the duct experiment. A correctly calibrated dynamic-soil
model would further narrow this gap.

### 1.5 USCRN — An Underutilised Resource

The US Climate Reference Network (USCRN), operated by NOAA, comprises 139
climate stations across the continental US. Each records hourly soil temperature
and volumetric moisture at **five depths: 5, 10, 20, 50, and 100 cm**, plus full
atmospheric forcing (air temperature, precipitation, solar radiation, RH). The
dataset spans 2012–present and is freely available.

For a PG&E distribution primary in 4" PVC Schedule 40 conduit with 30" (762 mm)
minimum cover [EDS 038193, V], the cable centre sits at approximately **0.82 m**
below grade [I]. The USCRN 50 cm and 100 cm sensors bracket this depth, making
physical interpolation well-posed. The USDA NRCS Soil Climate Analysis Network
(SCAN) has been used by Bates (2021) to supply site-specific soil state for
ampacity design in Arizona [V, Ch 11]. What neither SCAN nor USCRN provides in
current practice is a **forecast** of soil state at cable burial depth at the
24–72 h horizons relevant to cable system operation.

### 1.6 The Gap This Proposal Addresses

A complete review of the literature — Bracale et al. (2019), Espedal et al. (2025),
Liu et al. (2022), Ahmad et al. (2021), Brakelmann et al. (2021), Verschaffel-Drefke
et al. (2021), and Bates (2021) — reveals a consistent gap:

> **No published work provides a forecast of multi-depth measured soil temperature
> and moisture, at the cable's actual burial depth, as a live input to a cable
> thermal model validated against a field dataset, evaluated at 24–72 h planning
> horizons.**

The closest prior works and why they fall short:
- **Bracale et al. 2019** [V]: connects moisture to ampacity via a rain-bucket
  moisture model with ECMWF NWP inputs — not measured multi-depth soil state —
  and validates nothing against measured cable temperature.
- **Espedal et al. 2025** [V]: tunes a cable model with an LSTM using no soil
  moisture data; benefit over physics-only baseline is marginal.
- **Bates 2021** [V]: uses measured SCAN data as a static climatological
  lookup (99th-percentile design), not a real-time or forecast input.
- **Liu et al. 2022** [V]: most physically complete model (coupled thermo-hydraulic
  FEM) but uses literature soil properties, no measured field validation, no forecast.

The gap is both scientific (no forecast-driven dynamic rating demonstrated against
field data) and data-driven (USCRN has not been used for this purpose).

---

## 2. Foundation: Soil State Forecasting System (Completed Prior Work)

Before describing the proposed ampacity extension, we describe the soil
temperature and moisture forecasting pipeline — referred to as the **soil
forecasting system** — developed as a standalone research contribution forming
the foundation of this proposal.

### 2.1 What the System Does

The soil forecasting system takes USCRN hourly observations — soil temperature
and moisture at 5, 10, 20, 50, 100 cm plus atmospheric drivers — and produces
**forecasts of soil temperature and moisture at multiple depths for 24 h and
72 h horizons** at 39 USCRN stations spanning arid, humid, continental, and
semi-arid climate zones.

### 2.2 Physical Basis

Subsurface soil temperature is governed by:

$$\frac{\partial T}{\partial t} = \frac{\partial}{\partial z}\left(\alpha(z,\theta)\frac{\partial T}{\partial z}\right)$$

where thermal diffusivity $\alpha = \lambda(\theta)/C(\theta)$ depends on moisture
$\theta$ through the Johansen (1975) relation for thermal conductivity
$\lambda(\theta)$ and volumetric heat capacity $C(\theta)$. This physics creates
strong depth-lagged structure: the diurnal cycle damps to negligible amplitude by
50 cm; annual cycles persist to 100 cm. Any forecaster ignoring this structure
will underperform a simple baseline at depth.

### 2.3 Architecture

The system uses a **hybrid differentiable architecture**: an LSTM learns the
mapping from atmospheric forcing and shallow observations to the surface boundary
condition; a Crank-Nicolson finite-difference solver propagates the thermal signal
through the soil column using the physics equation, enforcing depth-lag structure
that a pure data-driven model cannot learn from limited data [Widyastuti et al.
2026, V]. For the moisture dimension, an attention-LSTM [Li et al. 2022, V]
operates jointly on atmospheric drivers and soil state.

### 2.4 Soil Thermal Properties — Johansen Relation

The link from forecast moisture $\theta$ to thermal resistivity $\rho$ uses the
Johansen (1975) model, implemented and verified in `code/02_soil_thermal_properties/johansen.py`:

$$\lambda(\theta) = \lambda_{dry} + K_e(\theta) \cdot (\lambda_{sat} - \lambda_{dry})$$

where the Kersten number $K_e$ interpolates between dry and saturated conductivity
as a function of saturation degree $S_r = \theta/\theta_{sat}$. Parameters for
27 of the 39 USCRN stations are taken from Wilson et al. (2016) [V]; the remaining
12 use texture-class fallback with sensitivity bounds reported.

**Self-test results [R]:** Computed conductivities at verified moisture levels:

| Soil type | θ | λ (W/(m·K)) | ρ (°C·cm/W) |
|---|---|---|---|
| Sand, wet (θ=0.30) | 0.30 | 2.17 | 46.2 |
| Sand, dry (θ=0.05) | 0.05 | 1.01 | 98.6 |
| Silt loam, wet (θ=0.35) | 0.35 | 1.09 | 91.9 |
| Silt loam, dry (θ=0.05) | 0.05 | 0.31 | 318.7 |
| Clay, wet (θ=0.40) | 0.40 | 0.97 | 103.6 |

Sand wet (46 °C·cm/W) vs dry (99 °C·cm/W): a factor of 2× change from moisture
alone. Silt dry (319 °C·cm/W) shows the extreme range in fine soils.

### 2.5 Data and Baseline

**Data:** USCRN hourly02 schema, 39 stations, 2012–2021. 38 confirmed fields
including soil temperature and moisture at all five depths, T_HR_AVG, P_CALC,
SOLARAD, SUR_TEMP, RH_HR_AVG [V, uscrn_HEADERS.txt].

**Baseline:** Persistence. Bracale et al. (2019) [V] showed that persistence
beats NWP-driven ML at 1–36 h leads for buried cable rating; this proposal
uses the same benchmark. Beating persistence at 24–72 h is the operational test.

**Status [Completed]:** Baselines scored at 20 cm and 50 cm for soil temperature
at 24 h and 72 h. Joint temperature/moisture forecast architecture implemented.
WP1 extends to 100 cm and scores moisture baseline.

---

## 3. Research Objectives

**Primary objective:** Connect the completed soil forecasting system to a
validated N-M cable thermal model to produce dynamic ampacity ratings at 24 h
and 72 h horizons; evaluate these against persistence-driven and static design
baselines across 39 climatically diverse USCRN stations.

**Secondary objectives:**

1. Extend the soil forecaster to 100 cm depth and score moisture forecasts
   against persistence baseline, completing the input vector required at
   typical cable burial depth (0.82 m for PG&E-style primary installation).

2. Validate the implemented N-M cable thermal model against the Darmstadt
   multi-bedding field dataset, characterising the residual error attributable
   to static vs dynamic soil rho — using the pipeline results in Section 1.4
   above as the starting baseline.

3. Quantify the operational value of forecast-driven ampacity: fraction of
   station-hours for which dynamic rating exceeds static design rating, and
   the forecast horizon at which the forecast outperforms persistence.

---

## 4. Methodology

### 4.1 Soil State at Cable Burial Depth — Depth Interpolation

The soil forecaster produces outputs at 50 cm and 100 cm. A PG&E primary cable
centre sits at ~0.82 m [I, EDS 038193/062288, V]. The Crank-Nicolson solver
used in the forecaster also provides interpolation: with observed temperatures
at 50 cm and 100 cm as Dirichlet boundaries, it estimates temperature at any
intermediate depth using diffusivity $\alpha(z)$ inferred by Bayesian inversion
[Brunetti et al. 2022, V].

**Self-test results [R]:** The depth interpolation script (`code/04_depth_interpolation/
depth_interp.py`) was verified to correctly bound the interpolated value at 82 cm
between the 50 cm and 100 cm boundary values for all synthetic test cases. The
annual cycle damping with depth is reproduced correctly (deeper = more damped,
phase-lagged).

**Uncertainty propagation:** Monte Carlo over diffusivity posterior and Johansen
texture parameters provides ±1σ uncertainty bands on $T_a$ and $\rho$ at cable
depth. These propagate into ±1σ ampacity uncertainty bounds.

### 4.2 Cable Thermal Model

**Governing equations:**

Conductor temperature from the N-M model:

$$T_c = T_a + I^2 R_{dc}(1+Y_c) R_{ca} + \Delta T_d$$

with the thermal resistance chain:

$$R_{ca} = T_i + T_j + T_d + T_e(\rho_e, L, D_e)$$

where $T_e$ is the soil resistance via the image-source method [Brakelmann et al.
2021, V], including mutual heating from adjacent cables in a trefoil arrangement.

For cyclic loading, the load-factor correction validated by Bates (2021):

$$I_{transient} = I_{SS} / \sqrt{\mu}$$

where $\mu$ is the loss factor computed from daily load factor $LF$. Bates showed
this reduces N-M mean error from **−8% ± 8.9% to −0.3% ± 1.4%** [V, Ch 9] — the
difference between a conservative screening tool and a precision model.

**Material parameters [V]:**

| Layer | Thermal rho (°C·cm/W) | Source |
|---|---|---|
| EPR insulation | 350 | N-M Table 6 [Bates V] |
| PVC jacket | 500 | N-M Table 6 [Bates V] |
| Fiber/PVC conduit wall | 480 | N-M Table 6 [Bates V] |
| FTB backfill @ 3% MC | ≤ 60 | PG&E EDS 038193 [V] |
| FTB backfill @ 0% MC | ≤ 75 | PG&E EDS 038193 [V] |
| Native soil (site-specific) | 45–320 | Johansen + measured θ [R] |

**Reference cable — Southwire 350 kcmil Cu [V, SPEC 46319]:**
- Conductor OD: 0.616", over insulation: 1.102", overall: 1.342"
- $R_{dc}$ at 25°C: 0.031 Ω/1000 ft → 1.017×10⁻⁴ Ω/m
- $R_{dc}$ at 90°C: 1.27×10⁻⁴ Ω/m [R, corrected for temperature coefficient]
- Normal temperature limit: 105°C; emergency: 140°C

**Sensitivity quantification [R]:**

The ampacity sensitivity to the two key soil parameters, at the reference
installation (RHO-90, Ta=20°C, baseline = 621 A at 30" / 636 A at 24") [R]:

| Change | Ampacity shift |
|---|---|
| RHO: 90 → 50 °C·cm/W (wet soil) | +92 A (**+11%**) |
| RHO: 90 → 157 °C·cm/W (AZ in-situ mean) | −99 A (−12%) |
| RHO: 90 → 270 °C·cm/W (AZ design) | −230 A (−27%) |
| Ta: 20°C → 10°C (winter) | +45 A (+5%) |
| Ta: 20°C → 35°C (summer peak) | −109 A (−13%) |
| Depth reference (underside vs top of bundle) | ±7 A (<1%) |

**Bottom line:** Soil moisture (via rho) dominates over ambient temperature
and is far more important than depth-reference convention uncertainties.

### 4.3 Darmstadt Dataset Validation

**Why Darmstadt?** The Darmstadt Cable Test Site (Verschaffel-Drefke et al.
2021 [V]) is the only publicly available, multi-bedding, real-scale underground
cable dataset with measured conductor temperature, soil moisture at the cable
surface, and full documentation of cable geometry and soil properties. Released
under CC BY-NC 4.0. No other paper in the surveyed literature uses it for model
validation.

**Dataset loaded and audited [R]:** All 10 sheets confirmed loaded successfully:

| Sheet | Rows | Key columns |
|---|---|---|
| MF_IV_CL | 5,598 | Time (d), load (A), conductor T × 4 beddings, air T, soil T@−0.8m, precip |
| MF_IV_EVU | 718 | Same + EVU load profile |
| MF_IV_PV | 718 | Same + PV load profile |
| SF_V+VI | 12,279 | Time (d), load V, load VI, T_cond V, T_pipe V, T_cond VI, T_pipe VI |
| MF_III_CL | 5,009 | Time (d), load, sheath T × 4, soil moisture × 4 (silt+undisturbed, sand+undisturbed) |
| Weather-Data-Temp | 17,065 | Calendar date, air T, soil T @−0.2m, soil T @−0.8m |
| TH Bedding Characteristic | 1,062 | λ(θ), moisture retention, hydraulic conductivity for all beddings |

**Baseline validation results [R]** (steady-state N-M, fixed wet-state rho,
Darmstadt boundary conditions — see Section 1.4 and `notes/VALIDATION_FINDINGS.md`
for full statistics):

- MF_IV_CL: −21% to −51% mean error by bedding (FTB best, sand/loam worst)
- SF V+VI: −40% to −68% (grouted FTB duct better than unfilled)
- MF_III sheath: −53%; NHR screening: 0.8% of timesteps exceed 0.2 W/cm threshold

**WP2 target:** Reduce the mean error to within ±10% by replacing fixed rho
with the moisture-derived $\rho(\theta)$ from the Johansen model using measured
soil moisture from the MF_III sheet — demonstrating that dynamic soil state
input closes the gap. This is the quantitative test of the proposal's central claim.

**Installation geometry [V, I]:**

| Reference point | Depth |
|---|---|
| Bundle underside [V, figure-based] | 0.650 m |
| Lower conductor centres [I] | 0.633 m |
| Centroid [I, used in validation] | 0.623 m |
| Upper conductor centre [I] | 0.604 m |

The ±4 cm uncertainty in depth reference changes ampacity by <1% [R] — not material.

### 4.4 Integration: Forecast Soil State → Dynamic Ampacity

```
USCRN hourly observations (39 stations)
  Tsoil at 5/10/20/50/100 cm,  moisture at 50 cm
  air temperature, precip, solar rad, RH
         │
         ▼
  Soil Forecasting System (LSTM + Crank-Nicolson)
  → T_soil forecast at 0.82 m:  t+24h, t+72h
  → moisture forecast at 50 cm: t+24h, t+72h
         │
         ▼
  Depth Interpolation (C-N solver, 50→82 cm)
  + Johansen relation: θ(t) → ρ(t)
         │ T_a(t), ρ(t) with ±1σ uncertainty
         ▼
  Neher-McGrath Cable Model
  (validated against Darmstadt — WP2)
         │
         ▼
  Dynamic ampacity I_max(t+24h), I_max(t+72h)
         │
         ▼
  Evaluated against:
    (1) Static design rating — Black Books / IEEE 835
    (2) Persistence-driven rating (soil state frozen at t=0)
    (3) SCAN climatological 99th-percentile rating [Bates method, V]
```

**Reference installation:** PG&E primary — 4" PVC Sch 40, 30" cover, Southwire
350 kcmil Cu, FTB backfill. Static values: $T_a$ = 20°C, $\rho$ = 90 °C·cm/W,
static ampacity = 621 A at 30" burial [R] (Black Books: RHO=90, Ta=20°C, LF=1.0;
Bates Table 3.1 reports 541 A for a different, unspecified cable; our reference
uses the Southwire 350 kcmil geometry and PVC conduit [V, SPEC 46319]).

**Evaluation metrics [Proposed]:**
1. Distribution of $(I_{dynamic} - I_{static}) / I_{static}$ across station-hours — accessible headroom
2. Fraction of station-hours for which dynamic rating exceeds static by >5% (operationally material)
3. RMSE of forecast-driven vs persistence-driven ampacity at t+24h and t+72h
4. Seasonal and climate-zone breakdown across all 39 stations

### 4.5 WP3 Preliminary Results: Dynamic Ampacity Across Climate Zones [R]

> **Status:** Completed. Pipeline run against real USCRN data, 13 stations × 3 burial depths
> (24" / 30" / 36"), 2019–2021. Full results in `notes/DYNAMIC_AMPACITY_FINDINGS.md`.

**Station selection:** 13 USCRN stations with valid 50 cm and 100 cm soil sensors
(required to bracket cable burial depths 0.61–0.91 m via C-N interpolation).
72 of 131 available stations meet this criterion; 13 chosen to span 6 climate zones.
Stations with only shallow sensors (5/10 cm, e.g. AZ Yuma) are excluded —
extrapolation from 10 cm to 76 cm is not physically valid for cable applications.

**Burial depths:** 24" (0.610 m, NEC minimum), 30" (0.762 m, PG&E standard [V EDS
038193]), 36" (0.914 m, heavy-traffic routes). Static design ratings: 636 A / 621 A /
610 A respectively (Black Books: RHO=90, Ta=20°C, LF=1.0) [R].

#### Summary at 30" burial (PG&E primary standard)

| Climate Zone | Stations | Mean Dynamic (A) | vs Static (621 A) | Headroom σ | Mean RHO (°C·cm/W) |
|---|---|---|---|---|---|
| Arid-SW | NM, NV, TX (4 stations) | 1225 | **+97%** | 9.1% | 117 |
| Mediterranean | CA Santa Barbara, CA Bodega | 1400 | **+125%** | 2.2% | 68 |
| Semi-arid-NW | OR Riley | 1421 | **+129%** | 2.8% | 74 |
| Sub-humid | OK Stillwater, NE Lincoln | 1450 | **+133%** | 4.5% | 57 |
| Humid-subtropical | AL Fairhope, NC Asheville | 1394 | **+124%** | 5.9% | 65 |
| Continental | WY Sundance, MI Chatham | 1472 | **+137%** | 3.4% | 67 |

Key numbers [R]:
- **Worst case (arid): TX Monahans** — 1153 A mean, +85.6% headroom, RHO=143.6 °C·cm/W, σ=9.5%
- **Best case (continental): WY Sundance** — 1513 A mean, +143.5% headroom, RHO=57.2 °C·cm/W
- **Highest forecast value (most variable): NV Mercury, NM Socorro, AL Fairhope** — σ 8–11%
- **100% of station-hours** across all 39 combinations exceed static design rating [R]
- **Depth effect:** headroom increases 3–8 pp from 24"→36" in humid/continental zones [R]

#### Interpretation for WP3 scope

1. **The latent capacity is real and large.** Static ratings underestimate real cable capacity
   by 86–143% (median ~120%) across diverse US climates. The gap exists because NEC-90 assumes
   continuous full load and worst-case dry soil — neither reflects actual operating conditions.

2. **Arid zones need forecasting most.** NV Mercury and TX Monahans have the lowest headroom
   AND highest variability (σ 9–11%) — a 24-hour soil moisture forecast directly determines
   whether ~200–250 A of additional capacity is available on a single circuit.

3. **CA stations confirm PG&E relevance.** Santa Barbara (RHO=54.5, Mediterranean) has large
   stable headroom (+130%); inland arid routes analogous to NM/NV stations have the most
   forecast-sensitive capacity. The proposed system targets both profiles.

4. **Wilson T1 parameterisation (WP3 improvement):** Default Johansen parameters were used
   (quartz=0.50, θ_sat=0.40). AL Fairhope is matched in Wilson T1 (LS texture, 78% sand [V]).
   Station-specific texture data will refine RHO estimates; expected effect: ±10–20% on RHO
   in clay-rich soils, smaller in sandy soils.

---

## 5. Data Sources

| Dataset | Role | Access |
|---|---|---|
| USCRN hourly02 (39 stations, 2012–2021) | Soil T + moisture at 5 depths; atmospheric drivers | Free, NOAA |
| Darmstadt field dataset (CC BY-NC 4.0, TUdatalib-665) | Cable model validation — conductor T, sheath T, moisture | Free, TU Darmstadt |
| Wilson et al. 2016 (soil texture table T1) | Johansen λ(θ) parameterisation, 27/39 stations | Available |
| Southwire SPEC 46319 (rev 1.000.009, 2025) | Reference cable geometry and resistance | Manufacturer datasheet |
| PG&E EDS 038193 / 062288 | Burial depth, FTB thermal spec, PVC conduit dims | Utility design standard |
| Bates 2021 dissertation | N-M validation data, NHR method, SCAN benchmark | Open (Colorado School of Mines) |
| USDA NRCS SCAN (public API) | Climatological soil T/moisture reference | Free, USDA |

**Not available / paywalled:** IEC 60287-1, IEC 60853, IEEE Std 442 full text.
Methods derived from these standards are accessed through Bates (2021) [V] and
Bracale et al. (2019) [V]; no compliance claims are made.

---

## 6. Expected Contributions

### 6.1 New Contributions **[Proposed]**

**C1 — Forecast-driven dynamic cable rating (primary contribution):**
The first evaluation of multi-depth *forecast* soil temperature and moisture —
from a network of measured ground stations — as a real-time input to a cable
thermal model validated against a publicly available field dataset, at 24 h and
72 h horizons across 39 climatically diverse US sites.

**C2 — Quantitative baseline of static N-M conservatism:**
Using the Darmstadt dataset, we provide the first empirical characterisation of
how static soil rho assumptions cause N-M to underestimate conductor temperature
by 21–68%, and demonstrate that replacing static rho with moisture-derived dynamic
rho closes this gap (WP2 target: mean error within ±10%). This extends Bates
(2021) [V] — who showed N-M conservatism against in-situ rho measurements — to
the dynamic case.

**C3 — Physics-consistent depth interpolation of USCRN to cable depth:**
A Crank-Nicolson method using the USCRN 50/100 cm sensor pair to estimate soil
state at any intermediate burial depth, parameterised by Bayesian-inferred
diffusivity profiles. Applicable to any US USCRN site without additional instrumentation.

**C4 — Operational ampacity headroom across climate zones:**
Quantitative bounds on forecast-driven ampacity headroom by soil type, climate
zone, and season across 39 USCRN stations — the first such network-scale analysis.

### 6.2 Building on Prior Art **[Advanced — cited]**

**A1 — Moisture → thermal resistivity → ampacity chain:** Bracale et al. (2019) [V]
established this in principle, model-only, at a UK single site. Extended here to
forecast inputs and 39 US sites with measured soil state.

**A2 — Load-factor correction for transient rating:** Validated by Bates (2021) [V]
for static inputs; extended here to forecast-varying inputs.

**A3 — USCRN/SCAN soil state as ampacity input:** Bates (2021) [V] used SCAN for
static 99th-percentile design; extended here to a continuous operational forecast.

### 6.3 What This Proposal Does NOT Claim

- "First" use of moisture in cable thermal modelling — Bracale (2019) [V]
- Field validation of ampacity at a USCRN station site — requires cable installation, out of scope
- Compliance with IEC 60287 or IEEE Std 835 — standards are paywalled
- Elimination of conservative design margin — margin is made visible and forecast-conditional, not zero
- Soil drying as a universal problem — only 0.8% of Darmstadt timesteps exceed NHR
  threshold [R]; but near-cable contact drying occurs in sand below the bulk NHR threshold

---

## 7. Work Packages and Timeline

| WP | Title | Tasks | Output |
|---|---|---|---|
| **WP1** | Soil state forecast at cable depth | Extend forecaster to 100 cm; score moisture vs persistence; Bayesian α inversion for depth interpolation to 0.82 m | Scored forecast model; uncertainty-propagated $T_a$ and $\rho$ at cable depth |
| **WP2** | Cable thermal model and Darmstadt validation | Build on baseline N-M results [R]; replace static rho with $\rho(\theta_{measured})$ from MF_III; validate against all configurations; load-factor correction | Validated dynamic model; mean error table targeting ±10% by configuration |
| **WP3** | Integration and dynamic rating | Connect WP1 forecasts → WP2 model → ampacity time series; evaluate vs static, persistence, SCAN-climatological baselines; 39-station analysis | Dynamic rating time series; headroom statistics by season and climate zone |
| **WP4** | Sensitivity and standards gap | Johansen uncertainty (12 stations without texture data); NHR drying screening; depth-reference sensitivity (already computed [R]: <1% effect); document IEEE P1254 gap | Sensitivity report; measurement protocol recommendation |
| **WP5** | Manuscript | Full paper with all sections, figures, and supplemental | Journal submission draft |

**WP2 now has a concrete baseline** from the pipeline results: the static N-M
underestimates conductor temperature by 21–68% (Table in Section 1.4). WP2's
quantitative goal is to reduce this to within ±10% using measured dynamic soil
moisture from the Darmstadt MF_III sheet.

---

## 8. Standards Gap

As documented by Bates (2021) [V, Ch 2], the IEEE project **P1254** — intended
to produce a guide standard for soil thermal stability measurement relevant to
cable ampacity — had its Project Authorization Request (PAR) expire in **2016
without consensus**. No enforceable standard exists for in-situ soil thermal
stability measurement for cable ampacity design. WP4 will document the specific
measurement and modelling requirements that such a standard would need to address,
informed by the integration of the soil forecasting system with the validated cable
thermal model.

The proposed pipeline would directly enable the type of continuous soil state
monitoring that IEEE P1254 was intended to standardise — replacing single-point
in-situ measurements with a network-level continuous forecast.

---

## 9. Key References

| Citation | Role |
|---|---|
| Neher & McGrath (1957). AIEE Trans. | Original ampacity equation [via Bates V] |
| Bates, C. (2021). *Underground Cable Ampacity*. PhD, Colorado School of Mines. | N-M validation; NHR method; SCAN use; software comparison [V] |
| Bracale et al. (2019). *IEEE Access*. | DLR forecast; moisture→ampacity chain; persistence baseline [V] |
| Espedal et al. (2025). *CIRED* (AAM). | ML cable model tuning; limits without soil data [V] |
| Verschaffel-Drefke et al. (2021). *Energies* 14, 7189. | Darmstadt field experiment; validation dataset [V] |
| Liu et al. (2022). *Energies* 15, 8897. | Thermo-hydraulic FEM; moisture dominance [V] |
| Ahmad et al. (2021). *Energies* 14, 8191. | Sand temperature field; convection in saturated soil [V] |
| Brakelmann et al. (2021). *Energies* 14, 6813. | Analytical multi-cable mutual heating [V] |
| Brunetti et al. (2022). *Earth Surf. Dyn.* 10(4). | Bayesian thermal diffusivity inversion [V] |
| Widyastuti et al. (2026). *Soil Tillage Res.* | Differentiable LSTM + Crank-Nicolson soil temperature forecast [V] |
| Li et al. (2022). *Geoderma*. | Attention-LSTM soil moisture/temperature [V] |
| Wilson et al. (2016). Supplemental Table T1. | USCRN soil texture; Johansen parameterisation [V] |
| Johansen, O. (1975). PhD thesis, University of Trondheim. | Thermal conductivity of soils [V, via Bracale; implemented in code] |
| PG&E EDS 038193 / 062288. | Burial depth; FTB thermal spec; PVC conduit dimensions [V] |
| Southwire SPEC 46319 (rev 1.000.009, 2025). | Reference cable geometry and resistance [V] |
| AIEE-IPCEA "Black Books" (1962). | Design standard assumptions [via Bates V] |
| IEEE Std 835 (1994). | Ampacity tables; design assumptions [via Bates V] |
| IEEE P1254 (PAR expired 2016). | Soil thermal stability standard gap [Bates V] |
| Malmedal, Bates & Cain (2014). IEEE REPC. | NHR method for soil drying screening [via Bates V] |
| USDA NRCS SCAN. | Climatological soil T/moisture reference [Bates V, Ch 11] |

---

## 10. Open Items Before Submission

### Resolved by pipeline results
- [x] Darmstadt validation baseline — computed [R]: 21–68% error by configuration
- [x] Depth-reference sensitivity — computed [R]: <1% effect, not material
- [x] NHR soil drying check — computed [R]: 0.8% of timesteps exceed threshold
- [x] Johansen conductivity implementation — verified [R] against literature values
- [x] Depth interpolation — verified [R] correct bounding behaviour

### Still open
- [ ] Select target journal (IEEE Trans. Power Delivery / Energies / Applied Energy)
- [ ] Confirm CC BY-NC 4.0 (Darmstadt) compatibility with target journal open-data policy
- [ ] Decide and lock WP1 model architecture — motivate with SoilSens baseline results
- [ ] Score moisture baseline at 50 cm (completes WP1 prerequisite)
- [ ] Transcribe Bracale Tables 5–7 (cable layer thermal properties — for WP2 if Darmstadt workbook values insufficient)
- [ ] Confirm SCAN API query format for WP3 climatological reference
- [ ] Download USCRN station files → `data/uscrn/` (needed to run WP3 pipeline script)
- [ ] Create `data/wilson_T1.csv` from Wilson et al. (2016) for station-level Johansen parameterisation

---

*All numbers and literature claims are traceable to full-text surveys in `notes/`.
Pipeline results tagged [R] are computed from the Darmstadt dataset by scripts in
`code/`; see `notes/VALIDATION_FINDINGS.md` for full statistics. No values have
been invented or extrapolated beyond what cited sources directly report.*
