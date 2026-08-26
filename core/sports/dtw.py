"""Pure NumPy DTW (no C extensions)."""

from __future__ import annotations

import numpy as np


def dtw_distance(a: np.ndarray, b: np.ndarray, window: int | None = None) -> float:
    """Sakoe–Chiba DTW on sequences shaped (T, D)."""
    if a.ndim == 1:
        a = a[:, None]
    if b.ndim == 1:
        b = b[:, None]
    n, m = int(a.shape[0]), int(b.shape[0])
    if n == 0 or m == 0:
        return float("inf")
    band = window if window is not None else max(n, m)
    inf = 1e30
    cost = np.full((n + 1, m + 1), inf, dtype=np.float64)
    cost[0, 0] = 0.0
    for i in range(1, n + 1):
        j0 = max(1, i - band)
        j1 = min(m, i + band)
        ai = a[i - 1]
        for j in range(j0, j1 + 1):
            d = float(np.linalg.norm(ai - b[j - 1]))
            cost[i, j] = d + min(cost[i - 1, j], cost[i, j - 1], cost[i - 1, j - 1])
    return float(cost[n, m])
