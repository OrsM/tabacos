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

## Known gaps
- Price table: the Oct-2024 "difference" was a misread. That file lists 2011-2023 then
  months of 2024; the Jun-2025 file lists 2011-2024 then months of 2025. Same numbers.
- Source anomaly, kept as published: cigarrillos 2024-06 = 4.61 in the Oct-2024 report,
  against 4.97-5.09 for the other nine months. Only one report carries it, so unresolved.
- Price parser cannot detect a missing value in the last product's (pipa) row, because
  chart text following the table also looks like prices.
- Province, distributor, monthly tables not parsed.
- Regional parser assumes one header era; April 2024 passes, nothing older tried.
- Brand shares are top-brands only (~65%), not market totals.

## SICP as method (one idea per chapter, only where it earns its keep)
1. Procedures: parsers are pure text -> facts functions; numbers.py is the base layer.
2. Data: facts are frozen records; downstream (build, SQL) sees only their fields.
   Next: dispatch on (table, era) through a table of parsers instead of if-chains
   (data-directed programming) once a second era of any table needs handling.
3. Streams: raw/ -> text -> facts as a lazy pipeline; build is the only place with state.
4. Metalinguistic: when 3+ parsers repeat the same row-regex shape, describe tables
   declaratively (columns, types, total row) and write one interpreter for them.
5. Compilation: not planned; revisit only if the interpreter is the bottleneck.
