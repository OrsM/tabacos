import re
from dataclasses import dataclass

from .errors import TableNotFound, UnsupportedLayout
from .numbers import es_decimal, es_percent

_NAMES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
          "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
_MONTH = re.compile(r"\b(%s)[a-z]*-(\d{2})\b" % "|".join(n[:3] for n in _NAMES), re.I)
_HEADING = re.compile(r"SEGMENTOS DE CIGARRILLOS M.S VENDIDOS")
_TIER = re.compile(r"^([A-ZÁÉÍÓÚ]+)\s{2,}.*\d+,\d+%\s*$")
_BRAND = re.compile(r"^(\S.*?)\s{2,}([A-Z][A-Z /.&]*?)\s+(\d,\d\d)\s+(\d+,\d+%)\s*$")


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
    name, yy = _MONTH.search(text).groups()
    month = f"20{yy}-{[n[:3] for n in _NAMES].index(name.lower()) + 1:02d}"
    facts, tier = [], None
    for line in text.splitlines()[3:]:
        if (m := _BRAND.match(line)):
            facts.append(SegmentSale(month, tier, m[1], m[2], es_decimal(m[3]), es_percent(m[4])))
        elif (m := _TIER.match(line)):
            tier = m[1]
    if not facts:
        raise UnsupportedLayout("segments: no brand rows recognised")
    return facts
