from datetime import date
from pathlib import Path
import pytest
from tabacos.errors import TableNotFound
from tabacos.regional import ReconciliationError
from tabacos.tourism import parse_tourism

FIX = Path(__file__).parent / "fixtures"


def load(name):
    return parse_tourism((FIX / f"turismo-{name}.txt").read_text())


@pytest.mark.parametrize("name, end, girona", [
    ("2025-06", date(2025, 6, 30), (12_974_934, 53_731_109)),
    ("2024-01", date(2024, 1, 31), (2_122_180, 6_314_553)),
    ("2022-06", date(2022, 6, 30), (13_652_881, 40_914_558)),   # "Resto" / "Provincias" wraps
])
def test_province_rows_with_both_consumption_columns(name, end, girona):
    facts = load(name)
    g = next(f for f in facts if f.area == "Girona")
    assert (g.national_ytd, g.tourist_ytd) == girona and g.period_end == end and g.kind == "province"
    assert any(f.area == "Resto Provincias" for f in facts)


@pytest.mark.parametrize("name", ["2020-04", "2018-08", "2022-06", "2024-01", "2025-06", "2023-09", "2020-10", "2020-01"])
def test_both_partitions_are_kept_and_reconcile(name):
    facts = load(name)
    assert {f.area for f in facts if f.kind == "zone"} == {"Frontera", "Turístico"}
    for kind in ("province", "zone"):
        assert sum(f.national_ytd for f in facts if f.kind == kind) == pytest.approx(
            sum(f.national_ytd for f in facts if f.kind == "zone"), abs=10)


def test_numbers_that_do_not_add_up_raise():
    text = (FIX / "turismo-2025-06.txt").read_text().replace("30.991.032", "31.991.032")
    with pytest.raises(ReconciliationError):
        parse_tourism(text)


def test_report_without_the_table():
    with pytest.raises(TableNotFound):
        parse_tourism("nothing")


@pytest.mark.parametrize("name, end", [("2023-09", date(2023, 9, 30)), ("2020-10", date(2020, 10, 31)), ("2020-01", date(2020, 1, 31))])
def test_names_on_a_different_line_from_their_numbers(name, end):
    facts = load(name)          # names sit above or below the numbers; rows are matched by order
    assert [f.area for f in facts][-3:] == ["Resto Provincias", "Frontera", "Turístico"]
    assert len(facts) == 16 and facts[0].area == "Alicante/Alacant" and facts[0].period_end == end
    assert next(f for f in facts if f.area == "Frontera").tourist_ytd > 0


def test_a_number_split_over_two_lines_is_caught_not_misread():
    # Nov 2025 prints Girona's tourist figure as "117.962.67" above the row and "3" on it.
    with pytest.raises(ReconciliationError):
        load("2025-11")
