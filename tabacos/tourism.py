import re
from dataclasses import dataclass
from datetime import date

from . import months
from .errors import TableNotFound, UnsupportedLayout
from .numbers import es_int
from .regional import ReconciliationError

SLACK = 10
_NUM = r"(\d[\d.]*)"
# The two percentage columns are ignored: they wrap, lose their sign or lose their % across lines.
# The name is optional: in some reports it sits on the line above or below its numbers.
_ROW = re.compile(rf"^\s*(?:([^\d\n]*?[^\d\s])\s+)?{_NUM}\s+{_NUM}\s+\S+\s+{_NUM}\s+{_NUM}(?:\s+\S+)?\s*$")
_ZONES = {"Frontera", "Turístico"}
# The report lists the same rows in the same order in every year (checked on 66 reports).
AREAS = ["Alicante/Alacant", "Almería", "Balears (Illes)", "Barcelona", "Girona", "Granada", "Guipúzcoa",
         "Huesca", "Lleida", "Málaga", "Murcia", "Navarra", "Tarragona", "Resto Provincias",
         "Frontera", "Turístico", "Total"]


@dataclass(frozen=True)
class TouristSales:
    area: str
    kind: str            # "province" (provinces + the rest) or "zone" (border / tourist); each partition sums to the total
    period_end: date
    national_ytd: int    # packs of 20, year to date
    tourist_ytd: int     # tourist and border consumption


def parse_tourism(text: str) -> list[TouristSales]:
    """Cigarette packs by province and by border/tourist zone, national vs tourist-and-border consumption.

    Rows are matched to AREAS by order; a name printed on a row must agree. Raises UnsupportedLayout
    unless there are 17 rows, and ReconciliationError unless both partitions sum to the printed total.
    """
    at = text.find("Consumo Nacional")
    if at < 0:
        raise TableNotFound("tourism and border")
    text = text[at:]
    if (label := months.find(text)) is None:
        raise UnsupportedLayout("tourism table: no month in header")
    end = months.month_end(*label)
    rows = [m for m in map(_ROW.match, text.splitlines()) if m][:len(AREAS)]
    if len(rows) < len(AREAS):
        raise UnsupportedLayout(f"tourism table: {len(rows)} numeric rows, expected {len(AREAS)}")
    facts = []
    for area, m in zip(AREAS, rows):
        printed = {"Provincias": "Resto Provincias"}.get(m[1], m[1])
        if printed and printed != area:
            raise UnsupportedLayout(f"tourism table: row {area!r} is printed as {printed!r}")
        facts.append(TouristSales(area, "zone" if area in _ZONES else "province", end, es_int(m[2]), es_int(m[4])))
    total = facts.pop()
    for k in ("province", "zone"):
        part = (sum(f.national_ytd for f in facts if f.kind == k), sum(f.tourist_ytd for f in facts if f.kind == k))
        if any(abs(a - b) > SLACK for a, b in zip(part, (total.national_ytd, total.tourist_ytd))):
            raise ReconciliationError(f"tourism {k} rows {part} do not sum to total {total}")
    return facts
