# Does a brand's share move with the price change the tax forces on it?

**Idea:** a tax change lifts every price, but by different amounts depending on where a brand's price sits
(the floor, the specific/ad valorem split). That difference is set by the tariff and the brand's pre-event
price, not chosen by the brand. If share moves with it, the response of share to a relative price change can be
read from the tax change.

**Design (January 2025 tariff, the only change inside the 2018-2026 brand panel):**
- `forced`: log tax-implied price change at the brand's pre-event price, relative to the share-weighted market mean.
- Reduced form: change in log share (post window minus pre window) regressed on `forced`.
- First stage: change in log relative price regressed on `forced` (1 = tax passed through as implied).
- IV estimate = reduced form / first stage.

**Placebo in time:** the same regression at every other date outside an exclusion zone around the event, with the
shock this tariff change *would* force on the prices of that date. It shows how much share normally moves with price
level (trading down, cheap brands gaining or losing for other reasons) over a similar window. Each estimate is judged
in units of the placebo spread of its own specification.

## Decisions are parameters, not choices

Nothing below is picked by looking at which result looks best. The analysis runs the whole grid and reports all of it.

| Decision | Values run |
|---|---|
| Windows (months from the event, pre / post) | six: Oct-Nov / Mar-May; Jul-Nov / Mar-Aug; Oct-Nov / Jun-Sep; Oct-Nov / Jan-Mar; Sep-Nov / Apr-Jul; one month each side |
| Best sellers entering or leaving the list | `ols` (nothing), `stable_listing` (keep brands whose number of listed tier rows never changes), `theil_sen` (median of pairwise slopes), `huber` (down-weights large residuals) |
| Weighting of brands | `equal`, or `pre_share` (mean share before the event; a log-share change of a 0.1% brand is mostly noise) |
| Placebo exclusion zone | 4, 8 and 12 months either side of the event |

The earlier version of this analysis trimmed brands by the size of their share change, a threshold chosen after seeing
the outliers; the sign of the headline depended on it. Trimming on the outcome is not an option here.

**Rules fixed before reading the curve:**
- The design needs a first stage: if fewer than half of all specifications have one between 0.5 and 1.5, relative prices did not
  move as the tax implies, the shock is not a usable source of variation, and no sign is reported at all.
- Otherwise a sign is reported only if at least 90% of the usable specifications agree on it.
- The event is called distinguishable from background only if at least 90% of those specifications place it outside
  +/-2 placebo standard deviations.
- Otherwise the report says the data do not determine it.

**Disclosure:** the grid and these rules were written after a first run that showed the sign flipping; they are a
response to that, not independent of it. The first-stage rule was added after the grid's first run, when 6 of 72
specifications qualified and the "100% negative" among them was a statement about six cases. It does not depend on the sign. New data (a further tax change in the panel) is the only clean test.

**The assumption that matters:** the brands the tax pushes most are cheap brands. Anything else that moves cheap brands
differently in the same months (income, trading down, a promotion) is mistaken for a price response. The placebo
spread estimates how large that is on ordinary dates; it cannot rule out something specific to 2025.

**Limits:** about 14 brands; one event; brand prices are averages over variants, so the forced shock is approximate;
only best sellers are listed.
