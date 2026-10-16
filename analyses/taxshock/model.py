"""Does share move with the price change that a tax change forces on a brand because of where its price sits?"""
import math

from tabacos.tax import TaxRate, price_after_tax_change


def _idx(month: str) -> int:
    y, m = month.split("-")
    return int(y) * 12 + int(m) - 1


def _month(idx: int) -> str:
    return f"{idx // 12}-{idx % 12 + 1:02d}"


def forced_relative_change(rows_pre: list[dict], old: TaxRate, new: TaxRate, vat_pct: float) -> dict:
    """brand -> log tax-implied price change at its pre-event price, relative to the share-weighted market mean.

    The tax change lifts every price; what differs by brand is how much, because of where its price sits
    against the floor and the specific/ad valorem split. Only that difference is used.
    """
    raw = {r["brand"]: math.log(price_after_tax_change(r["price"], old, new, vat_pct) / r["price"]) for r in rows_pre}
    w = {r["brand"]: r["share_pct"] for r in rows_pre}
    mean = sum(raw[b] * w[b] for b in raw) / sum(w.values())
    return {b: v - mean for b, v in raw.items()}


def _mean_logs(rows: list[dict], months: list[str]) -> dict:
    """brand -> (mean log share, mean log price) over the months it appears in."""
    acc: dict = {}
    for r in rows:
        if r["month"] in months:
            a = acc.setdefault(r["brand"], [0.0, 0.0, 0])
            a[0] += math.log(r["share_pct"])
            a[1] += math.log(r["price"])
            a[2] += 1
    return {b: (a[0] / a[2], a[1] / a[2]) for b, a in acc.items()}


def _listing_stable(rows: list[dict], months: list[str]) -> set:
    """Brands listed in every month of the windows (that exist in the panel) with an unchanged number of tier rows.

    A brand that enters or leaves the best-seller list during the windows, or gains or loses a tier row,
    shows a jump in share that is a property of the list, not of demand.
    """
    present = {r["month"] for r in rows if r["month"] in months}
    counts: dict = {}
    seen: dict = {}
    for r in rows:
        if r["month"] in present:
            counts.setdefault(r["brand"], set()).add(r.get("rows", 1))
            seen.setdefault(r["brand"], set()).add(r["month"])
    return {b for b, c in counts.items() if len(c) == 1 and seen[b] == present}


def _wmean(v, w):
    return sum(a * b for a, b in zip(v, w)) / sum(w)


def _ols(xs, ys, w=None):
    w = w or [1.0] * len(xs)
    mx, my = _wmean(xs, w), _wmean(ys, w)
    sxx = sum(wi * (x - mx) ** 2 for wi, x in zip(w, xs))
    b = sum(wi * (x - mx) * (y - my) for wi, x, y in zip(w, xs, ys)) / sxx
    e = [(y - my) - b * (x - mx) for x, y in zip(xs, ys)]
    return b, math.sqrt(sum(wi ** 2 * (x - mx) ** 2 * ee ** 2 for wi, x, ee in zip(w, xs, e))) / sxx


def _weighted_median(values, weights):
    pairs = sorted(zip(values, weights))
    half, acc = sum(weights) / 2, 0.0
    for v, wt in pairs:
        acc += wt
        if acc >= half:
            return v


def _theil_sen(xs, ys, w=None):
    """Weighted median of the slopes between all pairs of brands: moves little when a few brands are wrong."""
    w = w or [1.0] * len(xs)
    pairs = [((ys[j] - ys[i]) / (xs[j] - xs[i]), w[i] * w[j]) for i in range(len(xs)) for j in range(i) if abs(xs[j] - xs[i]) > 1e-12]
    return _weighted_median([p[0] for p in pairs], [p[1] for p in pairs]), float("nan")


def _huber(xs, ys, w=None, c: float = 1.345, rounds: int = 50):
    """Weighted least squares that gives less weight to brands with large residuals (iteratively reweighted)."""
    w = w or [1.0] * len(xs)
    b = _ols(xs, ys, w)[0]
    for _ in range(rounds):
        mx, my = _wmean(xs, w), _wmean(ys, w)
        res = [(y - my) - b * (x - mx) for x, y in zip(xs, ys)]
        scale = (sorted(abs(r) for r in res)[len(res) // 2] / 0.6745) or 1e-12
        hw = [wi * (min(1.0, c * scale / abs(r)) if r else 1.0) for wi, r in zip(w, res)]
        wx, wy = _wmean(xs, hw), _wmean(ys, hw)
        nb = sum(h * (x - wx) * (y - wy) for h, x, y in zip(hw, xs, ys)) / sum(h * (x - wx) ** 2 for h, x in zip(hw, xs))
        if abs(nb - b) < 1e-12:
            break
        b = nb
    return b, float("nan")


ESTIMATORS = {"ols": _ols, "stable_listing": _ols, "theil_sen": _theil_sen, "huber": _huber}


def _mean_share(rows: list[dict], months: list[str]) -> dict:
    acc: dict = {}
    for r in rows:
        if r["month"] in months:
            acc.setdefault(r["brand"], []).append(r["share_pct"])
    return {b: sum(v) / len(v) for b, v in acc.items()}


def shock_regression(rows: list[dict], pre: list[str], post: list[str], forced: dict, handler: str = "ols",
                     weight: str = "equal") -> dict:
    """Brand-level change between the pre and post windows, regressed on the forced shock.

    reduced_form: change in log share on forced shock. first_stage: change in log relative price on forced
    shock (1 = brands passed the tax through as implied). iv = reduced_form / first_stage.
    Both changes are centred across brands, so what moves every brand at once drops out.

    handler says how a best seller entering or leaving the list (a collapse or surge in share that is not a
    response) is dealt with, without looking at the outcome:
      ols            nothing
      stable_listing keep only brands whose number of listed tier rows does not change across the windows
      theil_sen      median of pairwise slopes
      huber          down-weights large residuals
    weight: `equal` gives every brand the same say; `pre_share` weights by its mean share before the event, because a
    log-share change of a 0.1% brand is mostly noise.
    """
    a, b = _mean_logs(rows, pre), _mean_logs(rows, post)
    keep = _listing_stable(rows, pre + post) if handler == "stable_listing" else None
    brands = [k for k in forced if k in a and k in b and (keep is None or k in keep)]
    dls = [b[k][0] - a[k][0] for k in brands]
    dlp = [b[k][1] - a[k][1] for k in brands]
    mp = sum(dlp) / len(dlp)
    x = [forced[k] for k in brands]
    fit = ESTIMATORS[handler]
    w = None if weight == "equal" else [_mean_share(rows, pre)[k] for k in brands]
    rf, rf_se = fit(x, dls, w)
    fs, fs_se = fit(x, [v - mp for v in dlp], w)
    return {"reduced_form": rf, "rf_se": rf_se, "first_stage": fs, "fs_se": fs_se,
            "iv": rf / fs if fs else float("nan"), "n": len(brands)}


def placebo_effects(rows: list[dict], old: TaxRate, new: TaxRate, vat_pct: float, event_month: str,
                    pre_offsets: tuple, post_offsets: tuple, exclude: int, min_brands: int = 8,
                    handler: str = "ols", weight: str = "equal") -> list[dict]:
    """The same regression at other dates, using the shock this tariff change would force on the prices of that date.

    Dates within `exclude` months of the real event are skipped. These show how much share normally moves
    with price level over a similar window, with no tax change.
    """
    present = sorted({r["month"] for r in rows}, key=_idx)
    have = set(present)
    out = []
    for m in present:
        i = _idx(m)
        if abs(i - _idx(event_month)) <= exclude:
            continue
        pre = [_month(i + o) for o in pre_offsets if _month(i + o) in have]
        post = [_month(i + o) for o in post_offsets if _month(i + o) in have]
        if not pre or not post:
            continue
        pre_rows = [r for r in rows if r["month"] == pre[-1]]
        forced = forced_relative_change(pre_rows, old, new, vat_pct)
        reg = shock_regression(rows, pre, post, forced, handler, weight)
        if reg["n"] >= min_brands:
            out.append({"month": m, **reg})
    return out
