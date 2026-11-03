import os as _o, sys as _s
_p = _o.path.dirname(_o.path.abspath(__file__))
while not _o.path.exists(_o.path.join(_p, 'src', 'config.py')): _p = _o.path.dirname(_p)
_s.path.insert(0, _o.path.join(_p, 'src'))
from config import WS_ROOT  # PATH-PATCH: was an absolute path to the original working directory
"""
Selma Episode 4 — detailed row-level audit before any model fitting.

Corrections applied:
- Reconcile SM range: 0.303-0.147=0.156 (within-episode), NOT 0.303-0.119=0.184 (annual).
  The annual minimum 0.119 occurred outside this episode. Print both clearly.
- Gradient: report per-depth, per-time statistics throughout episode, not just maximum.
- Precipitation: inspect USCRN P_CALC column (col 12) during episode for infiltration events.
- All-depth moisture histories: print all 5 depths, not just 5cm.
- Timestamps: verify row continuity, detect any within-episode gaps.
- Rounding: |ΔT|<0.15 means less than 1.5 reporting increments (not 'one increment').
- Document that observations are multi-probe aggregates; single-column model is a simplification.
"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import os, numpy as np

DEPTHS    = [5, 10, 20, 50, 100]
SM_COLS   = [28, 29, 30, 31, 32]
ST_COLS   = [33, 34, 35, 36, 37]
PCOL      = 12   # P_CALC (precipitation mm)
MISS_T    = -9999.0
MISS_SM   = -99.000
MISS_P    = -9999.0
raw_dir   = (WS_ROOT + r'\raw')

# ---- Load Selma 2019+2020 ----
paths = [os.path.join(raw_dir, f'CRNH0203-{yr}-AL_Selma_13_WNW.txt') for yr in [2019,2020]]
all_rows = []
for path in paths:
    with open(path, 'r') as f:
        for line in f:
            parts = line.split()
            if len(parts) >= 38:
                all_rows.append(parts)
n = len(all_rows)
sm  = np.full((n, 5), np.nan)
st  = np.full((n, 5), np.nan)
pr  = np.full(n, np.nan)
utc = []
for j, parts in enumerate(all_rows):
    utc.append(parts[1] + parts[2])
    for k, col in enumerate(SM_COLS):
        try:
            v = float(parts[col])
            if v > MISS_SM + 1: sm[j,k] = v
        except: pass
    for k, col in enumerate(ST_COLS):
        try:
            v = float(parts[col])
            if v > MISS_T + 1: st[j,k] = v
        except: pass
    try:
        v = float(parts[PCOL])
        if v > MISS_P + 1: pr[j] = v
    except: pass

print("Selma 2019-2020: total rows", n)

# ---- Re-identify Episode 4 (same logic as 02_episode_audit.py) ----
valid = np.all(~np.isnan(st), axis=1) & np.all(~np.isnan(sm), axis=1) & np.all(st > 1.0, axis=1)
episodes = []
in_ep = False; ep_start = 0
for i in range(n):
    if valid[i] and not in_ep:
        ep_start = i; in_ep = True
    elif not valid[i] and in_ep:
        if i - ep_start >= 96: episodes.append((ep_start, i))
        in_ep = False
if in_ep and n - ep_start >= 96: episodes.append((ep_start, n))

print(f"Total episodes (>=4 days): {len(episodes)}")
es, ee = episodes[3]   # Episode 4 (0-indexed)
ep_len = ee - es
print(f"\nEpisode 4: rows {es}..{ee}  ({ep_len} hours = {ep_len/24:.1f} days)")
print(f"UTC start: {utc[es]}  UTC end: {utc[ee-1]}")

ep_st = st[es:ee]
ep_sm = sm[es:ee]
ep_pr = pr[es:ee]
ep_utc = utc[es:ee]

# ---- AUDIT 1: Timestamp continuity ----
print("\n--- AUDIT 1: Timestamp continuity ---")
# Convert YYYYMMDD+HHmm to sequential index
def parse_utc(s):
    yr  = int(s[:4]); mo = int(s[4:6]); dy = int(s[6:8]); hr = int(s[8:10])
    # Approximate day-of-year offset
    days_per_month = [0,31,28,31,30,31,30,31,31,30,31,30,31]
    doy = sum(days_per_month[:mo]) + dy
    if yr % 4 == 0 and mo > 2: doy += 1
    return (yr - 2019)*8760 + (doy-1)*24 + hr

ep_times = np.array([parse_utc(u) for u in ep_utc])
dt = np.diff(ep_times)
gaps = np.where(dt != 1)[0]
print(f"  Expected consecutive 1-hr gaps: {ep_len-1}")
print(f"  Non-consecutive gaps found: {len(gaps)}")
if len(gaps): 
    for g in gaps[:5]: print(f"    Gap at row {g}: dt={dt[g]} hrs (UTC {ep_utc[g]} -> {ep_utc[g+1]})")

# ---- AUDIT 2: Moisture range reconciliation ----
print("\n--- AUDIT 2: Moisture range reconciliation ---")
print(f"  Annual SM-5cm: min={np.nanmin(sm[:,0]):.3f}  max={np.nanmax(sm[:,0]):.3f}  (annual extremes)")
print(f"  Episode 4 SM-5cm: min={ep_sm[:,0].min():.3f}  max={ep_sm[:,0].max():.3f}")
print(f"  Episode 4 range: {ep_sm[:,0].max()-ep_sm[:,0].min():.3f} m3/m3")
print(f"  (Report said 0.156; this is 0.303-0.147=0.156. Annual min 0.119 is outside episode.)")
print(f"  Annual-episode min difference: {np.nanmin(sm[:,0]) - ep_sm[:,0].min():.3f} m3/m3")

print(f"\n  All-depth moisture ranges within Episode 4:")
print(f"  {'Depth':>6}  {'min':>7}  {'max':>7}  {'range':>7}  {'mean':>7}  {'n_nan':>6}")
for k, d in enumerate(DEPTHS):
    col = ep_sm[:,k]
    valid_col = col[~np.isnan(col)]
    print(f"  {d:>5}cm  {valid_col.min():>7.3f}  {valid_col.max():>7.3f}  "
          f"{valid_col.max()-valid_col.min():>7.3f}  {valid_col.mean():>7.3f}  "
          f"{np.isnan(col).sum():>6}")

# ---- AUDIT 3: Precipitation during episode ----
print("\n--- AUDIT 3: Precipitation events ---")
pr_ep_valid = ep_pr[~np.isnan(ep_pr)]
print(f"  Valid precipitation readings: {len(pr_ep_valid)}/{ep_len}")
precip_hours = np.where(~np.isnan(ep_pr) & (ep_pr > 0))[0]
print(f"  Hours with precipitation > 0: {len(precip_hours)}")
if len(precip_hours) > 0:
    print(f"  Total precip in episode: {np.nansum(ep_pr):.1f} mm")
    print(f"  Precip events (first 10): hour, mm")
    for h in precip_hours[:10]:
        print(f"    Hour {h} (UTC {ep_utc[h]}): {ep_pr[h]:.1f} mm")
    # SM response to precip: check SM change in 1-6 hrs after precip
    print(f"\n  SM-5cm response to largest precip events:")
    largest = precip_hours[np.argsort(ep_pr[precip_hours])[-5:]]
    for h in sorted(largest):
        sm_before = ep_sm[max(0,h-2):h, 0].mean() if h > 2 else np.nan
        sm_after  = ep_sm[h:min(ep_len,h+6), 0].mean() if h < ep_len-6 else np.nan
        print(f"    Hour {h}: precip={ep_pr[h]:.1f}mm  SM_before={sm_before:.3f}  SM_after_6h={sm_after:.3f}  delta={sm_after-sm_before:.3f}")

# ---- AUDIT 4: Temperature gradients throughout episode ----
print("\n--- AUDIT 4: Temperature gradients — statistics throughout episode ---")
print(f"  (User correction: max alone does not establish gradients throughout.)")
print(f"  Per-depth-pair gradient statistics (C/m), hourly:")
depth_pairs = [(0,1,'5-10cm'), (1,2,'10-20cm'), (2,3,'20-50cm'), (3,4,'50-100cm')]
for i, j, label in depth_pairs:
    dz_cm = DEPTHS[j] - DEPTHS[i]
    grad = (ep_st[:,j] - ep_st[:,i]) / dz_cm * 100  # C/m
    print(f"  {label}: mean={grad.mean():.2f}  std={grad.std():.2f}  "
          f"p10={np.percentile(grad,10):.2f}  p50={np.percentile(grad,50):.2f}  p90={np.percentile(grad,90):.2f}  C/m")
# Also: fraction of hours where ALL inter-depth gradients exceed 2 C/m
all_grad_ok = np.ones(ep_len, dtype=bool)
for i, j, _ in depth_pairs:
    dz_cm = DEPTHS[j] - DEPTHS[i]
    g = abs((ep_st[:,j] - ep_st[:,i]) / dz_cm * 100)
    all_grad_ok &= (g >= 2.0)
print(f"\n  Fraction of hours where ALL 4 depth-pair gradients >= 2 C/m: {all_grad_ok.mean():.3f}")
print(f"  Hours satisfying this: {all_grad_ok.sum()}/{ep_len}")

# ---- AUDIT 5: Temperature resolution characteristics ----
print("\n--- AUDIT 5: Temperature resolution characteristics ---")
print(f"  (Correction: |ΔT|<0.15 C means <1.5 reporting increments, not 'one increment'.)")
print(f"  Reporting increment = 0.1 C. 1.5 increments = 0.15 C.")
for k, d in enumerate(DEPTHS):
    col = ep_st[:,k]
    dt_col = np.diff(col)
    frac_zero = np.mean(dt_col == 0.0)
    frac_1inc = np.mean(np.abs(dt_col) < 0.15)   # < 1.5 increments
    frac_2inc = np.mean(np.abs(dt_col) < 0.25)   # < 2.5 increments
    print(f"  {d:3}cm: frac(dt=0)={frac_zero:.3f}  frac(|dt|<1.5 inc)={frac_1inc:.3f}  frac(|dt|<2.5 inc)={frac_2inc:.3f}")

# ---- AUDIT 6: Multi-probe aggregation note ----
print("\n--- AUDIT 6: Multi-probe aggregation ---")
print("""  NOAA documents that each soil temperature value is computed from multiple probes
  at each nominal depth. The single-column 1D model treats each depth as a point.
  This is a structural mismatch that the observation model should represent.
  
  Specifically: the observed T at depth d is a spatial average over the instrument
  footprint (horizontal extent unknown). The 1D model predicts T at a single point.
  Horizontal heterogeneity in moisture and soil properties will contribute residuals
  that the 1D model cannot explain regardless of moisture conditioning.
  
  This does not prevent the pilot but limits physical interpretation of fitted residuals.
""")

# ---- AUDIT 7: Per-depth moisture histories — look for infiltration signals ----
print("--- AUDIT 7: Moisture propagation — do wet events penetrate to depth? ---")
print(f"  Correlation matrix of SM across depths:")
sm_valid_cols = []
labels = []
for k, d in enumerate(DEPTHS):
    col = ep_sm[:,k]
    if np.isnan(col).sum() < ep_len//4:
        sm_valid_cols.append(col)
        labels.append(f'{d}cm')
if len(sm_valid_cols) >= 2:
    print(f"  {'':>6} " + "  ".join(f"{l:>6}" for l in labels))
    for i, (row_col, row_label) in enumerate(zip(sm_valid_cols, labels)):
        corrs = []
        for j, col2 in enumerate(sm_valid_cols):
            mask = ~np.isnan(row_col) & ~np.isnan(col2)
            if mask.sum() > 10:
                r = np.corrcoef(row_col[mask], col2[mask])[0,1]
                corrs.append(f"{r:>6.3f}")
            else:
                corrs.append(f"{'---':>6}")
        print(f"  {row_label:>6} " + "  ".join(corrs))

# Lag analysis: does SM at 100cm lag SM at 5cm?
sm5  = ep_sm[:,0]; sm100 = ep_sm[:,4]
mask = ~np.isnan(sm5) & ~np.isnan(sm100)
if mask.sum() > 100:
    lags = [0, 6, 12, 24, 48, 72]
    print(f"\n  SM-5cm vs SM-100cm cross-correlation at lag (hours):")
    sm5_c   = sm5[mask]   - sm5[mask].mean()
    sm100_c = sm100[mask] - sm100[mask].mean()
    for lag in lags:
        if lag < len(sm5_c):
            r = np.corrcoef(sm5_c[lag:], sm100_c[:len(sm5_c)-lag])[0,1] if len(sm5_c)-lag > 10 else np.nan
            print(f"    lag={lag:3d}h: r={r:.3f}")

print("\n=== AUDIT COMPLETE ===")
print("Proceed to pilot model only after reviewing the above.")
print("Key questions before fitting:")
print("  1. Are precip-driven SM spikes within the episode? (check AUDIT 3)")
print("  2. Do gradients hold throughout, or only transiently? (check AUDIT 4)")
print("  3. Does moisture penetrate to 100cm in this episode, or is it decoupled?")
print("  4. Is the 0.044 m3/m3 wet-dry contrast within the episode enough to")
print("     produce a temperature signature at 20cm above the noise level?")
print("     This cannot be answered from the audit alone — needs the forward model.")
