"""Tobacco prices abroad from Eurostat: monthly HICP tobacco indices and annual price level indices.
Usage: python -m tabacos.eurostat   (rewrites sources/eurostat/)"""
import csv
import json
import math
import urllib.request
from itertools import product
from pathlib import Path

API = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/"
DIR = Path(__file__).parent.parent / "sources" / "eurostat"
COUNTRIES = ("ES", "FR", "PT", "IE")
QUERIES = {                          # file -> (dataset, parameters)
    # HICP, ECOICOP ver.1, 2015 = 100, to Dec 2025; and ver.2, 2025 = 100, from Jan 2025. Both are kept as published.
    "hicp-tobacco-v1.csv": ("prc_hicp_midx", "coicop=CP022&unit=I15&sinceTimePeriod=2015-01"),
    "hicp-tobacco-v2.csv": ("prc_hicp_minr", "coicop18=CP023&unit=I25&sinceTimePeriod=2025-01"),
    # Price level index of tobacco, EU27 = 100, annual
    "pli-tobacco.csv": ("prc_ppp_ind", "ppp_cat=A010202&na_item=PLI_EU27_2020&sinceTimePeriod=2012"),
}


def parse_jsonstat(d: dict) -> list[dict]:
    """JSON-stat 2.0 cube -> one dict per non-missing value, keyed by dimension name, plus 'value'."""
    ids, sizes = d["id"], d["size"]
    labels = [list(d["dimension"][i]["category"]["index"]) for i in ids]
    out = []
    for flat, combo in enumerate(product(*labels)):
        v = d["value"].get(str(flat))
        if v is not None:
            out.append({**dict(zip(ids, combo)), "value": v})
    return out


def read_rows(name: str) -> list[dict]:
    path = DIR / name
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as f:
        return [{**r, "value": float(r["value"])} for r in csv.DictReader(f)]


def price_gap(index: dict[tuple[str, str], float], pli: dict[tuple[str, int], float], a: str, b: str) -> dict[str, float]:
    """Monthly log of country a's tobacco price level over country b's.

    A country's level in a month is its price level index of that year (annual, EU27 = 100) times the month's HICP
    index over the HICP mean of that year. After the last year with a price level index the reference stays that year's
    mean, so the series continues with the monthly indices alone.
    """
    anchor = max(y for (_, y) in pli)

    def level(c: str, month: str) -> float | None:
        year = min(int(month[:4]), anchor)
        if (c, month) not in index or (c, year) not in pli:
            return None
        ref = [v for (cc, m), v in index.items() if cc == c and m.startswith(str(year))]
        return pli[(c, year)] * index[(c, month)] / (sum(ref) / len(ref))

    out = {}
    for month in sorted({m for (_, m) in index}):
        la, lb = level(a, month), level(b, month)
        if la and lb:
            out[month] = math.log(la / lb)
    return out


def link_hicp(v1: dict, v2: dict) -> dict:
    """One monthly series per country: ver.1 where it exists, ver.2 after it, rescaled so the two agree on average over
    the months both cover (the versions have different bases)."""
    out = dict(v1)
    for c in {c for c, _ in v2}:
        both = [m for (cc, m) in v2 if cc == c and (c, m) in v1]
        if not both:
            continue
        factor = sum(v1[(c, m)] for m in both) / sum(v2[(c, m)] for m in both)
        out.update({(cc, m): v * factor for (cc, m), v in v2.items() if cc == c and (c, m) not in v1})
    return out


def add_foreign_prices(db) -> None:
    """tobacco_hicp (linked monthly index), tobacco_pli (annual) and foreign_price_gap (log price level of France and
    Portugal over Spain's, monthly) from the committed CSVs."""
    v1 = {(r["geo"], r["time"]): r["value"] for r in read_rows("hicp-tobacco-v1.csv")}
    v2 = {(r["geo"], r["time"]): r["value"] for r in read_rows("hicp-tobacco-v2.csv")}
    pli = {(r["geo"], int(r["time"])): r["value"] for r in read_rows("pli-tobacco.csv")}
    if not v1 or not pli:
        return
    index = link_hicp(v1, v2)
    db["tobacco_hicp"].insert_all(({"country": c, "month": m, "index_2015_100": v} for (c, m), v in sorted(index.items())),
                                  pk=("country", "month"))
    db["tobacco_pli"].insert_all(({"country": c, "year": y, "level_eu27_100": v} for (c, y), v in sorted(pli.items())),
                                 pk=("country", "year"))
    rows = [{"country": c, "month": m, "log_gap_to_spain": g} for c in ("FR", "PT")
            for m, g in price_gap(index, pli, c, "ES").items()]
    db["foreign_price_gap"].insert_all(rows, pk=("country", "month"))


if __name__ == "__main__":
    DIR.mkdir(parents=True, exist_ok=True)
    for name, (dataset, params) in QUERIES.items():
        geo = "&".join(f"geo={c}" for c in COUNTRIES)
        req = urllib.request.Request(f"{API}{dataset}?{params}&{geo}", headers={"Accept": "application/json"})
        rows = parse_jsonstat(json.load(urllib.request.urlopen(req, timeout=60)))
        keep = [k for k in rows[0] if k not in ("freq", "unit", "coicop", "coicop18", "ppp_cat", "na_item")]
        with (DIR / name).open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=keep)
            w.writeheader()
            w.writerows({k: r[k] for k in keep} for r in rows)
        print(name, len(rows), "rows")
