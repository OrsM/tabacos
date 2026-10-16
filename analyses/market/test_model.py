import math
import random
import numpy as np
import pytest
from analyses.market.model import chain_price_index, fit_hac, design_matrix, circular_shift_placebo


def test_chain_index_follows_prices_of_brands_listed_in_both_months_and_ignores_entrants():
    rows = [{"month": "2024-01", "brand": "A", "price": 5.0, "share_pct": 10},
            {"month": "2024-01", "brand": "B", "price": 4.0, "share_pct": 10},
            {"month": "2024-02", "brand": "A", "price": 5.5, "share_pct": 10},
            {"month": "2024-02", "brand": "B", "price": 4.4, "share_pct": 10},
            {"month": "2024-02", "brand": "C", "price": 9.0, "share_pct": 10}]          # entrant at a high price: no effect
    idx = chain_price_index(rows)
    assert idx["2024-01"] == pytest.approx(1.0)
    assert idx["2024-02"] == pytest.approx(1.10)


def test_chain_index_spans_a_missing_month():
    rows = [{"month": m, "brand": "A", "price": p, "share_pct": 10} for m, p in [("2024-06", 5.0), ("2024-08", 5.5)]]
    assert chain_price_index(rows)["2024-08"] == pytest.approx(1.10)


def test_hac_fit_returns_coefficients_and_a_wider_se_for_autocorrelated_errors():
    rnd = np.random.default_rng(1)
    n = 120
    x = np.cumsum(rnd.normal(size=n)) * 0.1
    e = np.zeros(n)
    for t in range(1, n):
        e[t] = 0.8 * e[t - 1] + rnd.normal(scale=0.05)
    y = 1.0 - 0.5 * x + e
    X = np.column_stack([np.ones(n), x])
    fit = fit_hac(y, X, lags=6)
    naive = np.sqrt(np.diag(np.linalg.inv(X.T @ X)) * np.var(y - X @ fit["beta"], ddof=2))
    assert fit["beta"][1] == pytest.approx(-0.5, abs=0.2)
    assert fit["se"][1] > naive[1]


def simulate(elasticity, n=96, seed=2, trend=-0.002, noise=0.01):
    """Monthly log volume per day = trend + season + elasticity * log price; price steps up at three dates."""
    rnd = random.Random(seed)
    logp = []
    p = 0.0
    for t in range(n):
        if t in (30, 55, 80):
            p += 0.06
        logp.append(p + rnd.gauss(0, 0.002))
    season = [0.05 * math.sin(2 * math.pi * (t % 12) / 12) for t in range(n)]
    y = [trend * t + season[t] + elasticity * logp[t] + rnd.gauss(0, noise) for t in range(n)]
    return np.array(y), np.array(logp)


def test_recovers_a_known_elasticity_with_trend_and_season_controls():
    y, logp = simulate(-0.6)
    X = design_matrix(logp, month_of_year=[t % 12 + 1 for t in range(len(y))], trend="linear")
    fit = fit_hac(y, X, lags=6)
    assert fit["beta"][1] == pytest.approx(-0.6, abs=0.15)           # column 1 is log price


def test_placebo_shifts_do_not_find_an_effect_when_the_true_effect_is_zero():
    y, logp = simulate(0.0, seed=5)
    moy = [t % 12 + 1 for t in range(len(y))]
    draws = circular_shift_placebo(y, logp, moy, trend="linear", lags=6, min_shift=12)
    actual = fit_hac(y, design_matrix(logp, moy, "linear"), 6)["beta"][1]
    assert len(draws) >= 40 and abs(actual) < 0.3
    assert sum(abs(d) >= abs(actual) for d in draws) / len(draws) > 0.1


def test_design_matrix_leaves_out_columns_that_are_all_zero_such_as_a_month_with_no_report():
    moy = [m for m in list(range(1, 7)) + list(range(8, 13)) for _ in (0, 1)]            # no July
    logp = np.linspace(0, 1, len(moy)) ** 2                  # not collinear with the linear trend
    X = design_matrix(logp, moy, "linear")
    assert np.linalg.matrix_rank(X) == X.shape[1]
    assert np.allclose(X[:, 1], logp)                    # log price stays column 1
