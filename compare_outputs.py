"""Compare files regenerated in workspace/ (modified after setup) with the shipped originals via workspace_manifest.tsv."""
import os, sys, time, hashlib, json
import numpy as np, pandas as pd
H = os.path.dirname(os.path.abspath(__file__))
since = float(sys.argv[1]) if len(sys.argv) > 1 else 0
man = [l.rstrip('\n').split('\t') for l in open(os.path.join(H, 'workspace_manifest.tsv'), encoding='utf-8') if l.strip()]
seen = set(); rows = []
def h(p): return hashlib.md5(open(p, 'rb').read()).hexdigest()
for ws_rel, repo_rel in man:
    if ws_rel in seen or repo_rel.startswith(('scripts/', 'src/', 'data/', 'literature/')): continue
    seen.add(ws_rel)
    w = os.path.join(H, 'workspace', ws_rel); r = os.path.join(H, repo_rel.replace('/', os.sep))
    if not os.path.exists(w) or os.path.getmtime(w) < since: continue
    if h(w) == h(r): rows.append((ws_rel, 'identical bytes', '')); continue
    note = 'differs'
    if ws_rel.endswith('.csv'):
        try:
            a = pd.read_csv(r); b = pd.read_csv(w)
            if a.shape != b.shape: note = f'shape {a.shape} vs {b.shape}'
            else:
                num = a.select_dtypes('number').columns
                mx = float(np.nanmax(np.abs(a[num].values - b[num].values))) if len(num) else 0.0
                other = all(a[c].equals(b[c]) for c in a.columns if c not in num)
                note = f'max numeric diff {mx:.2e}; non-numeric same {other}'
                if mx < 1e-9 and other: rows.append((ws_rel, 'same values (formatting differs)', note)); continue
        except Exception as e: note = f'csv compare error {e}'
    elif ws_rel.endswith('.txt'):
        a = open(r, encoding='utf-8', errors='replace').read().splitlines(); b = open(w, encoding='utf-8', errors='replace').read().splitlines()
        if a == b: rows.append((ws_rel, 'same text (line endings differ)', '')); continue
        d = sum(1 for x, y in zip(a, b) if x != y) + abs(len(a) - len(b)); note = f'{d} differing lines of {len(a)}'
    rows.append((ws_rel, 'DIFFERENT', note))
out = ['# Regenerated vs shipped outputs', '', '| file | status | detail |', '|---|---|---|'] + [f'| {a} | {b} | {c} |' for a, b, c in sorted(rows)]
open(os.path.join(H, 'stage_output_comparison.md'), 'w', encoding='utf-8').write('\n'.join(out))
print('\n'.join(out))
