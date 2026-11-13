"""Earlier-stage results from the GitHub repo (soil-heat-forecasting), read with the
standard library only. Files in data/repo/ are copied unchanged from the repo:

  forecast_scores.csv          results/06_forecast_benchmark/  (stage 8 benchmark, per event)
  forecast_figure.png          results/06_forecast_benchmark/
  stage_run_log.json           repo root (re-execution of earlier-stage scripts)
  stage_output_comparison.md   repo root (regenerated vs shipped outputs)
  history.json                 extracted from docs/PROJECT_HISTORY.md
"""
import csv
import json
import statistics
from functools import lru_cache

from .core import DATA

REPO = DATA / "repo"
METHODS = [("B1", "Persistence"), ("B2", "Seasonal anomaly"), ("C1", "Conduction, global α"),
           ("C2", "Conduction, fitted α (primary)"), ("C3", "Conduction, station α"),
           ("RECON", "Reconstruction (uses future boundaries, diagnostic only)")]


@lru_cache(maxsize=1)
def benchmark():
    """Median event MAE by method, depth and horizon, recomputed from the repo's
    per-event scores. Validation split = the repo's reported numbers."""
    with open(REPO / "forecast_scores.csv", newline="") as f:
        rows = list(csv.DictReader(f))
    out = {}
    for split in ("dev", "val"):
        sub = [r for r in rows if r["split"] == split]
        tab = []
        for code, name in METHODS:
            row = {"code": code, "method": name}
            for d in ("T20", "T50"):
                for h in ("24", "48", "72"):
                    vals = [float(r[f"{code}_{d}_h1_{h}_mae"]) for r in sub
                            if r.get(f"{code}_{d}_h1_{h}_mae") not in ("", None, "nan")]
                    row[f"{d}_h{h}"] = round(statistics.median(vals), 3) if vals else None
            tab.append(row)
        out[split] = {"n_events": len(sub), "n_stations": len({r["station"] for r in sub}),
                      "table": tab}
    return out


@lru_cache(maxsize=1)
def stage_log():
    log = json.loads((REPO / "stage_run_log.json").read_text(encoding="utf-8"))
    counts = {}
    for e in log:
        k = e["status"].split(" ")[0]
        counts[k] = counts.get(k, 0) + 1
    rows = [{"script": e["script"], "status": e["status"],
             "seconds": e.get("seconds"), "note": e.get("reason", "")} for e in log]
    return {"counts": counts, "rows": rows}


@lru_cache(maxsize=1)
def repro():
    rows = []
    for line in (REPO / "stage_output_comparison.md").read_text(encoding="utf-8").splitlines():
        parts = [p.strip() for p in line.strip().strip("|").split("|")]
        if len(parts) == 3 and parts[0] not in ("file", "---") and not parts[0].startswith("-"):
            rows.append({"file": parts[0], "status": parts[1], "detail": parts[2]})
    same = sum(r["status"].startswith("identical") for r in rows)
    return {"identical": same, "total": len(rows), "different": [r for r in rows if not r["status"].startswith("identical")]}


def history():
    return json.loads((REPO / "history.json").read_text(encoding="utf-8"))


def everything():
    return {"history": history(), "benchmark": benchmark(), "stage_log": stage_log(), "repro": repro()}
