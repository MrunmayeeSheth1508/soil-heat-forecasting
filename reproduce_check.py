"""Reproducibility check: rerun inventory + scoring inside workspace/, compare with shipped results/06_forecast_benchmark."""
import os, sys, subprocess, time
import numpy as np, pandas as pd
H = os.path.dirname(os.path.abspath(__file__)); os.chdir(H)
env = dict(os.environ, PYTHONIOENCODING='utf-8')
t0 = time.time()
for s in (() if '--compare-only' in sys.argv else ('54_forecast_inventory.py', '56_forecast_scores.py')):
    r = subprocess.run([sys.executable, os.path.join('scripts', '08_forecast_benchmark', s)], env=env, capture_output=True, text=True)
    print(s, 'exit', r.returncode, f'{time.time()-t0:.0f}s'); 
    if r.returncode: print(r.stderr[-1500:]); sys.exit(1)
ref = os.path.join(H, 'results', '06_forecast_benchmark'); new = os.path.join(H, 'workspace', 'phase3', 'forecast')
ok = True
for f in ('issue_inventory.csv', 'forecast_scores.csv'):
    a = pd.read_csv(os.path.join(ref, f)); b = pd.read_csv(os.path.join(new, f))
    same_shape = a.shape == b.shape
    num = a.select_dtypes('number').columns
    mx = float(np.nanmax(np.abs(a[num].values - b[num].values))) if same_shape else float('nan')
    eq_obj = all(a[c].equals(b[c]) for c in a.columns if c not in num) if same_shape else False
    print(f, 'shape', a.shape, b.shape, 'max |numeric diff|', mx, 'non-numeric identical', eq_obj)
    ok &= same_shape and mx < 1e-9 and eq_obj
print('REPRODUCED EXACTLY' if ok else 'DIFFERENCES FOUND')
