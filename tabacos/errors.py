class TableNotFound(LookupError):
    """The report has no such table (reports of some years never had it)."""


class UnsupportedLayout(ValueError):
    """The table is there but this parser cannot read it."""
