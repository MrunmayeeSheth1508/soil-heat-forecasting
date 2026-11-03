import os as _o, sys as _s
_p = _o.path.dirname(_o.path.abspath(__file__))
while not _o.path.exists(_o.path.join(_p, 'src', 'config.py')): _p = _o.path.dirname(_p)
_s.path.insert(0, _o.path.join(_p, 'src'))
from config import WS_ROOT  # PATH-PATCH: was an absolute path to the original working directory
"""
Download USCRN hourly02 files for all stations, years 2019-2021, keep only soil T (5 depths), soil moisture (5 depths),
precipitation and LST date/hour as compact float32 arrays. Skips AK and HI.
"""
import sys, io, os, re, time, requests, numpy as np
from concurrent.futures import ThreadPoolExecutor, as_completed
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
BASE = 'https://www.ncei.noaa.gov/pub/data/uscrn/products/hourly02'
OUT = (WS_ROOT + r'\multi')
os.makedirs(OUT, exist_ok=True)
YEARS = [2019, 2020, 2021]

def listing(yr):
    r = requests.get(f'{BASE}/{yr}/', timeout=60); r.raise_for_status()
    return sorted(set(re.findall(r'CRNH0203-%d-([A-Za-z0-9_]+)\.txt' % yr, r.text)))

def parse(text):
    lst_date = []; lst_hr = []; vals = []
    for line in text.splitlines():
        p = line.split()
        if len(p) < 38: continue
        lst_date.append(int(p[3])); lst_hr.append(int(p[4]) // 100)
        row = []
        for c in [12] + list(range(28, 38)):
            try: v = float(p[c])
            except: v = np.nan
            row.append(v)
        vals.append(row)
    a = np.array(vals, dtype=np.float32)
    a[:, 0][a[:, 0] < -9000] = np.nan                       # precip
    sm = a[:, 1:6]; sm[sm < -90] = np.nan                    # soil moisture
    stt = a[:, 6:11]; stt[stt < -9000] = np.nan              # soil temp
    return np.array(lst_date, np.int32), np.array(lst_hr, np.int8), a

def job(stn, yr):
    fn = os.path.join(OUT, f'{stn}_{yr}.npz')
    if os.path.exists(fn): return stn, yr, 'cached'
    for attempt in range(3):
        try:
            r = requests.get(f'{BASE}/{yr}/CRNH0203-{yr}-{stn}.txt', timeout=120)
            if r.status_code != 200: return stn, yr, f'http {r.status_code}'
            d, h, a = parse(r.text)
            np.savez_compressed(fn, date=d, hour=h, P=a[:, 0], SM=a[:, 1:6], ST=a[:, 6:11])
            return stn, yr, 'ok'
        except Exception as e:
            err = str(e)[:60]; time.sleep(3)
    return stn, yr, 'fail ' + err

tasks = []
for yr in YEARS:
    names = [s for s in listing(yr) if not s.startswith(('AK_', 'HI_'))]
    print(yr, 'stations (non-AK/HI):', len(names))
    tasks += [(s, yr) for s in names]
t0 = time.time(); stat = {}
with ThreadPoolExecutor(max_workers=8) as ex:
    futs = [ex.submit(job, s, y) for s, y in tasks]
    for i, f in enumerate(as_completed(futs)):
        s, y, m = f.result(); stat[m.split()[0]] = stat.get(m.split()[0], 0) + 1
        if m.startswith(('fail', 'http')): print('  ', s, y, m)
        if (i + 1) % 50 == 0: print(f'  {i + 1}/{len(tasks)} done, {time.time() - t0:.0f}s', flush=True)
print('STATUS COUNTS', stat, f'total {time.time() - t0:.0f}s')
