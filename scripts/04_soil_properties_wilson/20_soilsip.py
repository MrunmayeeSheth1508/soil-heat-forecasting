import os as _o, sys as _s
_p = _o.path.dirname(_o.path.abspath(__file__))
while not _o.path.exists(_o.path.join(_p, 'src', 'config.py')): _p = _o.path.dirname(_p)
_s.path.insert(0, _o.path.join(_p, 'src'))
from config import WS_ROOT  # PATH-PATCH: was an absolute path to the original working directory
import requests, re, sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
B = 'https://www.ncei.noaa.gov/pub/data/uscrn/products/soilsip01/'
OUT = (WS_ROOT + r'\soilsip')
os.makedirs(OUT, exist_ok=True)
r = requests.get(B, timeout=60)
files = [h for h in re.findall(r'href="([^"?]+)"', r.text) if h.startswith('CRNSIP01_')]
other = [h for h in re.findall(r'href="([^"?]+)"', r.text) if not h.startswith('CRNSIP01_') and h != '../']
print('soilsip01 station files:', len(files), ' other items:', other)
for f in files:
    p = os.path.join(OUT, f)
    if not os.path.exists(p): open(p, 'w', encoding='utf-8').write(requests.get(B + f, timeout=60).text)
t = open(os.path.join(OUT, 'CRNSIP01_AL_Selma_13_WNW.txt'), encoding='utf-8').read()
print('===== Selma file, chars', len(t)); print(t[:7000])
for d in ['https://www.ncei.noaa.gov/pub/data/uscrn/products/previous_docs/', 'https://www.ncei.noaa.gov/pub/data/uscrn/documentation/']:
    try:
        rr = requests.get(d, timeout=60); print('=====', d, [h for h in re.findall(r'href="([^"?]+)"', rr.text) if 'soil' in h.lower() or 'sip' in h.lower()])
    except Exception as e: print(d, e)
