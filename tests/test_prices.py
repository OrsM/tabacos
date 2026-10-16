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


def test_merge_keeps_union_and_lets_the_newer_report_revise_an_older_one():
    from tabacos.prices import AvgPrice, merge_prices
    a = [AvgPrice("liar", "2024", 4.12), AvgPrice("liar", "2025-01", 4.39)]
    b = [AvgPrice("liar", "2024", 4.12), AvgPrice("liar", "2025-01", 4.40), AvgPrice("liar", "2025-02", 4.43)]
    prices, revisions = merge_prices([("jan.pdf", a), ("feb.pdf", b)])
    assert {(f.period, f.price) for f in prices} == {("2024", 4.12), ("2025-01", 4.40), ("2025-02", 4.43)}
    assert [(r.period, r.old, r.new, r.old_source, r.new_source) for r in revisions] == [
        ("2025-01", 4.39, 4.40, "jan.pdf", "feb.pdf")]


def test_report_without_price_table_raises_table_not_found():
    from tabacos.errors import TableNotFound
    with pytest.raises(TableNotFound):
        parse_prices("INFORME MENSUAL\nsin tabla\n")


@pytest.mark.parametrize("name, labels, spot", [
    ("2025-12", 25, {("cigarrillos", "2025-01"): 5.39}),        # 6-letter month label "Diciem-25"; no 2011
    ("2024-05", 18, {("cigarrillos", "2011"): 3.76}),           # "3," / "76" split
    ("2024-06", 19, {("cigarrillos", "2024-06"): 4.61}),        # "ene-" / "24" split labels
    ("2024-01", 14, {("liar", "2024-01"): 3.98}),               # whole series on one line
    ("2026-04", 18, {("cigarrillos", "2026-04"): 5.54}),
    ("2026-08", 22, {("cigarrillos", "2026-08"): 5.56}),
])
def test_every_layout_variant_seen_in_2024_2026(name, labels, spot):
    p = load(f"precios-{name}.raw.txt")
    assert len(p) == 3 * labels
    for k, v in spot.items():
        assert p[k] == v
