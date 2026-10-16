import math
import random
from datetime import date
import pytest
from analyses.taxshock.model import forced_relative_change, placebo_effects, shock_regression
from tabacos.tax import TaxRate

OLD = TaxRate("cigarrillos", date(2016, 12, 3), 51, 24.7, 131.5, 141.0, 196.0, "x")
NEW = TaxRate("cigarrillos", date(2025, 1, 1), 48.5, 33.5, 150.0, None, None, "y")
PRICES = {f"B{i}": 4.2 + 0.3 * i for i in range(8)}          # 4.2 .. 6.3


def months(start, n):
    y, m = map(int, start.split("-"))
    return [f"{y + (m - 1 + i) // 12}-{(m - 1 + i) % 12 + 1:02d}" for i in range(n)]


def build(elasticity, noise=0.01, seed=3):
    """Shares move with the forced price shock at the event month (index 24) and by noise elsewhere."""
    rnd = random.Random(seed)
    forced = forced_relative_change(_rows(["x"], {b: p for b, p in PRICES.items()}, {b: 10.0 for b in PRICES}), OLD, NEW, 21)
    rows, ms = [], months("2023-01", 40)
    for i, m in enumerate(ms):
        for b, p in PRICES.items():
            after = i >= 24
            price = p * math.exp(forced[b] * after)                       # pass-through of the forced relative change
            share = 10.0 * math.exp(elasticity * forced[b] * after + rnd.gauss(0, noise))
            rows.append({"month": m, "brand": b, "price": price, "share_pct": share})
    return rows, ms


def _rows(ms, prices, shares):
    return [{"month": m, "brand": b, "price": prices[b], "share_pct": shares[b]} for m in ms for b in prices]


def test_forced_change_is_bigger_for_cheap_packs_and_centred_on_the_market():
    forced = forced_relative_change(_rows(["x"], PRICES, {b: 10.0 for b in PRICES}), OLD, NEW, 21)
    assert forced["B0"] > forced["B7"]                                     # cheap packs rise most
    assert sum(forced.values()) / len(forced) == pytest.approx(0.0, abs=1e-12)   # equal shares: mean zero


def test_recovers_a_known_elasticity_from_the_tax_forced_shock():
    rows, ms = build(elasticity=-2.0)
    reg = shock_regression(rows, pre=ms[21:23], post=ms[26:29], forced=forced_relative_change(
        [r for r in rows if r["month"] == ms[22]], OLD, NEW, 21))
    assert reg["reduced_form"] == pytest.approx(-2.0, abs=0.3)
    assert reg["first_stage"] == pytest.approx(1.0, abs=0.05)
    assert reg["iv"] == pytest.approx(-2.0, abs=0.3)


def test_placebo_windows_show_no_effect_when_there_is_none():
    rows, ms = build(elasticity=0.0, noise=0.0005)
    effects = placebo_effects(rows, OLD, NEW, 21, event_month=ms[24], pre_offsets=(-3, -2), post_offsets=(2, 3, 4), exclude=7)
    assert len(effects) >= 5 and all(abs(e["reduced_form"]) < 0.5 for e in effects)


def test_trimming_drops_brands_whose_share_jumped_like_a_list_artefact():
    rows, ms = build(elasticity=-2.0, noise=0.0005)
    for r in rows:                                          # one brand drops out of the list after the event
        if r["brand"] == "B3" and r["month"] >= ms[26]:
            r["share_pct"] *= 0.2
    forced = forced_relative_change([r for r in rows if r["month"] == ms[22]], OLD, NEW, 21)
    full = shock_regression(rows, ms[21:23], ms[26:29], forced)
    trimmed = shock_regression(rows, ms[21:23], ms[26:29], forced, trim=0.5)
    assert trimmed["n"] == full["n"] - 1
    assert trimmed["reduced_form"] == pytest.approx(-2.0, abs=0.3) and abs(full["reduced_form"] + 2.0) > 0.3
