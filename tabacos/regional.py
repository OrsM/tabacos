import re
from dataclasses import dataclass
from datetime import date

from . import months
from .errors import TableNotFound, UnsupportedLayout
from .numbers import es_int

ROUNDING_SLACK = 5
_ROW = re.compile(r"^\s*(\S.*?)\s{2,}(\d[\d.]*)\s+(\d[\d.]*)\s+-?[\d,]+%\s*$")
_DATE = re.compile(r"\b(\d{1,2})-([A-Za-z]{3})-(\d{2})\b")


class ReconciliationError(UnsupportedLayout):
    pass


@dataclass(frozen=True)
class RegionalSales:
    region: str
    period_end: date
    packs_ytd: int
    basis: str = "current"      # "current": the report's own period; "prior": its prior-year column


def _period_ends(text: str) -> tuple[date, date]:
    """(current, prior-year) dates of the nearest "Hasta ... 30-Jun-25  30-Jun-24" line."""
    line = next(l for l in reversed(text.splitlines()) if _DATE.search(l))
    (d1, m1, y1), (d2, m2, y2) = _DATE.findall(line)[:2]
    return (date(2000 + int(y1), months.number(m1), int(d1)), date(2000 + int(y2), months.number(m2), int(d2)))


def parse_regional(text: str) -> list[RegionalSales]:
    """Cumulative cigarette packs (20 units) per autonomous community, for the report's period and for
    the same period a year earlier (basis="prior").

    Raises ReconciliationError when either column does not sum to its printed total within ROUNDING_SLACK.
    """
    at = text.find("AUTONOMAS")
    if at < 0:
        raise TableNotFound("regional sales")
    end, prior_end = _period_ends(text[max(0, at - 400):at])     # the date line sits above the column header
    rows, total = [], None
    for line in text[at:].splitlines():
        m = _ROW.match(line)
        if not m:
            continue
        name, cur, prior = m.group(1), es_int(m.group(2)), es_int(m.group(3))
        if name == "Totales":
            total = (cur, prior)
            break
        rows.append((name, cur, prior))
    sums = (sum(r[1] for r in rows), sum(r[2] for r in rows))
    if total is None or any(abs(a - b) > ROUNDING_SLACK for a, b in zip(sums, total)):
        raise ReconciliationError(f"regional rows {sums} do not sum to total {total}")
    return ([RegionalSales(n, end, c) for n, c, _ in rows]
            + [RegionalSales(n, prior_end, p, "prior") for n, _, p in rows])
