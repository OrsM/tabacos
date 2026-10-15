# Design

Goal: query Spanish tobacco sales and prices, then add other countries.
Reports change layout between years, so the design bet is: small parsers
per table and era, one gate (reconciliation) that tells us when a layout moved.

## Done (spike -> scaffold)
- regional cumulative sales (16 communities, reconciled to printed total, +-5 packs)
- best-selling brands per price tier (two header eras, tables split across pages)

## Known gaps
- Annual price series ("PRECIO MEDIO POR CATEGORIAS") not parsed: the Oct-2024
  file shows different recent-year values than the 2025 files. Understand why first.
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
