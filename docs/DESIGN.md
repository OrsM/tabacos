# Design

Goal: query Spanish tobacco sales and prices, then add other countries.
Reports change layout between years, so the design bet is: small parsers
per table and era, one gate (reconciliation) that tells us when a layout moved.

## Done (spike -> scaffold)
- regional cumulative sales (16 communities, reconciled to printed total, +-5 packs)
- best-selling brands per price tier (two header eras, tables split across pages)
- average price per product (annual 2011-, plus months of the current year): parsed from
  `pdftotext -raw`, where all three layout eras reduce to labels, then name, then values.
  Reports are merged and the build fails if two reports disagree (0 of 69 overlaps do).

## Coverage of the 77 reports (2018-2026)
Every table of every report is logged in `parse_log` as ok / absent (table not in that
report) / failed (table there, parser cannot read it). `build` prints the counts.

- regional_sales: ok 77/77 (anchored on the "AUTONOMAS" column header; it wraps onto its own line in some reports).
- avg_price (annual + monthly series): ok on all 30 reports that have it, 2024-01 onwards.
  Earlier reports never had this table. Reports are merged oldest first, a newer report
  revises an older one, and revisions are kept in `price_revisions` (4 of 129 overlaps:
  Feb-2024 as first published, and pipe tobacco Jan-2026 4.37 -> 4.79).
- segment_sales (best-selling brands): ok 28, failed 1 (Jan-2024 has no share column),
  absent 48. The 48 are 2018-2023 reports whose table is titled just "SEGMENTOS DE
  CIGARRILLOS" with current-year and prior-year columns, wrapped brand names and sidebar
  text at page breaks, in at least three header variants. Not written yet.

## Known gaps
- Average price per year does not exist before 2024 reports; 2011-2023 annual prices
  come from later reports, so no earlier history by month.
- Source anomaly, published as is in two reports (Jun-2024 and Oct-2024): cigarrillos
  2024-06 = 4.61 against 4.97-5.09 for the other nine months of 2024.
- Price parser cannot detect a missing value in the last product's (pipa) row, because
  chart text following the table also looks like prices.
- Province, distributor, monthly volume tables are not parsed.
- July reports do not exist; 2014-2017 and most of 2018-2019 URLs were not found.
- Brand shares are top brands only (~65%), not market totals.

## SICP as method (one idea per chapter, only where it earns its keep)
1. Procedures: parsers are pure text -> facts functions; numbers.py is the base layer.
2. Data: facts are frozen records; downstream (build, SQL) sees only their fields.
   Next: dispatch on (table, era) through a table of parsers instead of if-chains
   (data-directed programming) once a second era of any table needs handling.
3. Streams: raw/ -> text -> facts as a lazy pipeline; build is the only place with state.
4. Metalinguistic: when 3+ parsers repeat the same row-regex shape, describe tables
   declaratively (columns, types, total row) and write one interpreter for them.
5. Compilation: not planned; revisit only if the interpreter is the bottleneck.
