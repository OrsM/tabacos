# How does total cigarette volume respond to the price level?

The brand panel could not identify a share elasticity (see the panel and taxshock reports). This asks the coarser
question the data may support: the response of total national volume to an index of cigarette prices.

**Model:** `log(volume per period) = constant + b * log(price index) + month-of-year effects + trend + controls + error`
for the months 2019 onward, with Newey-West errors (6 lags). `b` is the elasticity of volume to price. The trend
absorbs the long decline in smoking; the price coefficient is then identified from price moves that depart from it
(the steps of 2022-23 and January 2025).

**Price:** a chain-linked (Tornqvist) index of the listed best sellers, or the share-weighted mean listed price.
The monthly average price published for all cigarettes exists only from 2024, so it cannot be the regressor.

**Volume:** packs distributed to tobacconists (sell-in), per covered month, per weekday or per Mon-Sat day.

## Decisions are parameters, not choices

All run; the report shows the whole distribution.

| Decision | Values run |
|---|---|
| Price measure | chain-linked index; share-weighted mean price |
| Volume | per covered month; per weekday; per Mon-Sat day |
| Trend | none, linear, quadratic, cubic |
| Covid (Mar 2020 - Jun 2021) | ignore; dummy; drop |
| Stockpile around the 1 Jan 2025 rise (Dec 2024, Jan 2025) | ignore; separate dummies; drop |
| Price lag | current month; mean of last 3 months; mean of last 6 |
| Sample start | 2019-01; 2021-07 (after Covid; the Covid choices then do not apply) |

**Rules fixed before reading the curve:**
1. **Identifying variation.** If the median specification leaves a standard deviation of residual log price below 0.02
   (price does not move independently of trend and season), no elasticity is reported.
2. **Precision.** If the median HAC standard error exceeds 0.35, the data cannot tell an inelastic response (-0.3) from a unit
   elastic one (-1), and the report says so instead of a number.
3. **Sign.** Reported only if at least 90% of specifications agree on it.
4. **Distinguishable from zero.** Only if at least 90% of specifications have a 95% interval that excludes zero and the
   baseline specification's placebo p-value is at most 0.10.
5. **Placebo:** the price series is rotated against volume by 12 or more months in either direction; the baseline specification's
   coefficient is compared with those rotations (they keep the price path's shape and autocorrelation, not its timing).
6. Otherwise: the data do not determine the elasticity, and the report gives the range of the central 80% of estimates.

**Baseline specification** (for the placebo only): chain index, per weekday, quadratic trend, Covid dummy, stockpile dummies,
3-month price mean, start 2019-01. It is a reference point, not a preferred estimate.

**Not controlled:** income and the general price level, the share of illicit trade, e-cigarette substitution, the smoking
ban timeline, regional tourism. Any of these that trends differently from the quadratic trend is mistaken for a price response.

**Limits:** about 90 months, three price steps, one stockpile event; volume is sell-in to tobacconists, not sales to smokers;
the price index covers best sellers only.
