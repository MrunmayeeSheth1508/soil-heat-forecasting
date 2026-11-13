"""Live mode: run the trained models from the full Phase 2 backend instead of reading
precomputed forecasts. Used automatically when the backend package (soilsens/), its
trained models and numpy/pandas/scikit-learn/torch are all importable, e.g. in GitHub
Codespaces with this folder inside the repo. On a locked-down laptop this quietly stays off.
"""
from __future__ import annotations

import math
import os
import sys

from . import core

STATE = {"enabled": False, "reason": "not checked", "requested": False}


def enable(requested=True):
    STATE["requested"] = requested
    if not requested:
        STATE.update(enabled=False, reason="off (use --live to turn on)")
        return STATE
    # the backend lives one level up when this folder sits inside the repo
    for cand in (core.ROOT.parent, core.ROOT.parent.parent, os.environ.get("SOILSENS_BACKEND", "")):
        if cand and (os.path.isdir(os.path.join(str(cand), "soilsens"))):
            sys.path.insert(0, str(cand))
            break
    try:
        from soilsens.forecast import base, gbt, gru  # noqa: F401
        from soilsens import config
        missing = [p.name for p in (config.model_dir() / "gbt_stage3.joblib", config.model_dir() / "gru.pt")
                   if not p.exists()]
        if missing:
            raise FileNotFoundError("trained models missing: " + ", ".join(missing))
        if not gru.HAVE_TORCH:
            raise ImportError("torch not installed")
        STATE.update(enabled=True, reason=f"backend at {config.REPO_ROOT}, models in {config.model_dir()}")
    except Exception as e:  # blocked DLLs, missing packages, no backend folder ...
        STATE.update(enabled=False, reason=f"{type(e).__name__}: {e}")
    return STATE


def forecast(name, issue, method, stage):
    """Returns (T, M) as lists of 72 x 5, computed live by the backend."""
    from soilsens.forecast.base import get_forecast
    fc = get_forecast(name, issue, method, stage, with_truth=False)
    conv = lambda a: [[float(v) if math.isfinite(v) else core.NAN for v in row] for row in a]
    return conv(fc.temp), conv(fc.moist)
