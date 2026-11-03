import os as _o, sys as _s
_p = _o.path.dirname(_o.path.abspath(__file__))
while not _o.path.exists(_o.path.join(_p, 'src', 'config.py')): _p = _o.path.dirname(_p)
_s.path.insert(0, _o.path.join(_p, 'src'))
from config import WS_ROOT  # PATH-PATCH: was an absolute path to the original working directory
"""
CORRECTED Gate 2 episode audit for USCRN soil candidate.

Corrections applied per mentor review:
- Brunetti estimates DEPTH-DEPENDENT diffusivity (not single constant), held constant
  within each sliding window. The 1.5 C threshold also required gradients >2 C/m,
  windows >= 4 days, sensor noise <= 0.02 C, bias SD <= 0.01 C. These cannot be
  assumed for USCRN's multi-probe aggregate product.
- USCRN soil temperature is reported to 0.1 C resolution, aggregated across probes.
  Reporting resolution, sensor accuracy, calibration bias, and spatial variability
  are different quantities. None of these is established to be within Brunetti's specs.
- Annual moisture range != identifiable episode contrast. Inspect minimum, maximum,
  duration, timing. Check for spikes, saturation, and missing data.
- Boundary scheme: use 5cm and 100cm as boundaries, calibrate on 10 and 50 cm,
  withhold 20 cm for validation. Withholding 100 cm requires a justified lower
  boundary below it — not available.
- Simultaneous coverage at 4 depths (5,10,20,50 cm + boundary at 100 cm) required.

This script:
A. Loads Selma AL and Versailles KY for 2019-2020
B. Identifies contiguous non-freezing episodes with simultaneous valid data at 5 depths
C. Within each episode: reports duration, depth gradients, moisture range, data quality
D. Identifies wetter vs drier sub-episodes
E. Reports USCRN measurement characteristics (resolution, probe description)
"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import os, numpy as np
from scipy.stats import pearsonr

DEPTHS  = [5, 10, 20, 50, 100]
SM_COLS = [28, 29, 30, 31, 32]  # SOIL_MOISTURE_5..100
ST_COLS = [33, 34, 35, 36, 37]  # SOIL_TEMP_5..100
MISS_T  = -9999.0
MISS_SM = -99.000

def load_station(paths):
    """Load and concatenate multiple year files for one station."""
    all_rows = []
    for path in paths:
        if not os.path.exists(path):
            print(f'  File not found: {path}'); continue
        with open(path, 'r') as f:
            lines = f.readlines()
        for line in lines:
            parts = line.split()
            if len(parts) < 38: continue
            all_rows.append(parts)
    if not all_rows: return None, None, None

    n = len(all_rows)
    sm  = np.full((n, 5), np.nan)
    st  = np.full((n, 5), np.nan)
    utc = []
    for j, parts in enumerate(all_rows):
        utc.append(parts[1] + parts[2])  # YYYYMMDD + HHmm
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
    return np.array(utc), st, sm

def find_episodes(st, sm, min_hours=96):
    """
    Find contiguous episodes where:
    - All 5 soil temperature depths are non-missing
    - All 5 soil moisture depths are non-missing
    - All soil temps > 1 C (non-freezing)
    - No data gaps (consecutive rows assumed hourly; caller ensures this)
    Min duration: 4 days = 96 hours (Brunetti minimum window)
    Returns list of (start_idx, end_idx) pairs.
    """
    # Valid = all depths non-NaN AND all temps > 1C
    valid = np.all(~np.isnan(st), axis=1) & np.all(~np.isnan(sm), axis=1) & np.all(st > 1.0, axis=1)

    episodes = []
    in_ep = False
    ep_start = 0
    for i in range(len(valid)):
        if valid[i] and not in_ep:
            ep_start = i; in_ep = True
        elif not valid[i] and in_ep:
            ep_len = i - ep_start
            if ep_len >= min_hours:
                episodes.append((ep_start, i))
            in_ep = False
    if in_ep and len(valid) - ep_start >= min_hours:
        episodes.append((ep_start, len(valid)))
    return episodes

def episode_stats(st_ep, sm_ep, depths=DEPTHS):
    """Compute key statistics for a single episode."""
    n = len(st_ep)
    # Depth gradients: use mean temperature profile
    t_mean = np.nanmean(st_ep, axis=0)
    grads  = np.diff(t_mean) / np.diff(depths)  # C/cm -> *100 for C/m
    max_grad_Cpm = abs(grads).max() * 100

    # Diurnal fluctuation at 5cm (median daily range)
    day_ranges = []
    for d in range(n // 24):
        block = st_ep[d*24:(d+1)*24, 0]
        block = block[~np.isnan(block)]
        if len(block) >= 12:
            day_ranges.append(block.max() - block.min())
    diurnal_5cm = np.median(day_ranges) if day_ranges else np.nan

    # Moisture stats at 5 and 20 cm
    sm5  = sm_ep[:, 0];  sm20 = sm_ep[:, 2]
    sm_min_5  = np.nanmin(sm5);  sm_max_5  = np.nanmax(sm5)
    sm_range_5 = sm_max_5 - sm_min_5

    # Check for spikes (sudden >0.1 m3/m3 change in 1 hour)
    dsm5 = np.abs(np.diff(sm5))
    n_spikes = np.sum(dsm5 > 0.10)

    # Rounding check: fraction of consecutive temperature readings that are identical
    # (0.1 C resolution -> adjacent identical values common when signal weak)
    dt5 = np.diff(st_ep[:, 0])
    frac_zero_dt = np.mean(dt5 == 0.0)

    # Temperature distinctiveness: range at 100cm vs 5cm
    range_5cm   = st_ep[:,0].max() - st_ep[:,0].min()
    range_100cm = st_ep[:,4].max() - st_ep[:,4].min()

    # Inter-depth correlation (high = signal penetrates; need it to be <1 to be informative)
    r_5_100, _ = pearsonr(st_ep[:,0], st_ep[:,4]) if n > 10 else (np.nan, np.nan)

    return dict(
        n_hours=n,
        diurnal_5cm=diurnal_5cm,
        max_grad_Cpm=max_grad_Cpm,
        sm_min_5=sm_min_5, sm_max_5=sm_max_5, sm_range_5=sm_range_5,
        n_sm_spikes=n_spikes,
        frac_zero_dt_temp=frac_zero_dt,
        range_5cm=range_5cm, range_100cm=range_100cm,
        r_5_100=r_5_100,
    )

def split_wet_dry(st_ep, sm_ep, threshold_percentile=40):
    """
    Split episode into drier and wetter halves by median sm at 5cm.
    Returns (dry_mask, wet_mask).
    """
    sm5    = sm_ep[:, 0]
    thresh = np.nanpercentile(sm5, threshold_percentile)
    dry    = sm5 <= thresh
    wet    = sm5 > thresh
    return dry, wet

# ============================================================
# MAIN AUDIT
# ============================================================
raw_dir = (WS_ROOT + r'\raw')

stations_to_check = [
    ('AL_Selma_13_WNW',  [2019, 2020]),
    ('KY_Versailles_3_NNW', [2019, 2020]),
]

for stn_name, years in stations_to_check:
    print(f"\n{'='*70}")
    print(f"STATION: {stn_name}")
    print(f"{'='*70}")

    paths = [os.path.join(raw_dir, f'CRNH0203-{yr}-{stn_name}.txt') for yr in years]
    utc, st, sm = load_station(paths)
    if utc is None:
        print('  No data loaded. Skipping.'); continue

    print(f"  Total rows loaded: {len(utc)}")

    # Annual stats
    print(f"\n--- Annual moisture (5cm) ---")
    sm5_all = sm[:,0]; sm5_valid = sm5_all[~np.isnan(sm5_all)]
    print(f"  Valid: {len(sm5_valid)}/{len(sm5_all)}")
    if len(sm5_valid) > 10:
        print(f"  min={sm5_valid.min():.3f}  max={sm5_valid.max():.3f}  range={sm5_valid.max()-sm5_valid.min():.3f}")
        print(f"  p5={np.percentile(sm5_valid,5):.3f}  median={np.median(sm5_valid):.3f}  p95={np.percentile(sm5_valid,95):.3f}")
        # Check spike count annually
        dsm = np.abs(np.diff(sm5_valid))
        print(f"  Hourly jumps >0.10 m3/m3: {np.sum(dsm>0.10)} (potential spikes or precip events)")
        print(f"  Hourly jumps >0.05 m3/m3: {np.sum(dsm>0.05)}")

    print(f"\n--- Simultaneous 5-depth valid coverage ---")
    all_valid = np.all(~np.isnan(st), axis=1) & np.all(~np.isnan(sm), axis=1)
    nonfreezing = np.all(st > 1.0, axis=1)
    print(f"  All 5 T and SM valid: {all_valid.sum()} hrs ({100*all_valid.mean():.1f}%)")
    print(f"  All valid + non-freezing: {(all_valid & nonfreezing).sum()} hrs ({100*(all_valid & nonfreezing).mean():.1f}%)")

    # Temperature reporting resolution check
    print(f"\n--- Temperature reporting resolution (0.1 C) ---")
    st5_valid = st[:,0][~np.isnan(st[:,0])]
    dt5_all   = np.diff(st5_valid)
    print(f"  Fraction of consecutive T-5cm readings that are identical (dt=0): {np.mean(dt5_all==0.0):.3f}")
    print(f"  Fraction |dt| < 0.15 C (within 1 reporting increment): {np.mean(np.abs(dt5_all)<0.15):.3f}")
    unique_vals = np.unique(np.round(st5_valid, 1))
    print(f"  Unique temperature values at 5cm: {len(unique_vals)} distinct in {len(st5_valid)} readings")

    # Find episodes
    episodes = find_episodes(st, sm, min_hours=96)
    print(f"\n--- Contiguous non-freezing episodes (>=4 days, all depths valid) ---")
    print(f"  Number of episodes: {len(episodes)}")

    if not episodes:
        print("  No usable episodes found. Station fails Gate 2 episode check.")
        continue

    # Stats per episode
    print(f"\n  {'Ep':>3}  {'dur(h)':>7}  {'diurnal':>8}  {'grad(C/m)':>10}  {'SM_min':>7}  {'SM_max':>7}  {'SM_rng':>7}  {'spikes':>7}  {'frac_dt0':>9}")
    for i, (es, ee) in enumerate(episodes[:15]):
        st_ep = st[es:ee]; sm_ep = sm[es:ee]
        s = episode_stats(st_ep, sm_ep)
        print(f"  {i+1:>3}  {s['n_hours']:>7}  {s['diurnal_5cm']:>8.2f}  {s['max_grad_Cpm']:>10.2f}  "
              f"{s['sm_min_5']:>7.3f}  {s['sm_max_5']:>7.3f}  {s['sm_range_5']:>7.3f}  "
              f"{s['n_sm_spikes']:>7}  {s['frac_zero_dt_temp']:>9.3f}")

    # Identify best episodes: strong diurnal + gradient + moisture contrast + no spikes
    good_eps = [(i, es, ee) for i, (es,ee) in enumerate(episodes)
                if episode_stats(st[es:ee], sm[es:ee])['diurnal_5cm'] >= 1.5
                and episode_stats(st[es:ee], sm[es:ee])['max_grad_Cpm'] >= 2.0
                and episode_stats(st[es:ee], sm[es:ee])['sm_range_5'] >= 0.05
                and episode_stats(st[es:ee], sm[es:ee])['n_sm_spikes'] == 0]
    print(f"\n  Episodes with diurnal>=1.5C + grad>=2C/m + SM_range>=0.05 + no spikes: {len(good_eps)}")

    if good_eps:
        print(f"  Best episode details (ep #{good_eps[0][0]+1}):")
        es, ee = good_eps[0][1], good_eps[0][2]
        s = episode_stats(st[es:ee], sm[es:ee])
        for k, v in s.items():
            print(f"    {k}: {v:.4f}" if isinstance(v, float) else f"    {k}: {v}")

        # Wet/dry split within best episode
        dry_m, wet_m = split_wet_dry(st[es:ee], sm[es:ee])
        print(f"\n  Wet/dry split (bottom 40% SM = dry, top 60% = wet):")
        print(f"    Dry subset: {dry_m.sum()} hrs  Wet subset: {wet_m.sum()} hrs")
        ep_st = st[es:ee]; ep_sm = sm[es:ee]
        if dry_m.sum() >= 96 and wet_m.sum() >= 96:
            dry_s = episode_stats(ep_st[dry_m], ep_sm[dry_m])
            wet_s = episode_stats(ep_st[wet_m], ep_sm[wet_m])
            print(f"    Dry: diurnal={dry_s['diurnal_5cm']:.2f}C  grad={dry_s['max_grad_Cpm']:.2f}C/m  SM_mean={ep_sm[dry_m,0].mean():.3f}")
            print(f"    Wet: diurnal={wet_s['diurnal_5cm']:.2f}C  grad={wet_s['max_grad_Cpm']:.2f}C/m  SM_mean={ep_sm[wet_m,0].mean():.3f}")
            print(f"    SM contrast (wet-dry mean at 5cm): {ep_sm[wet_m,0].mean()-ep_sm[dry_m,0].mean():.3f} m3/m3")
        else:
            print(f"    Insufficient hours in one subset for 4-day minimum.")

print("\n=== MEASUREMENT LIMITATIONS SUMMARY ===")
print("""
USCRN soil temperature product (from readme.txt):
  - Reported at 0.1 C resolution (one decimal place)
  - Combines measurements from multiple sensors at each nominal depth
  - 'Nominal' depths may have installation variance (not documented per-station)
  - Calibration history not included in the public hourly product

These differ from Brunetti's validation conditions:
  - Brunetti required sensor noise <= 0.02 C (USCRN resolution alone = 0.1 C)
  - Brunetti required sensor bias SD <= 0.01 C (unknown for USCRN aggregate)
  - Brunetti required sensor depth known to a few mm (unknown for USCRN)

Implication: the effective measurement uncertainty for this product is larger
than Brunetti's identifiability floor. Whether the moisture-conditioning signal
(expected to be O(0.1-0.5 C difference between wet and dry diffusivity predictions)
is detectable above USCRN's effective noise is not established.
This is the central question Gate 3 must answer quantitatively.
""")
