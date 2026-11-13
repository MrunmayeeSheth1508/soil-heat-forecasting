# SoilSens Phase 2: backend and prototype app

This folder adds a working skeleton for Phase 2 on top of the existing repo. It follows the Phase-1 slides and section 23.4 of the synthesis doc. It doesn't change anything that's already in the repo.

```
soilsens/                 backend package
  data.py                 load USCRN NPZ arrays (data/multistation_npz), QC, issue times
  forecast/base.py        get_forecast(): the ONE entry point the app calls
  forecast/baselines.py   persistence, diurnal persistence
  forecast/gbt.py         gradient-boosted trees + 4-stage ablation (trained, working)
  forecast/gru.py         GRU encoder, two heads, masked loss, early stopping (trained)
  physics/soil.py         Johansen conductivity, heat capacity
  physics/cable.py        cable catalogue (Southwire 350, Darmstadt MV150), beddings, duct
  physics/radial.py       transient radial heat model, I^2 R(T) source, backward Euler
  rating.py               warm-up from prior load + whole-horizon current search
  pipeline.py             assess(case) / compare(): full run with provenance tags
  evaluate.py             MAE by depth/lead, common issue set
app/streamlit_app.py      the prototype UI
scripts/                  train_gbt.py, train_gru.py, run_ablation.py, run_case.py
tests/                    numerical checks (pytest)
```

## Run it

Copy these folders into the repo root (next to `data/`), then run:

```bash
pip install -r requirements-phase2.txt
python scripts/train_gbt.py --stage all     # ~5-10 min, writes models/gbt_stage{0..3}.joblib
python scripts/train_gru.py --epochs 25      # ~6 min on 2 CPUs, writes models/gru.pt (needs torch)
python scripts/run_ablation.py              # writes outputs/ablation_summary.csv
python -m pytest tests -q                   # 9 physics checks
streamlit run app/streamlit_app.py
```

The app also works before any training is done. It then offers only the persistence and diurnal baselines. Data lives in `data/multistation_npz` by default. To use another location, set `SOILSENS_DATA_DIR`.

## Status

| Part | Status |
|---|---|
| Data loading, QC, issue times (08:00 LST daily, 168 h history, 72 h horizon) | working |
| Persistence and diurnal baselines | working |
| GBT, 4-stage ablation (temp only, + rain, + current moisture, + moisture history) | trained and scored on 13 stations: train 2019-2020, test 2021 |
| GRU | trained on 13 stations (2019 to Sep 2020, early stopping on Oct-Dec 2020), tested on 2021; beats the trees at 5-20 cm temperature, worse than the trees at 50-100 cm, worse than persistence for moisture |
| Depth interpolation to the cable | linear between sensor depths (as in the slides) |
| Native soil k(θ), Cv(θ) | Johansen with default parameters (estimated) |
| Single-cable transient model, in a duct or direct-buried, three beddings | working; 9 checks pass (steady state, energy balance, limits) |
| Local moisture | either background only, or a reduced "critical-isotherm drying" rule (scenario). **Not** moisture transport |
| Whole-horizon current search, load multiplier, forecast vs observed-background run | working |
| Uncertainty | resampled past persistence-error trajectories (simple version) |
| Trefoil / multiple cables, 2D cross-section, liquid/vapour transport, Darmstadt verification | **not implemented**; the UI says so |

## Known simplifications (say these out loud)

- **Radial geometry is an equivalent model.** The outer boundary sits at 2 × depth and is held at the background temperature. This gives the exact steady-state result for an isolated buried cable (Kennelly), but the transient response is only approximate.
- **The duct air gap uses one fixed estimate.** It's computed once from the IEC 60287 air-space formula at a mean temperature of 60 °C.
- **Bedding is an annulus of 0.15 m radius.** That's an estimate, not a trench geometry.
- **Nothing here has been verified against measurements yet.** Darmstadt verification is the next physics task.
- **The local ground thermal code from the synthesis doc isn't in GitHub.** That's `SoilSens_Local_Ground_Continuation.zip`, with its 55 tests. Once it's pushed, wire it in behind `pipeline.assess` in place of `physics/radial.py`.

## How to plug in the real models later

- **New forecaster:** add a branch in `forecast/base.get_forecast()` that returns `(temp[72,5], moist[72,5])`.
- **Better ground model:** keep the `simulate(cable, inst, t_bg, theta_bg, current, T0)` signature and return a `SimResult`.
- **The app needs no changes for either.**
