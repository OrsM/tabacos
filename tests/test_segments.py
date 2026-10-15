from pathlib import Path
from tabacos.segments import parse_segments

FIX = Path(__file__).parent / "fixtures"


def test_brand_rows_carry_their_tier_company_price_and_share():
    facts = parse_segments((FIX / "segmentos-2025-06.txt").read_text())
    marlboro = [f for f in facts if f.brand == "MARLBORO"]
    assert {(f.tier, f.price, f.share_pct) for f in marlboro} == {
        ("PREMIUM", 5.97, 12.41), ("BAJO", 4.84, 3.30)}
    assert marlboro[0].company == "PHILIP MORRIS"
    assert facts[0].month == "2025-06"


def test_tier_header_rows_are_not_brands():
    facts = parse_segments((FIX / "segmentos-2025-06.txt").read_text())
    assert not any(f.brand in {"PREMIUM", "MEDIO", "BAJO"} for f in facts)


def test_older_layout_abbreviated_lowercase_month_header():
    facts = parse_segments((FIX / "segmentos-2024-04.txt").read_text())
    assert facts[0].month == "2024-04" and facts[0].brand == "MARLBORO"
    assert {f.tier for f in facts} >= {"PREMIUM", "MEDIO", "BAJO"}


def test_table_continuing_onto_next_page_keeps_its_tier():
    facts = parse_segments((FIX / "segmentos-2025-05-split.txt").read_text())
    kings = [f for f in facts if f.brand == "KING"]
    assert [(f.tier, f.price) for f in kings] == [("INFERIOR", 4.40)]
