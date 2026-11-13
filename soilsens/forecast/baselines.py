"""Reference forecasts every AI model must beat."""
import numpy as np
import pandas as pd

from .. import config

TCOLS = [f"T{d}" for d in config.DEPTHS_CM]
MCOLS = [f"M{d}" for d in config.DEPTHS_CM]


def _last_valid(hist: pd.DataFrame, cols):
    return hist[cols].ffill().iloc[-1].to_numpy(dtype=float)


def persistence(hist: pd.DataFrame):
    """B1: hold the last valid value at each depth for all 72 leads."""
    H = config.HORIZON_H
    T = np.tile(_last_valid(hist, TCOLS), (H, 1))
    M = np.tile(_last_valid(hist, MCOLS), (H, 1))
    return T, M


def diurnal(hist: pd.DataFrame):
    """Repeat the last 24 h of temperature: value at lead L = value at (issue + L - 24 h).
    Keeps the daily cycle at shallow depths. Moisture is held (persistence)."""
    H = config.HORIZON_H
    last24 = hist[TCOLS].ffill().iloc[-24:].to_numpy(dtype=float)
    T = np.vstack([last24] * (H // 24))
    M = np.tile(_last_valid(hist, MCOLS), (H, 1))
    return T, M
