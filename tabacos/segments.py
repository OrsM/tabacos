import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

import pdfplumber

from .errors import TableNotFound, UnsupportedLayout
from . import months
from .numbers import es_decimal, es_percent

_MONTH = months.LABEL
_HEADING = re.compile(r"SEGMENTOS DE CIGARRILLOS M.S VENDIDOS")
_TIER = re.compile(r"^([A-ZÁÉÍÓÚ]+)\s{2,}.*\d+,\d+%\s*$")
_BRAND = re.compile(r"^(\S.*?)\s{2,}([A-Z][A-Z /.&]*?)\s+(\d,\d\d)\s+(\d+,\d+%)\s*$")


def _month_iso(name: str, yy: str) -> str:
    return f"20{yy}-{months.number(name):02d}"


@dataclass(frozen=True)
class SegmentSale:
    month: str
    tier: str
    brand: str
    company: str
    price: float
    share_pct: float


def parse_segments(text: str) -> list[SegmentSale]:
    """Best-selling cigarette brands per price tier; share is of that month's packs."""
    start = _HEADING.search(text)
    if not start:
        raise TableNotFound("best-selling segments")
    text = text[start.start():].split("VENTAS DE CIGARRILLOS")[0]
    if not _MONTH.search(text):
        raise UnsupportedLayout("segments: no month in header")
    month = _month_iso(*_MONTH.search(text).groups())
    facts, tier = [], None
    for line in text.splitlines()[3:]:
        if (m := _BRAND.match(line)):
            facts.append(SegmentSale(month, tier, m[1], m[2], es_decimal(m[3]), es_percent(m[4])))
        elif (m := _TIER.match(line)):
            tier = m[1]
    if not facts:
        raise UnsupportedLayout("segments: no brand rows recognised")
    return facts


# --- 2018-2023 reports: a bordered table, read from the PDF rather than its text ---

_PRICE = re.compile(r"\d,\d\d")
_SHARE = re.compile(r"\d+,\d+%")
_HEADER_PAGE = re.compile(r"^\s*SEGMENTOS\s+Cajetillas", re.M)


def _cells(row: list) -> list[str]:
    return [" ".join((c or "").split()) for c in row]


def segments_from_rows(rows: list[list]) -> list[SegmentSale]:
    """Brand rows of the segments table, given its rows from the first page on (header included).

    Only the current-year price and share are kept; the table repeats the prior year beside them.
    """
    month, tier, facts = None, None, []
    for row in rows:
        label, company, *rest = _cells(row) + ["", ""]
        rest = [c for c in rest if c]
        if "Precio Medio" in rest or label == "CATEGORÍA":
            if m := next((_MONTH.fullmatch(c) for c in rest if _MONTH.fullmatch(c)), None):
                month = _month_iso(*m.groups())
        elif company and len(rest) >= 2 and _PRICE.fullmatch(rest[0]) and _SHARE.fullmatch(rest[1]):
            facts.append(SegmentSale(month, tier, label, company, es_decimal(rest[0]), es_percent(rest[1])))
        elif label.isupper() and not company and label != "SEGMENTOS":
            tier = label
    if not rows or month is None:
        raise TableNotFound("segments table (2018-2023 layout)")
    if not facts:
        raise UnsupportedLayout("segments: no brand rows recognised")
    return facts


def _is_segment_table(rows: list[list]) -> bool:
    return bool(rows) and _cells(rows[0])[0] == "SEGMENTOS" and "Cajetillas" in _cells(rows[0])


def _continuation(page) -> list[list]:
    """Rows of the segments table carrying on at the top of `page`: with or without a repeated header."""
    for table in page.find_tables():
        if table.bbox[1] > 150:
            break
        rows = table.extract()
        first = _cells(rows[0])
        if first[0] == "SEGMENTOS" and not _is_segment_table(rows):
            return []                                   # another product's table starts the page
        if any(len(c := _cells(r)) > 2 and c[1] and _SHARE.search(" ".join(c)) for r in rows):
            return rows
    return []


def parse_segments_pdf(pdf_path: Path) -> list[SegmentSale]:
    """Segments table of a 2018-2023 report. Raises TableNotFound when the report has none."""
    pages = subprocess.run(["pdftotext", "-layout", str(pdf_path), "-"],
                           check=True, capture_output=True, text=True).stdout.split("\f")
    hit = next((i for i, t in enumerate(pages) if _HEADER_PAGE.search(t)), None)
    if hit is None:
        raise TableNotFound("segments table (2018-2023 layout)")
    with pdfplumber.open(pdf_path) as pdf:
        rows = []
        for table in pdf.pages[hit].find_tables():
            if _is_segment_table(table.extract()):
                rows = table.extract()
        if hit + 1 < len(pdf.pages):
            rows += _continuation(pdf.pages[hit + 1])
    return segments_from_rows(rows)
