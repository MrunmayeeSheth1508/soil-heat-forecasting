# Retrieval check: Wilson et al. 2016 and the Selma sensor studies

This check involved no model fitting. It **corrects** [soil_property_feasibility.md](soil_property_feasibility.md). That report missed this source and applied the porosity rule too strictly.

## 1. Source status

| Item | Status | Detail |
|---|---|---|
| Wilson et al. 2016, *Site-Specific Soil Properties of the US Climate Reference Network Soil Moisture*, VZJ, doi 10.2136/vzj2016.05.0047 (CC BY-NC-ND) | **Published but inaccessible** from this environment | The Wiley pages and the NOAA repository PDF both returned HTTP 403 (bot protection). I did not read the methods text myself. |
| **Supplemental_Table_T1.xls** | **Retrieved** | Downloaded from `ftp://ftp.atdd.noaa.gov/pub/wilson/Supplemental_Table_T1.xls` (300 KB). The old FTP link still works; the HTTPS mirror timed out. Saved as [raw file](file:///C:/Users/jtani/.gemini/antigravity/scratch/soil/wilson/Supplemental_Table_T1.xls) and [tidy CSV](file:///C:/Users/jtani/.gemini/antigravity/scratch/soil/wilson/wilson_T1_tidy.csv). Parser: [26_wilson_table.py](file:///C:/Users/jtani/.gemini/antigravity/scratch/soil/26_wilson_table.py). |
| Wilson et al. 2020, VZJ, doi 10.1002/vzj2.20013 (HydraProbe vs TDR-315L) | Abstract **retrieved**; full text **published but inaccessible** (403) | |
| Wilson et al. 2024, VZJ, doi 10.1002/vzj2.20336 (bulk electrical conductivity at 23 stations) | Abstract **retrieved**; full text **published but inaccessible** (403) | |

### What the table contains (primary)

- **Stations:** 70.
- **Depths:** 0.05, 0.1, 0.2, 0.5 and 1.0 m. Some sites are shallower; the table records the actual soil depth for each site.
- **Sampling:** three pits per site. For each pit the table gives distance, azimuth and slope from the tower, plus the installation date (2009–2011).
- **Properties by depth:** % silt, clay and sand, and texture class.
- **Properties averaged over the three pits, by depth:** volumetric water content at 1500 kPa and 33 kPa, and **bulk density (g cm⁻³)**. Each is reported as mean ± SD.
- **Also included:**
  - per-pit wc1500, wc33 and BD averaged over depths;
  - site-average chemistry (C, N, S, cations, CEC, pH).
- **Not included:** particle density and porosity.
- The pit geometry and depth list match the probe installation, so these are **probe-site measurements**, not survey pits. I could not read the methods text that would confirm this.

## 2. Coverage of the development stations (5, 10 and 20 cm)

| Station | Texture | Bulk density | Field capacity (33 kPa) | Wilting point (1500 kPa) |
|---|---|---|---|---|
| TX Muleshoe 19 S | **Retrieved** (clay 19–22%) | **Not reported** at 5–20 cm. Only at 0.5 m (1.50) and 1.0 m (1.14 ± 0.08), plus depth-averaged per-pit values of 1.4, 1.1 and 1.1. | Retrieved | Retrieved |
| SC McClellanville 7 NE | **Retrieved** (sand 93–94%) | **Not reported** | Retrieved | Retrieved |
| IL Champaign 9 SW | **Retrieved** (clay 30–32%) | **Not reported** | Not reported | Retrieved |
| OK Goodwell 2 SE | **Not reported.** The station is absent; the table has *Goodwell 2 E*, which is a separate USCRN station. | Not reported | Not reported | Not reported |
| NE Lincoln 8 ENE | **Retrieved** (clay 36–38%) | **Retrieved:** 1.36 ± 0.21, 1.49 ± 0.09, 1.46 ± 0.13 | Retrieved | Retrieved |
| AL Selma 13 WNW | **Retrieved** (clay 52–54%, silty clay) | **Not reported** | Not reported | Retrieved |

### Other candidates

Of the remaining 33 candidate stations, 22 appear in the table and 11 do not ([coverage CSV](file:///C:/Users/jtani/.gemini/antigravity/scratch/soil/wilson/wilson_candidate_coverage.csv)).

- **Texture and BD at all three depths (14 stations):** La Junta, Cortez, Sioux Falls, Lafayette, Montrose, Elgin, Fairhope, Chillicothe, Newton 5 ENE, Buffalo, Northgate, Los Alamos, Asheville 8 SSW, Durham.
  - **Elgin:** its listed soil depths (0.05, 0.2, 0.3, 0.45 m) do not match the column headers, so its depth mapping is ambiguous.
  - **Montrose and Buffalo:** some BD values have no SD.
- **Texture only, no BD at 5–20 cm (8 stations):** Watkinsville, Bedford, Manhattan, Oakley, Goodwell 2 E, Gadsden, Pierre, Batesville.
- **Absent from the table (11 stations):** Wolf Point 34 NE, Wolf Point 29 ENE, Dinosaur, Lewistown, Sundance, Port Aransas, Santa Barbara, Avondale, Kingston, Merced, Yosemite.

## 3. Selma sensor studies

From the **abstracts (primary)**:

- **2020 study:**
  - The TDR-315L gave "more representative soil water content measurements for stations with high-clay-content soils than the HydraProbe".
  - The authors conclude it is necessary to use "site-specific soil properties" for HydraProbe conversion.
- **2024 study (23 stations):**
  - In high-clay soils, bulk electrical conductivity reached 0.6 S m⁻¹ and volumetric water content reached about 0.7 m³ m⁻³. These high values were "associated with poor performance and failures of both HP and AP sensors".
  - The specific surface area of clay minerals was associated with conductivity magnitude.

**Not verified (search summaries only, no primary text read):**
- The Selma-specific figures (about 58% clay; HydraProbe reading 10–15% higher than TDR; VWC above 0.5).
- The clay mineralogy and calibration details.

**Additional station information from these studies:** none retrieved beyond the abstracts. Any Selma clay mineralogy or depth-dependent clay data in the full texts is **published but inaccessible** here. The 2016 table already provides Selma's depth-dependent clay content.

**Implication for earlier results (a caution, not a new result):** both abstracts report sensor-dependent moisture errors in high-clay soils. Selma's moisture series, and possibly Lincoln's (36–38% clay), may carry sensor-type biases. These would affect the earlier pilot's moisture coefficients at those stations.

## 4. Porosity, under the corrected rule

- Measured porosity and particle density are **not reported** anywhere.
- An **estimated** porosity, φ̂ = 1 − BD/ρs with an assumed ρs (for example 2.65 ± 0.05 g cm⁻³), could be computed wherever BD was retrieved. It would need to be labelled as estimated and tested for sensitivity.
- Among the development stations that is **Lincoln only**. It would also be possible for the 14 other stations listed above.

## 5. Feasibility status

- **Temperature and moisture observations:** available and usable.
- **The soil-property extension as specified** (development on the six previously examined stations): **currently blocked.**
  - Probe-site bulk density at 5–20 cm is not reported for 5 of the 6 stations (Muleshoe, McClellanville, Champaign, Selma, Goodwell 2 SE).
  - Goodwell 2 SE has no soil record at all.
- **A revised design is supported by the data but has not been run.** It would use the 15 stations with retrieved probe-site texture and BD (Lincoln plus the 14 above) and estimated porosity with a sensitivity test. Adopting it would mean changing the development set, so it is your decision.
- **Scientific novelty and transferability:** still unresolved.

The check stops here, as requested.
