import math
import random
import pytest
from analyses.panel.model import dispersion_by_month, first_differences, relative_log_prices, within_slope


def panel(months, brands, elasticity=-2.0, noise=0.01, seed=1):
    """Shares respond to relative price with a known elasticity; prices random-walk by brand."""
    rnd = random.Random(seed)
    price = {b: 5.0 + 0.3 * i for i, b in enumerate(brands)}
    share = {b: 10.0 for b in brands}
    rows = []
    for m in months:
        for b in brands:
            step = rnd.gauss(0, 0.03)
            price[b] *= math.exp(step)
            share[b] *= math.exp(elasticity * step + rnd.gauss(0, noise))
        rows += [{"month": m, "brand": (b, "x"), "price": price[b], "share_pct": share[b]} for b in brands]
    return rows


MONTHS = [f"{2020 + i // 12}-{i % 12 + 1:02d}" for i in range(48)]


def test_relative_price_is_measured_against_the_share_weighted_market_price():
    rows = [{"month": "2020-01", "brand": ("A", "x"), "price": 5.0, "share_pct": 10.0},
            {"month": "2020-01", "brand": ("B", "x"), "price": 6.0, "share_pct": 30.0}]
    rel = relative_log_prices(rows)
    market = (5 * 10 + 6 * 30) / 40
    assert rel[("2020-01", ("A", "x"))] == pytest.approx(math.log(5 / market))


def test_dispersion_falls_when_prices_converge():
    spread = [{"month": "a", "brand": (b, "x"), "price": p, "share_pct": 10.0} for b, p in [("A", 4.0), ("B", 6.0)]]
    close = [{"month": "b", "brand": (b, "x"), "price": p, "share_pct": 10.0} for b, p in [("A", 4.9), ("B", 5.1)]]
    d = dispersion_by_month(spread + close)
    assert d["a"] > d["b"] > 0


def test_differences_skip_gaps_in_the_calendar():
    rows = [{"month": m, "brand": ("A", "x"), "price": 5.0, "share_pct": 10.0 + i} for i, m in enumerate(["2020-05", "2020-06", "2020-08"])]
    rows += [{"month": m, "brand": ("B", "x"), "price": 5.0, "share_pct": 10.0} for m in ["2020-05", "2020-06", "2020-08"]]
    diffs = first_differences(rows)
    assert {d["month"] for d in diffs} == {"2020-06"}          # July is missing, so August has no previous month


def test_recovers_a_known_elasticity_from_brand_specific_price_moves():
    rows = panel(MONTHS, ["A", "B", "C", "D", "E", "F"], elasticity=-2.0)
    fit = within_slope(first_differences(rows))
    assert fit["slope"] == pytest.approx(-2.0, abs=0.25) and fit["se"] < 0.2 and fit["n"] > 200


def test_longer_differences_compare_months_that_many_apart():
    from analyses.panel.model import differences
    rows = [{"month": m, "brand": (b, "x"), "price": 5.0, "share_pct": 10.0 + i}
            for b in "AB" for i, m in enumerate(["2020-01", "2020-02", "2020-04"])]
    assert {d["month"] for d in differences(rows, lag=1)} == {"2020-02"}
    assert {d["month"] for d in differences(rows, lag=2)} == {"2020-04"}      # Feb -> Apr
