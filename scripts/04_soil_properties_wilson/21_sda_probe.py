import requests, json, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
URL = 'https://sdmdataaccess.sc.egov.usda.gov/Tabular/post.rest'
def q(sql):
    r = requests.post(URL, data={'query': sql, 'format': 'JSON+COLUMNNAME'}, timeout=120)
    try: return r.json().get('Table', [])
    except Exception: print('ERR', r.status_code, r.text[:400]); return []
# do lab tables exist?
t = q("SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME LIKE 'lab%'")
print('lab tables:', [x[0] for x in t[1:]] if t else t)
for tb in ['lab_combine_nasis_ncss', 'lab_layer', 'lab_physical_properties', 'lab_site']:
    c = q(f"SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME='{tb}'")
    print(tb, [x[0] for x in c[1:]][:80] if c else c)
