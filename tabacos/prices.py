import re
from dataclasses import dataclass

from .errors import TableNotFound, UnsupportedLayout
from .numbers import es_decimal

_PRODUCTS = ("cigarr", "liar", "pipa")
_NAMES = {"cigarr": "cigarrillos", "liar": "liar", "pipa": "pipa"}
_YEAR = re.compile(r"\d{4}")
_MONTH = re.compile(r"[A-Za-z]{2,8}-(\d{2})")
_VALUE = re.compile(r"\d,\d\d")
_PARTIAL = re.compile(r"\d,\d?")


@dataclass(frozen=True)
class AvgPrice:
    product: str
    period: str   # "2023" (annual) or "2024-10" (month)
    price: float


def _tokens(raw: str) -> list[str]:
    """Whitespace tokens with the PDF's fragments glued back: 'ene-'+'24', '3,'+'76', '3,7'+'6'."""
    out: list[str] = []
    for tok in raw.split():
        if out and (out[-1].endswith("-") and tok.isdigit()
                    or _PARTIAL.fullmatch(out[-1]) and _VALUE.fullmatch(out[-1] + tok)):
            out[-1] += tok
        else:
            out.append(tok)
    return out


def _labels(toks: list[str], i: int) -> tuple[list[str], int]:
    """Header run of year / month labels -> periods. Months are numbered by position."""
    periods, month = [], 0
    while i < len(toks):
        if _YEAR.fullmatch(toks[i]):
            periods.append(toks[i])
        elif m := _MONTH.fullmatch(toks[i]):
            month += 1
            periods.append(f"20{m[1]}-{month:02d}")
        else:
            break
        i += 1
    return periods, i


def _product(toks: list[str], i: int) -> tuple[str, int]:
    """Product name, possibly split over tokens ('Cigarr' 'illos')."""
    name = ""
    while i < len(toks) and toks[i].isalpha():
        name += toks[i].lower()
        i += 1
    key = next((p for p in _PRODUCTS if name.startswith(p)), None)
    if key is None:
        raise UnsupportedLayout(f"expected a product name, got {name or toks[i:i + 1]}")
    return _NAMES[key], i


def parse_prices(raw: str) -> list[AvgPrice]:
    """Average price per product: annual from 2011 (2012 in late 2025+), then months of the current year.

    Takes `pdftotext -raw` output. Raises UnsupportedLayout unless every product has
    exactly one price per header label.
    """
    toks = _tokens(raw)
    start = next((k for k, t in enumerate(toks) if t == "PRECIO" and toks[k + 1:k + 3] == ["MEDIO", "POR"]), None)
    if start is None:
        raise TableNotFound("average price series")
    i = start
    while i < len(toks) and not (_YEAR.fullmatch(toks[i]) or _MONTH.fullmatch(toks[i])):
        i += 1                      # skip the rest of the title
    periods, i = _labels(toks, i)
    facts = []
    for _ in _PRODUCTS:
        product, i = _product(toks, i)
        values = toks[i:i + len(periods)]
        if len(values) < len(periods) or not all(_VALUE.fullmatch(v) for v in values):
            raise UnsupportedLayout(f"{product}: expected {len(periods)} prices, got {values}")
        i += len(periods)
        facts += [AvgPrice(product, p, es_decimal(v)) for p, v in zip(periods, values)]
    return facts


@dataclass(frozen=True)
class Revision:
    product: str
    period: str
    old: float
    new: float
    old_source: str
    new_source: str


def merge_prices(reports: list[tuple[str, list[AvgPrice]]]) -> tuple[list[AvgPrice], list[Revision]]:
    """Union of reports given oldest first; on a conflict the newer report wins and the change is returned."""
    merged: dict[tuple[str, str], tuple[AvgPrice, str]] = {}
    revisions = []
    for source, facts in reports:
        for f in facts:
            old = merged.get((f.product, f.period))
            if old and old[0].price != f.price:
                revisions.append(Revision(f.product, f.period, old[0].price, f.price, old[1], source))
            merged[(f.product, f.period)] = (f, source)
    return [f for f, _ in merged.values()], revisions
