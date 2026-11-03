import os as _o, sys as _s
_p = _o.path.dirname(_o.path.abspath(__file__))
while not _o.path.exists(_o.path.join(_p, 'src', 'config.py')): _p = _o.path.dirname(_p)
_s.path.insert(0, _o.path.join(_p, 'src'))
from config import WS_ROOT  # PATH-PATCH: was an absolute path to the original working directory
"""
Step 1 soil-property audit. For each candidate station, find NCSS/KSSL lab pedons near the station coordinates
(stations.tsv gives 2 decimals, about +/-0.6 km) and report measured properties for layers overlapping 5-20 cm.
Nothing is estimated or filled in here. Map (SSURGO) values are NOT used.
"""
import requests, sys, io, os, json
import pandas as pd
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
URL = 'https://sdmdataaccess.sc.egov.usda.gov/Tabular/post.rest'
SO = WS_ROOT
def q(sql):
    r = requests.post(URL, data={'query': sql, 'format': 'JSON+COLUMNNAME'}, timeout=180)
    try:
        t = r.json().get('Table', [])
        return pd.DataFrame(t[1:], columns=t[0]) if t else pd.DataFrame()
    except Exception:
        print('ERR', r.text[r.text.find('<ServiceException>') + 18:][:300]); return pd.DataFrame()

S = pd.read_csv(os.path.join(SO, 'stations.tsv'), sep='\t', dtype=str)
S['key'] = S.STATE + '_' + S.LOCATION.str.replace(' ', '_') + '_' + S.VECTOR.str.replace(' ', '_')
checks = pd.read_csv(os.path.join(SO, 'record_checks.csv'))
cands = list(checks.station)
D = 0.03
allrows = []
for stn in cands:
    m = S[S.key == stn]
    if m.empty: print(stn, 'not in stations.tsv'); continue
    lat, lon = float(m.LATITUDE.iloc[0]), float(m.LONGITUDE.iloc[0])
    sql = f"""
    SELECT c.pedon_key, c.pedlabsampnum, c.upedonid, c.usiteid, c.site_obsdate, c.samp_name, c.corr_name,
           c.latitude_decimal_degrees AS plat, c.longitude_decimal_degrees AS plon,
           l.hzn_top, l.hzn_bot, l.hzn_desgn, l.layer_type, l.labsampnum,
           p.sand_total, p.silt_total, p.clay_total, p.texture_lab,
           p.bulk_density_third_bar, p.bulk_density_third_bar_method, p.bulk_density_oven_dry, p.bulk_density_field_moist,
           p.particle_density_less_than_2mm, p.particle_density_lt_2mm_method,
           p.water_retention_third_bar, p.water_retention_15_bar, p.water_retention_0_bar_sieve, p.total_frag_wt_pct_gt_2_mm_ws
    FROM lab_combine_nasis_ncss c
    JOIN lab_layer l ON l.pedon_key = c.pedon_key
    LEFT JOIN lab_physical_properties p ON p.labsampnum = l.labsampnum
    WHERE c.latitude_decimal_degrees BETWEEN {lat - D} AND {lat + D}
      AND c.longitude_decimal_degrees BETWEEN {lon - D} AND {lon + D}
      AND l.hzn_top < 20 AND l.hzn_bot > 5
    ORDER BY c.pedon_key, l.hzn_top"""
    df = q(sql)
    if df.empty:
        print(f'{stn:28s} ({lat:.2f},{lon:.2f}): NO lab pedon within +/-{D} deg'); continue
    df['station'] = stn; df['slat'] = lat; df['slon'] = lon; allrows.append(df)
    peds = df.groupby('pedon_key').agg(date=('site_obsdate', 'first'), usite=('usiteid', 'first'), name=('samp_name', 'first'),
                                       plat=('plat', 'first'), plon=('plon', 'first'), nlay=('labsampnum', 'size'))
    print(f'{stn:28s} ({lat:.2f},{lon:.2f}): {len(peds)} pedon(s)')
    for k, r in peds.iterrows():
        print(f'    pedon {k} date {str(r.date)[:10]} usiteid {r.usite} name {r["name"]} at ({r.plat},{r.plon}) layers in 5-20 cm: {r.nlay}')
if allrows:
    A = pd.concat(allrows); A.to_csv(os.path.join(SO, 'soil_lab_pedons_5_20cm.csv'), index=False)
    print('\nSaved', len(A), 'layer rows')
