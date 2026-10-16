from pathlib import Path
import pytest
from tabacos.errors import TableNotFound
from tabacos.segments import parse_segments_pdf, segments_from_rows

FIX = Path(__file__).parent / "fixtures"


def by_brand(facts):
    return {(f.tier, f.brand): f for f in facts}


def test_wrapped_cells_come_back_whole():
    f = by_brand(parse_segments_pdf(FIX / "seg-2023-12.pdf"))
    assert f[("BAJO", "JPS_DUCADOS RUBIO")].price == 4.55 and f[("BAJO", "JPS_DUCADOS RUBIO")].share_pct == 1.43
    assert f[("INFERIOR", "OME")].company == "KARELIA TOBACCO COMPANY INC"
    assert f[("PREMIUM", "MARLBORO")].month == "2023-12"


def test_old_report_where_the_brand_name_wraps():
    f = by_brand(parse_segments_pdf(FIX / "seg-2020-04.pdf"))
    assert f[("MEDIO", "WINSTON CLASSIC")].price == 4.60
    assert f[("MEDIO", "WINSTON CLASSIC")].share_pct == 7.65
    assert f[("NEGRO", "DUCADOS NEGRO")].share_pct == 3.92
    assert f[("PREMIUM", "MARLBORO")].month == "2020-04"


def test_table_continuing_on_next_page_keeps_tier_state():
    facts = parse_segments_pdf(FIX / "seg-2022-06-split.pdf")
    f = by_brand(facts)
    assert f[("INFERIOR", "WINSTON")].price == 4.38          # first row on page 2
    assert f[("NEGRO", "HERENCIA")].share_pct == 0.13
    assert f[("BAJO", "LUCKY STRIKE")].price == 4.50          # last tier rows on page 1
    assert not any(x.brand in {"Totales", "Frontera"} for x in facts)


def test_oldest_layout_2018():
    f = by_brand(parse_segments_pdf(FIX / "seg-2018-08.pdf"))
    assert f[("PREMIUM", "MARLBORO")].price == 4.99 and f[("PREMIUM", "MARLBORO")].month == "2018-08"


def test_pdf_without_the_table_raises_table_not_found():
    with pytest.raises(TableNotFound):
        segments_from_rows([])


@pytest.mark.parametrize("name", ["seg-2022-09-split", "seg-2022-03-split"])
def test_continuation_with_orphan_first_row_or_repeated_header(name):
    f = by_brand(parse_segments_pdf(FIX / f"{name}.pdf"))
    assert len(f) >= 18
    assert ("NEGRO", "HERENCIA") in f and ("INFERIOR", "WINSTON") in f
