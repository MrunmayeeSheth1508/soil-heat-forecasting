"""Score persistence, diurnal, GBT stages 0-3 (and GRU if trained) on the test year.

    python scripts/run_ablation.py            # writes outputs/ablation_scores.csv + summary
"""
import argparse
import _path  # noqa: F401
from soilsens import config, data, evaluate
from soilsens.forecast import gru

ap = argparse.ArgumentParser()
ap.add_argument("--stations", nargs="*")
ap.add_argument("--max-issues", type=int, default=60, help="per station, evenly spaced")
a = ap.parse_args()
avail = set(data.list_stations(require_deep=False))
stations = [s for s in (a.stations or config.DEFAULT_STATIONS) if s in avail]
methods = ["persistence", "diurnal", "gbt"] + (["gru"] if gru.HAVE_TORCH and gru.is_trained() else [])
df = evaluate.score(stations, methods=methods, stages=(0, 1, 2, 3), max_issues_per_station=a.max_issues)
out = config.output_dir()
df.to_csv(out / "ablation_scores.csv", index=False)
summ = evaluate.summary(df)
summ.to_csv(out / "ablation_summary.csv")
print(summ.to_string())
