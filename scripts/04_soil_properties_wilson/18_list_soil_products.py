import requests, re
B = 'https://www.ncei.noaa.gov/pub/data/uscrn/products/'
def ls(d, depth=0):
    r = requests.get(B + d, timeout=60)
    items = [h for h in re.findall(r'href="([^"?]+)"', r.text) if not h.startswith(('/', 'http')) and h != '../']
    for h in items:
        print('  ' * depth + d + h)
        if h.endswith('/') and depth < 2: ls(d + h, depth + 1)
for d in ['soil/', 'soil01/', 'soilsip01/']:
    ls(d)
