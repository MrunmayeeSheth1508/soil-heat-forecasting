# Soil heat transport: contribution check and experiment proposal

**Phase status:** literature comparison, data audit and design only. **No model fitting was run.** The 2022 data have not been downloaded.

## 1. Problem statement

Land models represent soil heat transport using thermal-conductivity schemes conditioned on soil properties and wetness. We have:
- hourly temperature and moisture at 5, 10 and 20 cm from USCRN stations;
- probe-site soil cores (Wilson et al. 2016).

**Question:** can a soil-conditioned moisture relationship, placed inside a heat solver, explain heat propagation at stations it was not calibrated on? And can network-grade sensors resolve that relationship, separately from temperature and seasonal effects?

Our earlier pilot gave a negative result here: a single shared moisture term did not transfer, and the station slopes changed sign.

## 2. Closest literature (primary text read for all five)

| | Brunetti et al. 2022 (ESurf) | Peng et al. 2024 (STR 106233) | Xie et al. 2024 (STR 106236) | Wang et al. 2023 (WRR) | Huang et al. 2026 (GMD) |
|---|---|---|---|---|---|
| **Inputs and estimated quantity** | 13-depth temperature profiles → depth-resolved diffusivity, constant within each sliding window (MCMC) [§2.2–2.3, §6.3] | Texture, θ, ρb, OC → diffusivity κ, by random forest and 9 pedotransfer functions (PTFs) [§2.1, §2.3] | Temperature at two depths → temperature at the third depth, plus a free κ(z,t) [§2.5] | Synthetic θ and T → λ₀(θ) and hydraulic conductivity [§3, §4.2] | Forcing plus 1–2 temperature depths → λ, C, a heat-transfer coefficient, T_b [§2.3, §3] |
| **Data** | Synthetic tests; field data at Berkeley (4 co-located probes, about 2 months) and Teller, AK (27 probes, 3 weeks) [§2.4.1–2.4.4] | 998 measurements on 106 soils compiled from 5 studies; measurement method is in Table 2 (not extracted) [§2.2] | **One** field site (Lishu, China), one year, daily means, 5/10/20 cm [§2.2] | **Synthetic only:** HYDRUS-1D, homogeneous 100 cm column, 3 textures, 5 days [§4] | Synthetic, plus **one** flux tower (Phoenix), 150 h calibration and 50 h evaluation [§3.3] |
| **Soil properties** | Correlated afterwards with bulk density, θ and carbon (r = 0.78–0.92) [§6.2] | Sand, silt, clay, θ, ρb, OC [§2.3] | Site texture and ρb reported only [§2.2] | Texture enters through the simulation parameters only [Table 1] | None; constant λ and C [§2.1] |
| **Moisture vs temperature separated?** | Temperature named a lesser influence and not modelled; observed moisture effect changes sign between sites [§2.1, §6.2] | No temperature term | No: κ is a free field; moisture comparison is visual only [§3.2] | No temperature dependence in λ₀ [Eq. 9] | Moisture deliberately excluded (arid site) [§3.3, §4] |
| **Validation on excluded sites or conditions** | Against independent needle-probe measurements; **no excluded-site prediction** [§2.4.3, §6.2] | **Random 75/25 split** of the pooled dataset; split unit (measurement or soil) not stated [§2.2]; metrics r, E′, SD [§2.4] | Withheld depth at the same site and year only [§2.5, §3.1] | Each texture trained separately; **no transfer** [§4] | Later 50 h at the same tower [§3.3] |
| **Sensor error and identifiability** | **Explicit.** Needs noise ≤ 0.02 °C, bias SD ≤ 0.01 °C and mm-accurate sensor spacing for ≤ 10% error [§3.3, §3.4, §7] | Not addressed | Upward/downward κ judged unreliable [§3.2]. A plain numerical solver gave RMSE 0.18 °C at 10 cm vs 0.21 °C for the PINN [§3.1, p. 5] | Noise added to θ only (0.5–2%); noise robustness "insufficient" [§4.1, §5] | **Explicit.** One depth is non-identifiable, λ and C are correlated, two depths resolve it, albedo must be fixed [§3.1–3.2, §4] |

**What this shows (verified only for these five papers):**
- None tests whether a moisture relationship for soil heat transport transfers to **excluded field stations**.
- None separates moisture from temperature effects in field data.
- The two that study identifiability (Brunetti, Huang) imply that network-grade sensors are a real constraint:
  - USCRN reports **0.1 °C resolution**, and 100% of the 10 cm values sit on the 0.1 °C grid;
  - each depth averages 3 probes;
  - probe depth is not known to the millimetre.

> [!WARNING]
> **The gap is not yet verified across the literature.** The forward/backward citation search did not run (the command was declined).
>
> I have also not read the established-formulation papers: Lu et al. 2007/2014, Côté & Konrad 2005, and Peters-Lidard et al. 1998, which compared conductivity schemes. Field evaluations of those schemes may already exist. A gap claim must wait for that search.

## 3. Data audit: 15 stations

Files: [30_audit15.py](file:///C:/Users/jtani/.gemini/antigravity/scratch/soil/30_audit15.py) and [audit15_table.csv](file:///C:/Users/jtani/.gemini/antigravity/scratch/soil/audit15_table.csv).

**Measured properties (Wilson 2016 Supplemental Table T1):**
- texture, bulk density (mean ± SD across 3 pits), and water content at 33 kPa and 1500 kPa;
- at 5, 10 and 20 cm;
- sampled at probe installation, 2009–2011.

**Derived property:** estimated porosity φ̂ = 1 − BD/2.65. The 2.65 is an *assumed* particle density, given ±0.05 uncertainty. Its SD propagates the between-pit BD SD and the particle-density uncertainty.

**Checks that passed:**
- All 15 stations matched a WBAN identifier, and coordinates agree to 2 decimals.
- 2019–2021 data are present at every station.
- The Wilson depths equal the USCRN depths, except Elgin (see the table).

| Station | Clay % (5/10/20 cm) | φ̂ (5/10/20 cm) | φ̂ SD | Hours with θ > φ̂ (5/10/20 cm) | Hours with T ≤ 0 °C at 5 cm | Flags |
|---|---|---|---|---|---|---|
| Lincoln 8 ENE | 36/37/38 | 0.49/0.44/0.45 | 0.04–0.08 | 0.3/6/8 % | 12% | **Baseline failure in the earlier pilot (RMSE 0.99 °C)** |
| La Junta 17 WSW | 20/21/21 | 0.44/0.47/0.43 | 0.01–0.06 | 0 | 7% | |
| Cortez 8 SE | 21/21/37 | 0.49/0.52/0.43 | 0.02–0.08 | 0 | 6% | Median θ at 5 cm 0.136 → 0.081 between 2019 and 2020 |
| Sioux Falls 14 NNE | 25/24/26 | 0.45/0.41/0.39 | 0.05–0.10 | 0/0/**25** % | 8% | Wetness exceeds φ̂ at 20 cm |
| Lafayette 13 SE | 14/14/24 | 0.54/0.46/0.47 | 0.01–0.07 | 0 | 0% | |
| Montrose 11 ENE | 19/19/22 | 0.58/0.53/0.42 | 0.04–0.05; 20 cm has none | 0 | 18% | θ coverage 69% at 5 cm |
| **Elgin 5 S** | 27/28/46 | **0.65/0.61/0.65** | 0.06–0.11 | 0 | 0% | **Depth mapping ambiguous; BD 0.94–1.04 implausibly low → exclude** |
| Fairhope 3 NE | 5/3/3 | 0.51/0.49/0.49 | 0.03–0.06 | 0 | 0% | |
| Chillicothe 22 ENE | 30/31/41 | 0.45/0.48/0.51 | 0.02–0.05 | **26/16/15** % | 3% | Wetness exceeds φ̂ |
| Newton 5 ENE | 6/5/17 | 0.43/0.40/0.39 | 0.03–0.06 | 0 | 0% | |
| Buffalo 13 ESE | 27/29/37 | 0.45/0.42/0.45 | 0.01; 10/20 cm have none | 0 | **32%** | θ coverage 67–72%; median θ at 5 cm 0.297 → 0.158 |
| Northgate 5 ESE | 17/15/15 | 0.55/0.55/0.50 | 0.04–0.07 | 0 | **38%** | θ coverage 61–67%; median θ at 5 cm 0.223 → 0.115 |
| Los Alamos 13 W | 26/26/24 | 0.59/0.61/0.58 | 0.01–0.04 | 0 | 19% | |
| Asheville 8 SSW | 15/27/17 | 0.39/0.37/0.31 | 0.04–0.14 | 2/7/6 % | 0% | |
| Durham 11 W | 11/15/24 | 0.41/0.39/0.38 | 0.02–0.09 | 1/1/0.3 % | 0% | |

**Implications for the design:**
1. **Observed wetness above φ̂** (relative saturation S > 1) occurs at Chillicothe, Sioux Falls, Lincoln and Asheville. Either the moisture sensor is biased in clayey soils (consistent with the Wilson 2020/2024 abstracts), the BD is unrepresentative, or the assumed particle density is wrong. S therefore cannot be used raw. This must be a stated sensitivity case, not silently capped.
2. **Frozen periods** are substantial at Northgate, Buffalo, Montrose and Los Alamos. Dielectric moisture readings and latent heat make these periods invalid for a conduction model, so they must be excluded by a predefined rule.
3. **Soil cores are 10 years older** than the observations. The design assumes static properties, which is a limitation.
4. **Sensor changes:** the hourly product has no sensor-type field, and I did not retrieve sensor change dates.
   - The large year-to-year drops in 5 cm median moisture (Buffalo, Northgate, Cortez, Sioux Falls) could be climate or instrument changes.
   - The Wilson 2020/2024 abstracts describe a HydraProbe-to-TDR comparison. The 2019 transition date comes from a search summary only, so it is unverified.
5. **Development station:** of the six previously examined development stations, only Lincoln is in this set, and it was the earlier baseline failure.

**Usable set:** 14 stations (Elgin excluded), all with measured texture and BD and estimated porosity.

## 4. One testable contribution

- **Closest existing approaches:**
  - property-based diffusivity or conductivity functions evaluated on pooled laboratory-type data with random splits (Peng);
  - single-site inversions from temperature profiles (Brunetti, Xie, Huang);
  - synthetic coupled water–heat learning (Wang).
- **Unresolved question:** on field stations excluded from fitting, does an **established, soil-conditioned** moisture formulation, with no fitted moisture parameters and only the same single local scale factor every model gets, predict 10 cm temperature better than:
  - a temperature-only baseline;
  - a single shared moisture term?

  And is the moisture contribution distinguishable given 0.1 °C sensor resolution, sensor bias and temperature–moisture co-variation?
- **Observations that can answer it:**
  - USCRN T at 5/10/20 cm and θ at 5/10/20 cm, 2019–2021 for development and 2022 for final evaluation;
  - Wilson probe-site texture and BD.
- **Results that would contradict the explanation:**
  - C does not beat A and B on excluded stations;
  - the gain disappears under porosity or sensor perturbations;
  - the gain appears only at stations where θ > φ̂ (pointing to sensor artefacts);
  - or C still needs station-specific moisture corrections whose sign differs between stations, as the earlier pilot's slopes did.
- **Why it matters beyond lower error:** it is a direct field check, at excluded stations, of the kind of soil-conditioned scheme land models use. It also states **when** routine network data can and cannot identify such a relationship, which constrains how much field networks can inform land-model parameterisations.

## 5. Smallest decisive experiment (conventional, no AI)

All models use the same verified 5–20 cm conduction solver. T5 and T20 are boundaries; T10 is evaluated. Initialisation is fixed and the warm-up is 48 h.

| Model | Effective diffusivity | Station-local allowance | Shared parameters |
|---|---|---|---|
| **A** | α_eff = a_s · (1 + c·(T − T_ref)) | a_s | c |
| **B** | A × exp(b·(θ − θ̄_s)) | a_s | c, b (either sign) |
| **C** | α_eff = a_s · λ_PTF(S, sand, φ̂) / C_v(θ, φ̂) × (1 + c·(T − T_ref)), with S = θ/φ̂, the conductivity λ from an established PTF (Lu et al. 2007, Kersten-number form), and the heat capacity C_v by de Vries | a_s | c only; **no fitted moisture parameter** |
| **C′** (optional) | C with one shared shape parameter of the PTF fitted on development stations | a_s | c, one shape parameter |

**Design notes:**
- **Equal local allowance:** each model gets one scale factor a_s, calibrated on the first 25% of that station's development record.
  - Mean wetness and the station-level offset are absorbed by a_s.
  - Within-station change comes only from θ (B) or from the PTF (C).
  - The PTF equations must be checked against the Lu et al. 2007 primary text before use (not yet read).
- **Excluded stations:**
  - Shared parameters (c, b, the C′ shape parameter) are fitted with leave-one-station-out across the 14 stations.
  - The 2022 period stays untouched until the final run, which uses the frozen parameters at all 14 stations.
- **Exclusions:** hours with T ≤ 0.5 °C at any depth (plus 48 h after); hours with missing data; Elgin.
- **Comparisons:**
  - paired C − A and C − B errors in 10 cm RMSE, by station and in 7-day contiguous blocks with block bootstrap;
  - decision rules fixed before running, e.g. the CI of the C − B difference excludes 0 and C wins at a majority of stations;
  - no hourly independence assumed.
- **Soil effects:** test whether the C gain varies with clay, sand and φ̂. Compare C with a version where the PTF uses the **wrong** station's soil properties (a permutation control).
- **Sensor bias:**
  - rerun with the hours where θ > φ̂ removed;
  - rerun with θ scaled by ±0.03;
  - rerun with φ̂ at ±1 SD and particle density 2.60/2.70;
  - flag the stations with year-to-year moisture shifts;
  - test for discontinuities once sensor change dates are retrieved.
- **Temperature–moisture confounding:**
  - evaluate within temperature-stratified blocks, i.e. matched temperature with contrasting θ, using the two-state bins from the earlier audit;
  - report the correlation between the fitted c and b.
- **Identifiability:** before fitting, compute how much T10 changes for a plausible moisture-driven change in α_eff. Compare that with 0.1 °C quantisation and with Brunetti's noise and bias thresholds. Report the stations and periods where the signal is below these limits.
- **Baseline failures:** report A's performance per station first. Flag stations like Lincoln separately and do not interpret B or C at stations where A fails.

## 6. Does AI have a necessary role?

**Not at present.** The relationship a nonlinear model would learn is the shape of diffusivity against relative saturation (and possibly texture). An established PTF already provides that shape with physical constraints. A shared monotone spline in S with 3–4 knots is the next step if C′ shows systematic, reproducible residual structure in S at excluded stations.

A neural network or Gaussian process is only justified if both of these hold:
1. the spline fails in a specific, repeatable way across excluded stations;
2. the identifiability analysis shows the data can constrain more degrees of freedom than a spline.

Neither is shown. Xie et al.'s own baseline also suggests a plain numerical solver is competitive with a PINN at 10 cm (§3.1, p. 5).

## 7. Possible climate relevance (not demonstrated)

- Conductivity and diffusivity schemes control ground heat flux and subsurface temperature in land models.
- A field test at excluded stations of whether soil-conditioned wetness dependence holds, plus where sensor data cannot resolve it, would inform how such schemes are evaluated.
- **This would not show improved climate forecasts.**

## 8. Recommendation: **reframe, then proceed narrowly**

Reframe as a **field transfer test of an established soil-conditioned thermal formulation and its identifiability limits with network-grade sensors**. Drop "new AI model" and "novel moisture effect".

**Before any fitting:**
1. Run the forward/backward citation search, plus the Lu 2007/2014 and Peters-Lidard 1998 primary texts, to confirm no field transfer evaluation of these schemes already exists. If one does, narrow the question to the identifiability-limits part, or close.
2. Retrieve the USCRN sensor change dates.
3. Pre-register the decision rules in §5.

**If the gap holds,** the experiment above is the smallest one that can give a decisive answer, positive or negative.
