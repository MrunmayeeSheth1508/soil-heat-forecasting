import re, sys, io, html
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
t = open(r'C:\Users\jtani\.gemini\antigravity\brain\d895d91a-33a5-49bd-8d56-6a58ee64f9a6\.system_generated\steps\2370\content.md', encoding='utf-8', errors='replace').read()
i = t.find('articleBody'); body = t[i:]
txt = html.unescape(re.sub(r'<[^>]+>', ' ', body)); txt = re.sub(r'\s+', ' ', txt)
for kw in ['bulk density', 'particle size', 'Soil Survey', 'soil core', 'cores', 'porosity', 'calibrat', 'texture', 'available', 'triplicate', 'three probes', 'average']:
    for m in re.finditer(kw, txt, re.I):
        print(f'[{kw}] ...{txt[max(0, m.start() - 300):m.end() + 300]}...\n')
        break
