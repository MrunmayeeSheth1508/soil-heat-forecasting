import os as _o, sys as _s
_p = _o.path.dirname(_o.path.abspath(__file__))
while not _o.path.exists(_o.path.join(_p, 'src', 'config.py')): _p = _o.path.dirname(_p)
_s.path.insert(0, _o.path.join(_p, 'src'))
from config import WS_ROOT  # PATH-PATCH: was an absolute path to the original working directory
"""Analysis of the layered-column null diagnostic: contrasts by column / run / selection / split, with cluster bootstrap (same method and seed policy as the pilot),
observed contrasts for the SAME event subsets, identification rates, attrition, overlap, forcing-spectrum dependence, station breakdown, and the comparison figure.
SIMULATED quantities are labelled as such everywhere."""
import sys, io, os, warnings
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace'); warnings.filterwarnings('ignore')
import numpy as np, pandas as pd
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
ROOT = WS_ROOT; P3 = os.path.join(ROOT, 'phase3')
modes = [m for m in ('dev', 'test') if os.path.exists(os.path.join(P3, f'layered_events_{m}.csv'))]
rng = np.random.default_rng(20261014)
def cboot_contrast(df, B=2000):
    df = df.reset_index(drop=True)
    if df.wet.nunique() < 2: return (np.nan, np.nan)
    ids = df.cluster.unique(); pos = {c: np.where(df.cluster.values == c)[0] for c in ids}; vals = []
    for _ in range(B):
        pick = rng.choice(ids, len(ids)); x = df.iloc[np.concatenate([pos[c] for c in pick])]
        if x.wet.nunique() < 2: continue
        vals.append(x[x.wet].delta.mean() - x[~x.wet].delta.mean())
    return (float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5))) if vals else (np.nan, np.nan)
def contrast(df):
    if df.wet.nunique() < 2: return np.nan
    return float(df[df.wet].delta.mean() - df[~df.wet].delta.mean())
L = []; allrows = []
E = {m: pd.read_csv(os.path.join(P3, f'layered_events_{m}.csv')) for m in modes}; Wn = {m: pd.read_csv(os.path.join(P3, f'layered_windows_{m}.csv')) for m in modes}
for m in modes:
    E[m]['start'] = pd.to_datetime(E[m].start); Wn[m]['start'] = pd.to_datetime(Wn[m].start)
    w = Wn[m]; ob = w[w.status == 'usable'].copy(); ob['delta'] = ob.lna2_obs - ob.lna1_obs
    L.append(f'======== {m.upper()} ========')
    L.append('ATTRITION (events): ' + str(w.status.value_counts().to_dict()) + f'; usable wet {int(ob.wet.sum())}, ctrl {int((~ob.wet).sum())}; observed identified {int(ob.ident_obs.sum())}')
    L.append(f'stress/post window OVERLAP: {int(ob.overlap.sum())} of {len(ob)} usable events (wet events {int(ob[ob.wet].overlap.sum())}); events with overlap among observed-identified: {int(ob[ob.ident_obs].overlap.sum())}')
    L.append(f'clusters: usable {ob.cluster.nunique()}; observed-identified {ob[ob.ident_obs].cluster.nunique()}  (clusters = start dates within 3 days chained across stations; operational, not guaranteed independent)')
    # observed contrast (archived rule)
    oi = ob[ob.ident_obs]; c_obs = contrast(oi); ci = cboot_contrast(oi); L.append(f'OBSERVED contrast (archived selection) {c_obs:+.3f} [{ci[0]:+.3f}, {ci[1]:+.3f}] (wet {int(oi.wet.sum())}, ctrl {int((~oi.wet).sum())})')
    e = E[m]
    for run in e.run.unique():
        er = e[e.run == run]
        for cname in er.column.unique():
            ec = er[er.column == cname]; key_events = ec[['station', 'start']]
            obs_same = ob.merge(key_events.drop_duplicates(), on=['station', 'start'])
            for sel in ('sim', 'obs', 'all'):
                if sel == 'sim': d = ec[ec.ident]
                elif sel == 'obs': d = ec.merge(ob[ob.ident_obs][['station', 'start']], on=['station', 'start'])
                else: d = ec
                if len(d) == 0: continue
                c = contrast(d); lo, hi = cboot_contrast(d) if (run in ('R0_refined_nf', 'R1_base_nf', 'R2_refined_round') and (sel in ('sim', 'obs') or cname in ('U', 'S_central', 'G_low', 'G_high'))) else (np.nan, np.nan)
                # observed contrast on the same event subset and selection
                if sel == 'sim': o = obs_same[obs_same.ident_obs]
                elif sel == 'obs': o = obs_same[obs_same.ident_obs]
                else: o = obs_same
                oc = contrast(o.assign(cluster=o.cluster)) if len(o) else np.nan
                allrows.append(dict(split=m, run=run, column=cname, selection=sel, n_wet=int(d.wet.sum()), n_ctrl=int((~d.wet).sum()), clusters=d.cluster.nunique(), mean_wet=float(d[d.wet].delta.mean()) if d.wet.any() else np.nan,
                                    mean_ctrl=float(d[~d.wet].delta.mean()) if (~d.wet).any() else np.nan, contrast=c, lo=lo, hi=hi, observed_same_subset=oc, ident_share=float(ec.ident.mean())))
R = pd.DataFrame(allrows); R.to_csv(os.path.join(P3, 'layered_contrasts.csv'), index=False)
pd.set_option('display.width', 250); pd.set_option('display.max_columns', 30)
for m in modes:
    L.append(f'\n---- {m.upper()} primary run R0 (refined generator, noise-free, SIMULATED): contrast by column, selection = events identified in the simulated pair ----')
    t = R[(R.split == m) & (R.run == 'R0_refined_nf') & (R.selection == 'sim')][['column', 'n_wet', 'n_ctrl', 'clusters', 'mean_wet', 'mean_ctrl', 'contrast', 'lo', 'hi', 'observed_same_subset', 'ident_share']]
    L.append(t.round(3).to_string(index=False))
    for sel, nm in (('obs', 'selection = events identified in the OBSERVED pair (the archived selection)'), ('all', 'selection = all usable events')):
        L.append(f'\n---- {m.upper()} R0, {nm} ----'); t = R[(R.split == m) & (R.run == 'R0_refined_nf') & (R.selection == sel)][['column', 'n_wet', 'n_ctrl', 'clusters', 'contrast', 'lo', 'hi', 'observed_same_subset']]; L.append(t.round(3).to_string(index=False))
    L.append(f'\n---- {m.upper()} numerical / noise / initialisation sensitivity (selection = simulated-identified), columns U, S_central, G_low, G_high ----')
    t = R[(R.split == m) & (R.selection == 'sim') & (R.column.isin(['U', 'S_central', 'G_low', 'G_high']))].pivot_table(index='column', columns='run', values='contrast'); L.append(t.round(3).to_string())
# forcing-spectrum / gradient dependence (R0, selection sim): Spearman of delta with log ratio of diurnal fraction and gradient change
from scipy.stats import spearmanr
L.append('\n---- FORCING DEPENDENCE (R0, simulated-identified events): Spearman correlation of the simulated change in ln alpha with the change in forcing character ----')
for m in modes:
    w = Wn[m]; w = w[w.status == 'usable'][['station', 'start', 'diurnal1', 'diurnal2', 'grad1', 'grad2']]; w['dlogdi'] = np.log(w.diurnal2 / w.diurnal1); w['dgrad'] = np.log(w.grad2 / w.grad1)
    for cname in ('U', 'S_central', 'G_low', 'G_high'):
        d = E[m][(E[m].run == 'R0_refined_nf') & (E[m].column == cname) & E[m][E[m].run == 'R0_refined_nf'].ident].merge(w, on=['station', 'start'])
        if len(d) > 5: r1 = spearmanr(d.delta, d.dlogdi); r2 = spearmanr(d.delta, d.dgrad); L.append(f'{m} {cname}: n {len(d)}; vs change in diurnal-band variance fraction rho {r1.correlation:+.2f} (p {r1.pvalue:.2f}); vs change in |T5-T100| rho {r2.correlation:+.2f} (p {r2.pvalue:.2f})')
# station breakdown (S_central, R0, selection sim)
L.append('\n---- STATION BREAKDOWN (S_central, R0, SIMULATED, simulated-identified): mean change in ln alpha by station and group ----')
for m in modes:
    d = E[m][(E[m].run == 'R0_refined_nf') & (E[m].column == 'S_central') & E[m][E[m].run == 'R0_refined_nf'].ident]
    if len(d): g = d.groupby(['station', 'wet']).delta.agg(['mean', 'count']).unstack('wet').round(3); L.append(f'{m}:\n' + g.to_string())
open(os.path.join(P3, 'layered_summary.txt'), 'w', encoding='utf-8').write('\n'.join(L)); print('\n'.join(L))

# ---------------- figure ----------------
OBS = {'dev': (0.142, 0.002, 0.277), 'test': (0.141, -0.143, 0.433)}
cols = ['U', 'U_a2e7', 'U_a1e6', 'G_low', 'G_high', 'S_central', 'S_dry_ref', 'S_wet_ref', 'S_Cs_low', 'S_Cs_high']
colour = {'U': '#7f7f7f', 'U_a2e7': '#b0b0b0', 'U_a1e6': '#b0b0b0', 'G_low': '#1f77b4', 'G_high': '#17becf', 'S_central': '#d62728', 'S_dry_ref': '#ff9896', 'S_wet_ref': '#ff9896', 'S_Cs_low': '#e377c2', 'S_Cs_high': '#e377c2'}
fig, ax = plt.subplots(1, 3, figsize=(18, 6.2), gridspec_kw=dict(width_ratios=[1.3, 1.3, 1.1]))
for a, m in zip(ax[:2], ('dev', 'test')):
    if m not in modes: a.set_title(f'{m}: not run'); continue
    o = OBS[m]; a.axhspan(o[1], o[2], color='black', alpha=0.10, label='OBSERVED 95% interval (archived)'); a.axhline(o[0], color='black', lw=2, label=f'OBSERVED contrast {o[0]:+.3f}')
    a.axhline(0.10, color='green', ls=':', label='reading rule: >= 0.10 "reproduces"'); a.axhline(0.0, color='k', lw=0.6)
    for i, c in enumerate(cols):
        r = R[(R.split == m) & (R.run == 'R0_refined_nf') & (R.selection == 'sim') & (R.column == c)]
        if not len(r): continue
        r = r.iloc[0]; a.errorbar(i, r.contrast, yerr=[[r.contrast - r.lo if np.isfinite(r.lo) else 0], [r.hi - r.contrast if np.isfinite(r.hi) else 0]], fmt='s', color=colour[c], capsize=4, ms=9)
        a.text(i, a.get_ylim()[0] if False else -0.46, f'n={r.n_wet}/{r.n_ctrl}', ha='center', fontsize=7, rotation=90)
    a.set_xticks(range(len(cols))); a.set_xticklabels(cols, rotation=60, ha='right', fontsize=8); a.set_ylim(-0.5, 0.5)
    a.set_title(f'{m.upper()}: contrast in ln alpha (wetting minus no-wetting)\nSIMULATED columns (squares, bootstrap 95%) vs OBSERVED (black)', fontsize=10); a.set_ylabel('contrast (log units)'); a.legend(fontsize=7, loc='upper right')
# panel 3: sensitivity of selected columns across runs and selection (dev and test)
a = ax[2]; runs = [('R0_refined_nf', 'sim'), ('R0_refined_nf', 'obs'), ('R0_refined_nf', 'all'), ('R1_base_nf', 'sim'), ('R2_refined_round', 'sim'), ('R3_refined_nf_Bs24', 'sim')]
lab = ['refined, sim-ident', 'refined, obs-ident', 'refined, all', 'base grid', 'rounded 0.1C', '24h exclusion']; w_ = 0.8 / len(runs); k = 0
for m, mk in zip(modes, ('o', '^')):
    for ci, c in enumerate(['U', 'G_low', 'G_high', 'S_central']):
        for ri, (run, sel) in enumerate(runs):
            r = R[(R.split == m) & (R.run == run) & (R.selection == sel) & (R.column == c)]
            if len(r): a.plot(ci + (ri - len(runs) / 2) * w_ + (0.04 if m == 'test' else -0.04), r.iloc[0].contrast, mk, color=plt.cm.viridis(ri / len(runs)), ms=6, mfc='none' if m == 'test' else None)
a.axhline(0.141, color='black', lw=1.5, label='OBSERVED +0.142 (dev) / +0.141 (test)'); a.axhline(0.0, color='k', lw=0.6); a.set_xticks(range(4)); a.set_xticklabels(['U', 'G_low', 'G_high', 'S_central'])
a.set_title('SIMULATED contrast sensitivity: run (colour), selection and numerics\ncircles = development, open triangles = test', fontsize=10); a.set_ylim(-0.3, 0.3)
for ri, l_ in enumerate(lab): a.plot([], [], 's', color=plt.cm.viridis(ri / len(runs)), label=l_)
a.legend(fontsize=7, loc='upper left')
fig.suptitle('Fixed-property layered columns (SIMULATED temperatures, same observed boundaries) vs the observed rain-linked contrast', fontsize=12)
fig.tight_layout(); fig.savefig(os.path.join(P3, 'layered_comparison.png'), dpi=130); print('figure saved')
