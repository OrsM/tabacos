"""raw/*.pdf -> tobacco.db. Usage: python -m tabacos.build [raw_dir] [db_path]"""
import subprocess
import sys
from dataclasses import asdict
from pathlib import Path

import sqlite_utils

from .errors import TableNotFound, UnsupportedLayout
from .prices import merge_prices, parse_prices
from .regional import parse_regional
from .segments import parse_segments

# table -> (parser, pdftotext mode, primary key)
TABLES = {
    "regional_sales": (parse_regional, "-layout", ("region", "period_end")),
    "segment_sales": (parse_segments, "-layout", ("month", "tier", "brand", "price")),
    "avg_price": (parse_prices, "-raw", ("product", "period")),
}


def pdf_text(pdf: Path, mode: str) -> str:
    return subprocess.run(["pdftotext", mode, str(pdf), "-"],
                          check=True, capture_output=True, text=True).stdout


def build(raw: Path, db_path: Path, extract=pdf_text) -> None:
    """Parse every report into every table; a report that fails one table is logged, not fatal."""
    db_path.unlink(missing_ok=True)
    db = sqlite_utils.Database(db_path)
    parsed = {t: [] for t in TABLES}
    log = []
    for pdf in sorted(raw.glob("*.pdf")):
        texts = {}                  # one pdftotext run per mode per report
        for table, (parse, mode, _) in TABLES.items():
            try:
                texts.setdefault(mode, extract(pdf, mode))
                facts, status, detail = parse(texts[mode]), "ok", ""
            except TableNotFound as e:
                facts, status, detail = [], "absent", str(e)
            except UnsupportedLayout as e:
                facts, status, detail = [], "failed", str(e)
            parsed[table].append((pdf.name, facts))
            log.append({"source": pdf.name, "table": table, "status": status,
                        "rows": len(facts), "detail": detail})
    db["parse_log"].insert_all(log)
    for table in ("regional_sales", "segment_sales"):
        pk = TABLES[table][2]
        db[table].insert_all(({**asdict(f), "source": name} for name, facts in parsed[table] for f in facts),
                             pk=pk, replace=True)
    reports = sorted((r for r in parsed["avg_price"] if r[1]), key=lambda r: max(f.period for f in r[1]))
    prices, revisions = merge_prices(reports)
    db["avg_price"].insert_all((asdict(f) for f in prices), pk=TABLES["avg_price"][2])
    db["price_revisions"].insert_all(asdict(r) for r in revisions)


def summary(db_path: Path) -> str:
    db = sqlite_utils.Database(db_path)
    rows = db.query("select \"table\", status, count(*) n from parse_log group by 1, 2 order by 1, 2")
    return "\n".join(f"{r['table']:16}{r['status']:8}{r['n']:4}" for r in rows)


if __name__ == "__main__":
    out = Path(sys.argv[2] if len(sys.argv) > 2 else "tobacco.db")
    build(Path(sys.argv[1] if len(sys.argv) > 1 else "raw"), out)
    print(summary(out))
