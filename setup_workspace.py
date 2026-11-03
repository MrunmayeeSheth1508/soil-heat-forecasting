"""Rebuild the original flat working layout under ./workspace from the organised repo folders.

    python setup_workspace.py            # build (idempotent)
    python setup_workspace.py --clean    # delete workspace first

Code, specs and result files are COPIED (so re-running a script can never overwrite the shipped reference
results). Files under data/ are HARD-LINKED when possible (no extra disk space; treat as read-only) and copied
otherwise. Layout is defined by workspace_manifest.tsv (workspace-relative path <TAB> repo-relative path).
"""
import os, sys, shutil
HERE = os.path.dirname(os.path.abspath(__file__))
WS = os.environ.get('SOIL_WS_ROOT', os.path.join(HERE, 'workspace'))
if '--clean' in sys.argv and os.path.exists(WS): shutil.rmtree(WS)
n_copy = n_link = n_skip = 0
for line in open(os.path.join(HERE, 'workspace_manifest.tsv'), encoding='utf-8'):
    line = line.rstrip('\n')
    if not line: continue
    ws_rel, repo_rel = line.split('\t')
    dst = os.path.join(WS, ws_rel); src = os.path.join(HERE, repo_rel.replace('/', os.sep))
    if os.path.exists(dst): n_skip += 1; continue
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    if repo_rel.startswith('data/'):
        try: os.link(src, dst); n_link += 1; continue
        except OSError: pass
    shutil.copy2(src, dst); n_copy += 1
for d in ('phase3/forecast', 'phase3/lit', 'phase3/repro', 'phase3/data'):
    os.makedirs(os.path.join(WS, d.replace('/', os.sep)), exist_ok=True)
print(f'workspace: {WS}\n copied {n_copy}, hard-linked {n_link}, already present {n_skip}')
