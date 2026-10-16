"""raw/*.pdf -> tobacco.db. Usage: python -m tabacos.build [raw_dir] [db_path]"""
import subprocess
import sys
from dataclasses import asdict
from pathlib import Path

import sqlite_utils

from .errors import TableNotFound, UnsupportedLayout
from .prices import merge_prices, parse_prices
from .regional import parse_regional
from .segments import parse_segments, parse_segments_pdf
from .tax import add_tax_tables
from .tourism import parse_tourism
from .views import create_views

# table -> (candidate parsers as (parser, input mode), primary key). The first candidate that finds
# the table wins; modes are pdftotext flags, or "pdf" for the file itself.
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


def build(raw: Path, db_path: Path, extract=pdf_text, tables=TABLES) -> None:
    """Parse every report into every table; a report that fails one table is logged, not fatal."""
    db_path.unlink(missing_ok=True)
    db = sqlite_utils.Database(db_path)
    parsed = {t: [] for t in tables}
    log = []
    for pdf in sorted(raw.glob("*.pdf")):
        texts = {}                  # one extraction per mode per report
        for table, (candidates, _) in tables.items():
            facts, status, detail = _parse(pdf, candidates, extract, texts)
            parsed[table].append((pdf.name, facts))
            log.append({"source": pdf.name, "table": table, "status": status,
                        "rows": len(facts), "detail": detail})
    db["parse_log"].insert_all(log)
    for table in ("regional_sales", "segment_sales", "tourist_sales"):
        if table in tables:
            db[table].insert_all(
                ({**asdict(f), "source": name} for name, facts in parsed[table] for f in facts),
                pk=tables[table][1], replace=True)
    if "avg_price" in tables:
        reports = sorted((r for r in parsed["avg_price"] if r[1]), key=lambda r: max(f.period for f in r[1]))
        prices, revisions = merge_prices(reports)
        db["avg_price"].insert_all((asdict(f) for f in prices), pk=tables["avg_price"][1])
        db["price_revisions"].insert_all(asdict(r) for r in revisions)
    if "segment_sales" in tables:
        add_tax_tables(db)
    create_views(db)


def summary(db_path: Path) -> str:
    db = sqlite_utils.Database(db_path)
    rows = db.query("select \"table\", status, count(*) n from parse_log group by 1, 2 order by 1, 2")
    return "\n".join(f"{r['table']:16}{r['status']:8}{r['n']:4}" for r in rows)


if __name__ == "__main__":
    out = Path(sys.argv[2] if len(sys.argv) > 2 else "tobacco.db")
    build(Path(sys.argv[1] if len(sys.argv) > 1 else "raw"), out)
    print(summary(out))
