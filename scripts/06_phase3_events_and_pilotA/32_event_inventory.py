import os as _o, sys as _s
_p = _o.path.dirname(_o.path.abspath(__file__))
while not _o.path.exists(_o.path.join(_p, 'src', 'config.py')): _p = _o.path.dirname(_p)
_s.path.insert(0, _o.path.join(_p, 'src'))
from config import WS_ROOT  # PATH-PATCH: was an absolute path to the original working directory
"""
Phase-3 event inventory. Rules are frozen in phase3/event_rules.md (written before this script was run).
No model fitting. Reads phase3/data/*.npy (2012-2021 only). Outputs:
  phase3/event_inventory.csv      one row per hot spell (all variants), with dryness, coverage, recovery status
  phase3/station_flags.csv        per-station sensor/soil flags and Wilson property availability
  phase3/historypairs_B.csv       per-station Direction B history-contrast feasibility counts
  phase3/event_summary.txt        counts
"""
import sys, io, os, glob, re, warnings
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
warnings.filterwarnings('ignore')
import numpy as np, pandas as pd

ROOT = WS_ROOT
D = os.path.join(ROOT, 'phase3', 'data'); O = os.path.join(ROOT, 'phase3')
stations = pd.read_csv(os.path.join(O, 'stations_phase3.csv')).station.tolist()
VARIANTS = {'primary': (90, 3), 'strict': (95, 4), 'relaxed': (85, 3)}
DEPTHS = [5, 10, 20, 50, 100]
MINH = 20

def load(stn):
    arrs = [np.load(f) for f in sorted(glob.glob(os.path.join(D, f'{stn}_*.npy')))]
    if not arrs: return None
    a = np.vstack(arrs)
    df = pd.DataFrame({'date': pd.to_datetime(a[:, 0].astype(int).astype(str), format='%Y%m%d', errors='coerce'),
                       'crx': a[:, 2], 'Ta': a[:, 3], 'Tx': a[:, 4], 'P': a[:, 6], 'sol': a[:, 7], 'sur': a[:, 8]})
    for k in range(5): df[f'SM{k}'] = a[:, 10 + k]; df[f'ST{k}'] = a[:, 15 + k]
    df = df.dropna(subset=['date'])
    g = df.groupby('date')
    cnt = g.count()
    out = pd.DataFrame(index=g.size().index)
    def agg(col, how, minh=MINH):
        s = getattr(g[col], how)(); s[cnt[col] < minh] = np.nan; return s
    out['Ta'] = agg('Ta', 'mean'); out['Tx'] = agg('Tx', 'max'); out['P'] = agg('P', 'sum'); out['sol'] = agg('sol', 'mean')
    for k in range(5): out[f'SM{k}'] = agg(f'SM{k}', 'mean'); out[f'ST{k}'] = agg(f'ST{k}', 'mean')
    out['crx'] = g['crx'].median()
    out = out.reindex(pd.date_range(out.index.min(), out.index.max(), freq='D'))
    # hourly stuck-run on SM1 (10 cm) for flag
    return out, df

def doy_clim(s, dates, win=7):
    """pooled over years, circular +/-win days: returns dict of arrays indexed by doy 1..366 for several stats"""
    doy = dates.dayofyear.values; yr = dates.year.values
    yrs = np.unique(yr); M = np.full((len(yrs), 367), np.nan)
    for i, y in enumerate(yrs):
        m = yr == y; M[i, doy[m]] = s[m]
    res = {q: np.full(367, np.nan) for q in (25, 40, 50, 75, 85, 90, 95)}
    for d in range(1, 367):
        idx = [((d - 1 + o) % 366) + 1 for o in range(-win, win + 1)]
        v = M[:, idx].ravel(); v = v[~np.isnan(v)]
        if len(v) >= 20:
            for q in res: res[q][d] = np.percentile(v, q)
    return res

def runs(mask):
    """maximal True runs -> list of (i0, i1) inclusive"""
    out = []; i = 0; n = len(mask)
    while i < n:
        if mask[i]:
            j = i
            while j + 1 < n and mask[j + 1]: j += 1
            out.append((i, j)); i = j + 1
        else: i += 1
    return out

def consec(mask, start, n=2):
    """first index >= start where mask is True for n consecutive; None if not"""
    for i in range(start, len(mask) - n + 1):
        if mask[i:i + n].all(): return i
    return None

def validfrac(x, i0, i1):
    seg = x[max(i0, 0):i1 + 1]
    return float(np.mean(~np.isnan(seg))) if len(seg) else 0.0

W = pd.read_csv(os.path.join(ROOT, 'wilson', 'wilson_T1_tidy.csv'))
audit15 = pd.read_csv(os.path.join(ROOT, 'audit15_table.csv')).set_index('station')

ev_rows = []; flag_rows = []; b_rows = []
for stn in stations:
    L = load(stn)
    if L is None: continue
    dd, hourly = L
    dates = dd.index; n = len(dates)
    Tx = dd['Tx'].values; P = dd['P'].values
    clim_Tx = doy_clim(Tx, dates)
    clim_SM = {k: doy_clim(dd[f'SM{k}'].values, dates) for k in (0, 1, 2, 3)}
    clim_ST = {k: doy_clim(dd[f'ST{k}'].values, dates) for k in range(5)}
    doy = dates.dayofyear.values
    # thermal anomaly per depth and warm-season SD
    anom = {}; sdA = {}
    for k in range(5):
        a = dd[f'ST{k}'].values - clim_ST[k][50][doy]
        anom[k] = a
        warm = np.isin(dates.month.values, [5, 6, 7, 8, 9])
        sdA[k] = float(np.nanstd(a[warm])) if np.isfinite(a[warm]).sum() > 100 else np.nan
    freeze = ~(dd['ST0'].values > 1.0)       # True when not clearly nonfreezing (or missing)
    SM = {k: dd[f'SM{k}'].values for k in range(5)}; ST = {k: dd[f'ST{k}'].values for k in range(5)}

    allspells = {}
    for vname, (pct, minhot) in VARIANTS.items():
        thr = clim_Tx[pct][doy]
        hot = Tx >= thr
        # merge gaps <= 2 days
        hr = runs(np.nan_to_num(hot, nan=0).astype(bool))
        merged = []
        for r in hr:
            if merged and r[0] - merged[-1][1] - 1 <= 2: merged[-1] = (merged[-1][0], r[1])
            else: merged.append(r)
        spells = [(a, b) for a, b in merged if int(np.nansum(hot[a:b + 1])) >= minhot]
        allspells[vname] = spells
    prim = allspells['primary']
    for vname, spells in allspells.items():
        for si, (a, b) in enumerate(spells):
            start, end = dates[a], dates[b]
            rainpre = np.nansum(P[max(a - 7, 0):b + 1]); rainvalid = validfrac(P, a - 7, b)
            below = SM[1][a:b + 1] <= clim_SM[1][40][doy[a:b + 1]]
            dryfrac = float(np.nanmean(below)) if np.isfinite(SM[1][a:b + 1]).any() else np.nan
            dry = (rainvalid >= 0.9) and (rainpre <= 5.0) and (dryfrac >= 0.5)
            # neighbours (any hot spell of same variant)
            prev_gap = (a - spells[si - 1][1]) if si > 0 else 9999
            next_gap = (spells[si + 1][0] - b) if si + 1 < len(spells) else 9999
            clean_pre = prev_gap > 21
            interrupted = next_gap <= 21
            fu_end = min(b + 21, (spells[si + 1][0] - 1) if si + 1 < len(spells) else b + 21, n - 1)
            fu_len = fu_end - b
            # nonfreezing
            nf = bool(np.all(ST[0][max(a - 7, 0):min(b + 21, n - 1) + 1] > 1.0))
            # coverage
            cov = {}
            for k, dn in [(0, 5), (1, 10), (2, 20), (3, 50), (4, 100)]:
                cov[f'covT{dn}'] = round(min(validfrac(ST[k], a - 7, fu_end), 1), 2)
            for k, dn in [(0, 5), (1, 10), (2, 20)]:
                cov[f'covSM{dn}'] = round(validfrac(SM[k], a - 7, fu_end), 2)
            cov['covP'] = round(validfrac(P, a - 7, fu_end), 2)
            covok = all(cov[f'covT{d}'] >= 0.8 for d in (5, 10, 20)) and all(cov[f'covSM{d}'] >= 0.8 for d in (5, 10, 20)) and cov['covP'] >= 0.8
            # forcing and anomalies
            txan = float(np.nanmean(Tx[a:b + 1] - clim_Tx[50][doy[a:b + 1]]))
            solm = float(np.nanmean(dd['sol'].values[a:b + 1]))
            pk = {}
            for k, dn in [(0, 5), (1, 10), (2, 20), (3, 50), (4, 100)]:
                seg = anom[k][a:min(b + 7, n - 1) + 1]
                pk[f'peakanom{dn}'] = float(np.nanmax(seg)) if np.isfinite(seg).any() else np.nan
            # wetting
            wet = None
            for d in range(b + 1, fu_end + 1):
                if P[d] >= 10.0: wet = d; break
            resp_s = resp_d = np.nan
            if wet is not None:
                for k, nm in [(0, 'resp5'), (2, 'resp20')]:
                    base = np.nanmin(SM[k][max(wet - 3, 0):wet + 1]) if np.isfinite(SM[k][max(wet - 3, 0):wet + 1]).any() else np.nan
                    after = SM[k][wet:min(wet + 3, n - 1) + 1]
                    r = float(np.nanmax(after) - base) if np.isfinite(after).any() and np.isfinite(base) else np.nan
                    if nm == 'resp5': resp_s = r
                    else: resp_d = r
            # recoveries
            rec = {}
            for k, dn in [(0, 5), (1, 10), (2, 20)]:
                seg_valid = validfrac(SM[k], b + 1, fu_end)
                if seg_valid < 0.7: rec[f'hydro{dn}'] = 'unobserved'
                elif wet is None: rec[f'hydro{dn}'] = 'no_wetting'
                else:
                    okm = (SM[k] >= clim_SM[k][40][doy]) if True else None
                    okm = np.where(np.isnan(SM[k]), False, okm)
                    i = consec(okm[:fu_end + 1], wet, 2)
                    rec[f'hydro{dn}'] = ('observed' if i is not None else ('interrupted' if interrupted and fu_end < b + 21 else 'censored'))
                    rec[f'hydro{dn}_day'] = (i - b) if i is not None else np.nan
            for k, dn in [(0, 5), (1, 10), (2, 20), (3, 50), (4, 100)]:
                seg_valid = validfrac(ST[k], b + 1, fu_end)
                thr = 0.5 * sdA[k] if np.isfinite(sdA[k]) else np.nan
                if seg_valid < 0.7 or not np.isfinite(thr): rec[f'therm{dn}'] = 'unobserved'
                else:
                    okm = np.where(np.isnan(anom[k]), False, anom[k] <= thr)
                    i = consec(okm[:fu_end + 1], b + 1, 2)
                    rec[f'therm{dn}'] = ('observed' if i is not None else ('interrupted' if interrupted and fu_end < b + 21 else 'censored'))
                    rec[f'therm{dn}_day'] = (i - b) if i is not None else np.nan
            complete = dry and nf and clean_pre and (not interrupted) and covok
            row = dict(station=stn, variant=vname, start=start.date(), end=end.date(), n_days=b - a + 1,
                       n_hot=int(np.nansum((Tx[a:b + 1] >= clim_Tx[{'primary': 90, 'strict': 95, 'relaxed': 85}[vname]][doy[a:b + 1]]))),
                       month=start.month, rain7_to_end_mm=round(float(rainpre), 1), rain_valid=round(rainvalid, 2), dry_frac=round(dryfrac, 2) if dryfrac == dryfrac else np.nan,
                       hot_dry=dry, clean_pre=clean_pre, interrupted=interrupted, followup_days=fu_len, nonfreezing=nf, cov_ok=covok,
                       complete_sequence=complete, Tmax_anom=round(txan, 1), solar=round(solm, 0), wet_day=(dates[wet].date() if wet is not None else None),
                       wet_mm=(round(float(P[wet]), 1) if wet is not None else np.nan), resp_shallow=resp_s, resp_deep=resp_d)
            row.update(cov); row.update({k: (round(v, 2) if isinstance(v, float) else v) for k, v in pk.items()}); row.update(rec)
            ev_rows.append(row)

    # ---------------- Station flags ----------------
    fl = dict(station=stn, n_days=n, first=dates[0].date(), last=dates[-1].date())
    for k, dn in [(0, 5), (1, 10), (2, 20), (3, 50), (4, 100)]:
        fl[f'T{dn}_valid'] = round(float(np.mean(~np.isnan(ST[k]))), 3)
        fl[f'SM{dn}_valid'] = round(float(np.mean(~np.isnan(SM[k]))), 3)
    crx = dd['crx'].dropna(); fl['crx_changes'] = int((crx.diff().abs() > 0).sum()); fl['crx_versions'] = ','.join(map(str, sorted(set(crx.round(2).tolist()))[:6]))
    # shift screen: 90-day block medians of SM anomaly
    for k, dn in [(0, 5), (1, 10), (2, 20)]:
        a = SM[k] - clim_SM[k][50][doy]
        nb = n // 90
        meds = [np.nanmedian(a[i * 90:(i + 1) * 90]) if np.isfinite(a[i * 90:(i + 1) * 90]).sum() >= 45 else np.nan for i in range(nb)]
        st = np.abs(np.diff(meds)); fl[f'SM{dn}_maxstep90'] = round(float(np.nanmax(st)), 3) if np.isfinite(st).any() else np.nan
    # stuck hours on 10 cm SM (hourly)
    h = hourly['SM1'].values; stuck = 0; cur = 1; maxrun = 1
    for i in range(1, len(h)):
        if not np.isnan(h[i]) and h[i] == h[i - 1]: cur += 1; maxrun = max(maxrun, cur)
        else: cur = 1
    fl['SM10_max_stuck_h'] = maxrun
    # Wilson property availability
    stt, rest = stn.split('_', 1); key = (stt + '_' + rest.replace('_', '')).upper()
    w = W[W.key == key]
    fl['in_wilson'] = len(w) > 0
    if len(w):
        w = w.iloc[0]
        for nm in ('clay', 'sand', 'bd', 'fc33', 'wp1500'):
            fl[f'w_{nm}'] = ','.join(str(int(d * 100)) for d in (0.05, 0.1, 0.2) if not pd.isna(w[f'{nm}_{d}']))
        fl['w_install'] = w.installed
    if stn in audit15.index:
        r = audit15.loc[stn]
        for dn in (5, 10, 20): fl[f'phi{dn}'] = round(r[f'phi{dn}_est'], 3); fl[f'frac_SM{dn}_gt_phi'] = round(r[f'frac_sm{dn}_gt_phi'], 3)
    flag_rows.append(fl)

    # ---------------- Direction B history contrast feasibility ----------------
    th = SM[1]; T5, T10, T20 = ST[0], ST[1], ST[2]
    hist = pd.Series(th).shift(1).rolling(14, min_periods=11).mean().values
    elig = (T5 > 1.0) & np.isfinite(T10) & np.isfinite(T20) & np.isfinite(th) & np.isfinite(hist) & (P < 1.0) & (pd.Series(P).shift(1).values < 1.0)
    tmean = (T5 + T10 + T20) / 3.0
    idx = np.where(elig)[0]
    cells = {}
    for i in idx:
        key = (int(th[i] // 0.03), int(tmean[i] // 3), 0)
        cells.setdefault((key[0], key[1]), []).append(i)
    nq = 0; epi_pairs = 0; years_with = set(); cells_total = 0
    for key, ii in cells.items():
        ii = np.array(sorted(ii)); cells_total += 1
        # day-of-year window +-45: split by seasonal block of 91 days (approximation: group by doy//91)
        for blk in np.unique(doy[ii] // 91):
            jj = ii[(doy[ii] // 91) == blk]
            if len(jj) < 4: continue
            h_ = hist[jj]; med = np.median(h_)
            lo = jj[h_ <= med]; hi = jj[h_ > med]
            if len(lo) == 0 or len(hi) == 0: continue
            if hist[hi].mean() - hist[lo].mean() < 0.05: continue
            def epis(x):
                out = []; last = -99
                for t in x:
                    if t - last > 5: out.append([t])
                    else: out[-1].append(t)
                    last = t
                return out
            el, eh = epis(lo), epis(hi)
            if len(el) >= 2 and len(eh) >= 2:
                nq += 1; epi_pairs += min(len(el), len(eh))
                for e in el + eh: years_with.add(dates[e[0]].year)
    b_rows.append(dict(station=stn, eligible_days=int(elig.sum()), cells=cells_total, qualifying_cells=nq,
                       sum_min_episodes=epi_pairs, years_with_contrast=len(years_with)))
    print(stn, 'spells primary', len(prim), 'B cells', nq, flush=True)

EV = pd.DataFrame(ev_rows); FL = pd.DataFrame(flag_rows); BR = pd.DataFrame(b_rows)
EV.to_csv(os.path.join(O, 'event_inventory.csv'), index=False)
FL.to_csv(os.path.join(O, 'station_flags.csv'), index=False)
BR.to_csv(os.path.join(O, 'historypairs_B.csv'), index=False)

# ---------------- cluster counts ----------------
def clusters(df):
    d = pd.to_datetime(df['start']).sort_values().values
    if len(d) == 0: return 0
    c = 1; last = d[0]
    for x in d[1:]:
        if (x - last) / np.timedelta64(1, 'D') > 3: c += 1
        last = x
    return c

lines = []
for v in VARIANTS:
    E = EV[EV.variant == v]; HD = E[E.hot_dry]
    lines.append(f'### variant {v}')
    lines.append(f'hot spells (all): {len(E)}  at {E.station.nunique()} stations; clean pre-window: {int(E.clean_pre.sum())}; interrupted: {int(E.interrupted.sum())}')
    lines.append(f'hot-DRY episodes: {len(HD)} at {HD.station.nunique()} stations; synoptic clusters: {clusters(HD)}')
    c1 = HD[HD.clean_pre]; lines.append(f'  clean pre-window: {len(c1)} (clusters {clusters(c1)})')
    c2 = c1[c1.nonfreezing]; lines.append(f'  + nonfreezing: {len(c2)} (clusters {clusters(c2)})')
    c3 = c2[~c2.interrupted]; lines.append(f'  + not interrupted: {len(c3)} (clusters {clusters(c3)})')
    c4 = c3[c3.cov_ok]; lines.append(f'  + coverage ok = COMPLETE sequences: {len(c4)} at {c4.station.nunique()} stations (clusters {clusters(c4)})')
    c5 = c4[c4.wet_day.notna()]; lines.append(f'  + wetting day (>=10 mm) in follow-up: {len(c5)} (clusters {clusters(c5)})')
    c6 = c5[(c5.resp_shallow >= 0.02)]; lines.append(f'  + shallow replenishment detected: {len(c6)}; deeper (20 cm) too: {int((c6.resp_deep >= 0.02).sum())}')
    sm = c4[c4.month.isin([5, 6, 7, 8, 9])]; lines.append(f'  complete sequences in May-Sep: {len(sm)}')
    lines.append('  complete per station: ' + ', '.join(f'{k}:{v_}' for k, v_ in c4.groupby('station').size().sort_values(ascending=False).head(12).items()))
    lines.append('')
HDp = EV[(EV.variant == 'primary') & EV.hot_dry & EV.complete_sequence]
lines.append('Primary complete sequences, recovery status counts (thermal, depth 5/10/20/50/100):')
for dn in (5, 10, 20, 50, 100): lines.append(f'  T{dn}: ' + str(HDp[f'therm{dn}'].value_counts().to_dict()))
lines.append('Primary complete sequences with wetting, hydrologic status (5/10/20):')
HW = HDp[HDp.wet_day.notna()]
for dn in (5, 10, 20): lines.append(f'  SM{dn}: ' + str(HW[f'hydro{dn}'].value_counts().to_dict()))
lines.append('\nDirection B feasibility (history-contrast cells, per station):')
lines.append(BR.sort_values('qualifying_cells', ascending=False).to_string(index=False))
lines.append(f'B totals: eligible days {int(BR.eligible_days.sum())}, qualifying cells {int(BR.qualifying_cells.sum())}, stations with >=1 cell {int((BR.qualifying_cells > 0).sum())}')
open(os.path.join(O, 'event_summary.txt'), 'w', encoding='utf-8').write('\n'.join(lines))
print('\n'.join(lines))
