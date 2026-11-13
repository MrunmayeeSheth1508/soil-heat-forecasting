"""Common forecast container and the single entry point the UI calls."""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from .. import config, provenance


@dataclass
class Forecast:
    station: str
    issue: pd.Timestamp
    method: str                       # "persistence", "diurnal", "gbt", "gru"
    times: pd.DatetimeIndex           # 72 hourly valid times
    temp: np.ndarray                  # (72, 5) degC
    moist: np.ndarray                 # (72, 5) m3/m3
    provenance: str = provenance.FITTED
    note: str = ""
    truth_temp: np.ndarray | None = None   # (72, 5) observed, if available (evaluation only)
    truth_moist: np.ndarray | None = None
    meta: dict = field(default_factory=dict)

    def frame(self) -> pd.DataFrame:
        cols = {"lead_h": np.arange(1, config.HORIZON_H + 1)}
        for i, d in enumerate(config.DEPTHS_CM):
            cols[f"T{d}_fc"] = self.temp[:, i]
        for i, d in enumerate(config.DEPTHS_CM):
            cols[f"M{d}_fc"] = self.moist[:, i]
        if self.truth_temp is not None:
            for i, d in enumerate(config.DEPTHS_CM):
                cols[f"T{d}_obs"] = self.truth_temp[:, i]
            for i, d in enumerate(config.DEPTHS_CM):
                cols[f"M{d}_obs"] = self.truth_moist[:, i]
        df = pd.DataFrame(cols, index=self.times)
        df.index.name = "time_lst"
        return df

    def at_depth(self, depth_m: float, which: str = "fc"):
        """Linear interpolation between sensor depths (slides: 'linear depth
        interpolation'). Returns (temp(72,), moist(72,))."""
        T = self.temp if which == "fc" else self.truth_temp
        M = self.moist if which == "fc" else self.truth_moist
        return interp_depth(T, depth_m), interp_depth(M, depth_m)


def interp_depth(arr: np.ndarray, depth_m: float) -> np.ndarray:
    """arr (n,5) at USCRN depths -> (n,) at depth_m, linear, ignoring NaN depths."""
    z = np.array(config.DEPTHS_M)
    out = np.full(arr.shape[0], np.nan)
    for k in range(arr.shape[0]):
        ok = ~np.isnan(arr[k])
        if ok.sum() >= 2:
            out[k] = np.interp(depth_m, z[ok], arr[k, ok])
        elif ok.sum() == 1:
            out[k] = arr[k, ok][0]
    return out


METHODS = {
    "persistence": "Persistence (B1): last observed value held for 72 h",
    "diurnal": "Diurnal persistence: last 24 h cycle repeated",
    "gbt": "Gradient-boosted trees (benchmark AI)",
    "gru": "GRU (primary AI) - needs trained weights",
}


def get_forecast(station: str, issue, method: str = "persistence", stage: int = 3,
                 with_truth: bool = True) -> Forecast:
    """THE function the UI calls. Swap implementations here, nothing else changes."""
    from .. import data
    from . import baselines

    s = data.load_station(station)
    issue = pd.Timestamp(issue)
    hist, fut = data.window(s, issue)

    if method == "persistence":
        T, M = baselines.persistence(hist)
        prov, note = provenance.CALCULATED, "Reference baseline, not AI."
    elif method == "diurnal":
        T, M = baselines.diurnal(hist)
        prov, note = provenance.CALCULATED, "Reference baseline, not AI."
    elif method == "gbt":
        from . import gbt
        T, M = gbt.predict(station, issue, stage=stage)
        prov, note = provenance.FITTED, f"GBT, ablation stage {stage} ({gbt.STAGE_NAMES[stage]})."
    elif method == "gru":
        from . import gru
        T, M = gru.predict(station, issue)
        prov, note = provenance.FITTED, "GRU encoder, two heads."
    else:
        raise ValueError(f"unknown method {method}")

    times = pd.date_range(issue + pd.Timedelta(hours=1), periods=config.HORIZON_H, freq="h")
    fc = Forecast(station, issue, method, times, T, M, prov, note)
    if with_truth and fut is not None:
        fc.truth_temp = fut[[f"T{d}" for d in config.DEPTHS_CM]].to_numpy()
        fc.truth_moist = fut[[f"M{d}" for d in config.DEPTHS_CM]].to_numpy()
    return fc
