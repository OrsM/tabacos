import re
from dataclasses import dataclass
from datetime import date, datetime

from .errors import TableNotFound, UnsupportedLayout
from .numbers import es_int

ROUNDING_SLACK = 5
_MONTHS = {"Ene": 1, "Feb": 2, "Mar": 3, "Abr": 4, "May": 5, "Jun": 6,
           "Jul": 7, "Ago": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dic": 12}
_ROW = re.compile(r"^\s*(\S.*?)\s{2,}(\d[\d.]*)\s+(\d[\d.]*)\s+-?[\d,]+%\s*$")
_DATE = re.compile(r"\b(\d{1,2})-([A-Za-z]{3})-(\d{2})\b")


class ReconciliationError(UnsupportedLayout):
    pass


@dataclass(frozen=True)
class RegionalSales:
    region: str
    period_end: date
    packs_ytd: int


def _period_end(text: str) -> date:
    line = next(l for l in reversed(text.splitlines()) if _DATE.search(l))
    d, mon, yy = _DATE.search(line).groups()          # first date on the line is the current year
    return date(2000 + int(yy), _MONTHS[mon.capitalize()], int(d))


def parse_regional(text: str) -> list[RegionalSales]:
    """Cumulative cigarette packs (20 units) per autonomous community.

    Raises ReconciliationError when rows do not sum to the printed total
    within ROUNDING_SLACK.
    """
    at = text.find("AUTONOMAS")
    if at < 0:
        raise TableNotFound("regional sales")
    end = _period_end(text[max(0, at - 400):at])     # the "Hasta ... 30-Jun-25 30-Jun-24" line sits above
    text = text[at:]
    rows, total = [], None
    for line in text.splitlines():
        m = _ROW.match(line)
        if not m:
            continue
        name, cur = m.group(1), es_int(m.group(2))
        if name == "Totales":
            total = cur
            break
        rows.append(RegionalSales(name, end, cur))
    if total is None or abs(sum(r.packs_ytd for r in rows) - total) > ROUNDING_SLACK:
        raise ReconciliationError(f"regional rows do not sum to total {total}")
    return rows
