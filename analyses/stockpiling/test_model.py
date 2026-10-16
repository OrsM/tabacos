import pytest
from analyses.stockpiling.model import swings


def series(years, growth=0.02, base=100.0, bump=None):
    """Flat seasonal-free monthly packs growing yearly; bump = {(year, month): multiplier}."""
    bump = bump or {}
    return {(y, m): base * (1 + growth) ** (y - years[0]) * bump.get((y, m), 1.0) for y in years for m in range(1, 13)}


def test_recovers_a_known_pull_forward():
    packs = series(range(2020, 2027), bump={(2024, 12): 1.10, (2025, 1): 0.90})
    rows = {r["year"]: r for r in swings(packs, pre_month=12, post_month=1, event_year=2025)}
    assert rows[2025]["is_event"] and not rows[2023]["is_event"]
    assert rows[2025]["pre_yoy"] == pytest.approx(1.02 * 1.10 - 1)          # +12.2% on a 2% growth base
    assert rows[2025]["post_yoy"] == pytest.approx(1.02 * 0.90 - 1)         # -8.2%
    assert rows[2025]["swing"] == pytest.approx(0.204, abs=1e-9)
    assert rows[2025]["net_yoy"] == pytest.approx((1.02**4 * 1.10 + 1.02**5 * 0.90) / (1.02**3 + 1.02**4) - 1)   # ~ trend: the bump nets out
    assert rows[2023]["swing"] == pytest.approx(0.0, abs=1e-12)             # placebo year


def test_the_year_after_the_event_shows_the_base_effect():
    packs = series(range(2020, 2027), bump={(2024, 12): 1.10, (2025, 1): 0.90})
    rows = {r["year"]: r for r in swings(packs, 12, 1, 2025)}
    assert rows[2026]["swing"] < -0.15 and rows[2026]["after_event"]


def test_years_with_missing_months_are_skipped():
    packs = series(range(2020, 2025))
    del packs[(2023, 1)]
    assert 2023 not in [r["year"] for r in swings(packs, 12, 1, 2025)]


def test_per_day_adjustment_removes_a_calendar_effect():
    days = {(y, m): 20 for y in range(2020, 2027) for m in range(1, 13)}
    days[(2025, 1)] = 22                                   # January 2025 has two more trading days
    packs = {k: 5.0 * d for k, d in days.items()}           # sales proportional to trading days, no event
    raw = {r["year"]: r for r in swings(packs, 12, 1, 2025)}
    adj = {r["year"]: r for r in swings(packs, 12, 1, 2025, days=days)}
    assert raw[2025]["swing"] == pytest.approx(-0.10)       # looks like a January boom
    assert adj[2025]["swing"] == pytest.approx(0.0, abs=1e-12)


def test_calendar_noise_is_lower_when_the_day_count_explains_the_months():
    from analyses.stockpiling.model import yoy_noise
    days = {(y, m): 18 + (3 * y + m) % 5 for y in range(2021, 2025) for m in range(1, 13)}
    packs = {k: 7.0 * d for k, d in days.items()}                      # sales follow trading days exactly
    assert yoy_noise(packs, days) == pytest.approx(0.0, abs=1e-12)
    assert yoy_noise(packs, None) > 0.02                                # raw packs carry the calendar noise
