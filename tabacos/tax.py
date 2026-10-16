"""Tobacco excise (Ley 38/1992 art. 60) and VAT (Ley 37/1992 art. 90) rates over time, from the BOE consolidated texts."""
import calendar
import html
import re
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path

PESETAS_PER_EURO = 166.386
SOURCES = Path(__file__).parent.parent / "sources" / "boe"

# The API's fecha_vigencia is the publication-side date. Where the law itself says effects start
# later, that wins; each phrase below is asserted to be in the text by tests/test_tax.py.
EFFECTIVE_FROM = {
    "BOE-A-2004-21688": date(2005, 1, 1),     # "con efectos a partir del 1 de enero de 2005"
    "BOE-A-2012-9364": date(2012, 9, 1),      # "surte efectos desde el 1 de septiembre de 2012"
    "BOE-A-2012-15650": date(2013, 1, 1),     # "con efectos desde el 1 de enero de 2013"
    "BOE-A-2013-7062": date(2013, 7, 5),      # "con efectos desde el 5 de julio de 2013"
}
VAT_EFFECTIVE_FROM = {
    "BOE-A-1994-28967": date(1995, 1, 1),     # "con efectos desde el 1 de enero de 1995"
    "BOE-A-2012-9364": date(2012, 9, 1),      # "con efectos desde el 1 de septiembre de 2012"
}


@dataclass(frozen=True)
class TaxRate:
    product: str                       # "cigarrillos" | "picadura"
    effective_from: date
    ad_valorem_pct: float              # % of the retail price including all taxes
    specific: float                    # EUR per 1000 cigarettes / per kg
    minimum: float | None              # tax cannot be lower than this (same unit)
    minimum_raised: float | None       # ...or this, for products priced below minimum_below_price
    minimum_below_price: float | None  # retail price per 1000 units (per kg) under which the raised minimum applies
    source: str                        # BOE id of the amending text


def _num(s: str) -> float:
    return float(s.replace(".", "").replace(",", "."))


def _versions(xml: str) -> list[tuple[str, date, str]]:
    out = []
    for v in re.split(r"(?=<version id_norma=)", xml)[1:]:
        m = re.match(r'<version id_norma="([^"]*)" fecha_publicacion="\d+" fecha_vigencia="(\d{4})(\d\d)(\d\d)"', v)
        text = html.unescape(re.sub(r"<[^>]+>", " ", v)).replace("­", "")
        out.append((m[1], date(int(m[2]), int(m[3]), int(m[4])), re.sub(r"\s+", " ", text)))
    return out


def _first(pattern: str, text: str, group: int = 1) -> float | None:
    m = re.search(pattern, text)
    return _num(m[group]) if m else None


def _rate(product: str, section: str, separate_minimum: float | None, when: date, source: str) -> TaxRate:
    """Read one product's tariff paragraph. pesetas -> euros."""
    unit = r"(?:cada 1\.000 cigarrillos|kilogramo)"
    spec = re.search(r"Tipo específico:\s*([\d,]+)\s*(euros|pesetas)", section)
    specific = _num(spec[1]) / (PESETAS_PER_EURO if spec[2] == "pesetas" else 1) if spec else 0.0
    ad_val = _first(r"Tipo proporcional:\s*([\d,]+)", section) or _first(r":\s*([\d,]+) por 100", section)
    minimum = _first(rf"tipo único de ([\d.,]+) euros por (?:cada )?{unit}", section) or separate_minimum
    raised = re.search(rf"se incrementará hasta ([\d.,]+) euros cuando .*? inferior a ([\d.,]+) euros por", section)
    return TaxRate(product, when, ad_val, specific, minimum,
                   _num(raised[1]) if raised else None, _num(raised[2]) if raised else None, source)


def rates_from_xml(xml: str) -> list[TaxRate]:
    """Cigarette and roll-your-own rates from every version of art. 60, oldest first."""
    rates = []
    for source, vigencia, text in _versions(xml):
        when = EFFECTIVE_FROM.get(source, vigencia)
        cig = text[text.index("Cigarrillos"):text.index("Epígrafe 3.")]
        pic = text[text.index("Picadura"):text.index("Epígrafe 4", text.index("Picadura"))]
        ep5 = _first(r"Epígrafe 5\. Los cigarrillos estarán gravados al tipo único de ([\d.,]+) euros", text)
        ep6 = _first(r"Epígrafe 6\. La picadura para liar estará gravada al tipo único de ([\d.,]+) euros", text)
        rates += [_rate("cigarrillos", cig, ep5, when, source), _rate("picadura", pic, ep6, when, source)]
    return sorted(rates, key=lambda r: (r.product, r.effective_from))


def vat_from_xml(xml: str) -> list[tuple[date, float]]:
    """(effective date, general VAT rate in %) from every version of art. 90, oldest first."""
    rows = [(VAT_EFFECTIVE_FROM.get(source, vigencia), _first(r"se exigirá al tipo del (\d+)", text))
            for source, vigencia, text in _versions(xml)]
    return sorted(rows)


def excise_per_1000(retail_price_per_1000: float, rate: TaxRate) -> float:
    """Excise per 1000 cigarettes (per kg) at a retail price (including all taxes) per 1000 (per kg)."""
    minimum = rate.minimum or 0.0
    if rate.minimum_raised and retail_price_per_1000 < rate.minimum_below_price:
        minimum = rate.minimum_raised
    return max(rate.ad_valorem_pct / 100 * retail_price_per_1000 + rate.specific, minimum)


@dataclass(frozen=True)
class Breakdown:
    price: float          # retail price of a pack of 20
    excise: float
    vat: float
    net: float            # what is left for manufacturer, distributor and retailer
    regime: str           # "ad_valorem" | "minimum" | "raised_minimum": which part of the tariff sets the excise

    @property
    def excise_share(self) -> float:
        return self.excise / self.price


def breakdown(price: float, rate: TaxRate, vat_pct: float, pack: int = 20) -> Breakdown:
    """Split a pack price into excise, VAT and the remainder, and say which rule fixes the excise."""
    per_1000 = price * 1000 / pack
    calculated = rate.ad_valorem_pct / 100 * per_1000 + rate.specific
    raised = bool(rate.minimum_raised) and per_1000 < rate.minimum_below_price
    floor = rate.minimum_raised if raised else (rate.minimum or 0.0)
    regime = ("raised_minimum" if raised else "minimum") if floor > calculated else "ad_valorem"
    excise = max(calculated, floor) * pack / 1000
    vat = price * vat_pct / (100 + vat_pct)
    return Breakdown(price, excise, vat, price - excise - vat, regime)


def price_after_tax_change(price: float, old: TaxRate, new: TaxRate, vat_pct: float, new_vat_pct: float | None = None) -> float:
    """Retail price after the tariff changes if the pre-tax remainder stays the same (full pass-through, no margin change)."""
    net = breakdown(price, old, vat_pct).net
    vat_pct = vat_pct if new_vat_pct is None else new_vat_pct
    lo, hi = net, net * 10 + 10
    for _ in range(80):                                   # net(P) rises with P, so bisect
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if breakdown(mid, new, vat_pct).net < net else (lo, mid)
    return (lo + hi) / 2


def add_tax_tables(db) -> None:
    """tax_rates, vat_rates from the committed BOE texts, and segment_tax: every brand price split into excise, VAT and rest."""
    art60 = (SOURCES / "ley-38-1992-art-60.xml").read_text(encoding="utf-8")
    art90 = (SOURCES / "ley-37-1992-art-90.xml").read_text(encoding="utf-8")
    rates, vat = rates_from_xml(art60), vat_from_xml(art90)
    db["tax_rates"].insert_all((asdict(r) for r in rates), pk=("product", "effective_from"), replace=True)
    db["vat_rates"].insert_all(({"effective_from": d, "vat_pct": p} for d, p in vat), pk="effective_from", replace=True)
    db["events"].insert_all(tax_events(rates, vat), pk=("date", "kind", "product"), replace=True)
    cigarette = [r for r in rates if r.product == "cigarrillos"]
    rows = []
    for s in db["segment_sales"].rows:
        year, month = map(int, s["month"].split("-"))
        on = date(year, month, calendar.monthrange(year, month)[1])
        rate = [r for r in cigarette if r.effective_from <= on][-1]
        vat_pct = [p for d, p in vat if d <= on][-1]
        b = breakdown(s["price"], rate, vat_pct)
        rows.append({"month": s["month"], "tier": s["tier"], "brand": s["brand"], "company": s["company"],
                     "price": s["price"], "ad_valorem_pct": rate.ad_valorem_pct, "vat_pct": vat_pct,
                     "regime": b.regime, "excise": b.excise, "vat": b.vat, "net": b.net, "excise_share": b.excise_share})
    db["segment_tax"].insert_all(rows, pk=("month", "tier", "brand", "price"), replace=True)


_COMPARED = ("ad_valorem_pct", "specific", "minimum", "minimum_raised", "minimum_below_price")


def tax_events(rates: list[TaxRate], vat: list[tuple[date, float]]) -> list[dict]:
    """One row per date on which a rate changed, saying which fields moved. The first rate of a product is not an event."""
    events = []
    for product in sorted({r.product for r in rates}):
        rows = [r for r in rates if r.product == product]
        for old, new in zip(rows, rows[1:]):
            moved = [f"{f} {getattr(old, f)} -> {getattr(new, f)}" for f in _COMPARED if getattr(old, f) != getattr(new, f)]
            if moved:
                events.append({"date": new.effective_from, "kind": "excise", "product": product,
                               "summary": "; ".join(moved), "source": new.source})
    for (_, old), (when, new) in zip(vat, vat[1:]):
        if old != new:
            events.append({"date": when, "kind": "vat", "product": "all", "summary": f"vat_pct {old} -> {new}", "source": "BOE-A-1992-28740"})
    return sorted(events, key=lambda e: (e["date"], e["kind"], e["product"]))
