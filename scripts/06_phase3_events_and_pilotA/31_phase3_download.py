import os as _o, sys as _s
_p = _o.path.dirname(_o.path.abspath(__file__))
while not _o.path.exists(_o.path.join(_p, 'src', 'config.py')): _p = _o.path.dirname(_p)
_s.path.insert(0, _o.path.join(_p, 'src'))
from config import WS_ROOT  # PATH-PATCH: was an absolute path to the original working directory
"""
Phase-3 download: USCRN hourly02, 2012-2021 ONLY (2022+ stays untouched as reserved evaluation period).
Stations: union of (a) the 39 audit-qualified stations, (b) the 15 Wilson-candidate stations, (c) the 6 earlier development stations.
Keeps (LST date/hour): CRX_VN (logger version), T_HR_AVG, T_MAX, T_MIN, P_CALC, SOLARAD(+flag), SUR_TEMP(+flag), RH,
soil moisture 5 depths, soil temperature 5 depths. Saved as separate files in phase3/data (existing multi/ files untouched).
"""
import sys, io, os, re, time, glob, requests, numpy as np, pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
BASE = 'https://www.ncei.noaa.gov/pub/data/uscrn/products/hourly02'
ROOT = WS_ROOT
OUT = os.path.join(ROOT, 'phase3', 'data'); os.makedirs(OUT, exist_ok=True)
YEARS = list(range(2012, 2022))

A = pd.read_csv(os.path.join(ROOT, 'audit_station_table.csv'))
q = A[(A.n_dry >= 200) & (A.two_state_bins >= 3) & (A.sd_TS >= 0.03) & (A.insane < 0.05)].station.tolist()
wil = ['NE_Lincoln_8_ENE', 'CO_La_Junta_17_WSW', 'CO_Cortez_8_SE', 'SD_Sioux_Falls_14_NNE', 'LA_Lafayette_13_SE',
       'CO_Montrose_11_ENE', 'AZ_Elgin_5_S', 'AL_Fairhope_3_NE', 'MO_Chillicothe_22_ENE', 'MS_Newton_5_ENE',
       'SD_Buffalo_13_ESE', 'ND_Northgate_5_ESE', 'NM_Los_Alamos_13_W', 'NC_Asheville_8_SSW', 'NC_Durham_11_W']
dev = [l.strip() for l in open(os.path.join(ROOT, 'pilot_stations.txt')) if l.strip()]
stations = sorted(set(q) | set(wil) | set(dev))
print('qualified', len(q), 'wilson', len(wil), 'dev', len(dev), 'union', len(stations))
pd.Series(stations).to_csv(os.path.join(ROOT, 'phase3', 'stations_phase3.csv'), index=False, header=['station'])

def parse(text):
    rows = []
    for line in text.splitlines():
        p = line.split()
        if len(p) < 38: continue
        def f(i):
            try: return float(p[i])
            except Exception: return np.nan
        rows.append([int(p[3]), int(p[4]) // 100, f(5), f(9), f(10), f(11), f(12), f(13), f(20), f(26)] +
                    [f(i) for i in range(28, 38)] +
                    [1.0 if p[14] == '0' else 0.0, 1.0 if p[21] == '0' else 0.0])
    a = np.array(rows, np.float64)
    # columns: 0 date,1 hour,2 crx,3 Tavg,4 Tmax,5 Tmin,6 P,7 solar,8 surT,9 RH,10-14 SM,15-19 ST,20 solarflag_ok,21 surflag_ok
    for c in (3, 4, 5, 6, 7, 8, 9, 15, 16, 17, 18, 19): a[a[:, c] <= -9000, c] = np.nan
    for c in range(10, 15): a[a[:, c] < -90, c] = np.nan
    a[a[:, 20] == 0, 7] = np.nan; a[a[:, 21] == 0, 8] = np.nan
    return a

def job(stn, yr):
    fn = os.path.join(OUT, f'{stn}_{yr}.npy')
    if os.path.exists(fn): return stn, yr, 'cached'
    err = ''
    for attempt in range(3):
        try:
            r = requests.get(f'{BASE}/{yr}/CRNH0203-{yr}-{stn}.txt', timeout=120)
            if r.status_code == 404: return stn, yr, 'http 404'
            if r.status_code != 200: return stn, yr, f'http {r.status_code}'
            np.save(fn, parse(r.text).astype(np.float32) if False else parse(r.text)); return stn, yr, 'ok'
        except Exception as e:
            err = str(e)[:60]; time.sleep(3)
    return stn, yr, 'fail ' + err

tasks = [(s, y) for s in stations for y in YEARS]
t0 = time.time(); stat = {}
with ThreadPoolExecutor(max_workers=8) as ex:
    futs = [ex.submit(job, s, y) for s, y in tasks]
    for i, f in enumerate(as_completed(futs)):
        s, y, m = f.result(); k = m.split()[0] + (' ' + m.split()[1] if m.startswith('http') else '')
        stat[k] = stat.get(k, 0) + 1
        if m.startswith(('fail', 'http')) and 'cached' not in m: print('  ', s, y, m, flush=True)
        if (i + 1) % 25 == 0: print(f'  {i + 1}/{len(tasks)} done {time.time() - t0:.0f}s', flush=True)
print('STATUS COUNTS', stat, f'total {time.time() - t0:.0f}s')
