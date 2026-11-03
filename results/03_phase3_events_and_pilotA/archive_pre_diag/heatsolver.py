"""Uniform-diffusivity 1-D heat solver for the 5-100 cm column (Crank-Nicolson, Dirichlet boundaries from observations)."""
import numpy as np
from numba import njit
from scipy.interpolate import PchipInterpolator

@njit(cache=True)
def _cn(alpha, tb_top, tb_bot, T0, dz, dt):
    n_steps = tb_top.shape[0]; N = T0.shape[0]
    out = np.empty((n_steps, N)); out[0, :] = T0
    r = alpha * dt / (2.0 * dz * dz)
    a = np.empty(N); b = np.empty(N); c = np.empty(N); d = np.empty(N)
    cp = np.empty(N); dp = np.empty(N)
    T = T0.copy()
    for s in range(1, n_steps):
        T[0] = tb_top[s]; T[N - 1] = tb_bot[s]
        # interior system for i = 1..N-2
        m = N - 2
        for i in range(m):
            j = i + 1
            a[i] = -r; b[i] = 1.0 + 2.0 * r; c[i] = -r
            d[i] = r * out[s - 1, j - 1] + (1.0 - 2.0 * r) * out[s - 1, j] + r * out[s - 1, j + 1]
        d[0] += r * T[0]; d[m - 1] += r * T[N - 1]
        cp[0] = c[0] / b[0]; dp[0] = d[0] / b[0]
        for i in range(1, m):
            den = b[i] - a[i] * cp[i - 1]
            cp[i] = c[i] / den; dp[i] = (d[i] - a[i] * dp[i - 1]) / den
        x = np.empty(m); x[m - 1] = dp[m - 1]
        for i in range(m - 2, -1, -1): x[i] = dp[i] - cp[i] * x[i + 1]
        out[s, 0] = T[0]; out[s, N - 1] = T[N - 1]
        for i in range(m): out[s, i + 1] = x[i]
    return out

def make_grid(z_top=0.05, z_bot=1.0, nint=38):
    z = np.linspace(z_top, z_bot, nint + 1); return z, z[1] - z[0]

def init_profile(z, z_obs, T_obs):
    return PchipInterpolator(z_obs, T_obs)(z)

def simulate(alpha, tb_top, tb_bot, z, T0, dt=3600.0):
    dz = z[1] - z[0]
    return _cn(float(alpha), np.ascontiguousarray(tb_top, float), np.ascontiguousarray(tb_bot, float), np.ascontiguousarray(T0, float), float(dz), float(dt))

def sample(sim, z, z_eval):
    """linear interpolation along depth at each time -> (n_steps, len(z_eval))"""
    idx = np.clip(np.searchsorted(z, z_eval) - 1, 0, len(z) - 2)
    w = (np.array(z_eval) - z[idx]) / (z[idx + 1] - z[idx])
    return sim[:, idx] * (1 - w) + sim[:, idx + 1] * w
