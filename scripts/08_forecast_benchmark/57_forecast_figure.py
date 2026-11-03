import os as _o, sys as _s
_p = _o.path.dirname(_o.path.abspath(__file__))
while not _o.path.exists(_o.path.join(_p, 'src', 'config.py')): _p = _o.path.dirname(_p)
_s.path.insert(0, _o.path.join(_p, 'src'))
from config import WS_ROOT  # PATH-PATCH: was an absolute path to the original working directory
"""57_forecast_figure.py — one forecast-vs-observation figure.
Three panels: (A) example traces at P10/P50/P90 of best-baseline MAE72;
(B) boxplots of MAE72 by baseline and depth; (C) MAE vs lead hour.
Events pre-specified by percentile rank of C2 T20 MAE72 in the validation set.
"""
import sys, io, os, warnings
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
warnings.filterwarnings('ignore')
sys.path.insert(0, WS_ROOT)

import numpy as np, pandas as pd, matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec

from forecastlib import (
    Station, forecast_all, development_alphas,
    DEPTH_COLS, HORIZON, P3, DEVYEARS, VALYEARS
)

FD   = os.path.join(P3, 'forecast')
BRAIN = r'C:\Users\jtani\.gemini\antigravity\brain\d895d91a-33a5-49bd-8d56-6a58ee64f9a6'

df_scores = pd.read_csv(os.path.join(FD, 'forecast_scores.csv'), parse_dates=['issue'])
val = df_scores[df_scores.split == 'val'].copy()

gA, sA, _ = development_alphas()

# ---- pre-specify example events by C2 T20 MAE72 percentile (P10, P50, P90) ----
col_ref = 'C2_T20_h1_72_mae'
p10_val = val[col_ref].quantile(0.10)
p50_val = val[col_ref].quantile(0.50)
p90_val = val[col_ref].quantile(0.90)

def pick_event(target_mae):
    idx = (val[col_ref] - target_mae).abs().idxmin()
    r = val.loc[idx]
    return r

ev10 = pick_event(p10_val)
ev50 = pick_event(p50_val)
ev90 = pick_event(p90_val)
examples = [('P10 (low error)', ev10, '#1b7837'),
            ('P50 (median error)', ev50, '#4575b4'),
            ('P90 (high error)', ev90, '#d73027')]

print('Example events:')
for label, ev, col in examples:
    print(f'  {label}: {ev.station} {ev.issue.date()} C2_T20_MAE72={ev[col_ref]:.3f} C')

# ---- retrieve full forecast traces for example events ----
def get_traces(ev):
    st = Station(ev.station, gA, sA.get(ev.station, gA))
    ts = ev.issue
    i0 = st.df.index.get_loc(ts)
    fut = st.df.iloc[i0 + 1: i0 + 1 + HORIZON]
    obs_T20 = fut['T20'].values
    obs_T50 = fut['T50'].values
    fc = forecast_all(st, ts, with_recon=True)
    hours = np.arange(1, HORIZON + 1)
    return hours, obs_T20, obs_T50, fc

# ---- figure layout ----
fig = plt.figure(figsize=(15, 12))
gs = gridspec.GridSpec(3, 3, figure=fig, hspace=0.45, wspace=0.35)

# Panels A0-A2: T20 traces for three example events
for col_idx, (label, ev, color) in enumerate(examples):
    ax = fig.add_subplot(gs[0, col_idx])
    hours, obs20, obs50, fc = get_traces(ev)
    ax.plot(hours, obs20, 'k-', lw=1.8, label='Observed T20', zorder=5)
    ax.plot(hours, fc['B1'][:, 0], color='#8c510a', lw=1.0, ls='--', label='B1 Persist.', alpha=0.8)
    ax.plot(hours, fc['B2'][:, 0], color='#bf812d', lw=1.0, ls=':', label='B2 Clim.', alpha=0.8)
    ax.plot(hours, fc['C2'][:, 0], color=color, lw=1.4, label='C2 Conduct.', alpha=0.9)
    ax.plot(hours, fc['RECON'][:, 0], color='grey', lw=0.8, ls='-.', label='RECON (obs bnd)', alpha=0.6)
    ax.set_title(f'{label}\n{ev.station[:20]} {ev.issue.strftime("%Y-%m-%d")}\nC2 MAE72={ev[col_ref]:.2f} °C',
                 fontsize=7.5)
    ax.set_xlabel('Lead hour', fontsize=8)
    ax.set_ylabel('T20 (°C)', fontsize=8)
    ax.tick_params(labelsize=7)
    ax.set_xlim(0, 72)
    if col_idx == 0:
        ax.legend(fontsize=6, loc='best')
    ax.axvline(24, color='k', lw=0.4, alpha=0.3)
    ax.axvline(48, color='k', lw=0.4, alpha=0.3)

# Panel B: boxplots MAE72 by baseline and depth (validation)
ax_b = fig.add_subplot(gs[1, :2])
COMPS   = ['B1', 'B2', 'C2', 'C1', 'C3', 'RECON']
LABELS  = ['B1\nPersist.', 'B2\nClim.', 'C2\nCond.(C2α)', 'C1\nCond.(global)', 'C3\nCond.(stn)', 'RECON\n(obs bnd)']
colors_d = {'T20': '#d73027', 'T50': '#4575b4'}
n = len(COMPS)
x = np.arange(n)
width = 0.35
for di, d_name in enumerate(['T20', 'T50']):
    data = [val[f'{c}_{d_name}_h1_72_mae'].dropna().values for c in COMPS]
    bp = ax_b.boxplot(data, positions=x + (di - 0.5) * width, widths=width * 0.85,
                      patch_artist=True, showfliers=False, medianprops={'color': 'k', 'lw': 1.5})
    for patch in bp['boxes']:
        patch.set_facecolor(colors_d[d_name])
        patch.set_alpha(0.65)

ax_b.set_xticks(x)
ax_b.set_xticklabels(LABELS, fontsize=7)
ax_b.set_ylabel('MAE over h1-72 (°C)', fontsize=8)
ax_b.set_title('MAE72 by competitor and depth (validation, n=716)', fontsize=8)
ax_b.tick_params(labelsize=7)
ax_b.axhline(0.30, color='k', lw=0.8, ls='--', alpha=0.4, label='0.30 °C threshold')
from matplotlib.patches import Patch
ax_b.legend(handles=[Patch(facecolor=colors_d['T20'], alpha=0.65, label='T20 (20 cm)'),
                      Patch(facecolor=colors_d['T50'], alpha=0.65, label='T50 (50 cm)')],
            fontsize=7, loc='upper right')

# Panel C: MAE vs lead (h1-24, h1-48, h1-72) for best baselines (validation medians)
ax_c = fig.add_subplot(gs[1, 2])
lead_vals = [24, 48, 72]
for d_name, best_comp, col_main in [('T20', 'C2', '#d73027'), ('T50', 'B1', '#4575b4')]:
    maes = [val[f'{best_comp}_{d_name}_h1_{t}_mae'].median() for t in lead_vals]
    ax_c.plot(lead_vals, maes, 'o-', color=col_main, lw=1.4, ms=5, label=f'{d_name} ({best_comp})')
ax_c.set_xlabel('Lead hour', fontsize=8); ax_c.set_ylabel('Median MAE (°C)', fontsize=8)
ax_c.set_title('MAE vs lead (validation)', fontsize=8)
ax_c.set_xticks([24, 48, 72]); ax_c.tick_params(labelsize=7)
ax_c.axhline(0.30, color='k', lw=0.8, ls='--', alpha=0.4)
ax_c.legend(fontsize=7)

# Panel D: station-level scatter T20 MAE72 vs boundary MAE T5 (validation)
ax_d = fig.add_subplot(gs[2, 0])
st_mae_t20 = val.groupby('station')['C2_T20_h1_72_mae'].median()
st_bnd_t5  = val.groupby('station')['bnd_mae_T5'].median()
common_st = st_mae_t20.index.intersection(st_bnd_t5.index)
ax_d.scatter(st_bnd_t5[common_st], st_mae_t20[common_st], s=20, alpha=0.7, color='#4575b4')
ax_d.set_xlabel('Boundary T5 MAE (median, °C)', fontsize=8)
ax_d.set_ylabel('T20 C2 MAE72 (median, °C)', fontsize=8)
ax_d.set_title('Station: boundary error vs interior error', fontsize=8)
ax_d.tick_params(labelsize=7)
r = np.corrcoef(st_bnd_t5[common_st], st_mae_t20[common_st])[0, 1]
ax_d.text(0.05, 0.92, f'r={r:.2f}', transform=ax_d.transAxes, fontsize=8)

# Panel E: T50 MAE72 distribution — B1 vs C2 (val)
ax_e = fig.add_subplot(gs[2, 1])
ax_e.hist(val['B1_T50_h1_72_mae'].dropna(), bins=30, alpha=0.55, color='#4575b4', label='B1 T50')
ax_e.hist(val['C2_T50_h1_72_mae'].dropna(), bins=30, alpha=0.55, color='#d73027', label='C2 T50')
ax_e.axvline(val['B1_T50_h1_72_mae'].median(), color='#4575b4', lw=1.5, ls='--')
ax_e.axvline(val['C2_T50_h1_72_mae'].median(), color='#d73027', lw=1.5, ls='--')
ax_e.set_xlabel('MAE72 (°C)', fontsize=8); ax_e.set_ylabel('Count', fontsize=8)
ax_e.set_title('T50 MAE72: B1 vs C2 (validation)', fontsize=8)
ax_e.tick_params(labelsize=7); ax_e.legend(fontsize=7)

# Panel F: headroom vs baseline strip plot at each depth
ax_f = fig.add_subplot(gs[2, 2])
for di, (d_name, best_comp) in enumerate([('T20', 'C2'), ('T50', 'B1')]):
    col_best  = f'{best_comp}_{d_name}_h1_72_mae'
    col_recon = f'RECON_{d_name}_h1_72_mae'
    paired = val[[col_best, col_recon]].dropna()
    headroom = paired[col_best].values - paired[col_recon].values
    jitter = np.random.default_rng(42).uniform(-0.2, 0.2, len(headroom))
    ax_f.scatter(np.full(len(headroom), di) + jitter, headroom, s=4, alpha=0.25,
                 color=['#d73027', '#4575b4'][di])
    ax_f.boxplot(headroom, positions=[di], widths=0.3, showfliers=False,
                 medianprops={'color': 'k', 'lw': 1.5}, patch_artist=True,
                 boxprops={'facecolor': ['#d73027', '#4575b4'][di], 'alpha': 0.4})
ax_f.axhline(0, color='k', lw=1.0, ls='-')
ax_f.set_xticks([0, 1]); ax_f.set_xticklabels(['T20\nC2-RECON', 'T50\nB1-RECON'], fontsize=8)
ax_f.set_ylabel('Headroom (°C)', fontsize=8)
ax_f.set_title('Headroom (best baseline minus RECON)', fontsize=8)
ax_f.tick_params(labelsize=7)

# ---- overall annotation ----
fig.suptitle(
    'Soil Temperature Forecast Feasibility — USCRN Validation Set (2018-2021)\n'
    'T20: MIXED (Room for AI trial) | T50: Baselines adequate  |  Retrospective evidence only',
    fontsize=9.5, fontweight='bold', y=0.98
)

out_path = os.path.join(FD, 'forecast_figure.png')
fig.savefig(out_path, dpi=150, bbox_inches='tight')
print(f'Figure saved to {out_path}')

# copy to brain folder for artifact display
brain_path = os.path.join(BRAIN, 'forecast_figure.png')
import shutil; shutil.copy2(out_path, brain_path)
print(f'Copied to brain: {brain_path}')
