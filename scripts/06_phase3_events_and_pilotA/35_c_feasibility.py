import os as _o, sys as _s
_p = _o.path.dirname(_o.path.abspath(__file__))
while not _o.path.exists(_o.path.join(_p, 'src', 'config.py')): _p = _o.path.dirname(_p)
_s.path.insert(0, _o.path.join(_p, 'src'))
from config import WS_ROOT  # PATH-PATCH: was an absolute path to the original working directory
"""Direction C feasibility (small, no model fitting): ORNL DAAC MODIS/VIIRS subset service (no login).
 1. product list (which daily / 8-day / 16-day vegetation products exist)
 2. land-cover homogeneity (MCD12Q1 LC_Type1, 5x5 500 m pixels = ~2.3 km square) for ALL phase-3 stations
 3. NDVI (MOD13Q1 250 m, 16-day) + pixel reliability for a few real hot-dry event windows at 6 stations:
    composite dates relative to the event, share of good-reliability center pixels, spatial heterogeneity
Outputs phase3/c_feasibility_out.txt, phase3/c_landcover.csv, phase3/c_ndvi_windows.csv"""
import sys, io, os, json, time, requests, numpy as np, pandas as pd
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
ROOT = WS_ROOT; O = os.path.join(ROOT, 'phase3')
U = 'https://modis.ornl.gov/rst/api/v1'
H = {'Accept': 'application/json'}
def get(url, params=None, tries=3):
    for i in range(tries):
        try:
            r = requests.get(url, params=params, headers=H, timeout=120)
            if r.status_code == 200: return r.json()
            err = f'{r.status_code} {r.text[:120]}'
        except Exception as e: err = str(e)[:100]
        time.sleep(4)
    return {'error': err}
L = []
prods = get(f'{U}/products')
names = [p['product'] + ' | ' + p.get('description', '')[:70] + ' | ' + str(p.get('frequency', '')) + ' | ' + str(p.get('resolution_meters', ''))
         for p in prods.get('products', [])] if 'products' in prods else []
want = [n for n in names if any(k in n for k in ('MOD09', 'MOD13', 'MOD15', 'MOD16', 'MOD17', 'MCD43', 'VNP13', 'VNP09', 'MOD11', 'MCD12', 'MCD15'))]
L.append('PRODUCTS (vegetation-relevant):'); L += ['  ' + n for n in want] if want else ['  (list unavailable: ' + str(prods.get('error')) + ')']

S = pd.read_csv(os.path.join(ROOT, 'stations.tsv'), sep='\t', dtype=str)
st = pd.read_csv(os.path.join(O, 'stations_phase3.csv')).station.tolist()
def coords(stn):
    s, rest = stn.split('_', 1); parts = rest.split('_'); loc = ''.join(parts[:-2]); vec = ''.join(parts[-2:])
    m = S[(S.STATE == s) & (S.LOCATION.str.replace(' ', '') == loc) & (S.VECTOR.str.replace(' ', '') == vec)]
    return (float(m.LATITUDE.iloc[0]), float(m.LONGITUDE.iloc[0])) if len(m) else (np.nan, np.nan)
LC = {1: 'evergreen needleleaf', 2: 'evergreen broadleaf', 3: 'deciduous needleleaf', 4: 'deciduous broadleaf', 5: 'mixed forest', 6: 'closed shrub', 7: 'open shrub',
      8: 'woody savanna', 9: 'savanna', 10: 'grassland', 11: 'wetland', 12: 'cropland', 13: 'urban', 14: 'crop/natural mosaic', 15: 'snow/ice', 16: 'barren', 17: 'water'}
rows = []
for stn in st:
    la, lo = coords(stn)
    r = get(f'{U}/MCD12Q1/subset', dict(latitude=la, longitude=lo, kmAboveBelow=1, kmLeftRight=1, startDate='A2019001', endDate='A2019001', band='LC_Type1'))
    if 'subset' not in r: rows.append(dict(station=stn, lat=la, lon=lo, error=str(r.get('error'))[:60])); continue
    d = np.array(r['subset'][0]['data']); c = d[len(d) // 2]
    vals, cnt = np.unique(d, return_counts=True)
    rows.append(dict(station=stn, lat=la, lon=lo, center=int(c), center_name=LC.get(int(c), '?'), frac_same=round(float(np.mean(d == c)), 2), classes=int(len(vals)),
                     dominant=LC.get(int(vals[cnt.argmax()]), '?')))
    print(stn, rows[-1].get('center_name'), rows[-1].get('frac_same'), flush=True)
LCd = pd.DataFrame(rows); LCd.to_csv(os.path.join(O, 'c_landcover.csv'), index=False)
L.append('\nLAND COVER (MCD12Q1 2019, 5x5 pixels of 500 m around the 2-decimal station coordinate):')
ok = LCd.dropna(subset=['center']) if 'center' in LCd else LCd
L.append(f'  stations queried {len(LCd)}, with result {len(ok)}')
L.append('  center class counts: ' + str(ok.center_name.value_counts().to_dict()))
L.append(f'  fraction of window pixels equal to center: median {ok.frac_same.median():.2f}; stations with >=0.8: {(ok.frac_same >= 0.8).sum()}; with 1.0: {(ok.frac_same == 1.0).sum()}')

# NDVI windows
ev = pd.read_csv(os.path.join(O, 'event_inventory.csv'))
C = ev[(ev.variant == 'primary') & ev.complete_sequence & ev.wet_day.notna() & ev.month.isin([5, 6, 7, 8, 9])]
pick = [s for s in ['NE_Lincoln_8_ENE', 'MO_Chillicothe_22_ENE', 'OK_Goodwell_2_SE', 'SD_Pierre_24_S', 'NM_Los_Alamos_13_W', 'AL_Selma_13_WNW'] if s in set(C.station)]
if len(pick) < 6: pick += [s for s in C.station.value_counts().index if s not in pick][:6 - len(pick)]
out = []
for stn in pick:
    la, lo = coords(stn); g = C[C.station == stn].head(2)
    for _, e in g.iterrows():
        s0 = pd.Timestamp(e.start) - pd.Timedelta(days=30); s1 = pd.Timestamp(e.end) + pd.Timedelta(days=45)
        f = lambda t: f'A{t.year}{t.dayofyear:03d}'
        res = {}
        for band in ('250m_16_days_NDVI', '250m_16_days_pixel_reliability'):
            res[band] = get(f'{U}/MOD13Q1/subset', dict(latitude=la, longitude=lo, kmAboveBelow=1, kmLeftRight=1, startDate=f(s0), endDate=f(s1), band=band))
        if 'subset' not in res['250m_16_days_NDVI'] or 'subset' not in res['250m_16_days_pixel_reliability']:
            out.append(dict(station=stn, start=e.start, end=e.end, error=str(res['250m_16_days_NDVI'].get('error'))[:60])); continue
        nd = {x['calendar_date']: np.array(x['data'], float) for x in res['250m_16_days_NDVI']['subset']}
        rl = {x['calendar_date']: np.array(x['data'], int) for x in res['250m_16_days_pixel_reliability']['subset']}
        for dte in sorted(nd):
            a = nd[dte].reshape(9, 9); q = rl[dte].reshape(9, 9)
            cen = a[3:6, 3:6]; cq = q[3:6, 3:6]
            good = (cq == 0) | (cq == 1)
            vals = np.where(good & (cen > -2000), cen, np.nan) / 10000.0
            out.append(dict(station=stn, ev_start=e.start, ev_end=e.end, wet_day=e.wet_day, composite=dte,
                            days_from_end=(pd.Timestamp(dte) - pd.Timestamp(e.end)).days,
                            ndvi_center3x3=round(float(np.nanmean(vals)), 3) if np.isfinite(vals).any() else np.nan,
                            good_frac=round(float(good.mean()), 2), spatial_sd_9x9=round(float(np.nanstd(np.where(a > -2000, a, np.nan) / 10000.0)), 3),
                            lc_frac_same=float(LCd.loc[LCd.station == stn, 'frac_same'].iloc[0]) if stn in set(LCd.station) and 'frac_same' in LCd else np.nan))
        print('ndvi', stn, e.start, flush=True)
N = pd.DataFrame(out); N.to_csv(os.path.join(O, 'c_ndvi_windows.csv'), index=False)
L.append('\nNDVI WINDOWS (MOD13Q1 16-day composites, event start-30 d .. end+45 d):')
if 'composite' in N:
    L.append(f'  events {N.groupby(["station", "ev_start"]).ngroups}, composites {len(N)}; mean good-reliability fraction in center 3x3: {N.good_frac.mean():.2f}')
    per = N.groupby(['station', 'ev_start']).agg(n=('composite', 'size'), post=('days_from_end', lambda x: int((x > 0).sum())), post21=('days_from_end', lambda x: int(((x > 0) & (x <= 21)).sum())))
    L.append('  composites per event window: ' + str(per.n.tolist()) + '; composites after the spell end: ' + str(per.post.tolist()) + '; within the 21-day follow-up: ' + str(per.post21.tolist()))
    L.append('  within-9x9 NDVI spatial SD (250 m pixels), median: ' + f'{N.spatial_sd_9x9.median():.3f}')
    L.append(N.groupby('station').apply(lambda g: f'{g.ndvi_center3x3.min():.2f}-{g.ndvi_center3x3.max():.2f}').to_string())
else: L.append('  no NDVI windows retrieved: ' + str(out[:3]))
open(os.path.join(O, 'c_feasibility_out.txt'), 'w', encoding='utf-8').write('\n'.join(L)); print('\n'.join(L))
