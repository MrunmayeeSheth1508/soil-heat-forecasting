import os as _o, sys as _s
_p = _o.path.dirname(_o.path.abspath(__file__))
while not _o.path.exists(_o.path.join(_p, 'src', 'config.py')): _p = _o.path.dirname(_p)
_s.path.insert(0, _o.path.join(_p, 'src'))
from config import WS_ROOT  # PATH-PATCH: was an absolute path to the original working directory
"""Compute the FROZEN column family (rules in phase3/layered_spec_frozen.md). Uses only Wilson probe-site cores and development-years (2012-2018) moisture.
No simulation and no contrast is computed here. Output: phase3/columns_frozen.csv + phase3/columns_frozen_summary.txt (hashed afterwards)."""
import sys, io, os, glob, hashlib, warnings
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace'); warnings.filterwarnings('ignore')
import numpy as np, pandas as pd
ROOT = WS_ROOT; P3 = os.path.join(ROOT, 'phase3'); D = os.path.join(P3, 'data')
EV = pd.read_csv(os.path.join(P3, 'archive_pre_diag', 'event_inventory.csv')); EV = EV[(EV.variant == 'primary') & EV.complete_sequence].copy()
EV['year'] = pd.to_datetime(EV.start).dt.year
stations_all = sorted(EV.station.unique()); dev_stations = sorted(EV[EV.year <= 2018].station.unique())
W = pd.read_csv(os.path.join(ROOT, 'wilson', 'wilson_T1_tidy.csv'))
def key(stn): s, rest = stn.split('_', 1); return (s + '_' + rest.replace('_', '')).upper()
DEP = [0.05, 0.1, 0.2, 0.5, 1.0]; LAYER_DEPTHS = {1: [0.05, 0.1, 0.2], 2: [0.2, 0.5], 3: [0.5, 1.0]}
LAYER_SENSORS = {1: ['M5', 'M10', 'M20'], 2: ['M20', 'M50'], 3: ['M50', 'M100']}
def hourly(stn):
    a = np.vstack([np.load(f) for f in sorted(glob.glob(os.path.join(D, f'{stn}_*.npy')))])
    t = pd.to_datetime(a[:, 0].astype(int).astype(str), format='%Y%m%d', errors='coerce') + pd.to_timedelta(a[:, 1], unit='h')
    df = pd.DataFrame({'T5': a[:, 15]}, index=t)
    for k, c in enumerate(['M5', 'M10', 'M20', 'M50', 'M100']): df[c] = a[:, 10 + k]
    return df[~df.index.isna()]
def kJ(theta, bd, sand, phi):
    Sr = min(theta / phi, 1.0); coarse = sand >= 0.5
    Ke = (0.7 * np.log10(Sr) + 1 if Sr > 0.05 else 0.0) if coarse else (np.log10(Sr) + 1 if Sr > 0.1 else 0.0); Ke = max(Ke, 0.0)
    ko = 2.0 if sand > 0.2 else 3.0; kmin = 8.8 ** sand * ko ** (1 - sand); ksat = kmin ** (1 - phi) * 0.57 ** phi
    kdry = (0.135 * bd + 0.0647) / (2.7 - 0.947 * bd); return (ksat - kdry) * Ke + kdry
VAR = {'central': dict(rho_s=2.65, Cs=2.0e6, q=50), 'dry_ref': dict(rho_s=2.65, Cs=2.0e6, q=25), 'wet_ref': dict(rho_s=2.65, Cs=2.0e6, q=75),
       'Cs_low': dict(rho_s=2.70, Cs=1.8e6, q=50), 'Cs_high': dict(rho_s=2.60, Cs=2.4e6, q=50)}
rows = []; notes = []
for stn in stations_all:
    w = W[W.key == key(stn)]
    if not len(w): notes.append(f'{stn}: not in Wilson table'); continue
    w = w.iloc[0]
    def layer_prop(L, name):
        vals = [w[f'{name}_{d}'] for d in LAYER_DEPTHS[L] if not pd.isna(w[f'{name}_{d}'])]
        return float(np.mean(vals)) if vals else np.nan
    bd = {L: layer_prop(L, 'bd') for L in (1, 2, 3)}; sd = {L: layer_prop(L, 'sand') / 100.0 for L in (1, 2, 3)}
    if np.isnan(bd[1]) or np.isnan(sd[1]): notes.append(f'{stn}: no usable L1 bulk density or sand -> excluded from S'); continue
    for L in (2, 3):                               # copy nearest layer if missing
        near = [x for x in ((1,) if L == 2 else (2, 1)) ]
        if np.isnan(bd[L]): bd[L] = next(bd[n] for n in near if not np.isnan(bd[n]))
        if np.isnan(sd[L]): sd[L] = next(sd[n] for n in near if not np.isnan(sd[n]))
    h = hourly(stn); h = h[(h.index.year >= 2012) & (h.index.year <= 2018) & (h['T5'] > 1.0)]
    for L in (1, 2, 3):
        lm = h[LAYER_SENSORS[L]].mean(axis=1, skipna=True).where(h[LAYER_SENSORS[L]].notna().sum(axis=1) >= 2).dropna()
        if len(lm) < 500: notes.append(f'{stn} L{L}: fewer than 500 development hours of moisture'); lm = pd.Series([np.nan])
        for vn, v in VAR.items():
            th = float(np.nanpercentile(lm, v['q'])) if lm.notna().any() else np.nan
            phi = 1 - bd[L] / v['rho_s']; clipped = th > phi; thc = min(th, phi) if not np.isnan(th) else np.nan
            if np.isnan(thc): continue
            k = kJ(thc, bd[L], sd[L], phi); C = (1 - phi) * v['Cs'] + thc * 4.18e6
            rows.append(dict(station=stn, variant=vn, layer=L, bd=bd[L], sand=sd[L], phi=phi, theta_ref=thc, theta_clipped=clipped, k=k, C=C, alpha=k / C, dev_station=stn in dev_stations))
COL = pd.DataFrame(rows)
# keep only stations with all three layers in every variant
cnt = COL.groupby(['station', 'variant']).layer.nunique(); good = cnt[cnt == 3].reset_index()[['station', 'variant']]
COL = COL.merge(good, on=['station', 'variant']); okst = sorted(set(COL.station))
cen = COL[(COL.variant == 'central')].pivot(index='station', columns='layer', values=['k', 'C']); cen.columns = [f'{a}{b}' for a, b in cen.columns]
dev = cen[cen.index.isin(dev_stations)]
rk = (dev.k1 / dev.k3); rC = (dev.C1 / dev.C3)
# uniform control
LA = np.linspace(np.log(5e-8), np.log(5e-6), 80); aU = float(np.exp(LA[np.argmin(np.abs(LA - np.log(4.58e-7)))])); CU = 2.5e6
G = dict(rk_p10=float(np.percentile(rk, 10)), rk_p50=float(np.percentile(rk, 50)), rk_p90=float(np.percentile(rk, 90)), rC_p50=float(np.percentile(rC, 50)), C_low=float(np.median(dev.C3)))
S = []
S.append('FROZEN COLUMN FAMILY (derived from Wilson cores and development-year moisture only; no simulation or contrast involved)')
S.append(f'event stations {len(stations_all)}, development stations (>=1 development event) {len(dev_stations)}; stations with usable S columns {len(okst)}; S-central development stations used for G: {len(dev)}')
S.append(f'U: alpha_U = {aU:.3e} m2/s (grid value nearest 4.58e-7), C_U = {CU:.2e}, k_U = {aU * CU:.3f} W/m/K; sensitivities alpha_U 2e-7 and 1e-6')
S.append(f'S-central layer values across stations (median [min, max]): ' + '; '.join(f'L{L} k {COL[(COL.variant == "central") & (COL.layer == L)].k.median():.2f} [{COL[(COL.variant == "central") & (COL.layer == L)].k.min():.2f}, {COL[(COL.variant == "central") & (COL.layer == L)].k.max():.2f}], C {COL[(COL.variant == "central") & (COL.layer == L)].C.median() / 1e6:.2f}e6, alpha {COL[(COL.variant == "central") & (COL.layer == L)].alpha.median():.2e}' for L in (1, 2, 3)))
S.append(f'theta_ref clipped to porosity in {int(COL[COL.variant == "central"].theta_clipped.sum())} of {len(COL[COL.variant == "central"])} station-layers (central)')
S.append(f'development ratios: k(L1)/k(L3) P10 {G["rk_p10"]:.3f}, P50 {G["rk_p50"]:.3f}, P90 {G["rk_p90"]:.3f}; C(L1)/C(L3) P50 {G["rC_p50"]:.3f}; median C(L3) {G["C_low"]:.3e}')
S.append(f'G_low : lower layer (20-100 cm) C = {G["C_low"]:.3e}, k = {aU * G["C_low"]:.3f}; upper (5-20 cm) k = {G["rk_p10"] * aU * G["C_low"]:.3f}, C = {G["rC_p50"] * G["C_low"]:.3e}  (alpha_up/alpha_low = {G["rk_p10"] / G["rC_p50"]:.2f})')
S.append(f'G_high: lower layer same; upper k = {G["rk_p90"] * aU * G["C_low"]:.3f}, C = {G["rC_p50"] * G["C_low"]:.3e}  (alpha_up/alpha_low = {G["rk_p90"] / G["rC_p50"]:.2f})')
S.append('NOTES: ' + '; '.join(notes[:40]))
pd.concat([COL.assign(kind='S'), pd.DataFrame([dict(station='ALL', variant='U', layer=0, k=aU * CU, C=CU, alpha=aU, kind='U'),
          dict(station='ALL', variant='G_low', layer=1, k=G['rk_p10'] * aU * G['C_low'], C=G['rC_p50'] * G['C_low'], alpha=G['rk_p10'] * aU / G['rC_p50'], kind='G'),
          dict(station='ALL', variant='G_low', layer=2, k=aU * G['C_low'], C=G['C_low'], alpha=aU, kind='G'),
          dict(station='ALL', variant='G_high', layer=1, k=G['rk_p90'] * aU * G['C_low'], C=G['rC_p50'] * G['C_low'], alpha=G['rk_p90'] * aU / G['rC_p50'], kind='G'),
          dict(station='ALL', variant='G_high', layer=2, k=aU * G['C_low'], C=G['C_low'], alpha=aU, kind='G')])]).to_csv(os.path.join(P3, 'columns_frozen.csv'), index=False)
open(os.path.join(P3, 'columns_frozen_summary.txt'), 'w', encoding='utf-8').write('\n'.join(S)); print('\n'.join(S))
print('sha256 columns_frozen.csv', hashlib.sha256(open(os.path.join(P3, 'columns_frozen.csv'), 'rb').read()).hexdigest())
