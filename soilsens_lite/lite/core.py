"""Station data, heat-spell archive, soil analysis and background forecasts.
Python standard library only.

Station arrays and GBT forecasts were exported from the full Phase 2 backend as int16
binaries (temperature x100, moisture x10000, rain x100; NaN = -32768).
"""
from __future__ import annotations

import json
import math
import statistics
import sys
from array import array
from datetime import datetime, timedelta
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
DEPTHS_CM = [5, 10, 20, 50, 100]
DEPTHS_M = [d / 100 for d in DEPTHS_CM]
HIST, HOR = 168, 72
NAN = float("nan")
FMT = "%Y-%m-%d %H:%M"
isnan = math.isnan


@lru_cache(maxsize=1)
def index():
    return json.loads((DATA / "index.json").read_text(encoding="utf-8"))


def stations():
    return list(index().keys())


def _read_i16(path):
    a = array("h")
    a.frombytes(path.read_bytes())
    if sys.byteorder == "big":
        a.byteswap()
    return a


class Station:
    def __init__(self, name):
        meta = index()[name]
        self.name, self.site = name, meta.get("site", {})
        self.start = datetime.strptime(meta["start"], FMT)
        n = self.n = meta["n"]
        raw = _read_i16(DATA / "stations" / f"{name}.bin")
        dec = lambda v, s: NAN if v <= -32767 else v / s
        self.T = [[dec(raw[i * 5 + j], 100) for j in range(5)] for i in range(n)]
        o = 5 * n
        self.M = [[dec(raw[o + i * 5 + j], 10000) for j in range(5)] for i in range(n)]
        o = 10 * n
        self.P = [dec(raw[o + i], 100) for i in range(n)]
        self.gbt_issues = meta["gbt_issues"]
        self._gbt_pos = {s: k for k, s in enumerate(self.gbt_issues)}

    def time(self, i):
        return self.start + timedelta(hours=i)

    def loc(self, ts):
        t = ts if isinstance(ts, datetime) else datetime.strptime(ts, FMT)
        return int(round((t - self.start).total_seconds() / 3600))

    def issue_times(self):
        out = []
        for i in range(HIST, self.n - HOR):
            t = self.time(i)
            if t.hour == 8 and not any(isnan(self.T[i][j]) for j in (2, 3, 4)):
                out.append(t.strftime(FMT))
        return out

    def gbt(self, issue, stage=3, model="gbt"):
        k = self._gbt_pos.get(issue)
        if k is None:
            return None
        raw = _gbt_raw(self.name, stage) if model == "gbt" else _gru_raw(self.name)
        if raw is None:
            return None
        base = k * HOR * 10
        T, M = [], []
        for h in range(HOR):
            row = raw[base + h * 10: base + h * 10 + 10]
            T.append([NAN if v <= -32767 else v / 100 for v in row[:5]])
            M.append([NAN if v <= -32767 else v / 10000 for v in row[5:]])
        return T, M

    # ---- daily means and a day-of-year climatology (for anomalies and the B2 baseline)
    @property
    def daily(self):
        if not hasattr(self, "_daily"):
            days = {}
            for i in range(self.n):
                d = self.time(i).date()
                days.setdefault(d, []).append(i)
            out = {}
            for d, idx in days.items():
                row = []
                for var in (self.T, self.M):
                    for j in range(5):
                        v = [var[i][j] for i in idx if not isnan(var[i][j])]
                        row.append(sum(v) / len(v) if len(v) >= 18 else NAN)
                p = [self.P[i] for i in idx if not isnan(self.P[i])]
                row.append(sum(p) if len(p) >= 18 else NAN)
                out[d] = row
            self._daily = out
        return self._daily

    def climatology(self, exclude_year=None):
        """Day-of-year (+/-7 d) median of daily means over the available years
        (optionally leaving one year out). Returns {doy: [T5..T100, M5..M100]}."""
        key = f"_clim_{exclude_year}"
        if not hasattr(self, key):
            by = {}
            for d, row in self.daily.items():
                if d.year == exclude_year:
                    continue
                by.setdefault(d.timetuple().tm_yday, []).append(row)
            clim = {}
            for doy in range(1, 367):
                rows = []
                for o in range(-7, 8):
                    rows += by.get((doy - 1 + o) % 366 + 1, [])
                clim[doy] = [statistics.median(v) if (v := [r[c] for r in rows if not isnan(r[c])]) else NAN
                             for c in range(10)]
            setattr(self, key, clim)
        return getattr(self, key)


@lru_cache(maxsize=64)
def _gbt_raw(name, stage):
    p = DATA / "gbt" / f"{name}_s{stage}.bin"
    return _read_i16(p) if p.exists() else None


@lru_cache(maxsize=16)
def _gru_raw(name):
    p = DATA / "gru" / f"{name}.bin"
    return _read_i16(p) if p.exists() else None


@lru_cache(maxsize=1)
def gru_card():
    p = DATA / "gru" / "model_card.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


@lru_cache(maxsize=16)
def station(name) -> Station:
    return Station(name)


# ------------------------------------------------------------------ heat-spell archive
@lru_cache(maxsize=1)
def spells():
    return json.loads((DATA / "archive" / "heat_spells.json").read_text(encoding="utf-8"))


def spells_for(name):
    return [s for s in spells() if s["station"] == name]


def _f(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def spell_analysis(name, spell_id=None, start=None, end=None, before_d=7, after_d=21):
    """Hourly series around a spell, daily anomalies and depth-response metrics.

    Metric definitions follow specs/pilotA_prereg.md: peak anomaly over [start, end+14 d],
    peak delay = days from spell start to the peak, persistence = days from the peak until the
    anomaly first falls to <= 50% of the peak, burden = positive anomaly summed over
    [start, end+21 d] (degree-days, not energy). The anomaly reference here is the 2019-2021
    day-of-year median (+/-7 d); the archive values use the repo's 2012-2021 reference.
    """
    s = station(name)
    sp = next((x for x in spells() if x["spell_id"] == spell_id), None) if spell_id else None
    if sp:
        start, end = sp["start"], sp["end"]
    d0 = datetime.strptime(start, "%Y-%m-%d")
    d1 = datetime.strptime(end, "%Y-%m-%d")
    w0, w1 = d0 - timedelta(days=before_d), d1 + timedelta(days=after_d + 1)
    i0, i1 = max(0, s.loc(w0)), min(s.n, s.loc(w1))
    times = [s.time(i).strftime(FMT) for i in range(i0, i1)]
    clim = s.climatology()
    days, anom = [], []
    d = w0
    while d < w1:
        row = s.daily.get(d.date())
        c = clim[d.timetuple().tm_yday]
        if row:
            days.append(d.strftime("%Y-%m-%d"))
            anom.append([row[j] - c[j] if not (isnan(row[j]) or isnan(c[j])) else NAN for j in range(5)])
        d += timedelta(days=1)
    metrics = []
    for j, dep in enumerate(DEPTHS_CM):
        series = [(datetime.strptime(dd, "%Y-%m-%d"), a[j]) for dd, a in zip(days, anom)]
        win = [(t, v) for t, v in series if d0 <= t <= d1 + timedelta(days=14) and not isnan(v)]
        if not win:
            metrics.append({"depth_cm": dep}); continue
        tp, vp = max(win, key=lambda x: x[1])
        pers, cens = None, True
        if vp > 0:
            for t, v in series:
                if t > tp and not isnan(v) and v <= 0.5 * vp:
                    pers, cens = (t - tp).days, False
                    break
            if pers is None:
                pers = (series[-1][0] - tp).days
        burden = sum(max(v, 0) for t, v in series if d0 <= t <= d1 + timedelta(days=21) and not isnan(v))
        m = {"depth_cm": dep, "peak_anom_C": round(vp, 2), "peak_delay_d": (tp - d0).days,
             "persistence_d": pers, "persistence_censored": cens, "burden_Cd": round(burden, 1)}
        if sp:
            m["archive_peak_anom_C"] = _f(sp.get(f"peakanom{dep}"))
            m["archive_recovery_day"] = _f(sp.get(f"therm{dep}_day"))
        metrics.append(m)
    return {"station": name, "spell": sp, "start": start, "end": end, "times": times,
            "T": s.T[i0:i1], "M": s.M[i0:i1], "P": s.P[i0:i1],
            "days": days, "anom": anom, "metrics": metrics}


# ------------------------------------------------------------------ forecasts
METHODS = {
    "persistence": "Persistence (B1): last observed value held",
    "seasonal": "Seasonal anomaly (B2-style conventional baseline)",
    "diurnal": "Diurnal persistence: last 24 h cycle repeated",
    "gbt": "Trained ML: gradient-boosted trees (precomputed, 2021)",
    "gru": "Trained ML: GRU neural network (precomputed, 2021)",
}
STAGES = {0: "Temperature history", 1: "+ past rainfall", 2: "+ current moisture", 3: "+ moisture history"}


def _ffill_last(rows):
    last = [NAN] * len(rows[0]) if rows else [NAN] * 5
    for r in rows:
        for j in range(len(r)):
            if not isnan(r[j]):
                last[j] = r[j]
    return last


def forecast(name, issue, method="persistence", stage=3):
    s = station(name)
    i = s.loc(issue)
    if i < HIST - 1 or i >= s.n:
        raise ValueError("Issue time outside the data.")
    histT, histM = s.T[i - HIST + 1:i + 1], s.M[i - HIST + 1:i + 1]
    t_issue = s.time(i)
    if method == "persistence":
        lt, lm = _ffill_last(histT), _ffill_last(histM)
        T, M = [list(lt) for _ in range(HOR)], [list(lm) for _ in range(HOR)]
        prov, note = "calculated", "Reference baseline (B1), not AI."
    elif method == "diurnal":
        cur = _ffill_last(histT[:-24])
        last24 = []
        for r in histT[-24:]:
            cur = [r[j] if not isnan(r[j]) else cur[j] for j in range(5)]
            last24.append(cur)
        T = [list(last24[h % 24]) for h in range(HOR)]
        lm = _ffill_last(histM)
        M = [list(lm) for _ in range(HOR)]
        prov, note = "calculated", "Reference baseline, not AI."
    elif method == "seasonal":
        clim = s.climatology(exclude_year=t_issue.year)
        doy0 = t_issue.timetuple().tm_yday
        last24 = list(zip(histT[-24:], histM[-24:]))
        anom = []
        for c in range(10):
            vals = [(r[0] if c < 5 else r[1])[c % 5] for r in last24]
            vals = [v for v in vals if not isnan(v)]
            ref = clim[doy0][c]
            anom.append(sum(vals) / len(vals) - ref if len(vals) >= 18 and not isnan(ref) else 0.0)
        T, M = [], []
        lt, lm = _ffill_last(histT), _ffill_last(histM)
        for h in range(1, HOR + 1):
            doy = (t_issue + timedelta(hours=h)).timetuple().tm_yday
            c = clim[doy]
            T.append([c[j] + anom[j] if not isnan(c[j]) else lt[j] for j in range(5)])
            M.append([c[5 + j] + anom[5 + j] if not isnan(c[5 + j]) else lm[j] for j in range(5)])
        prov = "calculated"
        note = ("Conventional baseline: day-of-year climatology (+/-7 d, other years) plus the "
                "current 24 h anomaly, held constant.")
    elif method in ("gbt", "gru"):
        from . import live
        r, mode = None, "precomputed"
        if live.STATE["enabled"]:
            if t_issue.year < 2021:
                raise ValueError("Trained-ML forecasts are shown for 2021 only: the models were trained on "
                                 "2019-2020, so earlier issues would be in-sample.")
            r, mode = live.forecast(name, issue, method, stage), "computed live by the trained model"
        else:
            r = s.gbt(issue, stage, model=method)
        if r is None:
            raise ValueError("Trained-ML forecasts exist only for 2021 issue times (trained on 2019-2020).")
        T, M = r
        prov = "fitted"
        if method == "gbt":
            note = f"Gradient-boosted trees, input configuration {stage}: {STAGES[stage]}. Trained 2019-2020; {mode}."
        else:
            note = ("GRU encoder over 168 h (temperature and moisture at 5 depths, rainfall, missing-data flags, "
                    f"calendar), separate temperature and moisture heads. Trained 2019 to Sep 2020, early stopping "
                    f"on Oct-Dec 2020, tested on 2021; {mode}.")
    else:
        raise ValueError(method)
    have_obs = i + HOR < s.n
    obsT = s.T[i + 1:i + 1 + HOR] if have_obs else None
    obsM = s.M[i + 1:i + 1 + HOR] if have_obs else None
    times = [s.time(i + 1 + h).strftime(FMT) for h in range(HOR)]
    hist_times = [s.time(i - HIST + 1 + h).strftime(FMT) for h in range(HIST)]
    return {"method": method, "stage": stage if method == "gbt" else None, "provenance": prov,
            "note": note, "times": times, "T": T, "M": M, "obsT": obsT, "obsM": obsM,
            "hist_times": hist_times, "histT": histT, "histM": histM,
            "histP": s.P[i - HIST + 1:i + 1], "errors": errors(T, M, obsT, obsM)}


def errors(T, M, obsT, obsM):
    """MAE by depth and lead block (1-24, 25-48, 49-72 h, and 1-72 h)."""
    if obsT is None:
        return None
    out = {}
    for var, F, O in (("T", T, obsT), ("M", M, obsM)):
        rows = []
        for j, d in enumerate(DEPTHS_CM):
            row = {"depth_cm": d}
            for lab, a, b in (("h1_24", 0, 24), ("h25_48", 24, 48), ("h49_72", 48, 72), ("h1_72", 0, 72)):
                e = [abs(F[h][j] - O[h][j]) for h in range(a, b) if not (isnan(F[h][j]) or isnan(O[h][j]))]
                row[lab] = round(sum(e) / len(e), 4) if len(e) >= 0.75 * (b - a) else None
            rows.append(row)
        out[var] = rows
    return out


def interp_depth(rows, depth_m):
    out = []
    for r in rows:
        pts = [(DEPTHS_M[j], r[j]) for j in range(5) if not isnan(r[j])]
        if not pts:
            out.append(NAN)
        elif depth_m <= pts[0][0] or len(pts) == 1:
            out.append(pts[0][1])
        elif depth_m >= pts[-1][0]:
            out.append(pts[-1][1])
        else:
            for (z0, v0), (z1, v1) in zip(pts, pts[1:]):
                if z0 <= depth_m <= z1:
                    out.append(v0 + (v1 - v0) * (depth_m - z0) / (z1 - z0))
                    break
    return out


def fill(series, default):
    out = list(series)
    last = None
    for k, v in enumerate(out):
        if isnan(v):
            if last is not None:
                out[k] = last
        else:
            last = v
    nxt = None
    for k in range(len(out) - 1, -1, -1):
        if isnan(out[k]):
            if nxt is not None:
                out[k] = nxt
        else:
            nxt = out[k]
    return [default if isnan(v) else v for v in out]
