import os as _o, sys as _s
_p = _o.path.dirname(_o.path.abspath(__file__))
while not _o.path.exists(_o.path.join(_p, 'src', 'config.py')): _p = _o.path.dirname(_p)
_s.path.insert(0, _o.path.join(_p, 'src'))
from config import WS_ROOT  # PATH-PATCH: was an absolute path to the original working directory
"""Step 1a: archive the frozen pilot outputs with SHA-256 hashes, and build a repro copy of the ORIGINAL pilot script that writes to phase3/repro/
(the original script and its outputs are not modified)."""
import os, shutil, hashlib, re, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
ROOT = WS_ROOT; P3 = os.path.join(ROOT, 'phase3')
A = os.path.join(P3, 'archive_pre_diag'); R = os.path.join(P3, 'repro'); os.makedirs(A, exist_ok=True); os.makedirs(R, exist_ok=True)
files = ['pilotA_out_dev.txt', 'pilotA_out_test.txt', 'pilotA_part1_dev.csv', 'pilotA_part1_test.csv', 'pilotA_part2_dev.csv', 'pilotA_part2_test.csv',
         'pilotA_part3_dev.csv', 'pilotA_part3_test.csv', 'pilotA_b_frozen.json', 'pilotA_prereg.md', 'event_rules.md', 'event_inventory.csv']
man = []
for f in files:
    s = os.path.join(P3, f)
    if not os.path.exists(s): man.append(f'{f}\tMISSING'); continue
    shutil.copy2(s, os.path.join(A, f)); h = hashlib.sha256(open(s, 'rb').read()).hexdigest(); man.append(f'{f}\t{h}\t{os.path.getsize(s)}')
for f in ['40_pilotA_run.py', 'heatsolver.py', '39_pilotA_solver_check.py', '32_event_inventory.py']:
    s = os.path.join(ROOT, f); shutil.copy2(s, os.path.join(A, f)); man.append(f'{f}\t{hashlib.sha256(open(s, "rb").read()).hexdigest()}\t{os.path.getsize(s)}')
open(os.path.join(A, 'MANIFEST.tsv'), 'w').write('\n'.join(man)); print('\n'.join(man))
src = open(os.path.join(ROOT, '40_pilotA_run.py'), encoding='utf8').read()
n0 = src.count("os.path.join(O, f'pilotA_") + src.count("os.path.join(O, 'pilotA_b_frozen.json')")
new = src.replace("os.path.join(O, f'pilotA_", "os.path.join(OUT, f'pilotA_").replace("os.path.join(O, 'pilotA_b_frozen.json')", "os.path.join(OUT, 'pilotA_b_frozen.json')")
new = new.replace("O = os.path.join(ROOT, 'phase3')", "O = os.path.join(ROOT, 'phase3'); OUT = os.path.join(ROOT, 'phase3', 'repro')", 1)
assert "OUT = " in new and n0 >= 6, n0
open(os.path.join(R, 'repro_40_pilotA.py'), 'w', encoding='utf8').write(new); print('output-path replacements:', n0)
