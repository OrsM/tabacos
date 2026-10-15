import re
from dataclasses import dataclass

from .numbers import es_decimal

_PRODUCTS = ("cigarr", "liar", "pipa")
_NAMES = {"cigarr": "cigarrillos", "liar": "liar", "pipa": "pipa"}
_YEAR = re.compile(r"\d{4}")
_MONTH = re.compile(r"[A-Za-z]{2,5}-(\d{2})")
_VALUE = re.compile(r"\d,\d\d")
_SPLIT = re.compile(r"\d,\d")


@dataclass(frozen=True)
class AvgPrice:
    product: str
    period: str   # "2023" (annual) or "2024-10" (month)
    price: float


def _labels(lines: list[str], i: int) -> tuple[list[str], int]:
    """Header run of year / month labels -> periods. Months are numbered by position."""
    periods, month = [], 0
    while i < len(lines):
        line = lines[i]
        if _YEAR.fullmatch(line):
            periods.append(line)
        elif m := _MONTH.fullmatch(line):
            month += 1
            periods.append(f"20{m[1]}-{month:02d}")
        else:
            break
        i += 1
    return periods, i


def _values(lines: list[str], i: int, n: int) -> tuple[list[float], int]:
    """n prices; the oldest layout splits '3,76' into '3,7' and '6'."""
    out = []
    while len(out) < n:
        if i >= len(lines):
            raise ValueError("price table ended early")
        line = lines[i]
        if _VALUE.fullmatch(line):
            out.append(es_decimal(line))
        elif _SPLIT.fullmatch(line) and i + 1 < len(lines) and re.fullmatch(r"\d", lines[i + 1]):
            i += 1
            out.append(es_decimal(line + lines[i]))
        else:
            raise ValueError(f"expected {n} prices, got {len(out)} before {line!r}")
        i += 1
    return out, i


def parse_prices(raw: str) -> list[AvgPrice]:
    """Average price per product: annual from 2011, then months of the current year.

    Takes `pdftotext -raw` output. Raises ValueError unless every product has
    exactly one price per header label.
    """
    lines = [l.strip() for l in raw.splitlines() if l.strip()]
    start = next(k for k, l in enumerate(lines) if l.startswith("PRECIO MEDIO POR CATEGOR"))
    periods, i = _labels(lines, start + 1)
    facts = []
    for _ in _PRODUCTS:
        key = next(p for p in _PRODUCTS if lines[i].lower().startswith(p))
        i += 1
        if lines[i].isalpha():          # "Cigarrill" / "os"
            i += 1
        values, i = _values(lines, i, len(periods))
        facts += [AvgPrice(_NAMES[key], p, v) for p, v in zip(periods, values)]
    return facts


def merge_prices(reports: list[list[AvgPrice]]) -> list[AvgPrice]:
    """Union of reports' prices; raises ValueError if two reports disagree on one (product, period)."""
    merged: dict[tuple[str, str], AvgPrice] = {}
    for fact in (f for facts in reports for f in facts):
        old = merged.setdefault((fact.product, fact.period), fact)
        if old.price != fact.price:
            raise ValueError(f"reports disagree on {fact.product} {fact.period}: {old.price} vs {fact.price}")
    return list(merged.values())
