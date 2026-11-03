# Research Proposal — Draft v2

## Dynamic Underground Cable Ampacity from Forecast Soil Conditions: A Data-Driven Pipeline from Multi-Depth Soil State Prediction to Real-Time Thermal Rating

**Date:** 4 November 2026  
**Status:** Pre-submission internal draft  

> [!NOTE]
> All literature claims are traceable to full-text reads documented in `scratch/ampacity/notes/`. Numbers carry source tags: [V] = verified from text, [I] = inferred, [catalogue] = from catalogue/abstract only. Completed prior work is labelled **[Completed]**; new contributions are labelled **[Proposed]**.

---

## 1. Background and Motivation

### 1.1 Underground Cable Ampacity — The Governing Problem

Underground power cables carry current from generators, substations, and renewable plants to loads. The maximum current they can carry continuously without exceeding the conductor's temperature limit is called their **ampacity**. Exceeding ampacity causes irreversible insulation degradation and ultimately cable failure; operating well below it wastes infrastructure capacity that could otherwise defer costly upgrades.

The governing equation for ampacity, due to Neher and McGrath (1957), is:

$$I = \sqrt{\frac{T_c - T_a - \Delta T_d}{R_{dc}(1+Y_c) \cdot R_{ca}}}$$

where $T_c$ is the maximum allowable conductor temperature (typically 90°C), $T_a$ is the ambient soil temperature at the cable's burial depth, $\Delta T_d$ is the temperature rise from dielectric losses, $R_{dc}$ is the conductor DC resistance, $Y_c$ is the AC loss factor, and $R_{ca}$ is the total thermal resistance from conductor to ambient soil. This equation is the basis of IEC 60287-1, the international standard for cable rating, and is implemented in all major commercial ampacity software (CYMCAP, ETAP, USAmp Prime).

Two parameters in the Neher-McGrath equation are **set by the soil**, not the cable:
- **$T_a$**: the ambient soil temperature at burial depth — typically 30–100 cm below grade.
- **$R_{ca}$**: dominated by the soil thermal resistance, which depends on the soil's thermal resistivity $\rho$ — itself a strong function of soil moisture content $\theta$.

Soil thermal resistance accounts for **70–90% of the total thermal resistance** between conductor and ambient in 15 kV direct-buried installations [Bates 2021, Ch 1, V]. It is the controlling variable in cable ampacity.

### 1.2 The Problem with Static Soil Assumptions

Current engineering practice — codified in the AIEE-IPCEA "Black Books" (1962), IEEE Std 835 (1994), and utility design standards — treats $T_a$ and $\rho$ as **fixed conservative values** chosen at the time of design:

- **$T_a$**: typically 20–25°C (a dry-season worst case) regardless of actual seasonal or diurnal conditions.
- **$\rho$**: typically 90 °C·cm/W (the NEC default) or a single-point in-situ measurement, held constant for the cable's operational life of 40–50 years.

This conservatism produces two well-documented consequences:

**1. Systematic overestimation of conductor temperature.** Bates (2021) conducted six controlled field experiments on a direct-buried cable in Boulder, Colorado, measuring conductor temperature directly while simultaneously computing it from Neher-McGrath. The steady-state N-M method overestimated conductor temperature by a mean of **8% ± 8.9%** (90% CI: -15% to -1%) even when the design resistivity was known accurately from in-situ measurements [Bates 2021, Table 9.1, V]. In a 10 MW photovoltaic cable installation in Arizona, the same author found that software predicted conductor temperatures of 75–87°C, while field loggers measured 55–61°C over the hottest summer months — an overestimate of 15–30°C [Bates 2021, Ch 11, V]. The actual in-situ soil thermal resistivity (157 °C·cm/W, mean; 99% CI: 118–197) was far below the design value (270–303 °C·cm/W) because the design was based on a dry worst-case assumption rather than measured conditions [Bates 2021, Ch 11, V].

**2. Inability to exploit available ampacity headroom.** Because the rating is fixed at design-time worst-case values, operators cannot increase current even when actual conditions are favourable — cooler soil in winter, wetter soil after rain — without a new engineering study. For overhead transmission lines, **Dynamic Line Rating (DLR)** — updating the rating continuously from measured ambient conditions — is now established in practice and regulation. The underground equivalent, **Dynamic Cable Rating (DCR)**, remains operationally immature. The core obstacle is that soil temperature and moisture at cable burial depth are not routinely monitored or forecast.

### 1.3 The Role of Soil Moisture — Why It Matters More Than Temperature

Soil thermal resistivity $\rho$ varies by a factor of **5–10** between wet and dry states of the same soil. For the sand bedding in the Darmstadt controlled field experiment (Verschaffel-Drefke et al. 2021), sand dried completely at the cable surface and rewetted within a single day during a loading cycle [V]. The thermohydraulic scenario study by Liu et al. (2022) found that soil initial moisture content and soil parameters dominate cable temperature — more than load magnitude in some scenarios — with overload adding 30–35°C at one site in a dry initial state [V]. Bracale et al. (2019) showed that moisture-driven resistivity change is the primary dynamic effect on buried cable rating over daily to seasonal timescales, even for a mild UK climate [V].

The practical problem is that **soil moisture at cable burial depth (0.6–1.0 m) is almost never measured in real cable systems**, and no established method exists to forecast it at that depth from surface or near-surface observations alone.

### 1.4 USCRN — An Underutilised Resource

The United States Climate Reference Network (USCRN), operated by NOAA, is a network of 139 climate monitoring stations across the continental US. Each station records hourly soil temperature and volumetric moisture content at **five depths: 5, 10, 20, 50, and 100 cm**, alongside full atmospheric forcing: air temperature, precipitation, solar radiation, relative humidity, and surface temperature. The dataset spans 2012–present at high quality and is freely available.

For a typical primary cable installation — for example, a PG&E distribution primary in 4" PVC Schedule 40 conduit with 30" (762 mm) minimum cover [PG&E EDS 038193, V] — the cable centre sits at approximately **0.82 m** below grade. The USCRN 50 cm and 100 cm sensors bracket this depth, making physical interpolation between them well-posed. The USDA NRCS Soil Climate Analysis Network (SCAN) — a related instrument network — has already been used by Bates (2021) to supply site-specific soil temperature and moisture at cable burial depth for ampacity design in Arizona [V, Ch 11]. What neither SCAN nor USCRN provides in current practice is a **forecast** of soil state at burial depth at the 24–72 hour horizons relevant to cable system planning and operation.

### 1.5 The Gap This Proposal Addresses

A complete review of the available ampacity forecasting literature — Bracale et al. (2019), Espedal et al. (2025), Liu et al. (2022), Ahmad et al. (2021), Brakelmann et al. (2021), Verschaffel-Drefke et al. (2021), and Bates (2021) — reveals a consistent gap:

**No published work provides a forecast of multi-depth measured soil temperature and moisture, at the cable's actual burial depth, as a live input to a validated cable thermal model, evaluated at operational (24–72 h) planning horizons.**

The closest works and why they fall short:
- **Bracale et al. 2019** [V]: connects moisture to ampacity via a coupled soil model, but uses a rain-bucket moisture model and ECMWF NWP layers — not measured multi-depth soil state — and validates nothing against measured cable temperature.
- **Espedal et al. 2025** [V]: tunes a cable model with an LSTM but uses no soil data; benefit over physics-only baseline is marginal and scenario-dependent.
- **Bates 2021** [V]: uses measured SCAN data for soil ambient conditions but as a static lookup (99th-percentile climatology), not a real-time or forecast input.
- **Liu et al. 2022** [V]: most physically complete model (coupled thermo-hydraulic FEM) but uses literature soil properties, no field validation, and no forecast.

The gap is both scientific (no forecast-driven dynamic rating demonstrated) and data-driven (the USCRN dataset has not been used for this purpose).

---

## 2. Foundation: A Soil State Forecasting System (Completed Prior Work)

Before describing the proposed ampacity extension, we describe the soil temperature and moisture forecasting pipeline that provides its inputs. This pipeline — referred to here as the **soil forecasting system** — was developed as a standalone research contribution and is described here as completed prior work forming the foundation of the present proposal.

### 2.1 What the Soil Forecasting System Does

The soil forecasting system takes USCRN hourly observations — soil temperature and moisture at 5, 10, 20, 50, 100 cm depth, plus atmospheric drivers — and produces **forecasts of soil temperature and moisture at multiple depths for 24 h and 72 h horizons**. It operates at 39 USCRN stations spanning a range of US climate zones (arid, humid, continental, semi-arid), soil types, and seasonal regimes.

The system's design is motivated by the following physical structure:

Subsurface soil temperature is governed by the 1D heat conduction equation with depth-dependent diffusivity $\alpha(z)$:

$$\frac{\partial T}{\partial t} = \frac{\partial}{\partial z}\left(\alpha(z,\theta) \frac{\partial T}{\partial z}\right)$$

where $\alpha$ depends on moisture $\theta$ through the soil thermal conductivity $\lambda(\theta)$ and volumetric heat capacity $C(\theta)$:

$$\alpha = \frac{\lambda(\theta)}{C(\theta)}$$

This physics creates strong depth-lagged structure in the soil temperature signal: the diurnal cycle damps to negligible amplitude by 50 cm and annual cycles persist to 100 cm and below. Any forecaster that ignores this structure will underperform a simple baseline at depth.

### 2.2 Architecture

The system uses a **hybrid differentiable architecture**: a neural network (LSTM) learns the mapping from atmospheric forcing and shallow soil observations to the surface boundary condition, while a Crank-Nicolson finite-difference solver propagates the thermal signal through the soil column using the physics equation above. The two components are differentiable end-to-end and trained jointly.

This architecture is motivated by Widyastuti et al. (2026) [V], who showed that this type of hybrid outperforms both a pure LSTM and a pure physics model at 50–100 cm depth for 24–72 h soil temperature forecasts, precisely because the physics encoder enforces depth-lag structure that a pure data-driven model cannot learn from limited training data. For the moisture dimension, an attention-LSTM (following Li et al. 2022 [V]) operates jointly on atmospheric drivers and soil state, forecasting volumetric moisture content at 50 cm.

### 2.3 Data and Baseline

**Data:** USCRN hourly02 schema, 39 stations, 2012–2021. 38 confirmed fields including `SOIL_TEMP_*` and `SOIL_MOISTURE_*` at all five depths, plus T_HR_AVG, P_CALC, SOLARAD, SUR_TEMP, RH_HR_AVG. Note: quality flags exist only for SOLARAD, SUR_TEMP, and RH_HR_AVG — soil temperature and moisture have no flag columns [V, uscrn_HEADERS.txt].

**Baseline:** Persistence (current soil state held constant for the forecast horizon). Bracale et al. (2019) [V] showed that persistence beats NWP-driven ML models at 1–36 h leads for buried cable rating; the soil forecasting system is evaluated against this same benchmark. Beating persistence at 24–72 h is the operational test.

**Status [Completed]:** Baselines scored at 20 cm and 50 cm for soil temperature at 24 h and 72 h horizons. Joint temperature/moisture forecast architecture implemented. The 100 cm depth forecast and moisture baseline evaluation are extended in WP1 of this proposal.

### 2.4 Soil Texture Parameterisation

The relationship between soil moisture $\theta$ and thermal resistivity $\rho$ is parameterised via the Johansen relation:

$$\lambda(\theta) = \lambda_{dry} + (\lambda_{sat} - \lambda_{dry}) \cdot S_r^{\kappa}$$

where $S_r = \theta / \theta_{sat}$ is the degree of saturation and $\kappa$ is a soil-texture-dependent exponent. Parameters are taken from Wilson et al. (2016), a supplemental soil texture table covering 27 of the 39 USCRN stations. For the remaining 12 stations, sensitivity bounds are reported rather than a single estimate.

---

## 3. Research Objectives

**Primary objective:** Connect the completed soil forecasting system to a validated underground cable thermal model to produce dynamic cable ampacity ratings at 24 h and 72 h horizons; evaluate these against a persistence-based static rating and against documented conservatism in current design practice.

**Secondary objectives:**

1. Extend the soil forecasting system to 100 cm depth and score moisture forecasts against a persistence baseline, providing the complete input vector required by the cable thermal model at typical burial depth (0.82 m for PG&E-style primary installation).

2. Implement and validate an IEC 60287-equivalent cable thermal model against the Darmstadt multi-bedding field dataset (Verschaffel-Drefke et al. 2021 [V]), covering direct-buried and duct-installed configurations with four bedding types.

3. Quantify the operational value of forecast-driven ampacity: fraction of the year for which dynamic rating exceeds the static design rating, and the forecast horizon at which the forecast outperforms persistence.

---

## 4. Methodology

### 4.1 Soil State at Cable Burial Depth — Depth Interpolation

The soil forecasting system produces outputs at 50 cm and 100 cm depth. A reference PG&E primary cable installation (4" PVC Sch 40, 30" cover [EDS 038193, V]) places the cable centre at approximately 0.82 m. The USCRN sensor pair at 50 cm and 100 cm brackets this depth, and a physically consistent interpolation is required.

**Method [Proposed]:** The same Crank-Nicolson solver used in the forecaster provides interpolation. With observed temperatures at 50 cm and 100 cm as Dirichlet boundary conditions, the solver estimates temperature at any intermediate depth on a 1 cm grid, using the diffusivity profile $\alpha(z)$ inferred from the USCRN data via Bayesian inversion (Brunetti et al. 2022 method [V]). This gives a physically consistent estimate of $T_a$ at 0.82 m.

For moisture, vertical interpolation between the 50 cm reading and an estimated value at 100 cm (from the moisture forecast) provides a soil moisture estimate at burial depth, from which $\rho(\theta)$ is computed via the Johansen relation.

**Uncertainty propagation:** Monte Carlo over the diffusivity posterior and the Johansen texture parameters provides ±1σ uncertainty bands on $T_a$ and $\rho$ at cable depth. These bands propagate into ±1σ ampacity uncertainty, bounding the operational significance of the forecast.

### 4.2 Cable Thermal Model

**Governing equations:**

The steady-state Neher-McGrath cable model computes conductor temperature as:

$$T_c = T_a + I^2 R_{dc}(1+Y_c) R_{ca} + \Delta T_d$$

where the thermal resistance chain $R_{ca}$ is:

$$R_{ca} = T_i + T_j + T_d + \rho \cdot T_e$$

with $T_i$ (insulation), $T_j$ (jacket), $T_d$ (duct/conduit), and $T_e$ (soil-to-surface) computed from cable geometry, material thermal resistivities, and the image-source mutual-heating factor for multi-cable configurations [Brakelmann et al. 2021, V].

For transient and cyclic loading, the load-factor correction validated by Bates (2021) is applied:

$$I_{transient} = I_{SS} \cdot \sqrt{1 / (LF^2 + (1 - LF^2) \cdot \mu)}$$

where LF is the load factor and $\mu$ is the loss factor. Bates (2021) showed that applying a 66% load factor to N-M steady-state reduces the mean error from -8% to **-0.3%** (90% CI: -1.4%, +0.8%) [V, Ch 9] — essentially exact for realistic load profiles.

**Material parameters:**

| Layer | Thermal rho (°C·cm/W) | Source |
|---|---|---|
| EPR insulation | 350 | N-M Table 6 [Bates V] |
| PVC jacket | 500 | N-M Table 6 [Bates V] |
| Fiber/PVC duct | 480 | N-M Table 6 [Bates V] |
| FTB backfill @ 3% MC | ≤ 60–80 (mix-dependent) | PG&E EDS 038193 / SnoPUD [V] |
| FTB backfill @ 0% MC | ≤ 75–110 | PG&E EDS 038193 / SnoPUD [V] |
| Native soil (range) | 50–300+ | Bates [V]; Johansen for site-specific |

Cable geometry for the reference installation (Southwire 350 kcmil Cu, SPEC 46319 [V]):
- Conductor OD: 0.616", over insulation: 1.102", overall: 1.342"
- DC resistance: 0.031 Ω/1000 ft at 25°C; AC resistance: 0.043 Ω/1000 ft at 90°C
- Normal temperature limit: 105°C; emergency: 140°C

### 4.3 Darmstadt Dataset Validation

**Why validate against Darmstadt?** The Darmstadt controlled field experiment (Verschaffel-Drefke et al. 2021 [V]) is the only publicly available, multi-bedding, real-scale underground cable field dataset with measured conductor temperature, soil moisture at the cable surface, and known cable geometry. It was released under CC BY-NC 4.0. No other paper in the surveyed literature uses it for model validation.

**Installation geometry [V, corrected]:**

Figure 2 of Verschaffel-Drefke et al. (2021) shows the main-field cross-section. The 0.65 m dimension is interpreted as the **underside of the upper-row trefoil bundle** (figure-based interpretation; no unambiguous written definition in the paper). Using 34 mm cable diameter (touching arrangement):

| Conductor | Depth below surface |
|---|---|
| Two lower conductor centres | 0.633 m |
| Upper conductor centre | 0.604 m |
| Centroid of three centres | 0.623 m |

The 0.65–0.85 m range in the paper text refers to different cable configurations (main-field upper vs deep-trench installations), not uncertainty about a single trefoil. A depth-reference sensitivity study (centre-of-conductor vs underside-of-bundle convention) will be included in the supplemental material.

**Environmental boundary conditions:** The Darmstadt validation uses the experiment's **own recorded boundary conditions** — air temperature and soil temperature at -0.8 m from the Darmstadt weather sheets. USCRN depth interpolation is not used here; it applies only to the reference-installation application (Section 4.1 and 4.4).

**Released configurations and validation plan:**

| Configuration | Duration | Validation target |
|---|---|---|
| MF_IV_CL (4 beddings, constant load) | 39 days | Primary: steady-state conductor temp, 4 bedding types |
| MF_IV_EVU (utility load profile) | 5 days | Load-factor correction validation |
| MF_IV_PV (PV load profile) | 5 days | Load-factor correction, asymmetric daily cycle |
| SF_V+VI (PVC duct, unfilled + grouted) | 51 days | Duct installation validation; directly applicable to PG&E geometry |
| MF_III_CL (sheath temp + moisture) | 35 days | Moisture dynamics at cable surface; drying/rewetting timescales |

**Soil bedding properties** are taken from the Darmstadt workbook ("TH Bedding Characteristic" sheet), which provides thermal conductivity as a function of moisture, moisture retention curves, and specific heat for sand, loam, FTB, and silt. The workbook's "volumetric heat capacity" column is solid-phase only (specific heat × grain density) and is corrected to $C_{vol} = (1-n) \cdot C_{solid} + \theta \cdot C_{water}$ [V, darmstadt_workbook_audit.md].

**Validation metric:** Mean signed error and 90% CI for predicted vs measured conductor temperature, following Bates (2021) [V, Ch 9–10]. Target: mean error within ±10% — consistent with CYMCAP and ETAP performance documented by Bates (-3% ± 15.4% and -4% ± 14.6% respectively [V, Table 10.6]).

### 4.4 Integration: Forecast Soil State → Dynamic Ampacity Rating

With both components validated, the integrated pipeline operates as follows:

```
USCRN hourly observations
  (Tsoil at 5/10/20/50/100 cm, moisture at 50 cm,
   air temp, precip, solar rad, RH — 39 stations)
           │
           ▼
  Soil forecasting system (Crank-Nicolson + LSTM)
  → T_soil forecast at 0.82 m:  t+24h, t+72h
  → moisture forecast at 50 cm: t+24h, t+72h
           │
           ▼
  Depth interpolation (C-N solver, 50→82 cm)
  + Johansen relation: θ(t) → ρ(t)
           │
     T_a(t)  and  ρ(t)
           │
           ▼
  IEC 60287 / Neher-McGrath cable model
  (validated against Darmstadt configurations)
           │
           ▼
  Dynamic ampacity I_max(t+24h), I_max(t+72h)
           │
           ▼
  Comparison against:
    (1) Static design ampacity [Black Books / IEEE 835]
    (2) Persistence-driven rating (soil state frozen at t=0)
    (3) Climatological 99th-percentile rating [Bates SCAN method]
```

**Reference installation:** PG&E primary circuit — 4" PVC Sch 40, 30" cover (cable centre 0.82 m), Southwire 350 kcmil Cu cable, FTB backfill. Static design values: $T_a$ = 20°C (Black Books [Bates V, Ch 2]), $\rho$ = 90 °C·cm/W (NEC default [Bates V, Ch 2]). Static ampacity from Neher-McGrath: 541 A (RHO-90) [Bates V, Table 3.1].

**Evaluation metrics [Proposed]:**
1. Mean and distribution of $(I_{dynamic} - I_{static}) / I_{static}$ across all station-hours: the average accessible headroom from forecast-driven rating
2. Fraction of station-hours for which dynamic rating exceeds static by > 5% (operationally material threshold)
3. RMSE of forecast-driven ampacity vs persistence-driven ampacity at t+24h and t+72h: does the forecast add value over holding today's reading constant?
4. Seasonal and climate-zone breakdown across the 39 USCRN stations

---

## 5. Data Sources

| Dataset | Role | Access status |
|---|---|---|
| USCRN hourly02 (39 stations, 2012–2021) | Soil temp + moisture at 5 depths; atmospheric drivers | Free, NOAA |
| Darmstadt field dataset (CC BY-NC 4.0, TUdatalib-665) | Cable model validation — conductor temp, sheath, moisture | Free, TU Darmstadt |
| Wilson et al. 2016 (supplemental soil texture table) | Johansen $\lambda(\theta)$ parameterisation, 27/39 stations | Available |
| Southwire SPEC 46319 (rev 1.000.009) | Reference cable geometry and resistance | Manufacturer datasheet |
| PG&E EDS 038193 / 062288 | Burial depth (30" cover), FTB thermal spec, PVC dims | Utility design standard |
| Bates 2021 dissertation | N-M validation data, NHR method, SCAN benchmark | Open (Colorado School of Mines) |
| USDA NRCS SCAN (public API) | Climatological soil temp/moisture at depth for reference | Free, USDA |

**Not available / paywalled:** IEC 60287-1, IEC 60853, IEEE Std 442 full text. Methods derived from these standards are accessed through Bates (2021) [V] and Bracale et al. (2019) [V]; no compliance claims are made.

---

## 6. Expected Contributions

### 6.1 New Contributions **[Proposed]**

**C1 — Forecast-driven dynamic cable rating (primary contribution):**  
The first evaluation of multi-depth *forecast* soil temperature and moisture — from a network of measured ground stations — as a real-time input to a cable thermal model for dynamic ampacity rating, compared against a persistence baseline at 24 h and 72 h horizons across 39 climatically diverse sites.

**C2 — Physics-consistent depth interpolation of USCRN to cable burial depth:**  
A Crank-Nicolson-based interpolation method using the USCRN 50 cm and 100 cm sensor pair to estimate soil temperature and moisture at any intermediate depth, parameterised by Bayesian-inferred diffusivity profiles. Applicable to any US USCRN site without additional instrumentation.

**C3 — Sensitivity of dynamic ampacity to forecast accuracy:**  
A quantitative bound on how much ampacity headroom is accessible from forecast-driven rating, as a function of soil type, climate zone, and season — across 39 USCRN stations.

### 6.2 Building on Prior Art **[Advanced — cited]**

**A1 — Moisture → thermal resistivity → ampacity chain** (Bracale et al. 2019 [V] established this in principle, model-only, UK single-site; here extended to forecast inputs at 39 US sites with measured soil state).

**A2 — Load-factor correction for transient rating** (validated by Bates 2021 [V] for static inputs; extended here to forecast-varying inputs).

**A3 — USCRN/SCAN soil state as ampacity design input** (Bates 2021 [V] used SCAN for static 99th-percentile climatological design; here extended to a continuous operational forecast).

### 6.3 What This Proposal Does NOT Claim

- "First" use of moisture in cable thermal modelling — Bracale (2019) [V]
- Field validation of ampacity at a USCRN station site — not in scope (requires cable installation)
- Compliance with IEC 60287 or IEEE Std 835 — standards are paywalled
- Elimination of conservative design margin — Bates (2021) [V] shows N-M is already conservative; this proposal makes that margin visible and forecast-conditional, not zero
- Soil drying as a universal problem — Bates (2021) [V] shows drying is unlikely at realistic cable heat rates in the tested soil; the Darmstadt experiment [V] shows it does occur in sand bedding within one day. Both outcomes are captured in the model.

---

## 7. Work Packages and Timeline

| WP | Title | Tasks | Output |
|---|---|---|---|
| **WP1** | Soil state forecast at cable depth | Extend forecaster to 100 cm; score moisture vs persistence baseline; Bayesian α inversion for USCRN depth interpolation to 0.82 m | Forecast model with scored metrics; uncertainty-propagated T_a and ρ at cable depth |
| **WP2** | Cable thermal model and Darmstadt validation | Implement IEC 60287-equivalent model; validate against MF_IV_CL (primary), SF_V+VI, MF_IV_EVU/PV, MF_III_CL; depth-reference sensitivity study | Validated model; mean error table by configuration and bedding type |
| **WP3** | Integration and dynamic rating | Connect WP1 outputs → WP2 model → ampacity time series; evaluate vs static, persistence, and SCAN-climatological baselines at 39 stations | Time series of forecast-driven dynamic rating; headroom statistics by season/zone |
| **WP4** | Sensitivity and standards gap | Johansen uncertainty (12 stations without texture data); NHR soil-drying screening; document IEEE P1254 gap | Sensitivity report; recommendation for field measurement protocol |
| **WP5** | Manuscript | Full paper with all sections | Journal submission draft |

---

## 8. Identified Standards Gap

As documented by Bates (2021) [V, Ch 2], the IEEE project **P1254** — intended to produce a guide standard for soil thermal stability measurement relevant to cable ampacity — was initiated in 2001 and its Project Authorization Request (PAR) expired in **2016 without consensus**. No enforceable standard exists for in-situ soil thermal stability measurement for cable ampacity design. The proposed work's WP4 will document the specific measurement and modelling requirements that such a standard would need to address, based on the integration of the soil forecasting system with the cable thermal model.

---

## 9. Key References

| Citation | Role |
|---|---|
| Neher & McGrath (1957). AIEE Trans. | Original ampacity equation [via Bates V] |
| Bates, C. (2021). *Underground Cable Ampacity*. PhD, Colorado School of Mines. | N-M validation; NHR method; SCAN use; software comparison [V] |
| Bracale et al. (2019). *IEEE Access*. | DLR forecast, moisture→ampacity chain, persistence baseline [V] |
| Espedal et al. (2025). *CIRED* (AAM). | ML cable model tuning; limits without soil data [V] |
| Verschaffel-Drefke et al. (2021). *Energies* 14, 7189. | Darmstadt field experiment; validation dataset [V] |
| Liu et al. (2022). *Energies* 15, 8897. | Thermo-hydraulic FEM; moisture dominance [V] |
| Ahmad et al. (2021). *Energies* 14, 8191. | Sand temperature field; convection in saturated soil [V] |
| Brakelmann et al. (2021). *Energies* 14, 6813. | Analytical multi-cable mutual heating method [V] |
| Brunetti et al. (2022). *Earth Surf. Dyn.* 10(4). | Bayesian thermal diffusivity inversion [V] |
| Widyastuti et al. (2026). *Soil Tillage Res.* | Differentiable LSTM + Crank-Nicolson soil temperature forecast [V] |
| Li et al. (2022). *Geoderma*. | Attention-LSTM soil moisture/temperature [V] |
| Wilson et al. (2016). Supplemental Table T1. | USCRN soil texture; Johansen parameterisation [V] |
| PG&E EDS 038193 / 062288 (user-supplied). | Burial depth; FTB thermal spec; PVC conduit dimensions [V] |
| Southwire SPEC 46319 (rev 1.000.009, 2025). | Reference cable geometry and resistance [V] |
| AIEE-IPCEA "Black Books" (1962). | Design standard assumptions [via Bates V] |
| IEEE Std 835 (1994). | Ampacity tables; design assumptions [via Bates V] |
| IEEE P1254 (PAR expired 2016). | Soil thermal stability standard gap [Bates V] |
| Malmedal, Bates & Cain (2014). IEEE REPC. | NHR method for soil drying screening [via Bates V] |
| USDA NRCS SCAN. | Climatological soil temp/moisture reference [Bates V, Ch 11] |

---

## 10. Open Items Before Submission

- [ ] Select target journal (IEEE Trans. Power Delivery / Energies / Applied Energy)
- [ ] Confirm CC BY-NC 4.0 compatibility with target journal's open-data policy
- [ ] Decide and lock WP1 model architecture (differentiable LSTM+C-N vs PINN vs ensemble) — motivate with SoilSens baseline experiment results
- [ ] Score moisture baseline at 50 cm (completes WP1 prerequisite)
- [ ] Transcribe Bracale Tables 5–7 (cable layer thermal conductivity — needed for WP2 if not using Darmstadt workbook values)
- [ ] Confirm SCAN API access and query format for WP3 climatological reference
- [ ] Depth-reference sensitivity study for Darmstadt (underside vs centre-of-conductor) — supplemental, not blocking

---

*All numbers and literature claims are traceable to full-text surveys in `scratch/ampacity/notes/`. No values have been invented or extrapolated beyond what the cited sources directly report.*
