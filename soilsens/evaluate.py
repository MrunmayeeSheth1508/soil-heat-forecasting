"""Score forecasters against later observations: MAE by depth and lead.

Chronological: only issues in the test year are scored. Same issue set for every
method (common-set rule), so numbers are directly comparable.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import config, data
from .forecast.base import get_forecast


def score(stations, methods=("persistence", "diurnal", "gbt"), stages=(3,), test_year=2021,
          leads=(1, 6, 12, 24, 48, 72), max_issues_per_station=None):
    rows = []
    for name in stations:
        s = data.load_station(name)
        issues = data.valid_issue_times(s)
        issues = issues[issues.year == test_year]
        if max_issues_per_station:
            issues = issues[:: max(1, len(issues) // max_issues_per_station)]
        for iss in issues:
            for m in methods:
                for st in (stages if m == "gbt" else (None,)):
                    try:
                        fc = get_forecast(name, iss, m, stage=st if st is not None else 3)
                    except FileNotFoundError:
                        continue
                    if fc.truth_temp is None:
                        continue
                    label = m if st is None else f"{m}_s{st}"
                    for var, F, O in (("T", fc.temp, fc.truth_temp), ("M", fc.moist, fc.truth_moist)):
                        err = np.abs(F - O)
                        for j, d in enumerate(config.DEPTHS_CM):
                            rows.append({"station": name, "issue": iss, "method": label,
                                         "var": var, "depth_cm": d,
                                         "mae72": np.nanmean(err[:, j]) if np.isfinite(err[:, j]).any() else np.nan,
                                         **{f"ae_h{L}": err[L - 1, j] for L in leads}})
    return pd.DataFrame(rows)


def summary(df: pd.DataFrame) -> pd.DataFrame:
    """Median over issues of 72 h MAE, per method x variable x depth."""
    return (df.groupby(["var", "depth_cm", "method"])["mae72"].median()
              .unstack("method").round(4))
