import json
from pathlib import Path
import pytest
from tabacos.pvp import resolutions_in_summary

FIX = Path(__file__).parent / "fixtures"


def test_finds_peninsula_price_resolutions_in_a_daily_summary_whether_items_are_a_list_or_one_object():
    found = resolutions_in_summary(json.loads((FIX / "sumario-mini.json").read_text()))
    assert [r["id"] for r in found] == ["BOE-A-2025-5742", "BOE-A-2025-5112"]    # "Península y Baleares" or "Monopolio"; Canarias is a different market


from datetime import date                       # noqa: E402
from tabacos.pvp import parse_resolution        # noqa: E402


def listings(id_):
    return parse_resolution((FIX / f"pvp-{id_}.xml").read_text(encoding="utf-8"))


def test_cigarette_listing_with_pack_size_and_publication_date():
    cig = [x for x in listings("BOE-A-2021-9788") if x.category == "cigarrillos"]
    assert [(x.product, x.pack_size, x.price, x.unit, x.published) for x in cig] == [
        ("Marlboro Red Duro 21 (21)", 21, 5.00, "cajetilla", date(2021, 6, 12))]


def test_several_cigarettes_and_a_name_without_a_pack_size():
    cig = {x.product: x for x in listings("BOE-A-2026-3380") if x.category == "cigarrillos"}
    assert len(cig) == 11
    assert (cig["Marlboro Red (35)"].pack_size, cig["Marlboro Red (35)"].price) == (35, 10.00)
    assert cig["Nobel Absolute"].pack_size is None and cig["Nobel Absolute"].price == 5.95


def test_roll_your_own_has_weight_not_a_pack_size():
    liar = {x.product: x for x in listings("BOE-A-2021-9788") if x.category == "picadura de liar"}
    assert liar["Golden Virginia 5 × 50 G (50 g)"].price == 8.95 and liar["L&B 5 × 50 G (50 g)"].unit == "unidad"


def test_old_layout_with_unit_before_each_section_and_brand_headings():
    got = {(x.category, x.product): x.price for x in listings("BOE-A-2018-10241")}
    assert got[("cigarros y cigarritos", "Mini White Filter (20)")] == 0.20
    assert got[("picadura de liar", "Look Out Original Papel (30 g)")] == 4.80


def test_heading_split_over_two_lines_and_other_territories_left_out():
    got = {(x.category, x.product): x.price for x in listings("BOE-A-2019-10026")}
    assert got[("picadura de liar", "Marlboro Gold Rolling and Tubing (70 g)")] == 12.00
    assert got[("picadura de pipa", "Adalya Blue Dragan (50 g)")] == 2.95        # Peninsula and Balearics
    assert all(p != 1.75 for (c, n), p in got.items() if n == "Adalya Blue Dragan (50 g)")   # Ceuta y Melilla price
    assert not any(x.category == "" for x in listings("BOE-A-2019-10026"))


from tabacos.pvp import PriceListing, price_changes     # noqa: E402


def L(res, day, product, price, category="cigarrillos"):
    return PriceListing(res, date.fromisoformat(day), category, product, None, price, "cajetilla")


def test_price_changes_between_consecutive_listings_of_the_same_product():
    rows = [L("r2", "2025-02-01", "Camel Blue 20", 5.90), L("r1", "2024-06-01", "camel blue 20.", 5.75),
            L("r3", "2025-06-01", "Camel Blue 20", 5.90),                      # re-listed at the same price: no change
            L("r2", "2025-02-01", "Other", 4.00)]
    ch = price_changes(rows)
    assert [(c.product, c.published, c.old_price, c.new_price) for c in ch] == [
        ("Camel Blue 20", date(2025, 2, 1), 5.75, 5.90)]
    assert ch[0].pct == pytest.approx((5.90 / 5.75 - 1) * 100)
    assert ch[0].old_published == date(2024, 6, 1)


def test_same_name_in_different_categories_is_a_different_product():
    rows = [L("r1", "2024-01-01", "Marlboro Red", 5.0), L("r2", "2024-02-01", "Marlboro Red", 9.0, "picadura de liar")]
    assert price_changes(rows) == []
