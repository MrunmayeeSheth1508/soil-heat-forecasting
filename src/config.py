"""Central path configuration.

All scripts were written against a flat working directory (`...\\scratch\\soil`, with `raw/`, `phase3/data`,
`phase3/forecast`, ...). `setup_workspace.py` rebuilds exactly that layout under `<repo>/workspace` from the
organised folders, and every script resolves its old absolute root to WS_ROOT below.
Scripts therefore read and write ONLY inside `workspace/`, never over the shipped `results/` or `data/`.

Override the location with the environment variable SOIL_WS_ROOT.
"""
import os
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WS_ROOT = os.environ.get('SOIL_WS_ROOT', os.path.join(REPO_ROOT, 'workspace'))
