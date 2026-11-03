import requests, re, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
B = 'https://www.ncei.noaa.gov/pub/data/uscrn/products/'
r = requests.get(B + 'soil01/', timeout=60)
items = [h for h in re.findall(r'href="([^"?]+)"', r.text) if not h.startswith('SOIL01_')]
print('non-station items in soil01/:', items)
r = requests.get(B + 'soilsip01/', timeout=60)
print('soilsip01 items:', [h for h in re.findall(r'href="([^"?]+)"', r.text)][:30])
for f in [x for x in items if x.lower().startswith(('readme', 'headers')) or x.endswith('.txt')]:
    t = requests.get(B + 'soil01/' + f, timeout=60).text
    print('=====', f, len(t)); print(t[:6000])
t = requests.get(B + 'soil01/SOIL01_AL_Selma_13_WNW.txt', timeout=60).text
print('===== SOIL01_AL_Selma_13_WNW.txt', len(t)); print(t[:5000])
