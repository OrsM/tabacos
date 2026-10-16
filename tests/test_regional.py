from datetime import date
from pathlib import Path
import pytest
from tabacos.regional import parse_regional, ReconciliationError

FIX = Path(__file__).parent / "fixtures"


def test_parses_sixteen_communities_with_period_end():
    facts = parse_regional((FIX / "ccaa-2025-06.txt").read_text())
    assert len(facts) == 16
    andalucia = next(f for f in facts if f.region == "Andalucía")
    assert andalucia.period_end == date(2025, 6, 30)
    assert andalucia.packs_ytd == 168_519_203


def test_layout_with_blank_lines_between_rows_and_without():
    old = parse_regional((FIX / "ccaa-2024-04.txt").read_text())
    assert len(old) == 16 and old[0].period_end == date(2024, 4, 30)


def test_total_mismatch_beyond_rounding_raises():
    text = (FIX / "ccaa-2025-06.txt").read_text().replace("168.519.203", "168.999.999")
    with pytest.raises(ReconciliationError):
        parse_regional(text)


def test_ignores_earlier_tables_in_a_full_report():
    earlier = "Totales            832.914.808 844.144.168     -1,33%\n"
    text = earlier + (FIX / "ccaa-2025-06.txt").read_text()
    assert len(parse_regional(text)) == 16


def test_report_without_regional_table_raises_table_not_found():
    from tabacos.errors import TableNotFound
    with pytest.raises(TableNotFound):
        parse_regional("INFORME MENSUAL\nsin tabla\n")


@pytest.mark.parametrize("name, end", [
    ("ccaa-2020-01", date(2020, 1, 31)),     # section titled "VENTAS POR COMUNIDADES AUTÓNOMAS", date above the column header
    ("ccaa-2020-02", date(2020, 2, 29)),
    ("ccaa-2024-01", date(2024, 1, 31)),     # "Ventas por CCAA", names indented
    ("ccaa-2021-10", date(2021, 10, 31)),    # "COMUNIDADES" and "AUTONOMAS" on different lines
    ("ccaa-2024-03", date(2024, 3, 31)),
])
def test_older_and_odd_headings(name, end):
    facts = parse_regional((FIX / f"{name}.txt").read_text())
    assert len(facts) == 16 and facts[0].period_end == end and facts[0].region == "Andalucía"
