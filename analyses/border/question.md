# Do tourist and border purchases respond to Spanish prices differently from residents'?

The Spanish literature reports the largest price responses in provinces that border France and Gibraltar and in
tourist provinces (see docs/learnings.md). The Comisionado reports split each province's sales into national
consumption and tourist-and-border consumption, so the two can be compared in the same provinces and months.

**Groups:** border = Girona, Guipuzcoa, Navarra, Lleida, Huesca; tourist = Balears, Malaga, Alicante. (The table lists
13 provinces; these are the ones that are mostly one or the other.)

**Primary quantity:** the *differential* elasticity, `d = b_tourist - b_national`: the coefficient on log price in
`log(tourist-and-border packs / national packs)`, with month-of-year effects, a trend and controls. Using the ratio
removes what moves both series at once (the national trend in smoking, weather, calendar). The two level elasticities
are shown beside it.

**Price:** the Spanish price index of the market-level analysis. What drives cross-border buying is the *difference*
with French, Andorran or Portuguese prices, which this repository does not have; a Spanish price change that coincides
with a French one would be mistaken for no effect.

**Tourist controls:** for the tourist group, log monthly international tourist arrivals to the matching regions (INE
FRONTUR; Andalucia stands in for Malaga, Comunitat Valenciana for Alicante, which overstates the region).

## Decisions are parameters, not choices

All run; the report shows the distribution. Specifications are not selected by how they look.

| Decision | Values run |
|---|---|
| Group | border; tourist |
| Outcome | ratio; tourist-and-border level; national level |
| Volume (levels only) | per covered month; per weekday; per Mon-Sat day |
| Price measure | chain-linked index; share-weighted mean price |
| Trend | linear, quadratic, cubic |
| Covid and border closures (Mar 2020 - Jun 2021) | ignore; dummy; drop |
| Stockpile months (Dec 2024, Jan 2025) | separate dummies; drop |
| Price lag | current month; mean of last 3; mean of last 6 |
| Arrivals control (tourist group only) | without; with |
| Sample start | 2019-01; 2021-07 (Covid choices then do not apply) |

**Rules fixed before reading the curve, applied to each group on the ratio outcome:**
1. If the median residual spread of log price after trend and season is below 0.02, no verdict.
2. If the median HAC standard error exceeds 0.35, no verdict (the data cannot separate a modest from a large difference).
3. The differential is called *negative* (tourist and border purchases more price-responsive than residents') only if at
   least 90% of specifications are negative, at least 90% have a 95% interval that excludes zero, and the baseline
   specification's placebo p-value is at most 0.10. Positive likewise. Otherwise: not determined by the data.
4. Placebo: the price series is rotated against the outcome by 12 or more months in either direction.

**Baseline specification (placebo only):** chain index, quadratic trend, Covid dummy, stockpile dummies, 3-month price
mean, start 2019-01, arrivals control for the tourist group.

**Not controlled:** foreign prices, exchange rates, border closures other than Covid, regional income, e-cigarettes, the
share of cross-border buying that is illicit.

**Limits:** about 90 months; the Spanish price moves in a few steps; tourist-and-border consumption collapsed and
recovered in 2020 to 2022 and tracks arrivals, which also move with the economy.
