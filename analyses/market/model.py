"""Market-level volume against a price index: regression pieces, with HAC errors and a circular-shift placebo."""
import math
from collections import defaultdict

import numpy as np


def chain_price_index(rows: list[dict]) -> dict[str, float]:
    """Chain-linked price index of the listed brands: each step uses the brands listed in both months,
    weighted by their average share (a Tornqvist index), so brands entering or leaving the list do not move it.
    A gap in the calendar (no July report) is bridged with one step between the months that exist."""
    by_month = defaultdict(dict)
    for r in rows:
        by_month[r["month"]][r["brand"]] = r
    months = sorted(by_month)
    index = {months[0]: 1.0}
    for prev, cur in zip(months, months[1:]):
        common = by_month[prev].keys() & by_month[cur].keys()
        w = {b: (by_month[prev][b]["share_pct"] + by_month[cur][b]["share_pct"]) / 2 for b in common}
        total = sum(w.values())
        step = sum(w[b] / total * (math.log(by_month[cur][b]["price"]) - math.log(by_month[prev][b]["price"])) for b in common)
        index[cur] = index[prev] * math.exp(step)
    return index


def fit_hac(y, X, lags: int) -> dict:
    """OLS with Newey-West (Bartlett) heteroskedasticity- and autocorrelation-consistent standard errors."""
    y, X = np.asarray(y, float), np.asarray(X, float)
    n, k = X.shape
    xtx_inv = np.linalg.inv(X.T @ X)
    beta = xtx_inv @ X.T @ y
    e = y - X @ beta
    u = X * e[:, None]
    s = u.T @ u
    for lag in range(1, lags + 1):
        g = u[lag:].T @ u[:-lag]
        s += (1 - lag / (lags + 1)) * (g + g.T)
    cov = xtx_inv @ s @ xtx_inv
    r2 = 1 - (e @ e) / ((y - y.mean()) @ (y - y.mean()))
    return {"beta": beta, "se": np.sqrt(np.diag(cov)), "r2": float(r2), "n": n}


def design_matrix(logp, month_of_year, trend: str, time=None, extras=None) -> np.ndarray:
    """Columns: constant, log price (column 1), month-of-year dummies (January is the base), trend terms, extras."""
    n = len(logp)
    t = np.arange(n, dtype=float) if time is None else np.asarray(time, float)
    t = (t - t.mean()) / (t.std() or 1.0)
    cols = [np.ones(n), np.asarray(logp, float)]
    moy = np.asarray(month_of_year)
    cols += [(moy == m).astype(float) for m in range(2, 13)]
    degree = {"none": 0, "linear": 1, "quadratic": 2, "cubic": 3}[trend]
    cols += [t ** d for d in range(1, degree + 1)]
    for e in extras or []:
        cols.append(np.asarray(e, float))
    keep = [c for i, c in enumerate(cols) if i < 2 or np.any(c != 0)]       # e.g. no July report: no July dummy
    return np.column_stack(keep)


def circular_shift_placebo(y, logp, month_of_year, trend: str, lags: int, min_shift: int, time=None, extras=None) -> list[float]:
    """The price coefficient when the price series is rotated against the volume series by `min_shift` or more
    months in either direction. A rotated series keeps the price path's shape and autocorrelation but not its timing."""
    n = len(y)
    out = []
    for shift in range(min_shift, n - min_shift + 1):
        shifted = np.roll(np.asarray(logp, float), shift)
        out.append(float(fit_hac(y, design_matrix(shifted, month_of_year, trend, time, extras), lags)["beta"][1]))
    return out
