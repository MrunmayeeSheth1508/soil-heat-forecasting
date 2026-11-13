"""GRU environmental forecaster (primary AI) - model, training, prediction.

Matches slide 11: one compact GRU encoder, separate temperature and moisture output
heads, scaled losses, masked missing targets. Input = 168 h of hourly T (5 depths),
M (5 depths), P, missingness flags and hour/day-of-year encodings. Output = change
from the issue-time value for leads 1-72 at 5 depths, for both variables.

Chronological protocol: train on 2019 to Sep 2020, validate (early stopping) on
Oct-Dec 2020, test on 2021. Normalisation statistics come from training data only.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .. import config, data

try:
    import torch
    from torch import nn
    HAVE_TORCH = True
except Exception:  # torch is optional for the rest of the app
    HAVE_TORCH = False

H, D = config.HORIZON_H, len(config.DEPTHS_CM)
HIST = config.HISTORY_H
TCOLS = [f"T{d}" for d in config.DEPTHS_CM]
MCOLS = [f"M{d}" for d in config.DEPTHS_CM]
N_IN = 5 + 5 + 1 + 10 + 4   # T, M, P, masks(T,M), hour/doy sin/cos
VAL_START = pd.Timestamp("2020-10-01")


def _arrays(name):
    s = data.load_station(name)
    return s, s.st, s.sm, s.p, s.time


def encode_window(T, M, P, times, norm):
    """T, M: (168,5); P: (168,); times: DatetimeIndex (168). Returns (168, N_IN) float32."""
    mT, mM = np.isnan(T), np.isnan(M)
    Tn = np.nan_to_num((T - norm["T_mu"]) / norm["T_sd"])
    Mn = np.nan_to_num((M - norm["M_mu"]) / norm["M_sd"])
    Pn = np.log1p(np.nan_to_num(np.clip(P, 0, None)))[:, None]
    hr, doy = times.hour.to_numpy(), times.dayofyear.to_numpy()
    cal = np.column_stack([np.sin(2 * np.pi * hr / 24), np.cos(2 * np.pi * hr / 24),
                           np.sin(2 * np.pi * doy / 365.25), np.cos(2 * np.pi * doy / 365.25)])
    return np.column_stack([Tn, Mn, Pn, mT, mM, cal]).astype(np.float32)


def _last_valid(a):
    out = np.full(a.shape[1], np.nan)
    for j in range(a.shape[1]):
        v = a[:, j][~np.isnan(a[:, j])]
        if len(v):
            out[j] = v[-1]
    return out


def _window(name, issue, norm):
    s, st, sm, p, t = _arrays(name)
    i = s.time.get_loc(issue)
    sl = slice(i - HIST + 1, i + 1)
    x = encode_window(st[sl], sm[sl], p[sl], t[sl], norm)
    return x, _last_valid(st[sl]), _last_valid(sm[sl]), i


if HAVE_TORCH:
    class GRUForecaster(nn.Module):
        def __init__(self, hidden=64):
            super().__init__()
            self.enc = nn.GRU(N_IN, hidden, batch_first=True)
            self.head_T = nn.Sequential(nn.Linear(hidden, 128), nn.ReLU(), nn.Linear(128, H * D))
            self.head_M = nn.Sequential(nn.Linear(hidden, 128), nn.ReLU(), nn.Linear(128, H * D))

        def forward(self, x):
            _, h = self.enc(x)
            h = h[-1]
            return self.head_T(h).view(-1, H, D), self.head_M(h).view(-1, H, D)


def build(stations, t0, t1, norm, hours=(8, 20)):
    X, YT, YM = [], [], []
    for name in stations:
        s, st, sm, p, t = _arrays(name)
        issues = data.valid_issue_times(s, hours=hours)
        issues = issues[(issues >= t0) & (issues < t1)]
        for iss in issues:
            x, nowT, nowM, i = _window(name, iss, norm)
            X.append(x)
            YT.append((st[i + 1:i + 1 + H] - nowT) / norm["dT_sd"])
            YM.append((sm[i + 1:i + 1 + H] - nowM) / norm["dM_sd"])
    return np.stack(X), np.stack(YT).astype(np.float32), np.stack(YM).astype(np.float32)


def _norm(stations, t1):
    Ts, Ms = [], []
    for n in stations:
        s = data.load_station(n)
        m = s.time < t1
        Ts.append(s.st[m]); Ms.append(s.sm[m])
    T, M = np.concatenate(Ts), np.concatenate(Ms)
    return {"T_mu": np.nanmean(T, 0), "T_sd": np.nanstd(T, 0) + 1e-6,
            "M_mu": np.nanmean(M, 0), "M_sd": np.nanstd(M, 0) + 1e-6,
            "dT_sd": 1.0, "dM_sd": 0.01}


def _loss(model, X, YT, YM):
    pT, pM = model(X)
    mT, mM = ~torch.isnan(YT), ~torch.isnan(YM)
    lT = ((pT - torch.nan_to_num(YT)) ** 2)[mT].mean()
    lM = ((pM - torch.nan_to_num(YM)) ** 2)[mM].mean()
    return lT + lM, lT, lM


def train(stations, epochs=25, hidden=64, lr=1e-3, patience=5, seed=0, verbose=True):
    if not HAVE_TORCH:
        raise ImportError("pip install torch  (CPU build is enough)")
    torch.manual_seed(seed); np.random.seed(seed)
    t_start, t_end = pd.Timestamp("2019-01-01"), pd.Timestamp("2021-01-01")
    norm = _norm(stations, VAL_START)
    Xtr, YTtr, YMtr = build(stations, t_start, VAL_START, norm)
    Xva, YTva, YMva = build(stations, VAL_START, t_end, norm)
    if verbose:
        print(f"  train windows {len(Xtr)}, validation windows {len(Xva)}", flush=True)
    Xtr, YTtr, YMtr = map(torch.tensor, (Xtr, YTtr, YMtr))
    Xva, YTva, YMva = map(torch.tensor, (Xva, YTva, YMva))
    model = GRUForecaster(hidden)
    opt = torch.optim.Adam(model.parameters(), lr=lr)
    best, best_state, bad, hist = float("inf"), None, 0, []
    for ep in range(epochs):
        model.train()
        perm = torch.randperm(len(Xtr))
        tot = 0.0
        for b in range(0, len(Xtr), 64):
            idx = perm[b:b + 64]
            loss, _, _ = _loss(model, Xtr[idx], YTtr[idx], YMtr[idx])
            opt.zero_grad(); loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            opt.step()
            tot += loss.item() * len(idx)
        model.eval()
        with torch.no_grad():
            vl = [(_loss(model, Xva[b:b + 256], YTva[b:b + 256], YMva[b:b + 256]), len(Xva[b:b + 256]))
                  for b in range(0, len(Xva), 256)]
        v = sum(l[0].item() * n for l, n in vl) / len(Xva)
        hist.append({"epoch": ep + 1, "train_loss": tot / len(Xtr), "val_loss": v})
        if verbose:
            print(f"  epoch {ep + 1:2d}  train {tot / len(Xtr):.4f}  val {v:.4f}", flush=True)
        if v < best - 1e-4:
            best, bad = v, 0
            best_state = {k: t.clone() for k, t in model.state_dict().items()}
        else:
            bad += 1
            if bad >= patience:
                break
    model.load_state_dict(best_state)
    torch.save({"state": best_state, "norm": norm, "hidden": hidden, "stations": list(stations),
                "train": "2019-01-01..2020-09-30", "validation": "2020-10-01..2020-12-31",
                "history": hist, "best_val": best}, config.model_dir() / "gru.pt")
    return model, hist


def is_trained() -> bool:
    return (config.model_dir() / "gru.pt").exists()


_CACHE = {}


def _load():
    if "m" not in _CACHE:
        p = config.model_dir() / "gru.pt"
        if not p.exists():
            raise FileNotFoundError("No trained GRU. Run: python scripts/train_gru.py")
        ck = torch.load(p, weights_only=False)
        m = GRUForecaster(ck["hidden"]); m.load_state_dict(ck["state"]); m.eval()
        _CACHE["m"], _CACHE["norm"] = m, ck["norm"]
    return _CACHE["m"], _CACHE["norm"]


def predict(station, issue):
    if not HAVE_TORCH:
        raise ImportError("GRU needs torch: pip install torch")
    m, norm = _load()
    x, nowT, nowM, _ = _window(station, pd.Timestamp(issue), norm)
    with torch.no_grad():
        pT, pM = m(torch.tensor(x[None]))
    T = nowT + pT[0].numpy() * norm["dT_sd"]
    M = np.clip(nowM + pM[0].numpy() * norm["dM_sd"], 0, 0.6)
    return T, M


def predict_many(station, issues, batch=256):
    """Vectorised prediction for many issue times (used to export forecasts)."""
    m, norm = _load()
    out = []
    for b in range(0, len(issues), batch):
        ws = [_window(station, pd.Timestamp(i), norm) for i in issues[b:b + batch]]
        with torch.no_grad():
            pT, pM = m(torch.tensor(np.stack([w[0] for w in ws])))
        for k, w in enumerate(ws):
            out.append((w[1] + pT[k].numpy() * norm["dT_sd"],
                        np.clip(w[2] + pM[k].numpy() * norm["dM_sd"], 0, 0.6)))
    return out
