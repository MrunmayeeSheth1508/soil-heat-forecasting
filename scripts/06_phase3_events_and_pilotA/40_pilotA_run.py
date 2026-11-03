import os as _o, sys as _s
_p = _o.path.dirname(_o.path.abspath(__file__))
while not _o.path.exists(_o.path.join(_p, 'src', 'config.py')): _p = _o.path.dirname(_p)
_s.path.insert(0, _o.path.join(_p, 'src'))
from config import WS_ROOT  # PATH-PATCH: was an absolute path to the original working directory
"""
Direction A pilot (frozen in phase3/pilotA_prereg.md). Usage: python 40_pilotA_run.py dev   |   python 40_pilotA_run.py test
Parts: (1) trajectories, (2) window-wise effective diffusivity with observed boundaries, (3) formulation vs alternatives for Delta ln alpha.
"""
import sys, io, os, glob, warnings, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace'); warnings.filterwarnings('ignore')
import numpy as np, pandas as pd
sys.path.insert(0, WS_ROOT)
from heatsolver import simulate, make_grid, init_profile, sample
MODE = sys.argv[1]; assert MODE in ('dev', 'test')
ROOT = WS_ROOT; D = os.path.join(ROOT, 'phase3', 'data'); O = os.path.join(ROOT, 'phase3')
rng = np.random.default_rng(20261014)
EV = pd.read_csv(os.path.join(O, 'event_inventory.csv'))
EV = EV[(EV.variant == 'primary') & EV.complete_sequence].copy()
EV['start'] = pd.to_datetime(EV.start); EV['end'] = pd.to_datetime(EV.end); EV['wet_day'] = pd.to_datetime(EV.wet_day)
EV['year'] = EV.start.dt.year
# synoptic clusters over ALL complete sequences (chain-linked within 3 days)
EV = EV.sort_values('start').reset_index(drop=True)
cl = 0; last = None; ids = []
for s in EV.start:
    if last is not None and (s - last).days > 3: cl += 1
    ids.append(cl); last = s
EV['cluster'] = ids
SPLIT = (EV.year <= 2018) if MODE == 'dev' else (EV.year >= 2019)
EVs = EV[SPLIT].copy()
print(MODE, 'sequences', len(EVs), 'clusters', EVs.cluster.nunique(), 'with wetting', int(EVs.wet_day.notna().sum()), flush=True)

# ---------------- hourly + daily data ----------------
def load_hourly(stn):
    a = np.vstack([np.load(f) for f in sorted(glob.glob(os.path.join(D, f'{stn}_*.npy')))])
    t = pd.to_datetime(a[:, 0].astype(int).astype(str), format='%Y%m%d', errors='coerce') + pd.to_timedelta(a[:, 1], unit='h')
    df = pd.DataFrame(a[:, 15:20], index=t, columns=['T5', 'T10', 'T20', 'T50', 'T100'])
    for k, c in enumerate(['M5', 'M10', 'M20', 'M50', 'M100']): df[c] = a[:, 10 + k]
    df = df[~df.index.isna()]; df = df[~df.index.duplicated()].sort_index()
    return df.reindex(pd.date_range(df.index.min(), df.index.max(), freq='h'))
def daily_from_hourly(h):
    g = h[['T5', 'T10', 'T20', 'T50', 'T100']].resample('D'); m = g.mean(); c = g.count(); m[c < 20] = np.nan; return m
def clim_median(s, dates, win=7):
    doy = dates.dayofyear.values; yr = dates.year.values; yrs = np.unique(yr); M = np.full((len(yrs), 367), np.nan)
    for i, y in enumerate(yrs): m = yr == y; M[i, doy[m]] = s[m]
    out = np.full(367, np.nan)
    for d in range(1, 367):
        idx = [((d - 1 + o) % 366) + 1 for o in range(-win, win + 1)]; v = M[:, idx].ravel(); v = v[~np.isnan(v)]
        if len(v) >= 20: out[d] = np.median(v)
    return out

# ---------------- Part 1 ----------------
DEP = [5, 10, 20, 50, 100]; rows1 = []
H = {}; DY = {}
for stn in EVs.station.unique():
    H[stn] = load_hourly(stn); DY[stn] = daily_from_hourly(H[stn])
for _, e in EVs.iterrows():
    dd = DY[e.station]; dates = dd.index; doy = dates.dayofyear.values
    a = dates.get_loc(e.start); b = dates.get_loc(e.end); r = dict(station=e.station, cluster=e.cluster, year=e.year, start=e.start, wet=pd.notna(e.wet_day), Tmax_anom=e.Tmax_anom, solar=e.solar)
    for k, dn in enumerate(DEP):
        s = dd[f'T{dn}'].values; an = s - clim_median(s, dates)[doy] if False else None
    cache = DY[e.station].attrs.get('clim')
    if cache is None:
        cache = {dn: clim_median(dd[f'T{dn}'].values, dates)[doy] for dn in DEP}; DY[e.station].attrs['clim'] = cache
    for dn in DEP:
        an = dd[f'T{dn}'].values - cache[dn]
        seg = an[a:min(b + 14, len(dates) - 1) + 1]
        if not np.isfinite(seg).any(): continue
        ip = int(np.nanargmax(seg)); pk = float(seg[ip]); r[f'peak{dn}'] = pk; r[f'delay{dn}'] = ip
        after = an[a + ip:min(b + 21, len(dates) - 1) + 1]; hd = np.where(after <= 0.5 * pk)[0]
        r[f'persist{dn}'] = float(hd[0]) if len(hd) else np.nan; r[f'cens{dn}'] = not len(hd)
        full = an[a:min(b + 21, len(dates) - 1) + 1]; r[f'burden{dn}'] = float(np.nansum(np.clip(full, 0, None)))
    pre = DY[e.station][f'T10']  # placeholder for tertiles below
    rows1.append(r)
P1 = pd.DataFrame(rows1)
# pre-event 10 cm moisture percentile within station (daily from hourly M10; mean of days -7..-1) and clay from Wilson
def pre_theta(e):
    h = H[e.station]['M10']; seg = h[e.start - pd.Timedelta(days=7):e.start - pd.Timedelta(hours=1)]
    return float(seg.mean()) if seg.notna().sum() > 100 else np.nan
EVs['pre_theta'] = EVs.apply(pre_theta, axis=1)
P1['pre_theta'] = EVs['pre_theta'].values
P1['theta_tert'] = P1.groupby('station').pre_theta.transform(lambda x: pd.qcut(x, 3, labels=False, duplicates='drop') if x.notna().sum() >= 3 else np.nan)
Wt = pd.read_csv(os.path.join(ROOT, 'wilson', 'wilson_T1_tidy.csv'))
def clay_of(stn):
    s, rest = stn.split('_', 1); key = (s + '_' + rest.replace('_', '')).upper(); w = Wt[Wt.key == key]
    return float(np.nanmean([w.iloc[0][f'clay_{d}'] for d in (0.1, 0.2)])) if len(w) else np.nan
P1['clay'] = P1.station.map({s: clay_of(s) for s in P1.station.unique()})

def cboot(df, fn, B=2000):
    df = df.reset_index(drop=True); cl_ids = df.cluster.unique(); pos = {c: np.where(df.cluster.values == c)[0] for c in cl_ids}; vals = []
    for _ in range(B):
        pick = rng.choice(cl_ids, len(cl_ids)); x = df.iloc[np.concatenate([pos[c] for c in pick])]
        try: v = fn(x)
        except Exception: continue
        if np.isfinite(v): vals.append(v)
    return (float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5))) if vals else (np.nan, np.nan)
L = [f'=== MODE {MODE}: PART 1 trajectories ===', f'sequences {len(P1)}, clusters {P1.cluster.nunique()}, stations {P1.station.nunique()}']
for dn in DEP:
    row = f'depth {dn:3d} cm:'
    for nm, col in [('peak C', f'peak{dn}'), ('delay d', f'delay{dn}'), ('persist d', f'persist{dn}'), ('burden degC-d', f'burden{dn}')]:
        med = P1[col].median(); ci = cboot(P1, lambda x: x[col].median(), 1000)
        row += f' | {nm} {med:.2f} [{ci[0]:.2f},{ci[1]:.2f}]'
    row += f' | persist censored {P1[f"cens{dn}"].mean():.2f}'
    L.append(row)
for col in ('burden20', 'persist20', 'peak20', 'delay20', 'burden50', 'persist50', 'persist100'):
    w1 = P1[P1.wet]; w0 = P1[~P1.wet]
    fn = lambda x: x[x.wet][col].median() - x[~x.wet][col].median()
    d = fn(P1); ci = cboot(P1, fn, 1000)
    L.append(f'wetting minus no-wetting, median {col}: {d:+.2f} [{ci[0]:+.2f},{ci[1]:+.2f}]  (n wet {len(w1)}, no-wet {len(w0)})')
for col in ('burden20', 'persist20'):
    fn = lambda x: x[x.theta_tert == 0][col].median() - x[x.theta_tert == 2][col].median()
    d = fn(P1); ci = cboot(P1, fn, 1000); L.append(f'driest minus wettest pre-event 10 cm moisture tertile, median {col}: {d:+.2f} [{ci[0]:+.2f},{ci[1]:+.2f}]')
cm = P1.clay.median()
for col in ('burden20', 'persist20', 'peak20'):
    fn = lambda x: x[x.clay >= cm][col].median() - x[x.clay < cm][col].median()
    sub = P1.dropna(subset=['clay']);
    if len(sub) > 10: d = fn(sub); ci = cboot(sub, fn, 1000); L.append(f'higher-clay (>= median {cm:.0f}%) minus lower-clay, median {col}: {d:+.2f} [{ci[0]:+.2f},{ci[1]:+.2f}] (n {len(sub)})')
sl = P1.dropna(subset=['peak5', 'Tmax_anom'])
slope = np.polyfit(sl.Tmax_anom, sl.peak5, 1)[0]; ci = cboot(sl, lambda x: np.polyfit(x.Tmax_anom, x.peak5, 1)[0], 1000)
L.append(f'forcing: slope of 5 cm peak anomaly on mean Tmax anomaly = {slope:.2f} [{ci[0]:.2f},{ci[1]:.2f}] C per C')
P1.to_csv(os.path.join(O, f'pilotA_part1_{MODE}.csv'), index=False)

# ---------------- Part 2 ----------------
LA = np.linspace(np.log(5e-8), np.log(5e-6), 80); AL = np.exp(LA)
SC = {'base': dict(d5=0.0, d100=0.0, ztop=0.05), 'bias_a': dict(d5=+0.1, d100=-0.1, ztop=0.05), 'bias_b': dict(d5=-0.1, d100=+0.1, ztop=0.05),
      'top6': dict(d5=0.0, d100=0.0, ztop=0.06), 'top4': dict(d5=0.0, d100=0.0, ztop=0.04)}
def getwin(stn, t0, t1):
    h = H[stn].loc[t0:t1, ['T5', 'T10', 'T20', 'T50', 'T100']]
    if len(h) < 24 * 5: return None
    miss = h.isna().mean().max()
    if miss > 0.10: return None
    hf = h.interpolate(limit=3, limit_area='inside')
    if hf.isna().any().any(): return None
    return hf
def fit_window(hf, sc):
    Tt = hf['T5'].values + sc['d5']; Tb = hf['T100'].values + sc['d100']
    z, dz = make_grid(sc['ztop'], 1.0, 38)
    zo = np.array([sc['ztop'], 0.10, 0.20, 0.50, 1.0]); T0 = init_profile(z, zo, [Tt[0], hf['T10'].values[0], hf['T20'].values[0], hf['T50'].values[0], Tb[0]])
    obs = hf[['T10', 'T20', 'T50']].values; sse = np.empty(len(AL)); Bs = 6
    best = None
    for i, a in enumerate(AL):
        sim = simulate(a, Tt, Tb, z, T0); pr = sample(sim, z, [0.10, 0.20, 0.50]); res = (pr - obs)[Bs:]
        sse[i] = float((res ** 2).sum())
        if best is None or sse[i] < best[0]: best = (sse[i], i, res)
    i0 = best[1]; res = best[2]; n = res.shape[0]
    rho = float(np.mean([np.corrcoef(res[:-1, k], res[1:, k])[0, 1] for k in range(3)])); rho = min(max(rho, 0.0), 0.99)
    neff = max(n * (1 - rho) / (1 + rho), 3.0)
    prof = neff * np.log(sse / sse[i0]); ok = np.where(prof <= 1.0)[0]
    lo, hi = LA[ok.min()], LA[ok.max()]
    ident = (0 < i0 < len(AL) - 1) and (ok.min() > 0) and (ok.max() < len(AL) - 1) and ((hi - lo) <= 0.6)
    rmse = float(np.sqrt(sse[i0] / res.size))
    return dict(lna=float(LA[i0]), lo=float(lo), hi=float(hi), ident=bool(ident), rmse=rmse, rho=rho, neff=float(neff), n=int(n))
rows2 = []
for _, e in EVs.iterrows():
    stn = e.station; wets = pd.notna(e.wet_day)
    ws = (e.start - pd.Timedelta(days=2), e.end + pd.Timedelta(days=2, hours=23))
    if wets:
        w2 = (e.wet_day + pd.Timedelta(days=1), min(e.wet_day + pd.Timedelta(days=10, hours=23), e.end + pd.Timedelta(days=21, hours=23)))
        if (w2[1] - w2[0]).days + 1 < 7: continue
    else: w2 = (e.end + pd.Timedelta(days=4), e.end + pd.Timedelta(days=14, hours=23))
    h1 = getwin(stn, *ws); h2 = getwin(stn, *w2)
    if h1 is None or h2 is None: rows2.append(dict(station=stn, cluster=e.cluster, start=e.start, wet=wets, usable=False)); continue
    r = dict(station=stn, cluster=e.cluster, start=e.start, month=e.month, wet=wets, usable=True, wet_mm=e.wet_mm)
    for sn, sc in SC.items():
        f1 = fit_window(h1, sc); f2 = fit_window(h2, sc)
        r[f'lna1_{sn}'] = f1['lna']; r[f'lna2_{sn}'] = f2['lna']; r[f'd_{sn}'] = f2['lna'] - f1['lna']
        if sn == 'base':
            for k, v in f1.items(): r[f'w1_{k}'] = v
            for k, v in f2.items(): r[f'w2_{k}'] = v
            r['ident'] = bool(f1['ident'] and f2['ident'])
            r['th1'] = float(H[stn].loc[ws[0]:ws[1], ['M10', 'M20', 'M50']].mean().mean()); r['th2'] = float(H[stn].loc[w2[0]:w2[1], ['M10', 'M20', 'M50']].mean().mean())
    rows2.append(r)
    if len(rows2) % 20 == 0: print('  windows done', len(rows2), flush=True)
P2 = pd.DataFrame(rows2); P2.to_csv(os.path.join(O, f'pilotA_part2_{MODE}.csv'), index=False)
U = P2[P2.usable]; I = U[U.ident]
L += ['', f'=== MODE {MODE}: PART 2 effective diffusivity (observed boundaries) ===', f'usable sequences {len(U)} of {len(P2)}; identified (both windows) {len(I)}; clusters {I.cluster.nunique()}',
      f'  wetting identified {int(I.wet.sum())} (clusters {I[I.wet].cluster.nunique()}), no-wetting identified {int((~I.wet).sum())} (clusters {I[~I.wet].cluster.nunique()})']
for nm, sub in [('all', U), ('identified', I)]:
    L.append(f'median RMSE of best alpha (C): stress window {sub.w1_rmse.median():.2f}, later window {sub.w2_rmse.median():.2f} ({nm}); median alpha stress {np.exp(sub.lna1_base.median()):.2e}, later {np.exp(sub.lna2_base.median()):.2e}')
def contrast(x, sn='base'):
    return x[x.wet][f'd_{sn}'].mean() - x[~x.wet][f'd_{sn}'].mean()
if len(I[I.wet]) > 2 and len(I[~I.wet]) > 2:
    for nm, sub in [('all seasons', I), ('May-Sep', I[I.month.isin([5, 6, 7, 8, 9])])]:
        if len(sub[sub.wet]) > 2 and len(sub[~sub.wet]) > 2:
            ci = cboot(sub, contrast, 2000)
            L.append(f'{nm}: mean Delta(wet) {sub[sub.wet].d_base.mean():+.3f}, mean Delta(no-wet) {sub[~sub.wet].d_base.mean():+.3f}, CONTRAST {contrast(sub):+.3f} [{ci[0]:+.3f},{ci[1]:+.3f}] (n {len(sub[sub.wet])}/{len(sub[~sub.wet])})')
    L.append('scenario contrasts (identified, all seasons): ' + ', '.join(f'{sn} {contrast(I, sn):+.3f}' for sn in SC))
    st = I[I.wet].groupby('station').d_base.agg(['mean', 'count']); st2 = st[st['count'] >= 2]
    L.append(f'stations with >=2 identified wetting events: {len(st2)}; share with positive mean Delta: {(st2["mean"] > 0).mean() if len(st2) else np.nan:.2f}')
else: L.append('too few identified sequences for the contrast (underpowered)')
L.append(f'identified wetting clusters {I[I.wet].cluster.nunique()} (< 20 means underpowered by the pre-registered rule)')

# ---------------- Part 3 ----------------
A15 = pd.read_csv(os.path.join(ROOT, 'audit15_table.csv')).set_index('station')
def props(stn):
    if stn not in A15.index or stn == 'AZ_Elgin_5_S': return None
    r = A15.loc[stn]
    if pd.isna(r.bd10) or pd.isna(r.bd20): return None
    bd = float(np.mean([r.bd10, r.bd20])); sand = float(np.mean([r.sand10, r.sand20])) / 100.0
    return dict(bd=bd, sand=sand, phi=1 - bd / 2.65)
def kJ(theta, p, clip):
    phi = p['phi']; Sr = theta / phi
    if clip: Sr = min(Sr, 1.0)
    coarse = p['sand'] >= 0.5
    if coarse: Ke = 0.7 * np.log10(Sr) + 1 if Sr > 0.05 else 0.0
    else: Ke = np.log10(Sr) + 1 if Sr > 0.1 else 0.0
    Ke = max(Ke, 0.0)
    vq = p['sand']; ko = 2.0 if vq > 0.2 else 3.0
    kmin = 8.8 ** vq * ko ** (1 - vq); ksat = kmin ** (1 - phi) * 0.57 ** phi
    kdry = (0.135 * p['bd'] + 0.0647) / (2.7 - 0.947 * p['bd'])
    return (ksat - kdry) * Ke + kdry
def alphaJ(theta, p, clip, Cs=2.0e6):
    Cv = (1 - p['phi']) * Cs + theta * 4.18e6; return kJ(theta, p, clip) / Cv
W = I[I.wet].copy(); W['pr'] = W.station.map(lambda s: props(s)); W = W[W.pr.notna()].copy()
W['dth'] = W.th2 - W.th1
def pred_J(r, clip, Cs=2.0e6):
    return float(np.log(alphaJ(r.th2, r.pr, clip, Cs) / alphaJ(r.th1, r.pr, clip, Cs)))
W['Sr1'] = W.apply(lambda r: r.th1 / r.pr['phi'], axis=1); W['Sr2'] = W.apply(lambda r: r.th2 / r.pr['phi'], axis=1)
W['srgt1'] = (W.Sr1 > 1) | (W.Sr2 > 1)
L += ['', f'=== MODE {MODE}: PART 3 formulation vs alternatives (identified wetting sequences at stations with Wilson bulk density) ===',
      f'events {len(W)} (clusters {W.cluster.nunique()}, stations {W.station.nunique()}); excluded for S_r > 1 in main variant: {int(W.srgt1.sum())}']
Wm = W[~W.srgt1].copy()
if len(Wm) >= 3:
    Wm['pJ'] = Wm.apply(lambda r: pred_J(r, False), axis=1); Wm['p0'] = 0.0
    if MODE == 'dev':
        bs = []
        pb = np.full(len(Wm), np.nan)
        for s in Wm.station.unique():
            tr = Wm[Wm.station != s]
            b = float((tr.dth * tr.d_base).sum() / (tr.dth ** 2).sum()) if len(tr) > 2 and (tr.dth ** 2).sum() > 0 else 0.0
            pb[(Wm.station == s).values] = b * Wm[Wm.station == s].dth.values
        Wm['pB'] = pb; bfull = float((Wm.dth * Wm.d_base).sum() / (Wm.dth ** 2).sum()); json.dump({'b': bfull}, open(os.path.join(O, 'pilotA_b_frozen.json'), 'w'))
        L.append(f'shared b (development, all events) = {bfull:+.3f} ln-alpha per m3/m3')
    else:
        bfull = json.load(open(os.path.join(O, 'pilotA_b_frozen.json')))['b']; Wm['pB'] = bfull * Wm.dth; L.append(f'shared b (frozen from development) = {bfull:+.3f}')
    for nm in ('p0', 'pB', 'pJ'): Wm[f'e_{nm}'] = (Wm.d_base - Wm[nm]).abs()
    L.append('MAE of Delta ln alpha: M0 %.3f | M_B %.3f | M_J %.3f' % tuple(Wm[f'e_{n}'].mean() for n in ('p0', 'pB', 'pJ')))
    L.append('sign agreement with observed Delta (ignoring zero predictions): M_B %.2f | M_J %.2f' % tuple(float(np.mean(np.sign(Wm[n]) == np.sign(Wm.d_base))) for n in ('pB', 'pJ')))
    for a, b_ in [('pJ', 'p0'), ('pJ', 'pB')]:
        fn = lambda x, a=a, b_=b_: (x[f'e_{b_}'] - x[f'e_{a}']).mean(); d = fn(Wm); ci = cboot(Wm, fn, 2000)
        L.append(f'MAE({b_}) - MAE({a}) = {d:+.3f} [{ci[0]:+.3f},{ci[1]:+.3f}] (positive favours {a})')
    for Cs in (1.8e6, 2.4e6):
        pj = Wm.apply(lambda r: pred_J(r, False, Cs), axis=1); L.append(f'sensitivity Cs={Cs:.1e}: MAE M_J {np.mean((Wm.d_base - pj).abs()):.3f}')
    pjc = W.apply(lambda r: pred_J(r, True), axis=1); L.append(f'sensitivity S_r clipped at 1 (all {len(W)} events): MAE M_J {np.mean((W.d_base - pjc).abs()):.3f}, M0 {W.d_base.abs().mean():.3f}')
    Wm.drop(columns=['pr']).to_csv(os.path.join(O, f'pilotA_part3_{MODE}.csv'), index=False)
else: L.append('too few events for the formulation comparison (underpowered)')
open(os.path.join(O, f'pilotA_out_{MODE}.txt'), 'w', encoding='utf-8').write('\n'.join(L)); print('\n'.join(L))
