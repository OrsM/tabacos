# What can the brand panel say about price and share?

**Panel:** one row per brand and month (`brand_month`): share of the listed best sellers and share-weighted price.
Tiers of a brand are merged. Only best sellers are listed, so a brand can drop out of a month.

**Relative price:** log price minus log of the month's share-weighted market price. A tax change that moves
every price moves the market price with it, so it drops out. What is left is a brand's price against the others.

**Questions of this first look:**
1. How much brand-specific price variation is there? (If prices move together, an elasticity cannot be read off them.)
2. Is the spread of prices across brands compressing, as the tax structure predicts?
3. What does a plain fixed-effects slope of log share on log relative price give, and how wide is its interval?

**Slope:** differences between months `lag` apart (brand effects drop out), both variables centred within the
month, standard error clustered by brand. Longer lags give prices more room to move but overlap, and brands that
reprice may be changing for other reasons (new variants, positioning).

**What would change my mind:** an interval that excludes zero at every lag; a spread that moves with something
other than composition of the list.
