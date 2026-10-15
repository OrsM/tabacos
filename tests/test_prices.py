from pathlib import Path
import pytest
from tabacos.prices import parse_prices

FIX = Path(__file__).parent / "fixtures"


def load(name):
    return {(f.product, f.period): f.price for f in parse_prices((FIX / name).read_text())}


def test_current_layout_annual_then_months_of_the_new_year():
    p = load("precios-2025-06.raw.txt")
    assert p[("cigarrillos", "2024")] == 5.07
    assert p[("liar", "2025-02")] == 4.43      # header says "febr-25"
    assert p[("pipa", "2025-06")] == 5.40
    assert len(p) == 3 * (14 + 6)


def test_month_label_typo_is_resolved_by_position():
    p = load("precios-2024-10.raw.txt")
    assert p[("cigarrillos", "2024-07")] == 5.07   # header says "Ju-24"
    assert p[("cigarrillos", "2024-06")] == 4.61   # as published
    assert len(p) == 3 * (13 + 10)


def test_oldest_layout_values_split_across_lines():
    p = load("precios-2024-04.raw.txt")
    assert p[("cigarrillos", "2011")] == 3.76      # printed "3,7" / "6"
    assert p[("pipa", "2024-04")] == 3.65
    assert len(p) == 3 * (13 + 4)


def test_label_value_count_mismatch_raises():
    text = (FIX / "precios-2025-06.raw.txt").read_text().replace("\n5,37\n", "\n", 1)
    with pytest.raises(ValueError):
        parse_prices(text)


def test_merge_keeps_union_and_rejects_reports_that_disagree():
    from tabacos.prices import AvgPrice, merge_prices
    a = [AvgPrice("liar", "2024", 4.12), AvgPrice("liar", "2025-01", 4.39)]
    b = [AvgPrice("liar", "2024", 4.12), AvgPrice("liar", "2025-02", 4.43)]
    assert {(f.period) for f in merge_prices([a, b])} == {"2024", "2025-01", "2025-02"}
    with pytest.raises(ValueError):
        merge_prices([a, [AvgPrice("liar", "2024", 4.99)]])
