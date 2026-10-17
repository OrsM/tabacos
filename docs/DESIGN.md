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
- segment_sales (best-selling brands): ok 76 of 77, failed 1 (Jan-2024 has no share column).
  Two parsers, tried in order: the text one for 2024+ reports, and `parse_segments_pdf`
  for 2018-2023, which reads the bordered table with pdfplumber (wrapped cells come back
  whole; a table split across pages is followed onto the next page). Row counts are 19-20
  for 69 of 76 reports; 2025 reports list fewer brands (15-18). Months covered: 75,
  2018-02 .. 2026-08. Only the current-year price and share are kept; the prior-year
  columns beside them are not.

- tourist_sales (national vs tourist/border packs by province and by zone): ok 76 of 77. Rows are
  matched by order to the 17 fixed areas because names wrap above or below their numbers. Failed:
  Nov-2025, where one figure is split over two lines (the reconciliation gate catches it).

## Retail price lists (tabacos/pvp.py, BOE)
The Comisionado publishes new and changed retail prices in BOE resolutions (about 47 a year since 2018,
403 found by scanning every daily summary). 24,474 price listings, 1,918 for cigarettes. They take effect
the day of publication. Titles say "Peninsula y Baleares" or "del area del Monopolio"; some resolutions
also price Ceuta y Melilla, which are left out. A listing is not a full price list: a product appears when
its price is new or changes. `price_changes` compares consecutive listings of the same name; a renamed
product looks like a new one. Pack size is only known when the name says so (1,276 of 1,918 cigarette
listings do not).

### Linking BOE listings to the monthly brand tables: checked, not built
The monthly "Precio Medio" of a brand row is not a listed price: it is an average over the brand's
variants (Marlboro premium 5.97 in Jan 2025 against listings of 5.75-6.40). Exact price matching links
only 38% of brand rows (557 of 1,465); names also differ (Ducados Negro, BN). At brand level the segment
price minus the mean listed price of in-force variants has a median absolute gap of 0.19 EUR (90th
percentile 0.57) over 1,069 brand-months, so neither source can stand in for the other. 46 of 70 brand
price jumps of 2% or more have a BOE listing of that brand in the same or the previous month, so listings
can date a jump about two times in three. The `brand_month` view merges a brand's tiers (share summed,
price share-weighted) to give a series that does not change identity when the tier thresholds move.

## Analysis decisions are parameters
An analysis does not get to pick the specification that tells the cleanest story. Each analyst decision
(window, handling of list artefacts, weighting, exclusion zones) is a value in a grid; the runner executes the
whole grid, reports the distribution of results, and applies a verdict rule written in question.md before the
curve is read. taxshock is the first analysis built this way: of 144 specifications 19% have a usable first stage,
so the rule gives no verdict. Decisions made by hand elsewhere (panel lags, pass-through windows, 20-pack
assumption) are listed in the replies of 2026-10-16 and still to be moved into grids.

## Tourist and border data
The tourist-and-border table also carries last year's column; both are parsed (2019 goes from 1 to 11 months),
merged with the newest report winning, and the overlapping months agree (0 revisions, in the `revisions` table).
INE tourist arrivals by main destination region (FRONTUR, 7 regions plus the total) are committed as
`sources/ine/frontur-destination.csv` and loaded as `tourist_arrivals`. Eurostat's tobacco HICP (two ECOICOP versions, linked on
their overlap) and annual price level index give a monthly France-Spain and Portugal-Spain price gap (`foreign_price_gap`);
the annual index anchors each year, the HICP moves it within the year, and after 2024 it follows the HICP alone. Andorra and
Gibraltar are not in Eurostat.

## Tax structure (tabacos/tax.py, sources/boe/)
Cigarette excise = max(ad valorem % of the retail price incl. all taxes + specific EUR per 1000,
a floor). 19 versions of art. 60 since 1993, parsed from the BOE consolidated text (committed under
sources/boe/; `python -m tabacos.boe` refreshes them). From Dec 2012 until 2024 the floor was raised
for brands priced under 196 EUR per 1000 (3.92 per pack); the 2025 reform dropped the raised floor
and moved to 48.5% + 33.5 per 1000 with a single floor of 150 (the floor binds under 4.80 per pack).
Effective dates follow the law's own text, not the BOE version date, for four amendments (checked
in tests). Rows before 2002 are in pesetas and were not checked against anything but the law text.
`segment_tax` splits every brand price into excise, VAT and remainder.

## Known gaps
- Average price per year does not exist before 2024 reports; 2011-2023 annual prices
  come from later reports, so no earlier history by month.
- Source anomaly, published as is in two reports (Jun-2024 and Oct-2024): cigarrillos
  2024-06 = 4.61 against 4.97-5.09 for the other nine months of 2024.
- Price parser cannot detect a missing value in the last product's (pipa) row, because
  chart text following the table also looks like prices.
- Province, distributor, monthly volume tables are not parsed.
- July reports do not exist; 2014-2017 and most of 2018-2019 URLs were not found.
- `octubre21.pdf` is really the September 2021 report (published 19 Oct 2021, header and body say
  September); `enero26-2.pdf` repeats `enero26`. Both parse correctly by their own period; the
  January duplicate overwrites the first.
- Tier share totals (e.g. PREMIUM 60.56%) are in the tables but not stored; they would show
  the shift towards premium directly.
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
