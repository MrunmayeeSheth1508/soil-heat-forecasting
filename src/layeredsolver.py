"""Conservative layered heat-conduction solver: C(z) dT/dt = d/dz( k(z) dT/dz ), k and volumetric heat capacity C specified separately.
Node-centred finite volume on a uniform node grid; element conductivity is the series (harmonic) combination of the layers an element spans,
element heat capacity is thickness-weighted; node heat capacity = mean of its two adjacent elements. Crank-Nicolson, Dirichlet at both ends.
Temperature and flux continuity at interfaces hold by construction (the same element flux enters one control volume and leaves the next).
In the uniform limit the coefficients equal those of heatsolver.py exactly (r = alpha dt / (2 dz^2))."""
import numpy as np
from numba import njit

def element_properties(z, interfaces, k_layers, C_layers):
    """z: node depths (m). interfaces: depths of layer boundaries (len = nlayers-1). Returns k_e (n-1), C_e (n-1)."""
    edges = np.concatenate([[-np.inf], np.asarray(interfaces, float), [np.inf]])
    ke = np.empty(len(z) - 1); Ce = np.empty(len(z) - 1)
    for e in range(len(z) - 1):
        a, b = z[e], z[e + 1]; res = 0.0; cap = 0.0
        for j in range(len(k_layers)):
            lo, hi = max(a, edges[j]), min(b, edges[j + 1])
            f = max(hi - lo, 0.0) / (b - a)
            if f > 0: res += f / k_layers[j]; cap += f * C_layers[j]
        ke[e] = 1.0 / res; Ce[e] = cap
    return ke, Ce

@njit(cache=True)
def _cn_layered(ke, Ce, tb_top, tb_bot, T0, dz, dt):
    n_steps = tb_top.shape[0]; N = T0.shape[0]
    out = np.empty((n_steps, N)); out[0, :] = T0
    m = N - 2
    bm = np.empty(m); bp = np.empty(m)
    for i in range(m):
        j = i + 1
        Cn = 0.5 * (Ce[j - 1] + Ce[j])
        bm[i] = ke[j - 1] / (Cn * dz * dz); bp[i] = ke[j] / (Cn * dz * dz)   # beta minus / plus
    a = np.empty(m); b = np.empty(m); c = np.empty(m); d = np.empty(m); cp = np.empty(m); dp = np.empty(m); x = np.empty(m)
    for s in range(1, n_steps):
        Tt = tb_top[s]; Tb = tb_bot[s]
        for i in range(m):
            j = i + 1
            a[i] = -0.5 * dt * bm[i]; c[i] = -0.5 * dt * bp[i]; b[i] = 1.0 + 0.5 * dt * (bm[i] + bp[i])
            d[i] = out[s - 1, j] + 0.5 * dt * (bp[i] * (out[s - 1, j + 1] - out[s - 1, j]) - bm[i] * (out[s - 1, j] - out[s - 1, j - 1]))
        d[0] += 0.5 * dt * bm[0] * Tt; d[m - 1] += 0.5 * dt * bp[m - 1] * Tb
        cp[0] = c[0] / b[0]; dp[0] = d[0] / b[0]
        for i in range(1, m):
            den = b[i] - a[i] * cp[i - 1]; cp[i] = c[i] / den; dp[i] = (d[i] - a[i] * dp[i - 1]) / den
        x[m - 1] = dp[m - 1]
        for i in range(m - 2, -1, -1): x[i] = dp[i] - cp[i] * x[i + 1]
        out[s, 0] = Tt; out[s, N - 1] = Tb
        for i in range(m): out[s, i + 1] = x[i]
    return out

def simulate_layered(z, interfaces, k_layers, C_layers, tb_top, tb_bot, T0, dt=3600.0):
    ke, Ce = element_properties(z, interfaces, k_layers, C_layers)
    dz = z[1] - z[0]
    return _cn_layered(ke, Ce, np.ascontiguousarray(tb_top, float), np.ascontiguousarray(tb_bot, float), np.ascontiguousarray(T0, float), float(dz), float(dt)), ke, Ce

def element_fluxes(sim_row, ke, dz):
    """downward-positive conductive flux magnitude k dT/dz at element midpoints (W/m2 sign: -k dT/dz, upward-positive convention avoided; returns k*(T[i+1]-T[i])/dz)"""
    return ke * (sim_row[1:] - sim_row[:-1]) / dz
