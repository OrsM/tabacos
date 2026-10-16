"""Descriptive statistics of the brand-by-month panel: relative prices, their spread, and share against price."""
import math
from collections import defaultdict


def _month_index(month: str) -> int:
    y, m = month.split("-")
    return int(y) * 12 + int(m)


def _by_month(rows):
    out = defaultdict(list)
    for r in rows:
        out[r["month"]].append(r)
    return out


def market_price(rows: list[dict]) -> float:
    """Share-weighted mean price of the listed brands in one month."""
    return sum(r["price"] * r["share_pct"] for r in rows) / sum(r["share_pct"] for r in rows)


def relative_log_prices(rows: list[dict]) -> dict[tuple[str, tuple], float]:
    """(month, brand) -> log(price) - log(market price of that month)."""
    out = {}
    for month, group in _by_month(rows).items():
        base = math.log(market_price(group))
        for r in group:
            out[(month, r["brand"])] = math.log(r["price"]) - base
    return out


def dispersion_by_month(rows: list[dict]) -> dict[str, float]:
    """Share-weighted standard deviation of log price across the listed brands, per month."""
    out = {}
    for month, group in _by_month(rows).items():
        w = sum(r["share_pct"] for r in group)
        mean = sum(r["share_pct"] * math.log(r["price"]) for r in group) / w
        out[month] = math.sqrt(sum(r["share_pct"] * (math.log(r["price"]) - mean) ** 2 for r in group) / w)
    return out


def first_differences(rows: list[dict]) -> list[dict]:
    return differences(rows, lag=1)


def differences(rows: list[dict], lag: int) -> list[dict]:
    """Brand-level change in log share and in log relative price between months `lag` calendar months apart."""
    rel = relative_log_prices(rows)
    by_brand = defaultdict(dict)
    for r in rows:
        by_brand[r["brand"]][r["month"]] = r
    out = []
    for brand, months in by_brand.items():
        for m1, r1 in months.items():
            prev = [m for m in months if _month_index(m) == _month_index(m1) - lag]
            if prev:
                r0 = months[prev[0]]
                out.append({"brand": brand, "month": m1,
                            "dlog_share": math.log(r1["share_pct"] / r0["share_pct"]),
                            "dlog_price": rel[(m1, brand)] - rel[(prev[0], brand)]})
    return out


def within_slope(diffs: list[dict]) -> dict:
    """Slope of change in log share on change in log relative price, both centred within each month.

    Centring within the month removes what moves every listed brand at once (the list's total share, season).
    Brand fixed effects are already gone because both variables are differences. The standard error is
    clustered by brand (CR0), because differences over long lags overlap and the same brand repeats.
    """
    by_month = defaultdict(list)
    for d in diffs:
        by_month[d["month"]].append(d)
    obs = []
    for group in by_month.values():
        if len(group) < 3:
            continue
        mx = sum(g["dlog_price"] for g in group) / len(group)
        my = sum(g["dlog_share"] for g in group) / len(group)
        obs += [(g["brand"], g["dlog_price"] - mx, g["dlog_share"] - my) for g in group]
    sxx = sum(x * x for _, x, _ in obs)
    slope = sum(x * y for _, x, y in obs) / sxx
    scores = defaultdict(float)
    for brand, x, y in obs:
        scores[brand] += x * (y - slope * x)
    se = math.sqrt(sum(v * v for v in scores.values())) / sxx
    return {"slope": slope, "se": se, "n": len(obs), "brands": len(scores), "sd_price_change": math.sqrt(sxx / len(obs))}
