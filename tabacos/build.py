"""raw/*.pdf -> tobacco.db. Usage: python -m tabacos.build [raw_dir] [db_path]"""
import hashlib
import pickle
import subprocess
import sys
from dataclasses import asdict
from datetime import date
from pathlib import Path

import sqlite_utils

from .errors import TableNotFound, UnsupportedLayout
from .merge import merge_latest
from .prices import merge_prices, parse_prices
from .pvp import parse_resolution, price_changes
from .regional import parse_regional
from .ine import read_arrivals
from .segments import parse_segments, parse_segments_pdf
from .tax import add_tax_tables
from .tourism import parse_tourism
from .views import create_views

# table -> (candidate parsers as (parser, input mode), primary key). The first candidate that finds
# the table wins; modes are pdftotext flags, or "pdf" for the file itself.
# tables whose reports overlap (current and prior-year columns): table -> (key, value) for merge_latest
MERGED = {
    "regional_sales": (lambda f: (f.region, f.period_end), lambda f: f.packs_ytd),
    "tourist_sales": (lambda f: (f.area, f.kind, f.period_end), lambda f: (f.national_ytd, f.tourist_ytd)),
}
TABLES = {
    "regional_sales": ([(parse_regional, "-layout")], ("region", "period_end")),
    "segment_sales": ([(parse_segments, "-layout"), (parse_segments_pdf, "pdf")],
                      ("month", "tier", "brand", "price")),
    "tourist_sales": ([(parse_tourism, "-layout")], ("area", "kind", "period_end")),
    "avg_price": ([(parse_prices, "-raw")], ("product", "period")),
}


def pdf_text(pdf: Path, mode: str):
    if mode == "pdf":
        return pdf
    return subprocess.run(["pdftotext", mode, str(pdf), "-"],
                          check=True, capture_output=True, text=True).stdout


PARSER_MODULES = ["errors", "months", "numbers", "prices", "pvp", "regional", "segments", "tourism"]


def code_fingerprint() -> str:
    """Hash of the parser sources: a cached parse is only reused while the parsers are unchanged."""
    h = hashlib.sha256()
    for name in PARSER_MODULES:
        h.update((Path(__file__).parent / f"{name}.py").read_bytes())
    return h.hexdigest()[:16]


def _cached(cache_dir, key: str, compute):
    """compute() once per key; results are pickled under cache_dir (None disables the cache)."""
    if cache_dir is None:
        return compute()
    path = Path(cache_dir) / f"{key}.pkl"
    if path.exists():
        return pickle.loads(path.read_bytes())
    result = compute()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(pickle.dumps(result))
    return result


def _parse(pdf: Path, candidates, extract, texts: dict):
    """(facts, status, detail) from the first candidate parser that finds the table."""
    for parse, mode in candidates:
        try:
            texts.setdefault(mode, extract(pdf, mode))
            return parse(texts[mode]), "ok", ""
        except TableNotFound as e:
            absent = str(e)
        except UnsupportedLayout as e:
            return [], "failed", str(e)
    return [], "absent", absent


def build(raw: Path, db_path: Path, extract=pdf_text, tables=TABLES, cache_dir=".cache/parse",
          fingerprint: str | None = None) -> None:
    """Parse every report into every table; a report that fails one table is logged, not fatal."""
    db_path.unlink(missing_ok=True)
    db = sqlite_utils.Database(db_path)
    parsed = {t: [] for t in tables}
    log = []
    fingerprint = fingerprint or code_fingerprint()
    for pdf in sorted(raw.glob("*.pdf")):
        texts = {}                  # one extraction per mode per report
        digest = hashlib.sha256(pdf.read_bytes()).hexdigest()[:20]
        for table, (candidates, _) in tables.items():
            facts, status, detail = _cached(cache_dir, f"{digest}-{table}-{fingerprint}",
                                            lambda: _parse(pdf, candidates, extract, texts))
            parsed[table].append((pdf.name, facts))
            log.append({"source": pdf.name, "table": table, "status": status,
                        "rows": len(facts), "detail": detail})
    db["parse_log"].insert_all(log)
    revisions = []
    for table, (key, value) in MERGED.items():
        if table in tables:
            # Each report also carries last year's column; the newest report's value for a month wins.
            reports = sorted(parsed[table], key=lambda r: max((f.period_end for f in r[1] if f.basis == "current"), default=date.min))
            winners, changed = merge_latest(reports, key=key, value=value)
            db[table].insert_all(({**asdict(f), "source": src} for f, src in winners), pk=tables[table][1])
            revisions += [{"table": table, "key": "|".join(map(str, r["key"])), "old": str(r["old"]), "new": str(r["new"]),
                           "old_source": r["old_source"], "new_source": r["new_source"]} for r in changed]
    if any(t in tables for t in MERGED):
        if revisions:
            db["revisions"].insert_all(revisions)
        else:                                               # no revisions is a result worth showing
            db["revisions"].create({"table": str, "key": str, "old": str, "new": str, "old_source": str, "new_source": str})
    for table in ("segment_sales",):
        if table in tables:
            db[table].insert_all(
                ({**asdict(f), "source": name} for name, facts in parsed[table] for f in facts),
                pk=tables[table][1], replace=True)
    if "avg_price" in tables:
        reports = sorted((r for r in parsed["avg_price"] if r[1]), key=lambda r: max(f.period for f in r[1]))
        prices, revisions = merge_prices(reports)
        db["avg_price"].insert_all((asdict(f) for f in prices), pk=tables["avg_price"][1])
        db["price_revisions"].insert_all(asdict(r) for r in revisions)
    if arrivals := read_arrivals():
        db["tourist_arrivals"].insert_all(arrivals, pk=("region", "month"))
    add_price_lists(db, Path(raw) / "boe", cache_dir, fingerprint)
    if "segment_sales" in tables:
        add_tax_tables(db)
    create_views(db)


def add_price_lists(db, boe_dir: Path, cache_dir, fingerprint: str) -> None:
    """price_listings and price_changes from the BOE price resolutions in boe_dir (skipped if there are none)."""
    files = sorted(boe_dir.glob("*.xml")) if boe_dir.is_dir() else []
    listings = []
    for f in files:
        digest = hashlib.sha256(f.read_bytes()).hexdigest()[:20]
        listings += _cached(cache_dir, f"{digest}-pvp-{fingerprint}", lambda: parse_resolution(f.read_text(encoding="utf-8")))
    if not listings:
        return
    db["price_listings"].insert_all(asdict(x) for x in listings)
    db["price_changes"].insert_all({**asdict(c), "pct": c.pct} for c in price_changes(listings))


def summary(db_path: Path) -> str:
    db = sqlite_utils.Database(db_path)
    rows = db.query("select \"table\", status, count(*) n from parse_log group by 1, 2 order by 1, 2")
    return "\n".join(f"{r['table']:16}{r['status']:8}{r['n']:4}" for r in rows)


if __name__ == "__main__":
    out = Path(sys.argv[2] if len(sys.argv) > 2 else "tobacco.db")
    build(Path(sys.argv[1] if len(sys.argv) > 1 else "raw"), out)
    print(summary(out))
