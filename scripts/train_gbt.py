"""Train the gradient-boosted tree forecaster for one or all ablation stages.

    python scripts/train_gbt.py --stage all
    python scripts/train_gbt.py --stage 3 --stations OK_Stillwater_2_W NE_Lincoln_8_ENE
"""
import argparse, time
import _path  # noqa: F401
from soilsens import config, data
from soilsens.forecast import gbt

ap = argparse.ArgumentParser()
ap.add_argument("--stage", default="all")
ap.add_argument("--stations", nargs="*")
ap.add_argument("--test-year", type=int, default=2021)
a = ap.parse_args()
avail = set(data.list_stations(require_deep=False))
stations = [s for s in (a.stations or config.DEFAULT_STATIONS) if s in avail]
stages = range(4) if a.stage == "all" else [int(a.stage)]
print(f"stations ({len(stations)}): {stations}")
for st in stages:
    t = time.time()
    print(f"stage {st}: {gbt.STAGE_NAMES[st]}")
    gbt.train(stations, stage=st, test_year=a.test_year)
    print(f"  saved {gbt._path(st)}  ({time.time() - t:.0f}s)")
