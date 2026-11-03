import os as _o, sys as _s
_p = _o.path.dirname(_o.path.abspath(__file__))
while not _o.path.exists(_o.path.join(_p, 'src', 'config.py')): _p = _o.path.dirname(_p)
_s.path.insert(0, _o.path.join(_p, 'src'))
from config import WS_ROOT  # PATH-PATCH: was an absolute path to the original working directory
"""56_forecast_scores.py — score all common-set issues; apply frozen decision rule.
Outputs: phase3/forecast/forecast_scores.csv, forecast_summary.txt, forecast_bootstrap.csv.
Run AFTER 55_forecast_verification passes. No future data; RECON is a clearly separated diagnostic.
"""
import sys, io, os, time, warnings
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
warnings.filterwarnings('ignore')
sys.path.insert(0, WS_ROOT)

import numpy as np, pandas as pd

from forecastlib import (
    Station, detect_spells, validity, forecast_all, development_alphas,
    DEPTH_COLS, HORIZON, P3, DEVYEARS, VALYEARS
)

FD = os.path.join(P3, 'forecast')
OUT_CSV  = os.path.join(FD, 'forecast_scores.csv')
OUT_SUM  = os.path.join(FD, 'forecast_summary.txt')
OUT_BOOT = os.path.join(FD, 'forecast_bootstrap.csv')

# ---- load inventory (common-set only) ----
INV = pd.read_csv(os.path.join(FD, 'issue_inventory.csv'), parse_dates=['issue'])
INV = INV[INV.common].copy()
print(f'Common-set issues: {len(INV)}  (dev {(INV.split=="dev").sum()}, val {(INV.split=="val").sum()})')

# ---- development alpha references (frozen: start year <= 2017) ----
gA, sA, nA = development_alphas()
print(f'Alpha references: global {gA:.3e} m2/s from {nA} archived windows; station medians for {len(sA)} stations')

# ---- helper: MAE over a lead-hour range ----
LEADS = {'h1_24': (0, 24), 'h1_48': (0, 48), 'h1_72': (0, 72)}
COMPETITORS = ['B1', 'B2', 'C1', 'C2', 'C3', 'RECON']
DEPTHS      = {'T20': 0, 'T50': 1}  # indices into competitor arrays

def mae(arr, lo, hi):
    return float(np.nanmean(np.abs(arr[lo:hi])))

def bias(arr, lo, hi):
    return float(np.nanmean(arr[lo:hi]))

# ---- load observations for scoring ----
from forecastlib import load_station, VALYEARS as VY, DEVYEARS as DY
from scipy.interpolate import PchipInterpolator

# ---- main scoring loop ----
t0 = time.time()
rows = []

stations_done = set()
all_stations = INV.station.unique()
print(f'Stations: {len(all_stations)}')

for stn in all_stations:
    st = Station(stn, gA, sA.get(stn, gA))
    sub = INV[INV.station == stn]
    for _, row in sub.iterrows():
        ts = row.issue
        # get outcome observations (future T20 and T50)
        i0 = st.df.index.get_loc(ts)
        fut = st.df.iloc[i0 + 1: i0 + 1 + HORIZON]
        obs_T20 = fut['T20'].values  # length HORIZON (may have NaNs)
        obs_T50 = fut['T50'].values

        # run all competitors (with RECON diagnostic)
        fc = forecast_all(st, ts, with_recon=True)

        rec = {
            'station': stn,
            'issue': ts,
            'split': row.split,
            'year': ts.year,
            'month': ts.month,
            'mayseps': bool(row.mayseps),
            'dry_at_issue': bool(row.dry_at_issue) if not pd.isna(row.dry_at_issue) else False,
            'nonfreezing_past': bool(row.nonfreezing_past) if not pd.isna(row.nonfreezing_past) else False,
            'cluster': int(row.cluster),
            'alpha_C2': fc['alpha_C2'],
            'alpha_C2_fitted': bool(fc['alpha_C2_fitted']),
            'T20_issue': float(row.T20_issue) if not pd.isna(row.T20_issue) else np.nan,
            'T50_issue': float(row.T50_issue) if not pd.isna(row.T50_issue) else np.nan,
            'rain72_ge10': bool(row.rain72_ge10),
        }

        # boundary forecast error (T5 and T100)
        obs_T5   = fut['T5'].values
        obs_T100 = fut['T100'].values
        bt = fc['bnd_top']; bb = fc['bnd_bot']
        rec['bnd_mae_T5']   = mae(bt - obs_T5, 0, 72)
        rec['bnd_mae_T100'] = mae(bb - obs_T100, 0, 72)

        # per-competitor scores at each depth and lead window
        for comp in COMPETITORS:
            pred_arr = fc.get(comp)
            if pred_arr is None:
                for d_name in DEPTHS:
                    for lead in LEADS:
                        rec[f'{comp}_{d_name}_{lead}_mae']  = np.nan
                        rec[f'{comp}_{d_name}_{lead}_bias'] = np.nan
                continue
            for d_name, d_idx in DEPTHS.items():
                obs = obs_T20 if d_name == 'T20' else obs_T50
                err = pred_arr[:, d_idx] - obs
                for lead, (lo, hi) in LEADS.items():
                    rec[f'{comp}_{d_name}_{lead}_mae']  = mae(err, lo, hi)
                    rec[f'{comp}_{d_name}_{lead}_bias'] = bias(err, lo, hi)

        rows.append(rec)

df = pd.DataFrame(rows)
df.to_csv(OUT_CSV, index=False)
elapsed = time.time() - t0
print(f'Scored {len(df)} issues in {elapsed:.0f}s. Saved to {OUT_CSV}')

# ---- summary statistics ----
BASELINES = ['B1', 'B2', 'C2']  # primary baselines per spec (C1, C3 are sensitivities)

def cluster_bootstrap(vals, clusters, n_boot=2000, seed=42):
    """mean of vals with cluster bootstrap CI. Returns (mean, lo95, hi95)."""
    rng = np.random.default_rng(seed)
    cl_vals = [vals[clusters == c] for c in np.unique(clusters)]
    cl_vals = [v for v in cl_vals if len(v) > 0]
    if len(cl_vals) == 0 or all(len(v) == 0 for v in cl_vals):
        return np.nan, np.nan, np.nan
    obs_mean = np.nanmean(vals)
    boot_means = []
    for _ in range(n_boot):
        samp = rng.choice(len(cl_vals), len(cl_vals), replace=True)
        boot_means.append(np.nanmean(np.concatenate([cl_vals[i] for i in samp])))
    lo, hi = np.percentile(boot_means, [2.5, 97.5])
    return obs_mean, lo, hi

lines = []
def say(s=''): lines.append(s); print(s)

say('=' * 72)
say('FORECAST FEASIBILITY SCORING SUMMARY')
say(f'Common-set issues: {len(df)}  dev: {(df.split=="dev").sum()}  val: {(df.split=="val").sum()}')
say(f'Alpha: global={gA:.3e}, C2-fitted={df[df.split=="val"].alpha_C2_fitted.mean():.1%} of val issues')
say('=' * 72)

boot_rows = []

for split_label, split_mask in [('VALIDATION (primary)', df.split == 'val'),
                                  ('DEVELOPMENT (descriptive)', df.split == 'dev')]:
    sub = df[split_mask]
    say(f'\n--- {split_label}: n={len(sub)} issues, clusters={sub.cluster.nunique()} ---')
    say(f'  Boundary forecast: T5 MAE={sub.bnd_mae_T5.median():.3f} C (median), T100 MAE={sub.bnd_mae_T100.median():.3f} C')
    say(f'  Alpha C2 fitted: {sub.alpha_C2_fitted.mean():.1%}; median alpha={sub.alpha_C2.median():.3e} m2/s')

    for d_name in ['T20', 'T50']:
        say(f'\n  Depth {d_name}:')
        best_mae = np.inf; best_comp = None
        for comp in COMPETITORS:
            col = f'{comp}_{d_name}_h1_72_mae'
            if col not in sub.columns: continue
            vals = sub[col].dropna().values
            if len(vals) == 0: continue
            med = np.nanmedian(vals)
            mn, lo, hi = cluster_bootstrap(vals, sub.loc[sub[col].notna(), 'cluster'].values)
            ci_half = (hi - lo) / 2 if not np.isnan(hi) else np.nan
            tag = '  [BEST BASELINE]' if (comp in BASELINES and med < best_mae) else ''
            say(f'    {comp:6s} MAE72={med:.3f} C (mean={mn:.3f}, 95%CI [{lo:.3f},{hi:.3f}], half-width={ci_half:.3f}){tag}')
            if comp in BASELINES and med < best_mae:
                best_mae = med; best_comp = comp
            boot_rows.append({'split': split_label, 'depth': d_name, 'comp': comp, 'n': len(vals),
                               'median_mae72': med, 'mean_mae72': mn, 'ci_lo': lo, 'ci_hi': hi})
        # headroom = best_baseline - RECON
        recon_col = f'RECON_{d_name}_h1_72_mae'
        best_col  = f'{best_comp}_{d_name}_h1_72_mae'
        if best_comp and recon_col in sub.columns:
            paired = sub[[best_col, recon_col]].dropna()
            headroom_vals = paired[best_col].values - paired[recon_col].values
            h_mean, h_lo, h_hi = cluster_bootstrap(headroom_vals, sub.loc[paired.index, 'cluster'].values)
            say(f'    Headroom ({best_comp}-RECON): mean={h_mean:.3f}, 95%CI [{h_lo:.3f},{h_hi:.3f}]')
            h_frac = h_mean / best_mae if best_mae > 0 else np.nan
            say(f'    Headroom fraction of best baseline: {h_frac:.1%}')
        say(f'    Best baseline for {d_name}: {best_comp} (median MAE72={best_mae:.3f} C)')

        # stratum breakdown (validation only)
        if split_label.startswith('VAL'):
            for strat_name, strat_mask in [
                ('May-Sep', sub.mayseps),
                ('Dry at issue', sub.dry_at_issue),
                ('Non-freezing', sub.nonfreezing_past),
                ('Rain >=10mm w/in 72h', sub.rain72_ge10),
            ]:
                s2 = sub[strat_mask]
                col = f'{best_comp}_{d_name}_h1_72_mae'
                if len(s2) < 5: continue
                say(f'      {strat_name}: n={len(s2)}, {best_comp} MAE72={s2[col].median():.3f} C')

# ---- lead profile ----
say('\n--- Lead-time MAE profile (validation, best baselines) ---')
val = df[df.split == 'val']
for d_name, best_comp_for_d in [('T20', None), ('T50', None)]:
    best_comp_for_d = min(BASELINES, key=lambda c: val[f'{c}_{d_name}_h1_72_mae'].median())
    parts = [f'  {d_name} best={best_comp_for_d}:']
    for lead in ['h1_24', 'h1_48', 'h1_72']:
        col = f'{best_comp_for_d}_{d_name}_{lead}_mae'
        parts.append(f'  {lead}={val[col].median():.3f} C')
    say(''.join(parts))

# ---- frozen decision rule (per spec) ----
say('\n' + '=' * 72)
say('FROZEN DECISION RULE (applied to validation set):')
val = df[df.split == 'val']
decisions = {}
for d_name in ['T20', 'T50']:
    best_comp = min(BASELINES, key=lambda c: val[f'{c}_{d_name}_h1_72_mae'].median())
    best_mae72 = val[f'{best_comp}_{d_name}_h1_72_mae'].median()
    recon_col = f'RECON_{d_name}_h1_72_mae'; best_col = f'{best_comp}_{d_name}_h1_72_mae'
    paired = val[[best_col, recon_col]].dropna()
    headroom_vals = paired[best_col].values - paired[recon_col].values
    h_mean, h_lo, h_hi = cluster_bootstrap(headroom_vals, val.loc[paired.index, 'cluster'].values)
    h_frac = h_mean / best_mae72 if best_mae72 > 0 else np.nan
    # CI on best baseline MAE
    bm_vals = val[best_col].dropna().values
    _, bm_lo, bm_hi = cluster_bootstrap(bm_vals, val.loc[val[best_col].notna(), 'cluster'].values)
    n_val_cl = val.cluster.nunique()

    say(f'\n  Depth {d_name}: best baseline={best_comp}, median MAE72={best_mae72:.3f} C, 95%CI [{bm_lo:.3f},{bm_hi:.3f}]')
    say(f'    Headroom: mean={h_mean:.3f} C, 95%CI [{h_lo:.3f},{h_hi:.3f}], fraction={h_frac:.1%}')

    # Rule (1): insufficient?
    if n_val_cl < 40 or (df.split=='dev').sum() < 80:
        dec = 'INSUFFICIENT'
        say(f'    -> Rule 1 triggered (clusters): INSUFFICIENT')
    # Rule (2): baselines adequate?
    elif best_mae72 < 0.30:
        dec = 'BASELINES_ADEQUATE'
        say(f'    -> Rule 2a: MAE72 < 0.30 C: BASELINES ADEQUATE')
    elif not np.isnan(h_frac) and h_frac < 0.25:
        dec = 'BASELINES_ADEQUATE'
        say(f'    -> Rule 2b: headroom < 25% of best baseline: BASELINES ADEQUATE')
    elif h_lo <= 0:
        dec = 'BASELINES_ADEQUATE'
        say(f'    -> Rule 2c: headroom CI includes zero: BASELINES ADEQUATE')
    else:
        dec = 'ROOM_FOR_AI_TRIAL'
        say(f'    -> Rule 3: none of the above: ROOM FOR A FAIR AI TRIAL')
    decisions[d_name] = dec
    say(f'    DECISION ({d_name}): {dec}')

say('\n  Combined decision:')
if all(v == 'INSUFFICIENT' for v in decisions.values()):
    say('    OVERALL: INSUFFICIENT SUPPORT')
elif all(v == 'BASELINES_ADEQUATE' for v in decisions.values()):
    say('    OVERALL: BASELINES ADEQUATE')
elif all(v == 'ROOM_FOR_AI_TRIAL' for v in decisions.values()):
    say('    OVERALL: ROOM FOR A FAIR AI TRIAL (both depths)')
else:
    say(f'    OVERALL: MIXED — {decisions}')

say('\n' + '=' * 72)
say('Note: This is retrospective feasibility evidence. Observed score differences')
say('do not prove an AI model can recover the missing information.')

open(OUT_SUM, 'w', encoding='utf-8').write('\n'.join(lines))
pd.DataFrame(boot_rows).to_csv(OUT_BOOT, index=False)
print(f'\nSummary saved to {OUT_SUM}')
print(f'Bootstrap table saved to {OUT_BOOT}')
