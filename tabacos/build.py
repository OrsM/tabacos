"""raw/*.pdf -> tobacco.db. Usage: python -m tabacos.build [raw_dir] [db_path]"""
import subprocess
import sys
from dataclasses import asdict
from pathlib import Path

import sqlite_utils

from .regional import parse_regional
from .segments import parse_segments


def pdf_text(pdf: Path) -> str:
    return subprocess.run(["pdftotext", "-layout", str(pdf), "-"],
                          check=True, capture_output=True, text=True).stdout


def build(raw: Path, db_path: Path) -> None:
    db_path.unlink(missing_ok=True)
    db = sqlite_utils.Database(db_path)
    for pdf in sorted(raw.glob("*.pdf")):
        text = pdf_text(pdf)
        src = {"source": pdf.name}
        db["regional_sales"].insert_all(
            ({**asdict(f), **src} for f in parse_regional(text)),
            pk=("region", "period_end"), replace=True)
        db["segment_sales"].insert_all(
            ({**asdict(f), **src} for f in parse_segments(text)),
            pk=("month", "tier", "brand", "price"), replace=True)


if __name__ == "__main__":
    build(Path(sys.argv[1] if len(sys.argv) > 1 else "raw"),
          Path(sys.argv[2] if len(sys.argv) > 2 else "tobacco.db"))
