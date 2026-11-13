"""Train the GRU forecaster (needs torch).  python scripts/train_gru.py --epochs 25
Chronological: train 2019-Sep 2020, early stopping on Oct-Dec 2020, test 2021."""
import argparse
import _path  # noqa: F401
from soilsens import config, data
from soilsens.forecast import gru

ap = argparse.ArgumentParser()
ap.add_argument("--stations", nargs="*")
ap.add_argument("--epochs", type=int, default=25)
ap.add_argument("--hidden", type=int, default=64)
a = ap.parse_args()
avail = set(data.list_stations(require_deep=False))
stations = [s for s in (a.stations or config.DEFAULT_STATIONS) if s in avail]
print("stations:", stations, flush=True)
gru.train(stations, epochs=a.epochs, hidden=a.hidden)
print("saved", config.model_dir() / "gru.pt")
