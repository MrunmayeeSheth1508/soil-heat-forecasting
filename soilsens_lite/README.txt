SoilSens Lite 3 - interactive assessment prototype (plain Python, nothing to install)
===================================================================================

RUN
  1. Unzip. Open PowerShell in the folder that contains run_soilsens.py
     (the zip contains a folder "soilsens_lite": cd into it).
  2. python run_soilsens.py            -> browser opens http://localhost:8501
     python run_soilsens.py --selftest -> should end with ALL PASSED
     python run_soilsens.py --port 8600 if 8501 is busy.
  Works under Windows Application Control: only the Python standard library is used.

LIVE MODE (GitHub Codespaces or any machine with the full backend)
  Put this soilsens_lite folder inside the repo, next to the backend's soilsens/ and
  models/ folders, then:
     python soilsens_lite/run_soilsens.py --live --no-browser
  The trees and the GRU then run live from the trained models (the header shows
  "ML models running live"). Without the backend it falls back to precomputed forecasts.

THE EVALUATOR'S PATH (five screens, top of the page)
  1 Soil observations   station, recorded heat spell (repo event archive), period, depths;
                        temperature, moisture, rainfall, highlighted spell, anomalies,
                        peak warming / delay / persistence / burden (+ archive values),
                        station map and site info, research-findings panel.
  2 Forecasts           heat-spell issue or any day; persistence, seasonal-anomaly
                        baseline, diurnal, trained ML (gradient-boosted trees with 4
                        input configurations, and a GRU neural network); 168 h observed + 72 h forecast + revealed later
                        observations; errors by depth and lead; input-experiment table.
  3 Installation        documented presets (PG&E 24/30 in, 36 in scenario, direct-buried,
                        Darmstadt trefoil), supported adjustments, cross-section drawing,
                        every input with its source in plain language.
  4 Thermal & ampacity  conductor temperature vs limit, backfill/soil temperatures,
                        2D temperature map with time slider, radial profile, local
                        moisture (drying rule), heat flow and stored heat, whole-horizon
                        permissible current and load multiplier; rerun with a new current.
  5 Evidence            A. Darmstadt MF_IV_CL reconstruction: recorded current and
                        conditions, measured vs calculated conductor temperature, MAE,
                        bias, coverage; measured MF_III moisture (sand drying).
                        B. Matched comparisons (environment, backfill, depth, moisture,
                        cable, duct, forecast model), saved and downloadable.
  Project archive       repo stages 1-8, stage-8 benchmark recomputed, reproducibility.
  Saved runs            every assessment is saved in runs/ (configuration, model
                        version, inputs, outputs) and can be reopened.

WHAT IS AND IS NOT DONE (also shown in the app)
  Done: one complete working path, end to end, on real data.
  Preliminary: ML = gradient-boosted trees (trained 2019-2020) and a GRU (trained
    2019 to Sep 2020, early stopping Oct-Dec 2020), both tested on 2021. Forecasts are
    precomputed here because Windows blocks scikit-learn and PyTorch on this laptop;
    they were produced by the full backend and match it exactly.
  Approximations: radial model (Kennelly 2h boundary); trefoil = equivalent bundle;
    2D map = quasi-steady image-method view of the radial solution; local moisture =
    reduced drying rule, no transport.
  Not yet: full 2D finite-element model, multiple circuits, moisture transport,
    Darmstadt configuration II reconstruction. Darmstadt agreement is good only in the
    fluidized backfill (MAE ~3 K); silt, sand and loam still show large errors.

DATA (all from the GitHub repo, see data/)
  stations/   13 USCRN stations, 2019-2021, int16 binaries
  gbt/        tree forecasts, 4 input configurations, every 2021 08:00 issue
  gru/        GRU forecasts for the same issues + model_card.json
  archive/    heat spells 2019-2021 from results/03_.../event_inventory.csv + issues
  catalogue/  Cable_Catalogue, Reference_Installations, Backfill_Specifications
  darmstadt/  MF_IV_CL and MF_III_CL (hourly), material curves, saved reconstruction runs
  repo/       stage-8 scores, figure, stage logs, project history
