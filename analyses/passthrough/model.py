"""How much of a price change is the tax, and what is left for the manufacturer."""
from statistics import median

from tabacos.tax import TaxRate, breakdown, price_after_tax_change


def change_rows(changes: list[dict], old: TaxRate, new: TaxRate, old_vat: float, new_vat: float) -> list[dict]:
    """For each price change (old_price -> new_price of a pack of 20) across a tax change old -> new.

    implied_price: what the price would be if the pre-tax remainder stayed the same.
    d_net: change in that remainder (EUR per pack); 0 means the tax change was passed through exactly.
    passthrough_ratio: actual price change divided by the tax-implied change (1 = tax only).
    regime_old: which part of the old tariff set the excise at the old price.
    """
    rows = []
    for c in changes:
        b0 = breakdown(c["old_price"], old, old_vat)
        b1 = breakdown(c["new_price"], new, new_vat)
        implied = price_after_tax_change(c["old_price"], old, new, old_vat, new_vat)
        implied_change = implied - c["old_price"]
        rows.append({**c, "regime_old": b0.regime, "regime_new": b1.regime, "implied_price": implied,
                     "actual_pct": (c["new_price"] / c["old_price"] - 1) * 100,
                     "implied_pct": (implied / c["old_price"] - 1) * 100,
                     "d_net": b1.net - b0.net,
                     "passthrough_ratio": (c["new_price"] - c["old_price"]) / implied_change if implied_change else None})
    return rows


def summarise(rows: list[dict]) -> list[dict]:
    """Medians by the regime at the old price."""
    out = []
    for regime in ("raised_minimum", "minimum", "ad_valorem"):
        grp = [r for r in rows if r["regime_old"] == regime]
        if grp:
            out.append({"regime_old": regime, "n": len(grp),
                        "median_actual_pct": median(r["actual_pct"] for r in grp),
                        "median_implied_pct": median(r["implied_pct"] for r in grp),
                        "median_d_net": median(r["d_net"] for r in grp)})
    return out
