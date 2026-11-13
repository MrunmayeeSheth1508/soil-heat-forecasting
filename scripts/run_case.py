"""Run one assessment from the command line and save CSV/JSON outputs.

    python scripts/run_case.py --station OK_Stillwater_2_W --issue "2021-07-15 08:00"
"""
import argparse, json
import _path  # noqa: F401
from soilsens import config
from soilsens.pipeline import Case, assess

ap = argparse.ArgumentParser()
ap.add_argument("--station", required=True)
ap.add_argument("--issue", required=True)
ap.add_argument("--method", default="persistence")
ap.add_argument("--depth", type=float, default=0.819)
ap.add_argument("--bedding", default="FTB (fluidized thermal backfill)")
ap.add_argument("--no-duct", action="store_true")
ap.add_argument("--drying", action="store_true")
ap.add_argument("--prior", type=float, default=300)
ap.add_argument("--future", type=float, default=400)
a = ap.parse_args()
c = Case(a.station, a.issue, method=a.method, depth_m=a.depth, bedding=a.bedding,
         in_duct=not a.no_duct, prior_current=a.prior, future_current=a.future,
         moisture_mode="critical-isotherm drying" if a.drying else "background only")
r = assess(c)
tag = f"{a.station}_{a.issue[:10]}_{a.method}"
out = config.output_dir()
r["trajectory"].to_csv(out / f"trajectory_{tag}.csv")
r["forecast"].frame().to_csv(out / f"forecast_{tag}.csv")
json.dump({"case": r["case"], "summary": r["summary"], "support": r["support"]},
          open(out / f"summary_{tag}.json", "w"), indent=2, default=str)
for k, v in r["summary"].items():
    print(f"{k:34s} {v['value']!s:>12}  [{v['provenance']}]")
