# How much of a tax change reaches the shelf price, and who absorbs the rest?

Cigarette excise is `max(ad valorem % x price + specific, floor)` and, until 2024, the floor was higher for
cheap packs. A change in the tariff therefore moves different prices by different amounts: with the
pre-tax remainder held fixed, the cheapest packs (where the floor binds) rise by the largest percentage.

**Statistic, per price change published in the window around a tax change:**
- `implied_pct`: the price change if the pre-tax remainder (what is left after excise and VAT) did not move.
- `d_net`: the actual change in that remainder, EUR per pack. Zero = pure pass-through; positive = the
  manufacturer took extra; negative = absorbed part of the tax.
- Grouped by the tariff regime at the old price (raised minimum / minimum / ad valorem).

**Window:** a change published from 14 days before the effective date to 90 days after (or until the next
tax change). Prices are listed the day the BOE resolution is published, which can lag the effective date.

**Sample:** cigarette price changes in the BOE lists, packs of 20 (or no size printed), old price between
2.00 and 9.00. Anything not a plain re-listing of the same product name is ignored; a renamed product looks new.

**What would change my mind:** few changes in a group (n is shown), changes that mix tax with other repricing
(new formats, promotions), or a wave of changes spread over months so that other causes enter the window.

**Not done:** volumes. Brand sales are monthly shares from 2018 only, and listed names are not yet linked to them.
