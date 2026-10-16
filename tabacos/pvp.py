"""Retail price (PVP) lists the Comisionado publishes in the BOE. Usage: python -m tabacos.pvp discover FROM TO"""
import html
import json
import re
import sys
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

SUMARIO = "https://www.boe.es/datosabiertos/api/boe/sumario/{day}"
TITLE = re.compile(r"precios de venta al público de determinadas labores de tabaco.*(Pen[ií]nsula|Monopolio)", re.I | re.S)
LIST_FILE = Path(__file__).parent.parent / "sources" / "boe" / "pvp-resolutions.tsv"


def _items(node):
    if isinstance(node, dict):
        if "identificador" in node and "titulo" in node:
            yield node
        for v in node.values():
            yield from _items(v)
    elif isinstance(node, list):
        for v in node:
            yield from _items(v)


def resolutions_in_summary(summary: dict) -> list[dict]:
    """Peninsula-and-Balearics price resolutions in one day's BOE summary."""
    return [{"id": i["identificador"], "title": i["titulo"]} for i in _items(summary) if TITLE.search(i["titulo"])]


def fetch_summary(day: date) -> dict | None:
    req = urllib.request.Request(SUMARIO.format(day=day.strftime("%Y%m%d")), headers={"Accept": "application/json"})
    try:
        return json.load(urllib.request.urlopen(req, timeout=60))
    except urllib.error.HTTPError as e:
        if e.code == 404:                       # no BOE that day
            return None
        raise


def discover(start: date, end: date, workers: int = 4) -> list[dict]:
    days = [start + timedelta(n) for n in range((end - start).days + 1) if (start + timedelta(n)).weekday() != 6]
    def one(day):
        summary = fetch_summary(day)
        return [{**r, "date": day.isoformat()} for r in resolutions_in_summary(summary)] if summary else []
    with ThreadPoolExecutor(workers) as pool:
        return [r for rs in pool.map(one, days) for r in rs]


@dataclass(frozen=True)
class PriceListing:
    resolution: str
    published: date          # the resolution takes effect the day it is published
    category: str            # "cigarrillos", "picadura de liar", "cigarros y cigarritos", ...
    product: str             # as printed, e.g. "Marlboro Red (35)"
    pack_size: int | None    # units in the pack when the name says so
    price: float             # retail price incl. all taxes
    unit: str                # "cajetilla" | "unidad" | "envase"


_PRICE = re.compile(r"\d{1,3}(?:\.\d{3})*,\d{2}")
_HEADING = re.compile(r"[A-Z]\)\s*(.+)")
_UNIT = re.compile(r"Euros/(\w+)", re.I)
_PACK = re.compile(r"\((?:el envase de )?(\d+)\)\.?$")
_NOT_A_PRODUCT = re.compile(r"PVP|–|Precio total de venta al público|Euros/.*", re.I)


def parse_resolution(xml: str) -> list[PriceListing]:
    """Every price in one resolution, with its section and unit. Raises ValueError if the text has no publication date."""
    published = re.search(r"<fecha_publicacion>(\d{4})(\d\d)(\d\d)<", xml)
    if not published:
        raise ValueError("resolution without a publication date")
    day = date(*map(int, published.groups()))
    id_ = re.search(r"<identificador>([^<]+)<", xml)[1]
    body = html.unescape(re.sub(r"<[^>]+>", "\n", xml[xml.find("<texto>"):]))
    raw = [l.strip() for l in body.splitlines() if l.strip()]
    lines, i = [], 0
    while i < len(raw):                                  # older layout: "A)" and its title on separate lines
        if re.fullmatch(r"[A-Z]\)", raw[i]) and i + 1 < len(raw):
            lines.append(f"{raw[i]} {raw[i + 1]}")
            i += 2
        else:
            lines.append(raw[i])
            i += 1
    category, unit, out, in_scope = "", "", [], True
    for prev, line in zip([""] + lines, lines):
        if "serán los siguientes" in line:               # a resolution can also price Ceuta y Melilla
            in_scope = bool(re.search(r"Pen[ií]nsula", line))
        elif (m := _HEADING.fullmatch(line)):
            category = m[1].lower().replace("picaduras", "picadura")
        elif (m := _UNIT.fullmatch(line)):
            unit = m[1].lower()
        elif in_scope and _PRICE.fullmatch(line) and prev and not _NOT_A_PRODUCT.fullmatch(prev) \
                and not _HEADING.fullmatch(prev) and not _PRICE.fullmatch(prev):
            product = prev.rstrip(".").strip()
            pack = _PACK.search(product)
            out.append(PriceListing(id_, day, category, product, int(pack[1]) if pack else None,
                                    float(line.replace(".", "").replace(",", ".")), unit))
    return out


@dataclass(frozen=True)
class PriceChange:
    category: str
    product: str
    published: date          # the new price takes effect the day it is published
    old_published: date
    old_price: float
    new_price: float

    @property
    def pct(self) -> float:
        return (self.new_price / self.old_price - 1) * 100


def _key(x: PriceListing) -> tuple[str, str]:
    return (x.category.rstrip("."), " ".join(x.product.lower().rstrip(".").split()))


def price_changes(listings: list[PriceListing]) -> list[PriceChange]:
    """A change is a product listed at a different price than its previous listing (names compared case-blind)."""
    last: dict = {}
    out = []
    for x in sorted(listings, key=lambda x: (x.published, x.resolution)):
        k = _key(x)
        if k in last and last[k].price != x.price:
            out.append(PriceChange(x.category, x.product.rstrip("."), x.published, last[k].published, last[k].price, x.price))
        last[k] = x
    return out


def merge_resolution_lists(*lists: list[dict]) -> list[dict]:
    by_id = {r["id"]: r for rs in lists for r in rs}
    return sorted(by_id.values(), key=lambda r: (r["date"], r["id"]))


def read_list() -> list[dict]:
    if not LIST_FILE.exists():
        return []
    rows = (l.rstrip("\n").split("\t") for l in LIST_FILE.read_text(encoding="utf-8").splitlines() if l)
    return [{"id": i, "date": d, "title": t} for i, d, t in rows]


if __name__ == "__main__":
    if sys.argv[1] == "discover":      # adds to the committed list; never drops entries
        found = merge_resolution_lists(read_list(), discover(date.fromisoformat(sys.argv[2]), date.fromisoformat(sys.argv[3])))
        LIST_FILE.write_text("".join(f"{r['id']}\t{r['date']}\t{r['title']}\n" for r in found), encoding="utf-8")
        print(len(found), "resolutions")
