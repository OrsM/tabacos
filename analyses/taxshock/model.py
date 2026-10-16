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


def _slope(xs: list[float], ys: list[float]) -> tuple[float, float]:
    mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
    sxx = sum((x - mx) ** 2 for x in xs)
    b = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sxx
    e = [(y - my) - b * (x - mx) for x, y in zip(xs, ys)]
    se = math.sqrt(sum((x - mx) ** 2 * ee ** 2 for x, ee in zip(xs, e))) / sxx
    return b, se


def shock_regression(rows: list[dict], pre: list[str], post: list[str], forced: dict, trim: float | None = None) -> dict:
    """Brand-level change between the pre and post windows, regressed on the forced shock.

    reduced_form: change in log share on forced shock. first_stage: change in log relative price on forced
    shock (1 = brands passed the tax through as implied). iv = reduced_form / first_stage.
    Both changes are centred across brands, so what moves every brand at once drops out.
    trim: leave out brands whose log share moved by more than this between the windows (a best seller that
    dropped out of or entered the list looks like a collapse or a surge, not a response).
    """
    a, b = _mean_logs(rows, pre), _mean_logs(rows, post)
    brands = [k for k in forced if k in a and k in b and (trim is None or abs(b[k][0] - a[k][0]) <= trim)]
    dls = [b[k][0] - a[k][0] for k in brands]
    dlp = [b[k][1] - a[k][1] for k in brands]
    mp = sum(dlp) / len(dlp)
    x = [forced[k] for k in brands]
    rf, rf_se = _slope(x, dls)
    fs, fs_se = _slope(x, [v - mp for v in dlp])
    return {"reduced_form": rf, "rf_se": rf_se, "first_stage": fs, "fs_se": fs_se,
            "iv": rf / fs if fs else float("nan"), "n": len(brands)}


def placebo_effects(rows: list[dict], old: TaxRate, new: TaxRate, vat_pct: float, event_month: str,
                    pre_offsets: tuple, post_offsets: tuple, exclude: int, min_brands: int = 8,
                    trim: float | None = None) -> list[dict]:
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
        reg = shock_regression(rows, pre, post, forced, trim)
        if reg["n"] >= min_brands:
            out.append({"month": m, **reg})
    return out
