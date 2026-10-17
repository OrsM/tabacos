import json
import math
from pathlib import Path
import pytest
from tabacos.eurostat import parse_jsonstat, price_gap

FIX = Path(__file__).parent / "fixtures"


def test_jsonstat_values_are_matched_to_their_dimension_labels_and_missing_ones_skipped():
    rows = parse_jsonstat(json.loads((FIX / "jsonstat-mini.json").read_text()))
    got = {(r["geo"], r["time"]): r["value"] for r in rows}
    assert got == {("ES", "2025-01"): 125.2, ("ES", "2025-02"): 125.3, ("FR", "2025-01"): 193.1, ("FR", "2025-02"): 193.5, ("FR", "2025-03"): 193.6}


def series(country, values, months):
    return {(country, m): v for m, v in zip(months, values)}


def test_price_gap_anchors_each_year_on_the_price_level_and_follows_the_monthly_index_inside_it():
    months = [f"2024-{m:02d}" for m in range(1, 13)]
    es = [100.0 + i for i in range(12)]                       # Spain's index rises through the year; its mean is 105.5
    index = {**series("ES", es, months), **series("FR", [200.0] * 12, months)}
    gap = price_gap(index, {("ES", 2024): 80.0, ("FR", 2024): 160.0}, "FR", "ES")
    assert gap["2024-01"] == pytest.approx(math.log(160 / (80 * 100 / 105.5)))
    assert gap["2024-12"] == pytest.approx(math.log(160 / (80 * 111 / 105.5)))
    assert gap["2024-01"] > gap["2024-12"]                    # Spain catches up inside the year, the gap narrows


def test_price_gap_after_the_last_price_level_year_keeps_that_years_mean_as_the_reference():
    months = ["2024-06", "2024-12", "2025-06"]
    index = {**series("ES", [100, 100, 110], months), **series("FR", [100, 100, 100], months)}
    gap = price_gap(index, {("ES", 2024): 80.0, ("FR", 2024): 160.0}, "FR", "ES")
    assert gap["2025-06"] == pytest.approx(math.log(160 / (80 * 110 / 100)))


def test_months_missing_for_one_country_are_left_out():
    index = {**series("ES", [100, 101], ["2024-01", "2024-02"]), **series("FR", [100], ["2024-01"])}
    assert set(price_gap(index, {("ES", 2024): 80.0, ("FR", 2024): 160.0}, "FR", "ES")) == {"2024-01"}


def test_linking_the_two_hicp_versions_rescales_the_newer_one_on_their_overlap():
    from tabacos.eurostat import link_hicp
    v1 = {**series("FR", [190.0, 192.0], ["2025-01", "2025-02"])}
    v2 = {**series("FR", [100.0, 102.0, 105.0], ["2025-01", "2025-02", "2025-03"])}      # different base
    linked = link_hicp(v1, v2)
    factor = (190 + 192) / (100 + 102)
    assert linked[("FR", "2025-01")] == 190.0 and linked[("FR", "2025-02")] == 192.0       # the older version where it exists
    assert linked[("FR", "2025-03")] == pytest.approx(105.0 * factor)
