import os as _o, sys as _s
_p = _o.path.dirname(_o.path.abspath(__file__))
while not _o.path.exists(_o.path.join(_p, 'src', 'config.py')): _p = _o.path.dirname(_p)
_s.path.insert(0, _o.path.join(_p, 'src'))
from config import WS_ROOT  # PATH-PATCH: was an absolute path to the original working directory
"""
USCRN station inventory scan — Gate 2 completion for soil candidate.
Downloads the 2019 file for each station and checks:
1. How many depths have valid (non-missing) soil temperature and moisture
2. Moisture range within the year (need delta_theta > 0.05 m3/m3)
3. Fraction of hours in non-freezing conditions
4. Diurnal temperature fluctuation at 5cm (need >= 1.5 C per Brunetti)

Uses only 2019 to keep download manageable; samples ~10 stations.
"""
import sys, io, requests, re, os
import numpy as np
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

MISS_T  = -9999.0
MISS_SM = -99.000
BASE    = 'https://www.ncei.noaa.gov/pub/data/uscrn/products/hourly02/2019/'

# Get full station list
r = requests.get(BASE, timeout=20)
# Clean filename extraction
files_raw = re.findall(r'CRNH0203-2019-[\w_]+\.txt', r.text)
# Deduplicate (HTML may repeat)
files = list(dict.fromkeys(files_raw))
print(f'Total stations in 2019: {len(files)}')

# Column indices (0-based, from HEADERS.txt):
# WBANO=0, UTC_DATE=1, UTC_TIME=2, ..., SOIL_MOISTURE_5=28, ..._10=29, ..._20=30, ..._50=31, ..._100=32
# SOIL_TEMP_5=33, ..._10=34, ..._20=35, ..._50=36, ..._100=37
SM_COLS = [28, 29, 30, 31, 32]  # moisture at 5,10,20,50,100 cm
ST_COLS = [33, 34, 35, 36, 37]  # temp at 5,10,20,50,100 cm
DEPTHS  = [5, 10, 20, 50, 100]

os.makedirs(WS_ROOT, exist_ok=True)

results = []
# Sample: download all non-AK stations (AK has freezing issues year-round)
non_ak = [f for f in files if '_AK_' not in f]
print(f'Non-AK stations: {len(non_ak)}')

# Download all to scan coverage (files are ~2MB each, skip if too slow after 60 stations)
for i, fname in enumerate(non_ak[:80]):
    url = BASE + fname
    try:
        r2 = requests.get(url, timeout=30)
        if r2.status_code != 200: continue
        lines = r2.text.splitlines()
        if len(lines) < 100: continue
        
        rows = []
        for line in lines:
            parts = line.split()
            if len(parts) < 38: continue
            rows.append(parts)
        
        arr_sm = np.full((len(rows), 5), np.nan)
        arr_st = np.full((len(rows), 5), np.nan)
        for j, parts in enumerate(rows):
            for k, col in enumerate(SM_COLS):
                try:
                    v = float(parts[col])
                    if v > MISS_SM + 1: arr_sm[j,k] = v
                except: pass
            for k, col in enumerate(ST_COLS):
                try:
                    v = float(parts[col])
                    if v > MISS_T + 1: arr_st[j,k] = v
                except: pass
        
        # Count valid depths (>50% non-missing over the year)
        sm_valid = [int(np.mean(~np.isnan(arr_sm[:,k])) > 0.5) for k in range(5)]
        st_valid = [int(np.mean(~np.isnan(arr_st[:,k])) > 0.5) for k in range(5)]
        n_depths_both = sum(a and b for a,b in zip(sm_valid, st_valid))
        
        # Moisture range (at 5cm, most sensitive)
        sm5 = arr_sm[:,0]; sm5 = sm5[~np.isnan(sm5)]
        delta_sm = sm5.max() - sm5.min() if len(sm5) > 100 else 0
        
        # Non-freezing fraction (all temps > 1C)
        st5 = arr_st[:,0]; st5_valid = st5[~np.isnan(st5)]
        nonfreezing_frac = np.mean(st5_valid > 1.0) if len(st5_valid) > 100 else 0
        
        # Diurnal fluctuation at 5cm (median daily range)
        if len(arr_st) > 48:
            day_ranges = []
            for d in range(len(arr_st) // 24):
                day_block = arr_st[d*24:(d+1)*24, 0]
                day_block = day_block[~np.isnan(day_block)]
                if len(day_block) >= 12:
                    day_ranges.append(day_block.max() - day_block.min())
            diurnal_fluct = np.median(day_ranges) if day_ranges else 0
        else:
            diurnal_fluct = 0
        
        station_name = fname.replace('CRNH0203-2019-','').replace('.txt','')
        results.append({
            'station': station_name,
            'n_depths_both': n_depths_both,
            'delta_sm_5cm': round(delta_sm, 3),
            'nonfreezing_frac': round(nonfreezing_frac, 2),
            'diurnal_fluct_5cm': round(diurnal_fluct, 2),
            'sm_valid': sm_valid,
            'st_valid': st_valid,
        })
    except Exception as e:
        pass
    
    if (i+1) % 10 == 0:
        print(f'  Scanned {i+1}/{min(len(non_ak),80)} stations...', flush=True)

print(f'\nScanned {len(results)} stations\n')

# Filter: require >=3 co-located depths, delta_sm > 0.05, nonfreezing > 0.5
good = [r for r in results if r['n_depths_both'] >= 3 and r['delta_sm_5cm'] > 0.05 and r['nonfreezing_frac'] > 0.5]
print(f'Stations meeting basic criteria (>=3 depths, delta_SM>0.05, >50% non-freezing): {len(good)}')
print()

# Show top stations by number of depths and diurnal fluctuation
good_sorted = sorted(good, key=lambda x: (-x['n_depths_both'], -x['delta_sm_5cm']))
print(f'Top candidates:')
print(f"{'Station':<35} {'n_depths':>8} {'delta_SM':>9} {'nonfreezing':>12} {'diurnal_C':>10}")
for r in good_sorted[:20]:
    print(f"{r['station']:<35} {r['n_depths_both']:>8} {r['delta_sm_5cm']:>9.3f} {r['nonfreezing_frac']:>12.2f} {r['diurnal_fluct_5cm']:>10.2f}")

print(f'\nStations with all 5 depths and Brunetti-sufficient fluctuation (>=1.5C):')
best = [r for r in good if r['n_depths_both'] == 5 and r['diurnal_fluct_5cm'] >= 1.5]
print(f'Count: {len(best)}')
for r in best[:10]:
    print(f"  {r['station']}  delta_SM={r['delta_sm_5cm']:.3f}  diurnal={r['diurnal_fluct_5cm']:.1f}C")
