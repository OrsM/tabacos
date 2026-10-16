from datetime import date
import pytest
from analyses.passthrough.model import change_rows, summarise
from tabacos.tax import TaxRate, price_after_tax_change

OLD = TaxRate("cigarrillos", date(2016, 12, 3), 51, 24.7, 131.5, 141.0, 196.0, "x")
NEW = TaxRate("cigarrillos", date(2025, 1, 1), 48.5, 33.5, 150.0, None, None, "y")


def make(old_price, new_price):
    return {"product": f"p{old_price}", "old_price": old_price, "new_price": new_price}


def test_a_tax_only_change_leaves_the_pretax_remainder_unchanged():
    old_prices = [4.20, 4.60, 5.20, 5.90]
    changes = [make(p, price_after_tax_change(p, OLD, NEW, 21)) for p in old_prices]
    rows = change_rows(changes, OLD, NEW, old_vat=21, new_vat=21)
    assert all(abs(r["d_net"]) < 1e-6 for r in rows)
    assert all(r["passthrough_ratio"] == pytest.approx(1.0) for r in rows)


def test_a_manufacturer_who_adds_to_the_tax_change_shows_a_positive_net_change():
    p = 5.20
    implied = price_after_tax_change(p, OLD, NEW, 21)
    rows = change_rows([make(p, implied + 0.10)], OLD, NEW, 21, 21)
    assert rows[0]["d_net"] > 0.02 and rows[0]["passthrough_ratio"] > 1.0
    assert rows[0]["regime_old"] == "ad_valorem"


def test_regime_is_taken_at_the_old_price_and_summary_groups_by_it():
    changes = [make(3.60, 4.40), make(4.00, 4.60), make(5.30, 5.60), make(5.40, 5.65)]
    rows = change_rows(changes, OLD, NEW, 21, 21)
    s = {r["regime_old"]: r for r in summarise(rows)}
    assert (s["raised_minimum"]["n"], s["minimum"]["n"], s["ad_valorem"]["n"]) == (1, 1, 2)
    upper = [r["d_net"] for r in rows if r["regime_old"] == "ad_valorem"]
    assert s["ad_valorem"]["median_d_net"] == pytest.approx(sum(upper) / 2)      # median of two = their mean
