import os as _o, sys as _s
_p = _o.path.dirname(_o.path.abspath(__file__))
while not _o.path.exists(_o.path.join(_p, 'src', 'config.py')): _p = _o.path.dirname(_p)
_s.path.insert(0, _o.path.join(_p, 'src'))
from config import WS_ROOT  # PATH-PATCH: was an absolute path to the original working directory
"""Descriptive check (no fitting): is the inventory's thermal-recovery rule informative at depth, and does the anomaly
propagate with depth in the expected order? Uses primary complete sequences from event_inventory.csv.
Outputs phase3/thermal_check_out.txt"""
import sys, io, os, glob, warnings
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace'); warnings.filterwarnings('ignore')
import numpy as np, pandas as pd
ROOT = WS_ROOT; D = os.path.join(ROOT, 'phase3', 'data')
E = pd.read_csv(os.path.join(ROOT, 'phase3', 'event_inventory.csv'))
C = E[(E.variant == 'primary') & E.complete_sequence].copy()

def daily_ST(stn):
    a = np.vstack([np.load(f) for f in sorted(glob.glob(os.path.join(D, f'{stn}_*.npy')))])
    df = pd.DataFrame({'date': pd.to_datetime(a[:, 0].astype(int).astype(str), format='%Y%m%d')})
    for k in range(5): df[f'ST{k}'] = a[:, 15 + k]
    g = df.groupby('date'); cnt = g.count(); m = g.mean()
    for k in range(5): m.loc[cnt[f'ST{k}'] < 20, f'ST{k}'] = np.nan
    return m.reindex(pd.date_range(m.index.min(), m.index.max()))

def clim_median(s, dates, win=7):
    doy = dates.dayofyear.values; yr = dates.year.values; yrs = np.unique(yr)
    M = np.full((len(yrs), 367), np.nan)
    for i, y in enumerate(yrs):
        m = yr == y; M[i, doy[m]] = s[m]
    out = np.full(367, np.nan)
    for d in range(1, 367):
        idx = [((d - 1 + o) % 366) + 1 for o in range(-win, win + 1)]
        v = M[:, idx].ravel(); v = v[~np.isnan(v)]
        if len(v) >= 20: out[d] = np.median(v)
    return out

rows = []
for stn, grp in C.groupby('station'):
    dd = daily_ST(stn); dates = dd.index; doy = dates.dayofyear.values
    anom = {k: dd[f'ST{k}'].values - clim_median(dd[f'ST{k}'].values, dates)[doy] for k in range(5)}
    sd = {k: np.nanstd(anom[k][np.isin(dates.month.values, [5, 6, 7, 8, 9])]) for k in range(5)}
    for _, r in grp.iterrows():
        a = dates.get_loc(pd.Timestamp(r.start)); b = dates.get_loc(pd.Timestamp(r.end))
        rec = dict(station=stn, start=r.start, month=r.month)
        for k, dn in enumerate((5, 10, 20, 50, 100)):
            seg = anom[k][a:min(b + 14, len(dates) - 1) + 1]
            if not np.isfinite(seg).any(): continue
            ip = int(np.nanargmax(seg)); pk = seg[ip]
            rec[f'peak{dn}'] = pk; rec[f'peakday{dn}'] = ip     # days from spell start
            thr = 0.5 * sd[k]; rec[f'thr{dn}'] = thr; rec[f'peak_over_thr{dn}'] = pk / thr if thr > 0 else np.nan
            # half-decay after peak
            after = seg[ip:]; hd = np.where(after <= 0.5 * pk)[0]
            rec[f'halfdecay{dn}'] = int(hd[0]) if len(hd) else np.nan
        rows.append(rec)
R = pd.DataFrame(rows); R.to_csv(os.path.join(ROOT, 'phase3', 'thermal_check.csv'), index=False)
L = []
L.append(f'sequences: {len(R)}')
for dn in (5, 10, 20, 50, 100):
    L.append(f'depth {dn:3d} cm: peak anom median {R[f"peak{dn}"].median():.2f} C | peak day (from spell start) median {R[f"peakday{dn}"].median():.1f} | '
             f'peak/threshold median {R[f"peak_over_thr{dn}"].median():.2f}, share with peak<=1.5xthr {np.mean(R[f"peak_over_thr{dn}"] <= 1.5):.2f} | '
             f'half-decay days after peak median {R[f"halfdecay{dn}"].median():.1f} (observed in {R[f"halfdecay{dn}"].notna().mean():.2f})')
ok = R.dropna(subset=['peakday5', 'peakday20', 'peakday100'])
L.append(f'ordering: peak at 20 cm later than at 5 cm in {np.mean(ok.peakday20 > ok.peakday5):.2f}, same day {np.mean(ok.peakday20 == ok.peakday5):.2f}; '
         f'100 cm later than 20 cm in {np.mean(ok.peakday100 > ok.peakday20):.2f}')
open(os.path.join(ROOT, 'phase3', 'thermal_check_out.txt'), 'w', encoding='utf-8').write('\n'.join(L)); print('\n'.join(L))
