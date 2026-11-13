"""USCRN hourly data access.

Station files are the repo's existing NPZ arrays (2019-2021, local standard time).
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache

import numpy as np
import pandas as pd

from . import config


@dataclass
class StationData:
    name: str
    time: pd.DatetimeIndex     # hourly, LST
    st: np.ndarray             # (n, 5) soil temperature, degC
    sm: np.ndarray             # (n, 5) volumetric moisture, m3/m3
    p: np.ndarray              # (n,) precipitation, mm/h

    def frame(self) -> pd.DataFrame:
        cols = {}
        for i, d in enumerate(config.DEPTHS_CM):
            cols[f"T{d}"] = self.st[:, i]
        for i, d in enumerate(config.DEPTHS_CM):
            cols[f"M{d}"] = self.sm[:, i]
        cols["P"] = self.p
        return pd.DataFrame(cols, index=self.time)


def list_stations(require_deep: bool = True) -> list[str]:
    """Stations available on disk. With require_deep, keep only those whose 50 and
    100 cm sensors are mostly valid (needed to interpolate to cable depth)."""
    files = sorted(config.data_dir().glob("*.npz"))
    names = sorted({re.sub(r"_\d{4}$", "", f.stem) for f in files})
    if not require_deep:
        return names
    return [n for n in names if _deep_ok(n)]


@lru_cache(maxsize=None)
def _deep_ok(name: str) -> bool:
    try:
        s = load_station(name)
    except Exception:
        return False
    nan_frac = np.isnan(s.st[:, 3:5]).mean(axis=0)
    return bool((nan_frac < 0.5).all())


@lru_cache(maxsize=64)
def load_station(name: str) -> StationData:
    files = sorted(config.data_dir().glob(f"{name}_*.npz"))
    files = [f for f in files if re.fullmatch(rf"{re.escape(name)}_\d{{4}}", f.stem)]
    if not files:
        raise FileNotFoundError(f"No NPZ files for {name} in {config.data_dir()}")
    parts = []
    for f in files:
        d = np.load(f)
        t = pd.to_datetime(d["date"].astype(str), format="%Y%m%d") + pd.to_timedelta(
            d["hour"].astype(int), unit="h")
        parts.append(pd.DataFrame(
            np.column_stack([d["ST"], d["SM"], d["P"]]), index=t))
    df = pd.concat(parts).sort_index()
    df = df[~df.index.duplicated(keep="first")]
    full = pd.date_range(df.index.min(), df.index.max(), freq="h")
    df = df.reindex(full)
    arr = df.to_numpy(dtype=float, copy=True)
    st, sm, p = arr[:, 0:5].copy(), arr[:, 5:10].copy(), arr[:, 10].copy()
    # QC: physically impossible values -> NaN (flag, don't silently fix)
    st[(st < -40) | (st > 70)] = np.nan
    sm[(sm < 0) | (sm > 0.6)] = np.nan
    p[(p < 0) | (p > 200)] = np.nan
    return StationData(name, full, st, sm, p)


def valid_issue_times(s: StationData, hours=(8,), need_future: bool = True) -> pd.DatetimeIndex:
    """Issue times with a usable 168 h history (and, if need_future, 72 h of truth).

    Default: one issue per day at 08:00 LST, like the existing benchmark.
    Pass hours=(2, 8, 14, 20) for more training samples.
    """
    idx = []
    n = len(s.time)
    hist, hor = config.HISTORY_H, config.HORIZON_H
    hours = set(hours)
    for i in range(hist, n - (hor if need_future else 0)):
        if s.time[i].hour not in hours:
            continue
        # current values at 20/50/100 cm must exist; history mostly present
        if np.isnan(s.st[i, 2:5]).any():
            continue
        if np.isnan(s.st[i - hist:i, 3:5]).mean() > 0.2:
            continue
        if need_future and np.isnan(s.st[i + 1:i + 1 + hor, 3:5]).mean() > 0.2:
            continue
        idx.append(s.time[i])
    return pd.DatetimeIndex(idx)


def window(s: StationData, issue: pd.Timestamp):
    """Return (history_df[168h ending at issue], future_df[72h after issue] or None)."""
    i = s.time.get_loc(issue)
    df = s.frame()
    hist = df.iloc[i - config.HISTORY_H + 1:i + 1]
    fut = df.iloc[i + 1:i + 1 + config.HORIZON_H]
    return hist, (fut if len(fut) == config.HORIZON_H else None)
