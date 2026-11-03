import os as _o, sys as _s
_p = _o.path.dirname(_o.path.abspath(__file__))
while not _o.path.exists(_o.path.join(_p, 'src', 'config.py')): _p = _o.path.dirname(_p)
_s.path.insert(0, _o.path.join(_p, 'src'))
from config import WS_ROOT  # PATH-PATCH: was an absolute path to the original working directory
"""Identification-screen sensitivity diagnostic (frozen list: phase3/ident_diag_spec_frozen.md). Exploratory. No refitting, no downloads, no new model family.
Observed quantities are from archived fits; SIMULATED quantities are from layered_events_*.csv."""
import sys, io, os, glob, warnings, itertools
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace'); warnings.filterwarnings('ignore')
import numpy as np, pandas as pd
from scipy.stats import mannwhitneyu, fisher_exact, spearmanr
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
ROOT = WS_ROOT; P3 = os.path.join(ROOT, 'phase3'); AR = os.path.join(P3, 'archive_pre_diag'); D = os.path.join(P3, 'data')
rng = np.random.default_rng(20261015)
LA = np.linspace(np.log(5e-8), np.log(5e-6), 80)
L = []
def say(s=''): L.append(s); print(s)

# ------------------------------------------------------------ load
EV = pd.read_csv(os.path.join(AR, 'event_inventory.csv')); EV = EV[(EV.variant == 'primary') & EV.complete_sequence].copy()
EV['start'] = pd.to_datetime(EV.start); EV['end'] = pd.to_datetime(EV.end); EV['wet_day'] = pd.to_datetime(EV.wet_day)
parts = []
for m in ('dev', 'test'):
    p = pd.read_csv(os.path.join(AR, f'pilotA_part2_{m}.csv')); p = p[p.usable].copy(); p['start'] = pd.to_datetime(p.start); p['split'] = m
    w = pd.read_csv(os.path.join(P3, f'layered_windows_{m}.csv')); w['start'] = pd.to_datetime(w.start); w = w[w.status == 'usable']
    p = p.merge(w[['station', 'start', 'overlap', 'n1', 'n2', 'diurnal1', 'diurnal2', 'grad1', 'grad2']], on=['station', 'start'], how='left')
    p = p.merge(EV[['station', 'start', 'end', 'wet_day', 'Tmax_anom', 'solar', 'n_days']], on=['station', 'start'], how='left'); parts.append(p)
T = pd.concat(parts, ignore_index=True); T['wet'] = T.wet.astype(bool); T['overlap'] = T.overlap.fillna(False).astype(bool); T['d'] = T.d_base
T['w1w'] = T.w1_hi - T.w1_lo; T['w2w'] = T.w2_hi - T.w2_lo
lo_, hi_ = LA[0] + 1e-9, LA[-1] - 1e-9
def interior(lna, lo, hi, interval=True):
    ok = (lna > lo_) & (lna < hi_)
    return ok & (lo > lo_) & (hi < hi_) if interval else ok
def ident_c(df, c=0.6, edge='interval'):
    a = interior(df.w1_lna, df.w1_lo, df.w1_hi, edge == 'interval'); b = interior(df.w2_lna, df.w2_lo, df.w2_hi, edge == 'interval')
    if c is None: return a & b
    return a & b & (df.w1w <= c) & (df.w2w <= c)
assert (ident_c(T, 0.6) == T.ident.astype(bool)).all(), 'cannot re-derive the archived identification rule from stored bounds'
say('Check: the archived identification decision is re-derived exactly from the stored interval bounds for all %d usable pairs.' % len(T))
T['ident'] = T.ident.astype(bool)
T['edge_opt'] = ~(interior(T.w1_lna, T.w1_lo, T.w1_hi, False) & interior(T.w2_lna, T.w2_lo, T.w2_hi, False))
T['edge_int'] = ~(interior(T.w1_lna, T.w1_lo, T.w1_hi, True) & interior(T.w2_lna, T.w2_lo, T.w2_hi, True))
T['unstable'] = (T.w1w > 0.6) | (T.w2w > 0.6)
T['mayseps'] = T.month.isin([5, 6, 7, 8, 9])

# ------------------------------------------------------------ window descriptors from hourly files on disk (no new data)
def load_hourly(stn):
    a = np.vstack([np.load(f) for f in sorted(glob.glob(os.path.join(D, f'{stn}_*.npy')))])
    t = pd.to_datetime(a[:, 0].astype(int).astype(str), format='%Y%m%d', errors='coerce') + pd.to_timedelta(a[:, 1], unit='h')
    df = pd.DataFrame(a[:, 15:20], index=t, columns=['T5', 'T10', 'T20', 'T50', 'T100']); df = df[~df.index.isna()]; df = df[~df.index.duplicated()].sort_index()
    return df.reindex(pd.date_range(df.index.min(), df.index.max(), freq='h'))
H = {s: load_hourly(s) for s in T.station.unique()}
rows = []
for _, e in T.iterrows():
    ws = (e.start - pd.Timedelta(days=2), e.end + pd.Timedelta(days=2, hours=23))
    w2 = (e.wet_day + pd.Timedelta(days=1), min(e.wet_day + pd.Timedelta(days=10, hours=23), e.end + pd.Timedelta(days=21, hours=23))) if e.wet else (e.end + pd.Timedelta(days=4), e.end + pd.Timedelta(days=14, hours=23))
    r = {}
    for k, (a, b) in (('1', ws), ('2', w2)):
        h = H[e.station].loc[a:b, ['T5', 'T10', 'T20', 'T50', 'T100']]
        r['miss' + k] = float(h.isna().mean().max()); r['nh' + k] = len(h); r['sd5_' + k] = float(h.T5.std()); r['mean5_' + k] = float(h.T5.mean()); r['rng5_' + k] = float(h.T5.max() - h.T5.min())
    rows.append(r)
T = pd.concat([T.reset_index(drop=True), pd.DataFrame(rows)], axis=1)
T.to_csv(os.path.join(P3, 'ident_diag_pairs.csv'), index=False)

def cboot(df, col='d', B=1000):
    df = df.reset_index(drop=True)
    if df.wet.nunique() < 2: return (np.nan, np.nan)
    ids = df.cluster.unique(); pos = {c: np.where(df.cluster.values == c)[0] for c in ids}; v = []
    for _ in range(B):
        x = df.iloc[np.concatenate([pos[c] for c in rng.choice(ids, len(ids))])]
        if x.wet.nunique() < 2: continue
        v.append(x[x.wet][col].mean() - x[~x.wet][col].mean())
    return (float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5))) if v else (np.nan, np.nan)
def contrast(df, col='d'): return float(df[df.wet][col].mean() - df[~df.wet][col].mean()) if df.wet.nunique() == 2 else np.nan

# ------------------------------------------------------------ 1. retained vs rejected
say('\n================ 1. RETAINED vs REJECTED PAIRS (observed fits; descriptive, unadjusted, dependent data) ================')
for nm, d in (('DEVELOPMENT', T[T.split == 'dev']), ('TEST', T[T.split == 'test']), ('POOLED', T)):
    R, J = d[d.ident], d[~d.ident]
    say(f'\n--- {nm}: usable {len(d)}, retained {len(R)}, rejected {len(J)} (rejection rate {len(J) / len(d):.2f}); wetting rejection {1 - d[d.wet].ident.mean():.2f}, control rejection {1 - d[~d.wet].ident.mean():.2f}')
    say(f'    reasons among rejected: unstable (width > 0.6) {int(J.unstable.sum())}; grid-edge optimum or interval {int(J.edge_int.sum())}; optimum on the grid edge {int(J.edge_opt.sum())}; overlap of windows {int(J.overlap.sum())}')
    rowsT = []
    def cmp(label, col, fmt='{:.2f}'):
        a, b = R[col].dropna(), J[col].dropna()
        if len(a) < 3 or len(b) < 3: return
        p = mannwhitneyu(a, b).pvalue; rowsT.append(f'    {label:44s} retained median {fmt.format(a.median()):>8s} | rejected median {fmt.format(b.median()):>8s} | unadjusted p {p:.3f}')
    for lab, col in [('stress-window length (hours)', 'nh1'), ('post/control-window length (hours)', 'nh2'), ('stress-window missing fraction (max depth)', 'miss1'), ('post/control missing fraction', 'miss2'),
                     ('stress-window SD of T5 (C)', 'sd5_1'), ('post/control SD of T5 (C)', 'sd5_2'), ('stress-window mean T5 (C)', 'mean5_1'), ('post/control mean T5 (C)', 'mean5_2'),
                     ('stress-window mean |T5-T100| (C)', 'grad1'), ('post/control mean |T5-T100| (C)', 'grad2'), ('stress-window diurnal-band variance fraction', 'diurnal1'), ('post/control diurnal fraction', 'diurnal2'),
                     ('spell mean Tmax anomaly (C)', 'Tmax_anom'), ('spell mean solar (W/m2)', 'solar'), ('stress-window RMSE at best alpha (C)', 'w1_rmse'), ('post/control RMSE (C)', 'w2_rmse'),
                     ('stress-window lag-1 residual correlation', 'w1_rho'), ('post/control lag-1 residual correlation', 'w2_rho'), ('stress-window effective n', 'w1_neff'), ('post/control effective n', 'w2_neff'),
                     ('stress-window interval width (ln)', 'w1w'), ('post/control interval width (ln)', 'w2w'), ('wetting amount (mm), wet only', 'wet_mm')]: cmp(lab, col)
    L.extend(rowsT); [print(x) for x in rowsT]
    ft = fisher_exact([[int((R.mayseps).sum()), int((~R.mayseps).sum())], [int(J.mayseps.sum()), int((~J.mayseps).sum())]])[1]
    say(f'    May-Sep share: retained {R.mayseps.mean():.2f}, rejected {J.mayseps.mean():.2f} (unadjusted Fisher p {ft:.3f}); wetting share: retained {R.wet.mean():.2f}, rejected {J.wet.mean():.2f}')
    st = d.groupby('station').ident.agg(['size', 'sum']); st['rej'] = st['size'] - st['sum']; st = st[st['size'] >= 3].sort_values('rej', ascending=False)
    say('    stations with >= 3 pairs (retained/rejected): ' + ', '.join(f'{i.split("_")[1]} {int(r["sum"])}/{int(r.rej)}' for i, r in st.head(14).iterrows()))
    say('    month group (retained/rejected): ' + ', '.join(f'{k} {int(g.ident.sum())}/{int((~g.ident).sum())}' for k, g in d.assign(mg=pd.cut(d.month, [0, 2, 5, 8, 11, 12], labels=['Dec-Feb', 'Mar-May', 'Jun-Aug', 'Sep-Nov', 'Dec'])).groupby('mg')))
# width vs signal strength (window level)
say('\n--- Spearman correlation of profile-interval width with signal strength and data quality (window level, pooled; descriptive) ---')
W = pd.concat([T[['split', 'wet', 'w1w', 'w1_rmse', 'w1_rho', 'nh1', 'miss1', 'sd5_1', 'grad1', 'diurnal1', 'mean5_1']].rename(columns=lambda c: c.replace('1', '')).assign(win='stress'),
               T[['split', 'wet', 'w2w', 'w2_rmse', 'w2_rho', 'nh2', 'miss2', 'sd5_2', 'grad2', 'diurnal2', 'mean5_2']].rename(columns=lambda c: c.replace('2', '')).assign(win='post/control')])
W.columns = [c if c in ('split', 'wet', 'win') else c for c in W.columns]
wc = {c: c for c in W.columns}
for lab, col in [('window length', 'nh'), ('missing fraction', 'miss'), ('SD of T5', 'sd5_'), ('mean |T5-T100|', 'grad'), ('diurnal-band fraction', 'diurnal'), ('mean T5', 'mean5_'), ('residual RMSE', 'w_rmse'), ('lag-1 residual correlation', 'w_rho')]:
    if col in W.columns or True:
        cc = [c for c in W.columns if c.startswith(col)]
        if not cc or 'ww' not in W.columns: continue
        r = spearmanr(W.ww, W[cc[0]], nan_policy='omit'); say(f'    width vs {lab:30s}: rho {r.correlation:+.2f} (n {W[cc[0]].notna().sum()}, p {r.pvalue:.3g})')
# logistic regression of rejection (information and physical covariates; fit-error variables excluded because they are outcomes of the fit)
try:
    import statsmodels.api as sm
    X = T[['nh1', 'nh2', 'miss1', 'miss2', 'sd5_1', 'sd5_2', 'grad1', 'grad2', 'diurnal1', 'diurnal2', 'Tmax_anom', 'wet', 'mayseps']].copy(); X['wet'] = X.wet.astype(float); X['mayseps'] = X.mayseps.astype(float)
    X['nh'] = (X.nh1 + X.nh2) / 2; X['miss'] = (X.miss1 + X.miss2) / 2; X['sd5'] = (X.sd5_1 + X.sd5_2) / 2; X['grad'] = (X.grad1 + X.grad2) / 2; X['diur'] = (X.diurnal1 + X.diurnal2) / 2
    X = X[['nh', 'miss', 'sd5', 'grad', 'diur', 'Tmax_anom', 'wet', 'mayseps']].dropna(); y = (~T.loc[X.index, 'ident']).astype(int)
    Z = (X - X.mean()) / X.std(); Z['const'] = 1.0; fit = sm.Logit(y, Z).fit(disp=0)
    say('\n--- logistic regression of REJECTION on standardised covariates (n %d; descriptive, unadjusted for clustering) ---' % len(y))
    for k, v in fit.params.items():
        if k != 'const': say(f'    {k:10s} coefficient {v:+.2f} (z {fit.tvalues[k]:+.1f}, p {fit.pvalues[k]:.3f})')
    say(f'    pseudo R2 {fit.prsquared:.2f}')
except Exception as ex: say('logistic regression not run: ' + str(ex)[:80])

# ------------------------------------------------------------ 2. influence
say('\n================ 2. INFLUENCE ON THE ALL-USABLE-EVENT CONTRAST (all variants reported; none chosen) ================')
def trimmed(x, q): 
    x = np.sort(np.asarray(x)); k = int(len(x) * q); return float(x[k:len(x) - k].mean()) if len(x) - 2 * k > 0 else np.nan
def hl(a, b): return float(np.median(np.subtract.outer(np.asarray(a), np.asarray(b)))) if len(a) and len(b) else np.nan
for nm, d in (('TEST', T[T.split == 'test'].reset_index(drop=True)), ('DEVELOPMENT', T[T.split == 'dev'].reset_index(drop=True))):
    say(f'\n--- {nm} all usable events: n {len(d)} (wet {int(d.wet.sum())}, control {int((~d.wet).sum())}), clusters {d.cluster.nunique()} ---')
    c0 = contrast(d); ci = cboot(d, B=2000); say(f'full contrast {c0:+.3f} [{ci[0]:+.3f}, {ci[1]:+.3f}]')
    inf = []; 
    for i in d.index: dd = d.drop(i); inf.append(c0 - contrast(dd))
    d['infl'] = inf; loe = c0 - np.array(inf); say(f'leave-one-EVENT-out contrast range {loe.min():+.3f} to {loe.max():+.3f}; sign changes in {int((np.sign(loe) != np.sign(c0)).sum())} of {len(loe)}')
    cl_inf = {}; 
    for c in d.cluster.unique(): cl_inf[c] = contrast(d[d.cluster != c])
    v = np.array(list(cl_inf.values())); say(f'leave-one-CLUSTER-out contrast range {np.nanmin(v):+.3f} to {np.nanmax(v):+.3f}; sign changes in {int((np.sign(v) != np.sign(c0)).sum())} of {len(v)}')
    srt = d.reindex(d.d.abs().sort_values(ascending=False).index)
    say('remove top-k events by |change| (k = 1..5, all reported): ' + '; '.join(f'k={k}: {contrast(d.drop(srt.index[:k])):+.3f}' for k in range(1, 6)))
    say(f'remove every grid-edge estimate (optimum or interval on the edge; {int(d.edge_int.sum())} events): {contrast(d[~d.edge_int]):+.3f} (wet {int(d[~d.edge_int].wet.sum())}, ctrl {int((~d[~d.edge_int].wet).sum())})')
    say(f'remove only events whose OPTIMUM is on the grid edge ({int(d.edge_opt.sum())}): {contrast(d[~d.edge_opt]):+.3f}')
    say(f'remove every unstable (width > 0.6) event = archived rule ({int(d.unstable.sum())} events; retained = identified): {contrast(d[d.ident]):+.3f}')
    say(f'symmetric trimmed mean contrast: 10% each tail {trimmed(d[d.wet].d, .1) - trimmed(d[~d.wet].d, .1):+.3f}; 20% {trimmed(d[d.wet].d, .2) - trimmed(d[~d.wet].d, .2):+.3f}; difference of group medians {d[d.wet].d.median() - d[~d.wet].d.median():+.3f}; Hodges-Lehmann {hl(d[d.wet].d, d[~d.wet].d):+.3f}')
    say(f'group distributions of change in ln alpha: wetting median {d[d.wet].d.median():+.2f}, IQR [{d[d.wet].d.quantile(.25):+.2f}, {d[d.wet].d.quantile(.75):+.2f}]; control median {d[~d.wet].d.median():+.2f}, IQR [{d[~d.wet].d.quantile(.25):+.2f}, {d[~d.wet].d.quantile(.75):+.2f}]')
    say(f'events with |change| > 0.5: {int((d.d.abs() > 0.5).sum())} (of which rejected {int(((d.d.abs() > 0.5) & ~d.ident).sum())}); share of squared deviations from the group means carried by the five largest |change| events: '
        f'{(srt.d.iloc[:5] - d.groupby("wet").d.transform("mean").reindex(srt.index).iloc[:5]).pow(2).sum() / (d.d - d.groupby("wet").d.transform("mean")).pow(2).sum():.2f}')
    top = d.reindex(d.infl.abs().sort_values(ascending=False).index).head(10)
    say('ten events with the largest influence (influence = full contrast minus contrast without the event):')
    for _, r in top.iterrows(): say(f'    {r.station.split("_")[1]:14s} {str(r.start.date())} {"wet " if r.wet else "ctrl"} change {r.d:+.2f} influence {r.infl:+.3f} widths {r.w1w:.2f}/{r.w2w:.2f} retained={r.ident} edge={r.edge_int} month {int(r.month)}')

# ------------------------------------------------------------ 3. width-cutoff sweep
say('\n================ 3. CONTRAST vs IDENTIFICATION-WIDTH CUTOFF (EXPLORATORY sensitivity, not a replacement confirmation test) ================')
CUTS = [0.2, 0.3, 0.4, 0.5, 0.6, 0.8, 1.0, 1.5, 2.0, 3.0, None]
sweep = []
for sp, d in (('development', T[T.split == 'dev']), ('test', T[T.split == 'test']), ('pooled', T)):
    for c in CUTS + ['opt_only', 'all']:
        if c == 'all': sel = d
        elif c == 'opt_only': sel = d[~d.edge_opt]
        else: sel = d[ident_c(d, c)]
        cc = contrast(sel); lo, hi = cboot(sel, B=1000) if len(sel) > 3 else (np.nan, np.nan)
        sweep.append(dict(split=sp, cutoff=('none (interval inside grid)' if c is None else c), n_wet=int(sel.wet.sum()), n_ctrl=int((~sel.wet).sum()), clusters=sel.cluster.nunique(), clusters_wet=sel[sel.wet].cluster.nunique(),
                          clusters_ctrl=sel[~sel.wet].cluster.nunique(), contrast=cc, lo=lo, hi=hi))
S = pd.DataFrame(sweep); S.to_csv(os.path.join(P3, 'ident_sweep.csv'), index=False)
say(S.round(3).to_string(index=False))

# figure 1
fig, ax = plt.subplots(2, 3, figsize=(17, 8), sharex='col')
xs = [str(c) if c is not None else 'none' for c in CUTS] + ['optimum\nonly', 'all\nusable']
for j, sp in enumerate(('development', 'test', 'pooled')):
    s = S[S.split == sp].reset_index(drop=True); a = ax[0, j]
    a.axhline(0, color='k', lw=0.7); a.axvline(4, color='grey', ls=':', lw=1)
    yerr = [(s.contrast - s.lo).fillna(0).values, (s.hi - s.contrast).fillna(0).values]; a.errorbar(range(len(s)), s.contrast, yerr=yerr, fmt='o-', color='C3' if sp != 'pooled' else 'C4', capsize=3)
    a.set_title(f'{sp}: contrast in ln alpha (OBSERVED, cluster bootstrap 95%)\ndotted line = archived cutoff 0.6', fontsize=10); a.set_ylim(-1.0, 0.8); a.set_ylabel('wetting minus control')
    b = ax[1, j]; b.plot(range(len(s)), s.n_wet, 's-', color='C0', label='wetting events'); b.plot(range(len(s)), s.n_ctrl, '^-', color='C1', label='control events')
    b.plot(range(len(s)), s.clusters, 'd--', color='k', label='clusters (either group)'); b.axvline(4, color='grey', ls=':', lw=1); b.set_ylabel('count'); b.set_xticks(range(len(s))); b.set_xticklabels(xs, fontsize=8); b.set_xlabel('identification interval-width cutoff (ln units)')
    if j == 0: b.legend(fontsize=8)
fig.suptitle('EXPLORATORY SENSITIVITY of the observed rain-linked contrast to the identification cutoff (not a replacement confirmation test; no causal claim)', fontsize=11)
fig.tight_layout(); fig.savefig(os.path.join(P3, 'ident_sweep.png'), dpi=130)

# ------------------------------------------------------------ 4. same-subset comparison
say('\n================ 4. SAME-SUBSET COMPARISON: OBSERVED vs SIMULATED fixed columns on exactly the same events ================')
E = pd.concat([pd.read_csv(os.path.join(P3, f'layered_events_{m}.csv')).assign(split=m) for m in ('dev', 'test')]); E['start'] = pd.to_datetime(E.start)
E = E[E.run == 'R0_refined_nf']
core = set(E[E.column == 'S_central'].station); say(f'core-based (S-eligible) stations: {len(core)}; S-eligible usable pairs: development {int(((T.split == "dev") & T.station.isin(core)).sum())}, test {int(((T.split == "test") & T.station.isin(core)).sum())}')
sim_cols = ['U', 'G_low', 'G_high', 'S_central', 'S_dry_ref', 'S_wet_ref', 'S_Cs_low', 'S_Cs_high']
SS = []
for sp in ('dev', 'test'):
    base = T[(T.split == sp) & T.station.isin(core)]
    for sel_name, c in (('all usable', 'all'), ('identified 0.6 (archived)', 0.6), ('width <= 0.3', 0.3), ('width <= 1.0', 1.0), ('width <= 2.0', 2.0), ('interval inside grid, no width cutoff', None)):
        sel = base if c == 'all' else base[ident_c(base, c)]
        if sel.wet.nunique() < 2 or min(sel.wet.sum(), (~sel.wet).sum()) < 1: continue
        row = dict(split=sp, selection=sel_name, n_wet=int(sel.wet.sum()), n_ctrl=int((~sel.wet).sum()), clusters=sel.cluster.nunique(), observed=contrast(sel), obs_lo=cboot(sel, B=1000)[0], obs_hi=cboot(sel, B=1000)[1])
        for col in sim_cols:
            e = E[(E.split == sp) & (E.column == col)][['station', 'start', 'delta']]; m = sel.merge(e, on=['station', 'start'], how='inner')
            row['sim_' + col] = contrast(m, 'delta') if len(m) == len(sel) else np.nan
        SS.append(row)
SS = pd.DataFrame(SS); SS.to_csv(os.path.join(P3, 'ident_same_subset.csv'), index=False)
pd.set_option('display.width', 250); pd.set_option('display.max_columns', 30); say(SS.round(3).to_string(index=False))
say('\nEvent-level agreement between OBSERVED and SIMULATED change in ln alpha on the S-eligible usable pairs (Spearman; descriptive):')
for sp in ('dev', 'test'):
    base = T[(T.split == sp) & T.station.isin(core)]
    for col in ('G_low', 'G_high', 'S_central'):
        e = E[(E.split == sp) & (E.column == col)][['station', 'start', 'delta']].rename(columns={'delta': 'sd'}); m = base.merge(e, on=['station', 'start']); r = spearmanr(m.d, m.sd)
        ri = spearmanr(m[m.ident].d, m[m.ident].sd) if m.ident.sum() > 4 else None
        say(f'    {sp} {col}: all n {len(m)} rho {r.correlation:+.2f} (p {r.pvalue:.2f})' + (f'; retained n {int(m.ident.sum())} rho {ri.correlation:+.2f} (p {ri.pvalue:.2f})' if ri is not None else ''))
# figure 2: same-subset comparison
fig, axs = plt.subplots(1, 2, figsize=(15, 5.5), sharey=True)
for a, sp in zip(axs, ('dev', 'test')):
    s = SS[SS.split == sp].reset_index(drop=True)
    for i, r in s.iterrows():
        a.errorbar(i - 0.3, r.observed, yerr=[[r.observed - r.obs_lo], [r.obs_hi - r.observed]], fmt='o', color='black', capsize=3, label='OBSERVED (95%)' if i == 0 else None)
        for k, (col, colr) in enumerate((('U', '#7f7f7f'), ('G_low', '#1f77b4'), ('G_high', '#17becf'), ('S_central', '#d62728'))):
            a.plot(i - 0.15 + 0.1 * k, r['sim_' + col], 's', color=colr, label=f'SIMULATED {col}' if i == 0 else None)
    a.axhline(0, color='k', lw=0.6); a.set_xticks(range(len(s))); a.set_xticklabels([f'{r.selection}\nn={r.n_wet}/{r.n_ctrl}' for _, r in s.iterrows()], fontsize=7, rotation=20, ha='right')
    a.set_title(f'{sp.upper()}: core-based stations only; OBSERVED vs SIMULATED on identical events', fontsize=10); a.set_ylabel('contrast in ln alpha'); a.legend(fontsize=7)
fig.suptitle('Same-population comparison (exploratory; simulated columns are fixed-property models, not measurements)', fontsize=11); fig.tight_layout(); fig.savefig(os.path.join(P3, 'ident_same_subset.png'), dpi=130)
open(os.path.join(P3, 'ident_diag_summary.txt'), 'w', encoding='utf-8').write('\n'.join(L)); print('done')
