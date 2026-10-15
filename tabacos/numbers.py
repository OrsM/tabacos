import re

_INT = re.compile(r"-?\d{1,3}(\.\d{3})+|-?\d+")


def es_int(s: str) -> int:
    """'1.234' -> 1234. Raises ValueError unless s is a whole number."""
    if not _INT.fullmatch(s):
        raise ValueError(f"not a Spanish integer: {s!r}")
    return int(s.replace(".", ""))


def es_decimal(s: str) -> float:
    """'5,97' -> 5.97."""
    return float(s.replace(".", "").replace(",", "."))


def es_percent(s: str) -> float:
    """'-2,56%' -> -2.56."""
    return es_decimal(s.rstrip("%"))
