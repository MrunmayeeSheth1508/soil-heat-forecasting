# Contribution check: decision report (soil heat transport)

No model fitting was run. This report supersedes the scope claims in [soil_contribution_proposal.md](soil_contribution_proposal.md).

## Decision: **(a) a defensible conventional project**, with modest and partly unverified novelty

There is **no concrete, necessary AI role**. If your mentor requires AI to be central, this question does not meet that requirement. For that purpose it should be treated as **(c)**.

## 1. What the citation search found

**Method:**
- An OpenAlex full-text search for evaluations of conductivity schemes.
- The full list of **106 works citing Dai et al. 2019**, which is the hub paper for scheme evaluation in land models.
- Abstracts read for the closest candidates.

**Access legend:** P = primary full text read. A = abstract only. T = title only (closed access, abstract not available).

| Work | Access | What it did | Relevance |
|---|---|---|---|
| Dai et al. 2019, JAMES, doi 10.1029/2019MS001723 | A | Put 7 conductivity schemes into the Common Land Model. Evaluated conductivity estimates **and** simulated soil temperature in single-point and global runs. Johansen and its derivatives (Côté & Konrad 2005; Balland & Arp 2005; Lu et al. 2007) were "significantly superior". Scheme differences matter most in arid/semiarid and seasonally frozen regions. | **Closest land-model evaluation.** The proposed comparison of "established formulation vs simpler baselines" has largely been done inside a land model. Their sites, soil inputs and hold-out design are **unknown** (Wiley blocked access). |
| He et al. 2020, Earth-Sci. Rev. 211:103419 | A | Reviewed 24 schemes from 38 models. Tested them against 439 laboratory conductivity measurements on 16 soils, and against CLM land-surface temperature vs MODIS at 3 sites. "None of the STC schemes could be used to accurately predict λ for all soil types." Schemes did worse in fine-textured soils. | Shows scheme performance is soil-dependent. Its field test uses remotely sensed surface temperature, not subsurface profiles. |
| CLM5 sensitivity study (2021), JAMES, doi 10.1029/2021MS002670 | A | Tested soil-property data and a conductivity scheme in CLM5 against 5 eddy-covariance sites, 4 soil moisture/temperature networks and **60 soil-temperature sites** on the Tibetan Plateau. | A multi-site field evaluation that includes the effect of soil-property inputs. Regional (permafrost/cold). |
| Catena 2020 104608 (11 schemes, central Qinghai–Tibet); Geoderma 2021 115207 (14 frozen-soil models with observations and SHAW); Geoderma 2021 115330 (schemes in CLM5, Tibetan permafrost); Int. J. Therm. Sci. 2023 108301 (13 models) | T | Field and model evaluations of established schemes | **Methods unknown.** Some may already use measured site soil properties and observed boundaries. I cannot rule this out. |
| J. Hydrol. 2026 136118 (physics-constrained NN for conductivity curves); J. Soils Sediments 2025, doi 10.1007/s11368-025-04052-4 (physics plus ML conductivity, with explainability) | T | ML or physics-constrained learning of conductivity–wetness relations | **AI for conductivity relations already exists.** Data type (laboratory or field) is unknown. |
| ClimaLand (2026), JAMES, doi 10.1029/2025MS005118 | A | A land model built to integrate ML parameterizations trained on in-situ and satellite data | Machine-learned land parameterizations are an active, well-resourced line of work. |
| The five earlier papers | P | See [soil_contribution_proposal.md](soil_contribution_proposal.md) §2 | Single site, synthetic, or laboratory work; none tests transfer to excluded field stations. |

**I have not read** Lu et al. 2007 (doi 10.2136/sssaj2006.0041, confirmed via Dai's abstract), Côté & Konrad 2005 (10.1139/t04-106) or Peters-Lidard et al. 1998. Their equations are needed before any implementation, but they would not change the novelty assessment.

## 2. What remains unanswered (as far as accessible evidence shows)

Field evaluation of established schemes **already exists**, mostly in land models and largely on the Tibetan Plateau. The remaining question is narrower:

> At climatically diverse, mostly non-permafrost stations, using **probe-site measured soil properties** and **observed 5 cm and 20 cm temperatures as boundaries** (which removes atmospheric-forcing and surface-energy errors), does an established soil-conditioned formulation predict the 10 cm temperature better than temperature-only or shared-moisture alternatives, **under transfer with local calibration**? And can that moisture response be distinguished from temperature/seasonal co-variation and sensor bias in routine network data?

**Novelty is modest and incremental.** It is a cleaner, isolated test (removing forcing errors, using probe-site soil cores, quantifying identifiability), not a new physical finding. It is **partly unverified**, because four closely related evaluations are closed access and their methods are unknown.

## 3. Corrections to the previous proposal

| Issue | Correction |
|---|---|
| "14 usable stations" | **14 candidates.** Still unresolved: moisture above estimated porosity (Chillicothe, Sioux Falls at 20 cm, Lincoln, Asheville); possible sensor changes (§4); no measurement uncertainty on hourly θ; and BD SD missing at some depths (Montrose 20 cm; Buffalo 10 and 20 cm). |
| 0.1 °C as a detectability limit | **Removed.** 0.1 °C is reporting resolution, not a detection threshold. Detectability is judged from the uncertainty of the actual paired comparison: block-bootstrap intervals that keep temporal dependence, plus explicit scenarios for persistent biases (sensor offsets, probe-depth error, θ calibration error). Brunetti's 0.02 °C noise and 0.01 °C bias limits apply to its own setup and are cited only as context. |
| "θ scaled by ±0.03" | Two **specified** scenarios: (i) an **additive** offset of ±0.03 m³ m⁻³, the order of typical stated accuracy for dielectric probes (the manufacturer specification must be checked before use); (ii) a **multiplicative** ±10% calibration-slope error, motivated by the reported clay-soil calibration problems (Wilson 2020/2024 abstracts). The 10% figure is a scenario choice, not a verified sensor value. |
| Model C combined λ and C_v into an effective diffusivity | **Consistent equation (below).** |
| "If A fails, B/C cannot be interpreted" | **Diagnose first.** Separate (1) numerical problems (solver verification, grid/time-step convergence, initialisation) and (2) observation problems (gaps, boundary-sensor offsets, depth error, frozen periods) from (3) failure of the physical hypothesis. A moisture-free baseline may fail **because** moisture matters. Only failures traced to (1) or (2) exclude a station. |
| Monotone spline | **No forced monotonicity.** Conductivity rises with wetness, but diffusivity λ/C_v can rise, flatten or fall. Brunetti §6.2 reports opposite moisture–diffusivity signs at two sites. Any flexible term is unconstrained in sign and shape, with complexity limited by identifiability. |
| Evaluation name | Leave-one-station-out shared parameters + a local first-25% scale factor = **"transfer with local calibration"**, named explicitly. Pure transfer (no local factor) would be a separate, harder test. |

### Consistent heat equation

The existing pilot solver used a depth-uniform form, ∂T/∂t = α(t) ∂²T/∂z². That is not valid once properties vary with depth.

**For all models:**

$$C_v(z,t)\,\frac{\partial T}{\partial t} = \frac{\partial}{\partial z}\!\left[\lambda(z,t)\,\frac{\partial T}{\partial z}\right]$$

- **Derivation:** start from energy conservation, ∂(C_v T)/∂t = ∂/∂z(λ ∂T/∂z) − C_w ∂(qT)/∂z. Combine with water conservation (∂θ/∂t = −∂q/∂z). Then neglect convective heat transport C_w q ∂T/∂z and vapour transport. That neglect is a stated assumption, which fails during infiltration.
- **Depth representation:**
  - nodes at 5–20 cm, Δz = 2.5 cm, finite-volume flux form;
  - λ at cell faces as a harmonic mean;
  - C_v at nodes;
  - Crank–Nicolson with coefficients evaluated at the half step.
  - Soil properties are interpolated linearly in depth between the Wilson 5, 10 and 20 cm values. θ is interpolated the same way between the observed θ5, θ10 and θ20.
- **Models A/B** are the special case λ/C_v uniform in depth.
- **Control model C₀:** C's formulation with **depth-uniform** station-average properties. This separates the effect of depth layering from the effect of the soil-conditioned moisture response.
- **Verification:** the flux-form solver must be re-verified against an analytic or manufactured two-layer solution before use. The earlier check covered only the uniform case.

## 4. Sensor history

**Not resolved; this is a limitation.**

- The public USCRN products checked (`hourly02`, `soil01`, `soilsip01` README/HEADERS, `DATASET-STATUS.txt`) contain **no sensor-type or replacement-date field**.
- A search summary states that HydraProbe → Acclima TDR-315 replacement was phased, per station, roughly 2017 onward, as probes failed. This is **unverified**: I did not read the primary source (technical memo USCRN-19-001).
- Consequence: 2019–2021 and 2022 may mix sensor types within and across stations.
- **Mitigation options:**
  1. request per-station, per-depth sensor histories from NCEI or ATDD;
  2. limit the analysis to periods with no detectable level shift. This is a descriptive changepoint screen, and it would confound real climate shifts;
  3. treat sensor type as an unknown persistent bias, covered by the §3 scenarios.

  Only option 1 resolves it.

## 5. Why not (b)

The relationship a nonlinear model would learn is diffusivity (or conductivity and heat capacity) as a function of wetness and soil properties. However:
- established schemes already supply this;
- ML and physics-constrained-NN versions of such curves exist (§1);
- the earlier pilot showed a shared moisture term did not transfer.

A flexible learner would be justified only if C and C₀ leave reproducible, station-transferable residual structure that a low-order term cannot capture, **and** the data are shown to constrain more degrees of freedom. Neither is established. Choosing a neural network, Gaussian process or PINO now would be adding AI for its own sake.

## 6. What would strengthen or settle the novelty question (not done)

- Full texts of: Dai et al. 2019 (open access, but blocked to me); Catena 2020 104608; Geoderma 2021 115207 and 115330; J. Hydrol. 2026 136118.
  - If any already uses probe-site soil properties with observed-boundary profiles across multiple stations and excluded-site evaluation, the question narrows to the identifiability part only.
- NCEI sensor histories.
- Lu et al. 2007 primary text, for the implementation.
