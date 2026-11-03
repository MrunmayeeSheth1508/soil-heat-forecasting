# Data

| Folder | Original location (`...\scratch\soil\`) | Files | Contents |
|---|---|---|---|
| `phase3_processed_hourly/` | `phase3/data` | 390 | Hourly USCRN arrays (`<station>_<year>.npy`) for the 39 audited stations, 2012-2021, used by all forecast code (`forecastlib.load_station`) |
| `raw_uscrn_hourly_samples/` | `raw` | 4 | Raw CRNH0203 hourly text files (Selma, Versailles 2019-2020) |
| `uscrn_soil_sip/` | `soilsip` | 23 | USCRN soil-moisture / soil-property (CRNSIP01) station files |
| `multistation_npz/` | `multi` | 393 | Early multistation arrays (2019-2021) |

Other data files:

- Soil properties: `results/02_soil_properties/` (Wilson 2016 tables, soil-lab pedons, `stations.tsv`).
- Event inventories: `results/03_phase3_events_and_pilotA/event_inventory.csv`, `results/06_forecast_benchmark/issue_inventory.csv`.
- Station list: `results/03_phase3_events_and_pilotA/stations_phase3.csv`.
- Stillwater 2019 sample: `results/01_early_pilots_and_audits/stillwater_2019.txt`.
- Paper PDFs: `literature/`.

Source: NOAA NCEI USCRN, https://www.ncei.noaa.gov/pub/data/uscrn/products/hourly02/ (downloaded 2026-10-08). Times are local standard time. Missing values follow USCRN codes, as handled in `forecastlib.load_station`.
