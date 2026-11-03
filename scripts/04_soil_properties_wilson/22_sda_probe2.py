import requests, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
URL = 'https://sdmdataaccess.sc.egov.usda.gov/Tabular/post.rest'
def q(sql):
    r = requests.post(URL, data={'query': sql, 'format': 'JSON+COLUMNNAME'}, timeout=120)
    try: return r.json().get('Table', [])
    except Exception: return 'ERR ' + r.text[r.text.find('<ServiceException>') + 18:][:200].strip()
print(q("SELECT TOP 2 * FROM lab_combine_nasis_ncss"))
print(q("SELECT TOP 2 * FROM lab_physical_properties"))
print(q("SELECT TOP 2 * FROM lab_layer"))
