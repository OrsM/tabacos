import re
from dataclasses import dataclass
from datetime import date, datetime

from .numbers import es_int

ROUNDING_SLACK = 5
_MONTHS = {"Ene": 1, "Feb": 2, "Mar": 3, "Abr": 4, "May": 5, "Jun": 6,
           "Jul": 7, "Ago": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dic": 12}
_ROW = re.compile(r"^\s*(\S.*?)\s{2,}(\d[\d.]*)\s+(\d[\d.]*)\s+-?[\d,]+%\s*$")
_DATE = re.compile(r"\b(\d{1,2})-([A-Za-z]{3})-(\d{2})\b")


class ReconciliationError(ValueError):
    pass


@dataclass(frozen=True)
class RegionalSales:
    region: str
    period_end: date
    packs_ytd: int


def _period_end(text: str) -> date:
    d, mon, yy = _DATE.search(text).groups()
    return date(2000 + int(yy), _MONTHS[mon.capitalize()], int(d))


def parse_regional(text: str) -> list[RegionalSales]:
    """Cumulative cigarette packs (20 units) per autonomous community.

    Raises ReconciliationError when rows do not sum to the printed total
    within ROUNDING_SLACK.
    """
    text = text[text.index("Ventas por Autonom"):]
    end = _period_end(text)
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
