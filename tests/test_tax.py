from datetime import date
from pathlib import Path
import pytest
from tabacos.tax import excise_per_1000, rates_from_xml, vat_from_xml

SRC = Path(__file__).parent.parent / "sources" / "boe"
ART60 = (SRC / "ley-38-1992-art-60.xml").read_text(encoding="utf-8")
ART90 = (SRC / "ley-37-1992-art-90.xml").read_text(encoding="utf-8")


def cig(on: date):
    """The cigarette rate in force on a date."""
    rows = [r for r in rates_from_xml(ART60) if r.product == "cigarrillos" and r.effective_from <= on]
    return rows[-1]


def test_current_structure_after_the_2025_reform():
    r = cig(date(2025, 1, 1))
    assert (r.ad_valorem_pct, r.specific, r.minimum, r.minimum_below_price) == (48.5, 33.5, 150.0, None)
    assert r.minimum_raised is None


def test_2016_to_2024_has_a_raised_minimum_below_196_per_1000():
    r = cig(date(2020, 6, 1))
    assert (r.ad_valorem_pct, r.specific, r.minimum, r.minimum_raised, r.minimum_below_price) == (51, 24.7, 131.5, 141.0, 196.0)
    assert r.effective_from == date(2016, 12, 3)


def test_vigencia_date_is_overridden_where_the_law_says_effects_start_later():
    assert cig(date(2013, 7, 4)).specific == 19.1          # 2013 increase applies from 5 July, not 30 June
    assert cig(date(2013, 7, 5)).specific == 24.1
    assert cig(date(2012, 8, 31)).ad_valorem_pct == 55      # the July 2012 decree applies from 1 September
    assert cig(date(2012, 9, 1)).ad_valorem_pct == 53.1
    assert cig(date(2013, 1, 1)).minimum == 123.97          # Ley 16/2012: effects from 1 Jan 2013
    assert cig(date(2005, 1, 1)).ad_valorem_pct == 54       # Ley 2/2004: effects from 1 Jan 2005


def test_overrides_are_backed_by_text_in_the_law():
    for phrase in ("1 de septiembre de 2012", "5 de julio de 2013", "1 de enero de 2013", "1 de enero de 2005"):
        assert phrase in ART60


def test_minimum_from_the_separate_epigraph_before_2012():
    assert [cig(date(y, m, 15)).minimum for y, m in [(2006, 3), (2006, 12), (2010, 1), (2011, 1)]] == [55, 70, 91.3, 116.9]


def test_pesetas_are_converted_to_euros():
    r = cig(date(1993, 6, 1))
    assert r.ad_valorem_pct == 48.5 and r.specific == pytest.approx(150 / 166.386, abs=1e-3)


def test_roll_your_own():
    rows = [r for r in rates_from_xml(ART60) if r.product == "picadura"]
    now = [r for r in rows if r.effective_from <= date(2025, 1, 1)][-1]
    assert (now.ad_valorem_pct, now.specific, now.minimum) == (37.68, 33.4, 112.5)
    y2014 = [r for r in rows if r.effective_from <= date(2014, 1, 1)][-1]
    assert (y2014.specific, y2014.minimum, y2014.minimum_raised, y2014.minimum_below_price) == (22, 96.5, 100.5, 165)


def test_vat_general_rate_history():
    vat = vat_from_xml(ART90)
    on = lambda d: [r for r in vat if r[0] <= d][-1][1]
    assert [on(d) for d in (date(1994, 6, 1), date(1995, 1, 1), date(2010, 7, 1), date(2012, 8, 31), date(2012, 9, 1))] == [15, 16, 18, 18, 21]


def test_excise_regimes():
    r = cig(date(2020, 6, 1))
    assert excise_per_1000(250, r) == pytest.approx(0.51 * 250 + 24.7)          # ad valorem regime
    assert excise_per_1000(150, r) == 141.0                                      # raised minimum below 196
    assert excise_per_1000(197, r) == pytest.approx(max(0.51 * 197 + 24.7, 131.5))   # ordinary minimum from 196


from tabacos.tax import breakdown, price_after_tax_change    # noqa: E402


def test_breakdown_of_a_pack_in_each_regime():
    r = cig(date(2020, 6, 1))
    b = breakdown(5.00, r, vat_pct=21)                      # 250 per 1000: ad valorem regime
    assert (b.regime, round(b.excise, 3), round(b.vat, 3)) == ("ad_valorem", 3.044, 0.868)
    assert round(b.net, 3) == 1.088 and round(b.excise_share, 3) == 0.609
    cheap = breakdown(3.50, r, vat_pct=21)                  # 175 per 1000 < 196: raised minimum binds
    assert (cheap.regime, round(cheap.excise, 3)) == ("raised_minimum", 2.82)
    assert breakdown(4.00, r, vat_pct=21).regime == "minimum"    # 200 per 1000: 0.51*200+24.7 = 126.7 < 131.5
    assert breakdown(4.50, r, vat_pct=21).regime == "ad_valorem"  # 225: 139.45 > 131.5


def test_price_after_a_tax_change_keeps_the_pre_tax_revenue_fixed():
    old, new = cig(date(2024, 12, 31)), cig(date(2025, 1, 1))
    p2 = price_after_tax_change(5.79, old, new, vat_pct=21)
    n_old = breakdown(5.79, old, 21).net
    assert breakdown(p2, new, 21).net == pytest.approx(n_old, abs=1e-6)
    assert p2 > 5.79


def test_tax_tables_and_segment_tax_in_the_database():
    import sqlite_utils
    from tabacos.tax import add_tax_tables
    db = sqlite_utils.Database(memory=True)
    db["segment_sales"].insert({"month": "2025-01", "tier": "PREMIUM", "brand": "MARLBORO", "company": "PHILIP MORRIS",
                                "price": 5.97, "share_pct": 12.0, "source": "x"})
    db["segment_sales"].insert({"month": "2024-12", "tier": "PREMIUM", "brand": "MARLBORO", "company": "PHILIP MORRIS",
                                "price": 5.79, "share_pct": 12.0, "source": "x"})
    add_tax_tables(db)
    assert db["tax_rates"].count > 30 and db["vat_rates"].count == 5
    jan = next(db["segment_tax"].rows_where("month = '2025-01'"))
    assert jan["regime"] == "ad_valorem" and round(jan["excise"], 4) == 3.5655 and jan["vat_pct"] == 21
    dec = next(db["segment_tax"].rows_where("month = '2024-12'"))
    assert dec["ad_valorem_pct"] == 51 and dec["excise_share"] == pytest.approx(0.5948, abs=1e-3)


def test_events_list_what_changed_on_each_date():
    from tabacos.tax import tax_events
    ev = tax_events(rates_from_xml(ART60), vat_from_xml(ART90))
    jan25 = next(e for e in ev if e["date"] == date(2025, 1, 1) and e["product"] == "cigarrillos")
    assert jan25["kind"] == "excise" and jan25["source"] == "BOE-A-2024-26694"
    assert "ad_valorem_pct 51.0 -> 48.5" in jan25["summary"] and "minimum 131.5 -> 150.0" in jan25["summary"]
    assert "minimum_raised 141.0 -> None" in jan25["summary"]
    vat = [e for e in ev if e["kind"] == "vat"]
    assert [(e["date"], e["summary"]) for e in vat if e["date"].year >= 2010] == [
        (date(2010, 7, 1), "vat_pct 16.0 -> 18.0"), (date(2012, 9, 1), "vat_pct 18.0 -> 21.0")]
    assert not any(e["date"] == date(1996, 1, 1) and e["kind"] == "vat" for e in ev)    # 16 -> 16 is not an event
