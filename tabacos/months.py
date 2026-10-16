import calendar
import re
from datetime import date

NAMES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
         "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
LABEL = re.compile(r"\b(%s)[a-z]*-(\d{2})\b" % "|".join(n[:3] for n in NAMES), re.I)   # "Junio-25", "jun-25"


def number(name: str) -> int:
    """'Junio' / 'jun' -> 6."""
    return [n[:3] for n in NAMES].index(name.lower()[:3]) + 1


def month_end(year: int, month: int) -> date:
    return date(year, month, calendar.monthrange(year, month)[1])


_WRAPPED = re.compile(r"\b(%s)[a-z]*-[^\d]*?\b(\d{2})\b" % "|".join(n[:3] for n in NAMES), re.I)


def find(text: str) -> tuple[int, int] | None:
    """(year, month) of the first month label, also when the year wraps onto a later line."""
    m = _WRAPPED.search(text)
    return (2000 + int(m[2]), number(m[1])) if m else None
