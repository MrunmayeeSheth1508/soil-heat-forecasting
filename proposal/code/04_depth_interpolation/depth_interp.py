"""
depth_interp.py — physics-consistent interpolation of USCRN soil
temperature and moisture from measured depths to cable burial depth.

Uses a 1D heat conduction Crank-Nicolson solver with the 50 cm and
100 cm USCRN sensors as Dirichlet boundary conditions, estimating
temperature at any intermediate depth (e.g. 0.82 m for PG&E primary).

References:
  Brunetti et al. (2022) Earth Surf. Dyn. 10(4) — Bayesian α inversion [V]
  Widyastuti et al. (2026) Soil Tillage Res. — differentiable C-N solver [V]
  Bates (2021) Ch 3/11 — SCAN data used at 40" depth for N-M ambient [V]

The Crank-Nicolson solver is unconditionally stable for any dt and dz.

Run from proposal/ root:
    python code/04_depth_interpolation/depth_interp.py
"""
import numpy as np
from scipy.linalg import solve_banded
from pathlib import Path


# ---------------------------------------------------------------------------
# USCRN measurement depths (metres)
# [V uscrn_HEADERS.txt — confirmed 5 depths]
# ---------------------------------------------------------------------------
USCRN_DEPTHS_M = np.array([0.05, 0.10, 0.20, 0.50, 1.00])

# PG&E reference installation cable centre depth [V EDS 038193/062288 + derived]
PGE_CABLE_DEPTH_M = 0.819   # 30" cover + 4.5"/2 OD ≈ 0.819 m


# ---------------------------------------------------------------------------
# Crank-Nicolson solver for 1D heat conduction
# dT/dt = d/dz (alpha(z) * dT/dz)
# ---------------------------------------------------------------------------
def build_cn_matrix(alpha: np.ndarray, dz: float, dt: float):
    """
    Build the tri-diagonal (A, B) matrices for the Crank-Nicolson scheme.
    Interior nodes: A @ T^{n+1} = B @ T^n
    Boundary nodes handled separately (Dirichlet).

    Parameters
    ----------
    alpha : diffusivity at each interior grid node (m²/s)
    dz    : grid spacing (m)
    dt    : time step (s)

    Returns A, B as full square arrays (small N; use banded solver for large).
    """
    N = len(alpha)
    r = alpha * dt / (2.0 * dz**2)   # stability parameter

    A = np.zeros((N, N))
    B = np.zeros((N, N))

    for i in range(N):
        ri = r[i]
        A[i, i] =  1.0 + 2.0 * ri
        B[i, i] =  1.0 - 2.0 * ri
        if i > 0:
            A[i, i-1] = -ri
            B[i, i-1] =  ri
        if i < N - 1:
            A[i, i+1] = -ri
            B[i, i+1] =  ri

    return A, B


def interpolate_to_depth(
    T_50cm: np.ndarray,    # soil temperature at 50 cm (time series, °C)
    T_100cm: np.ndarray,   # soil temperature at 100 cm (time series, °C)
    target_depth_m: float = PGE_CABLE_DEPTH_M,
    alpha_m2_per_s: float = 4.5e-7,   # soil thermal diffusivity (m²/s)
    dz: float = 0.01,                 # grid resolution (m)
    dt_s: float = 3600.0,             # time step (s, = 1 hour for USCRN)
    spin_up_steps: int = 72,          # hours to spin up before reporting
) -> np.ndarray:
    """
    Estimate soil temperature at target_depth_m by running the C-N heat
    conduction solver between the 50 cm and 100 cm boundary conditions.

    Parameters
    ----------
    T_50cm, T_100cm : arrays of length N_timesteps (°C)
    target_depth_m  : depth to interpolate to (m), must be in [0.50, 1.00]
    alpha_m2_per_s  : thermal diffusivity (uniform; Bayesian inversion
                      from Brunetti et al. 2022 will replace this)
    dz, dt_s        : grid spacing and time step

    Returns
    -------
    T_target : temperature at target_depth_m (same length as input, NaN for spin-up)
    """
    assert 0.50 <= target_depth_m <= 1.00, \
        f"target_depth_m={target_depth_m} must be between 0.50 and 1.00 m"
    assert len(T_50cm) == len(T_100cm)

    z_top = 0.50
    z_bot = 1.00
    n_interior = int(round((z_bot - z_top) / dz)) - 1
    z_interior = np.linspace(z_top + dz, z_bot - dz, n_interior)

    # Target index in interior grid
    tgt_idx = int(round((target_depth_m - z_top - dz) / dz))
    tgt_idx = np.clip(tgt_idx, 0, n_interior - 1)

    # Uniform diffusivity profile
    alpha = np.full(n_interior, alpha_m2_per_s)
    A, B = build_cn_matrix(alpha, dz, dt_s)

    # Initial condition: linear interpolation
    T = np.interp(z_interior, [z_top, z_bot], [T_50cm[0], T_100cm[0]])

    N_t = len(T_50cm)
    T_out = np.full(N_t, np.nan)

    for i in range(1, N_t):
        bc_top = T_50cm[i]
        bc_bot = T_100cm[i]
        rhs = B @ T
        # Apply Dirichlet BCs
        r = alpha * dt_s / (2.0 * dz**2)
        rhs[0]  += r[0]  * (bc_top + T_50cm[i-1])
        rhs[-1] += r[-1] * (bc_bot + T_100cm[i-1])
        T = np.linalg.solve(A, rhs)
        if i >= spin_up_steps:
            T_out[i] = T[tgt_idx]

    return T_out


def interpolate_moisture_linear(
    theta_50cm: np.ndarray,
    theta_100cm: np.ndarray,
    target_depth_m: float = PGE_CABLE_DEPTH_M,
) -> np.ndarray:
    """
    Linear interpolation of volumetric moisture content to target depth.
    A simple fallback until a Richards-equation solver is implemented.
    For the 50–100 cm range, moisture gradients are typically small.
    [I — physics-consistent interpolation; Richards equation not yet implemented]
    """
    w = (target_depth_m - 0.50) / (1.00 - 0.50)
    return (1.0 - w) * theta_50cm + w * theta_100cm


# ---------------------------------------------------------------------------
# Self-test with synthetic sinusoidal forcing
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import sys, io
    if hasattr(sys.stdout, 'buffer') and sys.stdout.encoding and sys.stdout.encoding.lower() in ('cp1252', 'ascii'):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    N = 8760   # 1 year of hourly data
    t = np.arange(N)
    # Synthetic: surface drives annual cycle; 100 cm lags and damps
    T_50  = 15.0 + 10.0 * np.sin(2.0 * np.pi * t / 8760 - np.pi/2)
    T_100 = 15.0 +  6.0 * np.sin(2.0 * np.pi * t / 8760 - np.pi)

    T_82 = interpolate_to_depth(T_50, T_100, target_depth_m=0.82,
                                 spin_up_steps=168)

    out_dir = Path(__file__).resolve().parents[2] / "results" / "depth_interp"
    out_dir.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(t, T_50,  label="50 cm (USCRN)", alpha=0.8)
    ax.plot(t, T_100, label="100 cm (USCRN)", alpha=0.8)
    ax.plot(t, T_82,  label="82 cm (interpolated → cable depth)", lw=2)
    ax.set_xlabel("Hour of year")
    ax.set_ylabel("Soil temperature (°C)")
    ax.set_title("Depth interpolation: 50 cm + 100 cm → 82 cm (PG&E cable centre)")
    ax.legend()
    fig.tight_layout()
    fig.savefig(out_dir / "depth_interp_demo.png", dpi=120)
    print(f"Figure saved to {out_dir}/depth_interp_demo.png")

    valid = T_82[~np.isnan(T_82)]
    print(f"T @ 82 cm: mean={valid.mean():.2f}°C  min={valid.min():.2f}°C  "
          f"max={valid.max():.2f}°C")
    print(f"T @ 50 cm: mean={T_50.mean():.2f}°C")
    print(f"T @ 100cm: mean={T_100.mean():.2f}°C")
    print("Expected: 82 cm should be between 50 and 100 cm values, "
          "closer to 100 cm (deeper → more damped).")
