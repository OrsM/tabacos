# Sources to join to the Comisionado data

Status: **probed** = an endpoint answered with data; **found** = seen in a search result only.

## Already in the 77 reports, not yet parsed
- Tourist and border consumption by province ("VENTAS DE CIGARRILLOS TURISMO Y FRONTERA"):
  national vs tourist/border packs, cumulative, per province (Girona, Guipuzcoa, Navarra,
  Lleida, Balears, Malaga, Alicante...) plus totals for Frontera / Turistico. Present in all 77
  reports (text check). The cheapest way to separate tourist from resident demand.
- Brand tier share totals, province sales, distributor volumes, roll-your-own and pipe segments.

## INE open API (probed, JSON, no key): https://servicios.ine.es/wstempus/js/ES/
- Tourist arrivals, op 330 (FRONTUR): monthly from 2015; tables by destination region
  (10823, 75720), by country of residence (10822, 75719).
- Tourist spending, op 329 (EGATUR): monthly from 2015; by region (10839, 75714).
- CPI, op 25: group "Bebidas alcoholicas y tabaco" (alcohol and tobacco together), national and by
  region (tables 76125, 76136), and at constant taxes (76131). Index at current vs constant taxes
  is a way to read off tax pass-through; the group mixes alcohol, so tobacco-only is not yet found.
- Population by age: op 22 / 326 (population figures, projections) exist; the age-by-region
  table id is NOT yet identified.

## BOE open API (probed): https://www.boe.es/datosabiertos/api/ (send `Accept: application/json`)
- Daily summaries (`/boe/sumario/YYYYMMDD`) answered with JSON. The Comisionado publishes
  retail price lists (PVP) per brand in BOE resolutions several times a month (found for 2025:
  BOE-A-2025-3558, -5112, -5742, -7437, -8366, -9150, -9741): brand-level price-change events,
  not yet fetched.
- Consolidated law metadata answered (`/legislacion-consolidada/id/BOE-A-1992-28741/metadatos`,
  Ley 38/1992 on special taxes); full text index is available as XML. Rate history by version not
  yet extracted. A search result states that from 1 Jan 2025 cigarettes carry 48.5% ad valorem plus
  33.5 EUR per 1000 with a 150 EUR per 1000 minimum; verify against the BOE text before using.

## Consumption and prevalence
- EDADES (Ministerio de Sanidad): daily smokers aged 15-64 fell from 34.9% (1997) to 25.8% (2024),
  per press coverage (found). Microdata/tables format not yet checked.
- Not found: any public brand-by-age data. Brand loyalty by age cannot be measured directly from public
  sources; only region-level proxies (age structure vs brand share) are possible.

## Cross-country
- EU excise rates: European Commission TAXUD tables and Tax Foundation summaries (found, not probed).
