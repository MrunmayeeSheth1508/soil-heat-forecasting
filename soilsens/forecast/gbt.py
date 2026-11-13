"""Gradient-boosted tree forecaster with the four-stage ablation from the slides.

Design (simple on purpose, Phase 2 starting point):
  * one HistGradientBoostingRegressor per target (5 temperature + 5 moisture depths)
  * lead hour is an input feature, so one model covers leads 1-72
  * target is the CHANGE from the issue-time value (y[t+L] - y[t])
  * NaNs are handled natively by the model (missingness stays visible)
  * chronological split: train on years < test_year, test on test_year

Ablation stages (each adds one information group):
  0 temperature only | 1 + rainfall | 2 + current moisture | 3 + moisture history
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import joblib

try:  # sklearn's compiled modules can be blocked by Windows Application Control
    from sklearn.ensemble import HistGradientBoostingRegressor
    HAVE_SKLEARN, SKLEARN_ERROR = True, ""
except Exception as e:  # pragma: no cover
    HistGradientBoostingRegressor = None
    HAVE_SKLEARN, SKLEARN_ERROR = False, str(e)

from .. import config, data

STAGE_NAMES = {0: "temperature only", 1: "+ rainfall", 2: "+ current moisture",
               3: "+ moisture history"}
TRAIN_LEADS = np.r_[1, 2, 3, 4, 6, 9, 12, 15, 18, 21, 24, 30, 36, 42, 48, 54, 60, 66, 72]
TARGETS = [f"T{d}" for d in config.DEPTHS_CM] + [f"M{d}" for d in config.DEPTHS_CM]


def features(hist: pd.DataFrame, issue: pd.Timestamp, stage: int) -> dict:
    """Engineered features from the 168 h history ending at the issue time."""
    f = {}
    T = hist[[f"T{d}" for d in config.DEPTHS_CM]].to_numpy(float)
    M = hist[[f"M{d}" for d in config.DEPTHS_CM]].to_numpy(float)
    P = hist["P"].to_numpy(float)
    for j, d in enumerate(config.DEPTHS_CM):
        col = T[:, j]
        f[f"T{d}_now"] = col[-1]
        for lag in (3, 6, 12, 24, 48):
            f[f"T{d}_d{lag}"] = col[-1] - col[-1 - lag]
        f[f"T{d}_mean24"] = np.nanmean(col[-24:]) if np.isfinite(col[-24:]).any() else np.nan
        f[f"T{d}_mean168"] = np.nanmean(col) if np.isfinite(col).any() else np.nan
        f[f"T{d}_amp24"] = (np.nanmax(col[-24:]) - np.nanmin(col[-24:])) if np.isfinite(col[-24:]).any() else np.nan
    # calendar / context (common to all stages)
    hr, doy = issue.hour, issue.dayofyear
    f["hour_sin"], f["hour_cos"] = np.sin(2 * np.pi * hr / 24), np.cos(2 * np.pi * hr / 24)
    f["doy_sin"], f["doy_cos"] = np.sin(2 * np.pi * doy / 365.25), np.cos(2 * np.pi * doy / 365.25)
    f["t_missing_frac"] = float(np.isnan(T).mean())
    if stage >= 1:   # + rainfall
        for w in (1, 6, 24, 72, 168):
            f[f"P_sum{w}"] = np.nansum(P[-w:])
        wet = np.where(np.nan_to_num(P) > 0.2)[0]
        f["h_since_rain"] = (len(P) - 1 - wet[-1]) if len(wet) else 999
    if stage >= 2:   # + current moisture (trailing 24 h mean + coverage)
        for j, d in enumerate(config.DEPTHS_CM):
            c = M[-24:, j]
            f[f"M{d}_mean24"] = np.nanmean(c) if np.isfinite(c).any() else np.nan
            f[f"M{d}_cov24"] = float(np.isfinite(c).mean())
    if stage >= 3:   # + moisture history (drying / wetting trajectory)
        for j, d in enumerate(config.DEPTHS_CM):
            c = M[:, j]
            f[f"M{d}_now"] = c[-1]
            for lag in (24, 72, 167):
                f[f"M{d}_d{lag}"] = c[-1] - c[-1 - lag]
            f[f"M{d}_min168"] = np.nanmin(c) if np.isfinite(c).any() else np.nan
            f[f"M{d}_max168"] = np.nanmax(c) if np.isfinite(c).any() else np.nan
    return f


def build_rows(stations, stage, years=None, hours=(2, 8, 14, 20), leads=TRAIN_LEADS):
    """Training table: one row per (issue, lead). Vectorised over leads."""
    X, Y, meta = [], [], []
    leads = np.asarray(leads)
    for name in stations:
        s = data.load_station(name)
        df = s.frame()
        arr = df[TARGETS].to_numpy(float)
        issues = data.valid_issue_times(s, hours=hours)
        if years is not None:
            issues = issues[issues.year.isin(years)]
        locs = s.time.get_indexer(issues)
        for iss, i in zip(issues, locs):
            hist = df.iloc[i - config.HISTORY_H + 1:i + 1]
            base = features(hist, iss, stage)
            X.append(base)
            Y.append(arr[i + leads] - arr[i])        # (n_leads, 10)
            meta.append((name, iss))
    Xb = pd.DataFrame(X)
    nL = len(leads)
    Xr = Xb.loc[Xb.index.repeat(nL)].reset_index(drop=True)
    Xr["lead"] = np.tile(leads, len(Xb))
    Yr = pd.DataFrame(np.concatenate(Y) if Y else np.empty((0, len(TARGETS))), columns=TARGETS)
    return Xr, Yr, meta


def train(stations, stage=3, test_year=2021, max_iter=200, verbose=True):
    years = [y for y in (2019, 2020, 2021) if y < test_year]
    X, Y, _ = build_rows(stations, stage, years=years, hours=(8, 20))
    models = {}
    for t in TARGETS:
        ok = Y[t].notna()
        if ok.sum() < 200:
            continue
        m = HistGradientBoostingRegressor(max_iter=max_iter, learning_rate=0.05,
                                          max_leaf_nodes=31, l2_regularization=1.0,
                                          early_stopping=True, random_state=0)
        m.fit(X[ok], Y.loc[ok, t])
        models[t] = m
        if verbose:
            print(f"  stage {stage} {t}: {ok.sum()} rows")
    bundle = {"stage": stage, "stations": list(stations), "train_years": years,
              "columns": list(X.columns), "models": models}
    joblib.dump(bundle, _path(stage))
    return bundle


def _path(stage):
    return config.model_dir() / f"gbt_stage{stage}.joblib"


_CACHE = {}


def load(stage):
    if stage not in _CACHE:
        p = _path(stage)
        if not p.exists():
            raise FileNotFoundError(
                f"No trained GBT for stage {stage}. Run: python scripts/train_gbt.py --stage {stage}")
        _CACHE[stage] = joblib.load(p)
    return _CACHE[stage]


def is_trained(stage) -> bool:
    return HAVE_SKLEARN and _path(stage).exists()


def predict(station, issue, stage=3):
    b = load(stage)
    s = data.load_station(station)
    df = s.frame()
    i = s.time.get_loc(issue)
    hist = df.iloc[i - config.HISTORY_H + 1:i + 1]
    base = features(hist, issue, stage)
    now = hist[TARGETS].ffill().iloc[-1].to_numpy(float)
    X = pd.DataFrame([dict(base, lead=L) for L in range(1, config.HORIZON_H + 1)])[b["columns"]]
    out = np.tile(now, (config.HORIZON_H, 1))   # falls back to persistence if no model
    for k, t in enumerate(TARGETS):
        if t in b["models"]:
            out[:, k] = now[k] + b["models"][t].predict(X)
    out[:, 5:] = np.clip(out[:, 5:], 0.0, 0.6)
    return out[:, :5], out[:, 5:]
