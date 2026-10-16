# tabacos

Spain's monthly tobacco market reports (Comisionado para el Mercado de Tabacos)
parsed into SQLite and served with Datasette.

    ./fetch.sh                      download the PDFs listed in sources/es.urls
    uv run pytest                   parser tests (fixtures are excerpts of real reports)
    uv run python -m tabacos.build  raw/*.pdf -> tobacco.db
    uv run datasette tobacco.db -m metadata.yml

Needs `pdftotext` (poppler). Every parse is gated by a reconciliation check:
rows must sum to the printed total (within rounding) or the build fails.

Status and the SICP angle: docs/DESIGN.md.

## Source and licence of the data

All data comes from the monthly reports of the Comisionado para el Mercado de Tabacos
(https://www.hacienda.gob.es/Tabacos/). Reuse is free under Ley 37/2007 provided the source
is cited and the content is neither altered nor its meaning distorted. Values are stored as
published; apparent errors are flagged in docs/DESIGN.md, not corrected. The PDFs themselves
are not in this repository (`./fetch.sh` downloads them); `tests/fixtures/` holds short excerpts.
