import os as _o, sys as _s
_p = _o.path.dirname(_o.path.abspath(__file__))
while not _o.path.exists(_o.path.join(_p, 'src', 'config.py')): _p = _o.path.dirname(_p)
_s.path.insert(0, _o.path.join(_p, 'src'))
from config import WS_ROOT  # PATH-PATCH: was an absolute path to the original working directory
import requests, sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
URL = 'https://sdmdataaccess.sc.egov.usda.gov/Tabular/post.rest'
SO = WS_ROOT
def q(sql):
    r = requests.post(URL, data={'query': sql, 'format': 'JSON+COLUMNNAME'}, timeout=180)
    try: return r.json().get('Table', [])
    except Exception: return 'ERR ' + r.text[r.text.find('<ServiceException>') + 18:][:300].strip()
for tb in ['lab_combine_nasis_ncss', 'lab_site', 'lab_pedon', 'lab_area']:
    t = q(f'SELECT TOP 1 * FROM {tb}')
    print(tb, t[0] if isinstance(t, list) and t else t)
# projects mentioning climate reference
print(q("SELECT TOP 40 project_key, project_name FROM lab_combine_nasis_ncss WHERE project_name LIKE '%limate%' OR project_name LIKE '%CRN%' GROUP BY project_key, project_name"))
st = requests.get('https://www.ncei.noaa.gov/pub/data/uscrn/products/stations.tsv', timeout=60).text
open(os.path.join(SO, 'stations.tsv'), 'w', encoding='utf-8').write(st)
print(st[:800])
