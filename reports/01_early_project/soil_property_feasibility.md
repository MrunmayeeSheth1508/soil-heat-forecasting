# Soil-property audit and transfer test: feasibility report

> [!WARNING]
> **Superseded in part by [soil_wilson2016_retrieval.md](soil_wilson2016_retrieval.md).**
> - This report missed Wilson et al. 2016 (probe-site soil cores at 70 USCRN stations). Its supplementary table is retrievable.
> - The statements "no station-specific soil information" and "conclusion (i)" are therefore wrong as written.
> - The porosity rule was also applied too strictly: an assumed particle density is acceptable if the result is labelled as estimated and sensitivity-tested.
> - **Current status:** the extension is blocked for the six development stations (probe-site bulk density is missing at 5 of 6). A 15-station design with estimated porosity is supported by the data but has not been run.

**Question:** Does accounting for soil properties help a moisture-dependent heat model transfer between stations?

**Outcome:** The test stopped at Step 1. Steps 2–5 (freezing the design, models A/B/C, paired evaluation) were **not run**. No new temperature-model results were produced, and the 2022 period is still untouched.

## 1. What was required

Model C needs relative saturation, S = θ/φ, and so needs **measured porosity** φ for the 5–20 cm layer at every station. Texture and bulk density are needed to condition the relationship and to test sensitivity. Your rules exclude substituting texture for porosity and inventing missing values.

## 2. Sources checked

| Source | What it contains | Station soil properties? |
|---|---|---|
| NCEI USCRN `soil01` | Hourly soil moisture and temperature time series | No |
| NCEI USCRN `soilsip01` (`CRNSIP01_*.txt`) | A further hourly 10-column time series at 5 depths | No; there are no static properties |
| NRCS NCSS/KSSL lab data via Soil Data Access (`lab_combine_nasis_ncss`, `lab_layer`, `lab_physical_properties`, `lab_site`, `lab_pedon`) | Lab pedons with particle size, bulk density and particle density | Searched within ±0.03° (about 3 km) of all 39 stations, keeping layers that overlap 5–20 cm ([script](file:///C:/Users/jtani/.gemini/antigravity/scratch/soil/24_soil_lab_audit.py), [rows](file:///C:/Users/jtani/.gemini/antigravity/scratch/soil/soil_lab_pedons_5_20cm.csv)). **No pedon is a USCRN probe-site sample.** |
| Bell et al. 2013, *J. Hydrometeorol.* 14:977, doi 10.1175/JHM-D-12-0146.1 (primary text) | States that installation soil samples go to the USDA National Soil Survey Center for "bulk density, field capacity (−33 kPa), permanent wilting point (−1500 kPa), and other general soil characteristics" | **Values are not published, and no data link is given.** |

## 3. Development stations (5–20 cm)

| Station | Nearest lab pedon (series, year, distance) | Station measurement? | Texture | Bulk density | Porosity / particle density |
|---|---|---|---|---|---|
| TX Muleshoe 19 S | none | — | missing | missing | missing |
| SC McClellanville 7 NE | none | — | missing | missing | missing |
| OK Goodwell 2 SE | none | — | missing | missing | missing |
| IL Champaign 9 SW | Drummer, 1976, ~3 km | No | 0–20 cm: sand 14%, clay 30% | missing | missing |
| NE Lincoln 8 ENE | Sharpsburg/Aksarben, 1973 and 2006, <1 km | No | clay 31–45% | 1.11–1.33 g cm⁻³ (⅓ bar) | missing |
| AL Selma 13 WNW | Vaiden, 1958, ~2 km | No | clay 47–59% | missing | missing |

Other candidates:
- 19 stations have no lab pedon nearby.
- Manhattan, Batesville, Kingston and Yosemite have many generic survey pedons, from different series and decades.
- Every `particle_density_less_than_2mm` value found (34 rows) is **2.65 with method "NK"**. That is an assumed default, not a measurement.

**Uncertainty that cannot be reduced from public data:**
- Public station coordinates have only 2 decimals (about ±0.6 km), so even nearby pedons cannot be tied to the probe pit.
- Each USCRN depth averages 3 probes, and Bell et al. show probe responses differ even among working probes.
- Survey pedons sampled 2–5 decades ago in another soil series are not station measurements. They cannot provide a measured φ.

## 4. Missing measurements (why it is not feasible)

1. Station-specific 5–20 cm **bulk density**: missing at all 6 development stations. Lincoln has only non-station survey values.
2. Station-specific 5–20 cm **particle size**: missing at all 6. Three stations have only non-station survey values.
3. **Measured porosity, or measured particle density**: missing at all 39 stations. The only φ available would be 1 − BD/2.65, which uses an assumed particle density. Your rules exclude that.

The installation samples analysed by NSSC (Bell 2013) are the right data, but they are not in the public lab database or the NCEI products.

## 5. What the data support so far (from the earlier pilot, unchanged)

- Moisture and temperature contrasts are usable at several stations ([audit](soil_multistation_audit.md)).
- A shared within-station moisture term in effective diffusivity **worsened** leave-one-station-out prediction: −0.0125 °C, CI −0.0154 to −0.0094 ([pilot](soil_multistation_pilot.md)).
- The station-specific moisture slopes are individually tight but **differ in sign**, from +0.46 at Muleshoe to −0.23 at McClellanville. Soil differences could explain that, but the hypothesis cannot be tested without measured properties.
- **Baseline failures** to flag separately:
  - Lincoln: RMSE 0.99 °C.
  - Goodwell: RMSE 0.67 °C, and the fitted effective α of 1.9×10⁻⁶ m² s⁻¹ is implausibly high.

## 6. Limitations of this audit

- Only public, programmatically reachable sources were searched. No data request was made to NCEI or NRCS.
- The pedon search radius (±0.03°) is a judgement call. Widening it would add only more non-station pedons.
- SSURGO map estimates were deliberately not used. They are not station measurements and would not supply measured φ.

## 7. Possible routes to feasibility (not done; your choice)

- **Ask NCEI or the NRCS NSSC for the USCRN installation-core lab results.** This is the only route to station-measured bulk density and texture. Porosity would still need a measured particle density, or an assumption you would have to state and approve explicitly.
- **Use another network that publishes lab characterisation at the probe site**, for example SCAN stations with KSSL pedons sampled at installation. That needs its own audit.
- **Run a reduced design using bulk density only**, explicitly labelled non-station, at the few stations with nearby BD (e.g. Lincoln, Manhattan, Sioux Falls). This would be a different, weaker question, not the test specified.

## 8. AI role

**None concrete at present.** The conventional test cannot be specified without measured soil inputs, and the shared moisture term already failed transfer. A nonlinear model would have no soil information to learn from that is tied to the probe sites.

---

## Conclusion

**(i) Soil information is insufficient, so the extension is not feasible** with public data. Station-specific 5–20 cm texture and bulk density are missing at all six development stations, and measured porosity is missing at all 39 candidate stations.
