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
- Windows: pre = Oct-Nov 2024, post = Mar-May 2025, so the January stockpile and its unwinding are out.

**Placebo in time:** the same regression at every other date at least 8 months from the event, with the shock this
tariff change *would* force on the prices of that date. It shows how much share normally moves with price level
(trading down, cheap brands gaining or losing for other reasons) over a similar window. The event's reduced form is
judged against that spread, not against zero.

**The assumption that matters:** brands that the tax pushes more are cheap brands. Anything else that moves cheap brands
differently from dear ones in the same months (income, trading down, a promotion) is mistaken for a price response.
The placebo distribution estimates how large that is on ordinary dates; it cannot rule out something specific to 2025.

**What would change my mind:** an event estimate inside the placebo spread; a first stage far from 1 (the tax is not
what moved prices); results that change sign across reasonable windows.

**Limits:** 15 or so brands; one event; brand prices are averages over variants, so the forced shock is approximate;
only best sellers are listed.
