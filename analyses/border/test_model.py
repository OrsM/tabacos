import pytest
from analyses.border.model import group_series


def row(area, end, national, tourist, months=1):
    return {"area": area, "period_end": end, "national": national, "tourist": tourist, "months": months}


def test_group_series_sums_the_provinces_of_a_group_per_period():
    rows = [row("Girona", "2024-01-31", 10, 40), row("Navarra", "2024-01-31", 5, 20),
            row("Girona", "2024-02-29", 12, 44), row("Navarra", "2024-02-29", 6, 21),
            row("Huesca", "2024-01-31", 99, 99)]                                # not in the group
    got = group_series(rows, ["Girona", "Navarra"])
    assert [(g["end"], g["national"], g["tourist"], g["months"]) for g in got] == [("2024-01", 15, 60, 1), ("2024-02", 18, 65, 1)]


def test_group_series_drops_a_period_where_a_province_is_missing():
    rows = [row("Girona", "2024-01-31", 10, 40), row("Navarra", "2024-01-31", 5, 20), row("Girona", "2024-02-29", 12, 44)]
    assert [g["end"] for g in group_series(rows, ["Girona", "Navarra"])] == ["2024-01"]


def test_group_series_keeps_the_months_covered_of_a_two_month_report():
    rows = [row("Girona", "2024-08-31", 20, 80, months=2), row("Navarra", "2024-08-31", 10, 40, months=2)]
    assert group_series(rows, ["Girona", "Navarra"])[0]["months"] == 2
