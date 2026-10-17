# What a decade of Spanish cigarette sales can and cannot tell us

<!-- description: Spain's monthly cigarette sales, prices and tax law as one dataset: how a tax rise reaches the shelf, why the 2024 stockpile was the calendar, and what the data cannot identify. -->

*Draft for the website. Numbers come from the analyses in this repository and can be re-run
(`analyses/*/report.md`); literature notes come from abstracts and search summaries, marked where I have
not read the full paper. Check those against the primary sources before publishing.*

## In one paragraph

Spain's Comisionado para el Mercado de Tabacos publishes monthly PDF reports on cigarette sales and prices.
We turned 77 of them (2018 to 2026), the BOE's tax law and 700 BOE price resolutions into one queryable
database, then asked what drives volume and price. Short answers: the tax structure explains how a tax rise
reaches shelf prices; the apparent pre-tax stockpile of December 2024 is mostly a calendar effect; and the
data do not identify how brand shares or total volume respond to price any better than the existing literature
already says. The useful result is a map of what this kind of data can and cannot support.

## What we built

- 77 monthly reports parsed into regional sales, best-selling brands by price tier, tourist and border
  consumption, and average prices. Every table is checked against the printed totals; the regional table
  parses in all 77, and 1,022 region-months that appear in two reports never disagree.
- The tax history: 19 versions of the excise article since 1993 (euros, floor, raised floor) and the VAT rate,
  from the BOE's consolidated text.
- 39,232 retail price listings from 700 BOE resolutions since 2012.
- Everything public and reproducible: github.com/OrsM/tabacos.

## Six things we learned

1. **A tax rise is not one price rise.** Cigarette excise is `max(48.5% of price + 33.5 per 1000, 150 per 1000)`
   since January 2025 (51% + 24.7, floor 131.5, and a higher floor below 3.92 per pack before). Under the floor a
   price increase adds no tax, so the manufacturer keeps about 83% of each extra euro; above it, about 34%.
   Holding the pre-tax remainder fixed, the 2025 reform implies +1.5% for a premium pack and +7% to +11% for the cheapest.
2. **Prices followed the tax closely, with little extra.** Across six tax changes (2012 to 2025) the price
   changes of floor-priced packs sat within a point or two of the tax-implied change in most events. The excess
   over ordinary repricing was small in 2012 to 2016 and absent in early 2025. Ordinary repricing itself is large
   now: +3% to +7% per change in 2021 to 2025, against +1.1% in 2014 to 2017.
3. **The pre-tax stockpile was a calendar artefact.** Raw distributor sales were +11.2% in December 2024 and -10.8% in
   January 2025. December 2024 had 20 trading days, December 2023 had 18. Per trading day the swing (+6.6 points) lies inside
   the range of winters with no tax change (-0.9 to +7.6). Counting days (weekdays less national holidays) cut
   month-to-month noise from 6.6 to 4.6 points. Any study of monthly sales around a tax date needs this.
4. **Brand-level elasticities are not identified here.** A brand's price relative to the market moves by about 1% a month; its
   share moves far more. A fixed-effects slope has intervals of about -5 to +5 at a one-month horizon. The 2025 tax
   change, which pushes cheap brands harder, gave a usable first stage in 19% of 144 specifications, and the
   estimates scatter around zero inside the placebo spread. Brands entering or leaving the best-seller list
   create share jumps that look like demand shocks.
5. **Market-level volume against price is consistent with the literature but not independent evidence.** Across 864
   specifications the central 80% of elasticity estimates run from -1.29 to +0.10, median -0.36, 86% negative. The
   pre-stated rules do not let us report a number: price barely moves independently of trend and season (residual
   spread 0.011) and the answer depends mostly on the trend.

6. **Tourist and border purchases do not clearly respond more to Spanish prices than residents' do.** We compared
   tourist-and-border packs with national packs in the same provinces (3 tourist provinces, 5 border ones), using
   the same grid-and-rule approach. The pre-stated rules give no verdict for either group: price moves in too few
   steps, and the median standard error is 0.48 (tourist) and 1.04 (border). The estimates depend on the sample: for
   the tourist provinces the differential is -0.11 (median) over the whole period but -1.46 (100% of specifications
   negative, 92% with an interval excluding zero) when the sample starts in July 2021. That is the direction the Spanish
   literature reports, in a window where arrivals were recovering at the same time as prices rose. For border
   provinces the median differential against the Spanish price is positive (+1.08). Adding the French-Spanish price
   gap from Eurostat (France's tobacco price level was 1.5 times Spain's in 2018 and 2.3 to 2.4 times since 2021) does not
   settle it: the gap moves enough to be identified, but the estimate is centred near zero (median -0.09 on its own,
   +0.10 holding the Spanish price fixed) with a standard error of 0.49, and no specification family passes our rules.
   Treat the post-COVID tourist-province result as a lead, not a finding.

## How it sits with the literature

- **Size of the response.** A meta-analysis of 86 studies found a mean cigarette price elasticity of -0.48
   ([Gallet and List 2003, *Health Economics*](https://ideas.repec.org/a/wly/hlthec/v12y2003i10p821-835.html)); a
   study of 47 Spanish provinces opens by noting agreement on about -0.4, but finds long-run elasticities above
   one in absolute value in many provinces, largest in border and tourist provinces
   ([*Nicotine & Tobacco Research* 2021](https://reunir.unir.net/handle/123456789/11550)). Our median of -0.36 is
   in that range; our data cannot narrow it. The border and tourist split in the Comisionado reports is a direct way to look at
   that second result (item 6): the post-COVID tourist-province estimate points the same way, the full-period and
   border-province estimates do not, and none of it passes our rules.
- **Segments.** A recent preprint estimates elasticities for low-, medium- and high-priced Spanish cigarettes using
   official sales data 2005 to 2025
   ([Research Square](https://www.researchsquare.com/article/rs-9967642/v2); I could not read it). It is the closest
   prior work. Our brand and tier data suggest that identifying segment elasticities is harder than the headline
   numbers imply, and this should be checked against how that paper handles list composition.
- **Pass-through.** In UK panel data the industry absorbed tax increases on the cheapest products and overshifted on dearer
   ones ([Tobacco Control 2021](https://tobaccocontrol.bmj.com/content/30/e1/e27.full), from the abstract). In EU
   panel data from 2010 to 2020, ad valorem taxes were passed on almost fully and specific taxes less so
   ([Empirica 2025](https://ideas.repec.org/a/kap/empiri/v52y2025i2d10.1007_s10663-024-09637-9.html), from the
   summary). Spain differs in having a floor that binds on the cheapest packs; there we see close to full
   pass-through at the floor and no clear overshifting once ordinary repricing is allowed for. That contrast
   is worth a careful look, not a claim.
- **Price compression and minimum taxes.** The literature on price compression and minimum excise taxes argues that
   tax structure shapes how far the industry can keep the cheap end cheap
   ([example](https://tobaccocontrol.bmj.com/content/22/e1/e21.abstract)). The Spanish structure and its
   change in 2025 make a natural case; our tier-level pass-through is a first descriptive step.
- **Stockpiling.** Forestalling ahead of tax rises is documented (UK 2021 wholesale sales up 17% year on year;
   Illinois 2012; Louisiana tax-stamp purchases). We found none in Spain's monthly data once trading days are
   counted, with the caveat of one event and few placebo winters.
- **Age.** A 2026 difference-in-differences study of 27 EU countries finds tax increases reduce smoking mainly among
   15 to 24 year olds
   ([Stoller and Huber, arXiv](https://arxiv.org/abs/2604.05841), from the abstract). Our data have no age
   dimension; regional age structure is the only route, and a weak one.

## Why it might be interesting

- **Data and method, not a new elasticity.** Monthly brand and tier data, the BOE price lists and the legal
  tax history as joined tables are rare in the open; the pipeline's checks (reconciliation to printed totals,
  overlap agreement across reports) make errors visible.
- **A worked example of reporting what cannot be identified.** Each analysis runs its whole grid of analyst
  decisions and applies a verdict rule written before the result was read. The trimming threshold that once
  flipped a sign is now one point in a curve.
- **Two practical warnings.** Count trading days before reading a tax stockpile. Brand shares from a best-seller list move when
  the list changes.

## Limits

One country, one major tax event inside the brand panel, sell-in volumes (not sales to smokers), best sellers only,
about 65% of the market. No age, income, illicit trade or e-cigarette data.

## What would make it stronger

Andorran and Gibraltar prices (France and Portugal are now in, from Eurostat, at national level and as annual price
levels moved monthly by the HICP), and provincial rather than national prices on the border; regional arrivals for the provinces concerned (INE's table has
only seven regions); the 2012, 2013 and 2016 tax changes with volumes, if monthly volumes can be found before 2019.
