import os as _o, sys as _s
_p = _o.path.dirname(_o.path.abspath(__file__))
while not _o.path.exists(_o.path.join(_p, 'src', 'config.py')): _p = _o.path.dirname(_p)
_s.path.insert(0, _o.path.join(_p, 'src'))
from config import WS_ROOT  # PATH-PATCH: was an absolute path to the original working directory
"""56b_forecast_tail.py — lead profile + decision rule from already-saved forecast_scores.csv"""
import sys, io, os, warnings
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
warnings.filterwarnings('ignore')
sys.path.insert(0, WS_ROOT)
import numpy as np, pandas as pd

FD = (WS_ROOT + r'\phase3\forecast')
df = pd.read_csv(os.path.join(FD, 'forecast_scores.csv'), parse_dates=['issue'])
BASELINES = ['B1', 'B2', 'C2']
OUT_SUM = os.path.join(FD, 'forecast_summary.txt')

lines = []
def say(s=''):
    lines.append(s)
    print(s)

def cluster_bootstrap(vals, clusters, n_boot=2000, seed=42):
    rng = np.random.default_rng(seed)
    cl_vals = [vals[clusters == c] for c in np.unique(clusters)]
    cl_vals = [v for v in cl_vals if len(v) > 0]
    if not cl_vals:
        return np.nan, np.nan, np.nan
    boot_means = []
    for _ in range(n_boot):
        samp = rng.choice(len(cl_vals), len(cl_vals), replace=True)
        boot_means.append(np.nanmean(np.concatenate([cl_vals[i] for i in samp])))
    return np.nanmean(vals), float(np.percentile(boot_means, 2.5)), float(np.percentile(boot_means, 97.5))

val = df[df.split == 'val']

# ---- lead profile ----
say('--- Lead-time MAE profile (validation, best baselines) ---')
for d_name in ['T20', 'T50']:
    best_comp = min(BASELINES, key=lambda c: val[f'{c}_{d_name}_h1_72_mae'].median())
    parts = [f'  {d_name} best={best_comp}:']
    for lead in ['h1_24', 'h1_48', 'h1_72']:
        col = f'{best_comp}_{d_name}_{lead}_mae'
        parts.append(f'  {lead}={val[col].median():.3f} C')
    say(''.join(parts))

# ---- station-level spread ----
say('\n--- Station-level MAE72 spread (validation) ---')
for d_name, comp in [('T20', 'C2'), ('T50', 'B1')]:
    col = f'{comp}_{d_name}_h1_72_mae'
    st = val.groupby('station')[col].median()
    say(f'  {d_name} {comp}: n_stations={len(st)}, '
        f'median={st.median():.3f}, '
        f'IQR=[{st.quantile(0.25):.3f},{st.quantile(0.75):.3f}], '
        f'max={st.max():.3f} ({st.idxmax()})')

# ---- frozen decision rule ----
say('\n' + '=' * 72)
say('FROZEN DECISION RULE (validation set):')
decisions = {}
for d_name in ['T20', 'T50']:
    best_comp = min(BASELINES, key=lambda c: val[f'{c}_{d_name}_h1_72_mae'].median())
    best_mae72 = val[f'{best_comp}_{d_name}_h1_72_mae'].median()
    best_col  = f'{best_comp}_{d_name}_h1_72_mae'
    recon_col = f'RECON_{d_name}_h1_72_mae'
    paired = val[[best_col, recon_col]].dropna()
    headroom_vals = paired[best_col].values - paired[recon_col].values
    h_mean, h_lo, h_hi = cluster_bootstrap(headroom_vals, val.loc[paired.index, 'cluster'].values)
    h_frac = h_mean / best_mae72 if best_mae72 > 0 else float('nan')
    bm_vals = val[best_col].dropna().values
    _, bm_lo, bm_hi = cluster_bootstrap(bm_vals, val.loc[val[best_col].notna(), 'cluster'].values)
    n_val_cl = int(val.cluster.nunique())

    say(f'\n  {d_name}: best={best_comp}, median MAE72={best_mae72:.3f} C, CI=[{bm_lo:.3f},{bm_hi:.3f}]')
    say(f'    Headroom ({best_comp}-RECON): mean={h_mean:.3f} C, CI=[{h_lo:.3f},{h_hi:.3f}], fraction={h_frac:.1%}')

    if n_val_cl < 40 or (df.split == 'dev').sum() < 80:
        dec = 'INSUFFICIENT'
        say('    -> Rule 1: INSUFFICIENT')
    elif best_mae72 < 0.30:
        dec = 'BASELINES_ADEQUATE'
        say('    -> Rule 2a: MAE72 < 0.30 C => BASELINES ADEQUATE')
    elif not (h_frac != h_frac) and h_frac < 0.25:
        dec = 'BASELINES_ADEQUATE'
        say('    -> Rule 2b: headroom < 25% => BASELINES ADEQUATE')
    elif h_lo <= 0:
        dec = 'BASELINES_ADEQUATE'
        say('    -> Rule 2c: headroom CI includes 0 => BASELINES ADEQUATE')
    else:
        dec = 'ROOM_FOR_AI_TRIAL'
        say('    -> Rule 3: none of the above => ROOM FOR A FAIR AI TRIAL')
    decisions[d_name] = dec
    say(f'    DECISION ({d_name}): {dec}')

say('\n  Combined:')
vals_d = list(decisions.values())
if all(v == 'INSUFFICIENT' for v in vals_d):
    say('    OVERALL: INSUFFICIENT SUPPORT')
elif all(v == 'BASELINES_ADEQUATE' for v in vals_d):
    say('    OVERALL: BASELINES ADEQUATE')
elif all(v == 'ROOM_FOR_AI_TRIAL' for v in vals_d):
    say('    OVERALL: ROOM FOR A FAIR AI TRIAL (both depths)')
else:
    say(f'    OVERALL: MIXED -- T20={decisions["T20"]}, T50={decisions["T50"]}')

say('\n' + '=' * 72)
say('Retrospective feasibility evidence only. Score differences do not prove')
say('an AI model can recover the remaining information.')

# append to existing summary file
existing = open(OUT_SUM, 'r', encoding='utf-8').read() if os.path.exists(OUT_SUM) else ''
open(OUT_SUM, 'w', encoding='utf-8').write(existing + '\n' + '\n'.join(lines))
print('\nSummary appended to', OUT_SUM)
