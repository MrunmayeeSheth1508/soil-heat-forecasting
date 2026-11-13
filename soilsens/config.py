"""Paths and constants."""
import os
from pathlib import Path

PKG_DIR = Path(__file__).resolve().parent
REPO_ROOT = PKG_DIR.parent

DEPTHS_CM = [5, 10, 20, 50, 100]          # USCRN sensor depths (index 0..4)
DEPTHS_M = [d / 100 for d in DEPTHS_CM]
HISTORY_H = 168                            # input window (slides: 168 h)
HORIZON_H = 72                             # forecast horizon (slides: 72 h)


def data_dir() -> Path:
    """USCRN station arrays: <STATION>_<YEAR>.npz with keys date, hour, P, SM(…,5), ST(…,5).

    Override with env var SOILSENS_DATA_DIR. Default is the repo's data/multistation_npz.
    """
    env = os.environ.get("SOILSENS_DATA_DIR")
    if env:
        return Path(env)
    return REPO_ROOT / "data" / "multistation_npz"


def model_dir() -> Path:
    d = Path(os.environ.get("SOILSENS_MODEL_DIR", REPO_ROOT / "models"))
    d.mkdir(parents=True, exist_ok=True)
    return d


def output_dir() -> Path:
    d = Path(os.environ.get("SOILSENS_OUTPUT_DIR", REPO_ROOT / "outputs"))
    d.mkdir(parents=True, exist_ok=True)
    return d

# Climate-diverse default set (the 13 stations of the earlier ampacity runs that are
# present in data/multistation_npz). Used for training unless --stations is given.
DEFAULT_STATIONS = [
    "NM_Socorro_20_N", "NM_Las_Cruces_20_N", "NV_Mercury_3_SSW", "TX_Monahans_6_ENE",
    "CA_Santa_Barbara_11_W", "CA_Bodega_6_WSW", "OR_Riley_10_WSW", "OK_Stillwater_2_W",
    "NE_Lincoln_8_ENE", "AL_Fairhope_3_NE", "NC_Asheville_13_S", "WY_Sundance_8_NNW",
    "MI_Chatham_1_SE",
]
