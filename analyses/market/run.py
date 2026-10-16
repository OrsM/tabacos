"""python -m analyses.market.run [db] -> result_market_curve, report.md and curve.png"""
import itertools
import math
import statistics as st
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt          # noqa: E402
import numpy as np                       # noqa: E402
import sqlite_utils                      # noqa: E402

from analyses.panel.model import market_price                  # noqa: E402
from tabacos.workdays import working_days                      # noqa: E402

from .model import chain_price_index, circular_shift_placebo, design_matrix, fit_hac   # noqa: E402

HERE = Path(__file__).parent
PRICE = ("chain_index", "weighted_mean")
VOLUME = ("per_month", "per_weekday", "per_monsat_day")
TREND = ("none", "linear", "quadratic", "cubic")
COVID = ("ignore", "dummy", "drop")
STOCK = ("ignore", "dummy", "drop")
LAG = (1, 3, 6)
START = ("2019-01", "2021-07")
LAGS_HAC, MIN_SHIFT = 6, 12
MIN_SD, MAX_SE, AGREE, BASELINE_P = 0.02, 0.35, 0.9, 0.10
BASELINE = dict(price="chain_index", volume="per_weekday", trend="quadratic", covid="dummy", stock="dummy", lag=3, start="2019-01")
INK, MUTED, GRID, ACCENT = "#1f2328", "#59636e", "#e1e4e8", "#1f6feb"


def mi(month: str) -> int:
    return int(month[:4]) * 12 + int(month[5:]) - 1


def months_covered(end: str, n: int) -> list[str]:
    e = mi(end)
    return [f"{(e - k) // 12}-{(e - k) % 12 + 1:02d}" for k in range(n)]


def price_series(db) -> dict:
    """Monthly price measures from the brand panel: chain-linked index and share-weighted mean price."""
    brands = [{"month": r["month"], "brand": (r["brand"], r["company"]), "price": r["price"], "share_pct": r["share_pct"]}
              for r in db.query("select month, brand, company, price, share_pct from brand_month")]
    chain = chain_price_index(brands)
    by_month = {}
    for r in brands:
        by_month.setdefault(r["month"], []).append(r)
    wmean = {m: market_price(g) / market_price(by_month[min(by_month)]) for m, g in by_month.items()}
    return {"chain_index": chain, "weighted_mean": wmean}


def load(db):
    periods = []
    for r in db.query("select period_end, packs, months from monthly_packs where period_end >= '2019-01'"):
        end = r["period_end"][:7]
        cov = months_covered(end, r["months"])
        periods.append({"end": end, "months": r["months"], "packs": r["packs"],
                        "wd": sum(working_days(int(m[:4]), int(m[5:])) for m in cov),
                        "ms": sum(working_days(int(m[:4]), int(m[5:]), True) for m in cov)})
    return sorted(periods, key=lambda p: p["end"]), price_series(db)


def price_at(series: dict, end: str, k: int):
    avail = sorted(m for m in series if mi(m) <= mi(end))
    window = avail[-k:]
    if not window or mi(end) - mi(window[-1]) > 1:
        return None
    return float(np.mean([math.log(series[m]) for m in window]))


def run_spec(periods, price_series, spec: dict) -> dict | None:
    rows = []
    for p in periods:
        if mi(p["end"]) < mi(spec["start"]):
            continue
        covid = mi("2020-03") <= mi(p["end"]) <= mi("2021-06")
        stock = p["end"] in ("2024-12", "2025-01")
        if (spec["covid"] == "drop" and covid) or (spec["stock"] == "drop" and stock):
            continue
        lp = price_at(price_series[spec["price"]], p["end"], spec["lag"])
        if lp is None:
            continue
        vol = {"per_month": p["packs"] / p["months"], "per_weekday": p["packs"] / p["wd"], "per_monsat_day": p["packs"] / p["ms"]}[spec["volume"]]
        rows.append((p["end"], math.log(vol), lp, covid, p["end"] == "2024-12", p["end"] == "2025-01"))
    y = np.array([r[1] for r in rows])
    logp = np.array([r[2] for r in rows])
    moy = [int(r[0][5:]) for r in rows]
    time = [mi(r[0]) - mi(rows[0][0]) for r in rows]
    extras = []
    if spec["covid"] == "dummy" and spec["start"] < "2021-07":
        extras.append([float(r[3]) for r in rows])
    if spec["stock"] == "dummy":
        extras += [[float(r[4]) for r in rows], [float(r[5]) for r in rows]]
    X = design_matrix(logp, moy, spec["trend"], time, extras)
    if X.shape[0] < X.shape[1] + 15:
        return None
    fit = fit_hac(y, X, LAGS_HAC)
    # identifying variation: what is left of log price after season, trend and controls
    others = np.delete(X, 1, axis=1)
    resid = logp - others @ np.linalg.lstsq(others, logp, rcond=None)[0]
    beta, se = float(fit["beta"][1]), float(fit["se"][1])
    return {**spec, "beta": beta, "se": se, "lo": beta - 1.96 * se, "hi": beta + 1.96 * se, "n": fit["n"], "r2": fit["r2"],
            "identifying_sd": float(resid.std()), "_y": y, "_logp": logp, "_moy": moy, "_time": time, "_extras": extras}


def grid():
    for price, volume, trend, covid, stock, lag, start in itertools.product(PRICE, VOLUME, TREND, COVID, STOCK, LAG, START):
        if start >= "2021-07" and covid != "ignore":
            continue
        yield dict(price=price, volume=volume, trend=trend, covid=covid, stock=stock, lag=lag, start=start)


def verdict(specs: list[dict], baseline_p: float, min_sd: float = MIN_SD, max_se: float = MAX_SE) -> dict:
    betas = [s["beta"] for s in specs]
    neg = sum(b < 0 for b in betas) / len(betas)
    excl = sum(s["hi"] < 0 or s["lo"] > 0 for s in specs) / len(specs)
    med_sd, med_se = st.median(s["identifying_sd"] for s in specs), st.median(s["se"] for s in specs)
    q = np.percentile(betas, [10, 50, 90])
    if med_sd < min_sd:
        outcome = "no elasticity reported: price barely moves independently of trend and season"
    elif med_se > max_se:
        outcome = "no elasticity reported: too imprecise to tell inelastic from unit elastic"
    elif neg >= AGREE or 1 - neg >= AGREE:
        sign = "negative" if neg >= AGREE else "positive"
        outcome = (f"sign {sign}" + (", distinguishable from zero" if excl >= AGREE and baseline_p <= BASELINE_P
                                     else ", not distinguishable from zero"))
    else:
        outcome = "not determined by the data"
    return {"outcome": outcome, "share_negative": neg, "share_excluding_zero": excl, "median_identifying_sd": med_sd,
            "median_se": med_se, "p10": float(q[0]), "median": float(q[1]), "p90": float(q[2]), "baseline_p": baseline_p}


def verdict_map(specs, baseline_p) -> list[str]:
    """The verdict under other thresholds for the two rules that have one: the rules' numbers are themselves decisions."""
    lines = ["| Residual log-price spread needed | Max s.e. allowed | Verdict |", "|---|---|---|"]
    for sd, se in itertools.product((0.005, 0.01, 0.02, 0.03), (0.25, 0.35, 0.5)):
        lines.append(f"| {sd:g} | {se:g} | {verdict(specs, baseline_p, sd, se)['outcome']} |")
    return lines


def figure(specs):
    fig, axes = plt.subplots(1, len(TREND), figsize=(10, 3.4), dpi=150, sharey=True)
    for ax, t in zip(axes, TREND):
        g = sorted((s for s in specs if s["trend"] == t), key=lambda s: s["beta"])
        ax.axhline(0, color=MUTED, linewidth=0.8)
        ax.vlines(range(len(g)), [s["lo"] for s in g], [s["hi"] for s in g], color="#a5c8ff", linewidth=0.6, zorder=1)
        ax.scatter(range(len(g)), [s["beta"] for s in g], s=5, color=ACCENT, zorder=3)
        ax.set_title(f"{t} trend", fontsize=9, color=INK, loc="left")
        ax.set_xticks([])
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
        ax.tick_params(colors=MUTED, labelsize=8)
    axes[0].set_ylabel("elasticity of volume to price (95% interval)", color=MUTED, fontsize=8)
    ylo = min(-4, max(-8, np.percentile([s["lo"] for s in specs], 2)))
    yhi = max(3, min(8, np.percentile([s["hi"] for s in specs], 98)))
    axes[0].set_ylim(ylo, yhi)
    fig.suptitle("Every specification, by the trend that absorbs the long decline", x=0.01, ha="left", fontsize=9.5, color=INK)
    fig.tight_layout()
    fig.savefig(HERE / "curve.png")
    plt.close(fig)


def table(specs, key, values):
    lines = [f"| {key} | Specs | Median elasticity | Share negative | Median s.e. |", "|---|---|---|---|---|"]
    for v in values:
        g = [s for s in specs if s[key] == v]
        if g:
            lines.append(f"| {v} | {len(g)} | {st.median(s['beta'] for s in g):+.2f} | {sum(s['beta'] < 0 for s in g) / len(g):.0%} | {st.median(s['se'] for s in g):.2f} |")
    return lines


def render(specs, v, base, placebo) -> str:
    lines = ["# Market-level elasticity of cigarette volume to price", "",
             "Generated by `python -m analyses.market.run`. See question.md: every decision is a parameter, the verdict rules were written first.", "",
             "## Verdict", "", f"**{v['outcome']}**", "",
             f"- {len(specs)} specifications. Central 80% of estimates: {v['p10']:+.2f} to {v['p90']:+.2f} (median {v['median']:+.2f}); "
             f"{v['share_negative']:.0%} negative; {v['share_excluding_zero']:.0%} have a 95% interval excluding zero.",
             f"- Median HAC standard error {v['median_se']:.2f} (rule: above {MAX_SE} the data cannot separate -0.3 from -1).",
             f"- Median residual spread of log price after trend and season {v['median_identifying_sd']:.3f} (rule: below {MIN_SD} means no independent price variation).",
             f"- Baseline specification: {base['beta']:+.2f} (s.e. {base['se']:.2f}); placebo rotations of the price series give "
             f"{np.percentile(placebo, 5):+.2f} to {np.percentile(placebo, 95):+.2f} (5th to 95th percentile), and {v['baseline_p']:.0%} of them are at least as extreme.",
             "", "![Specification curve](curve.png)", "",
             "## Does the verdict depend on the thresholds of the rules?", "",
             "The two numeric thresholds were fixed before the run, but they are decisions too. The same specifications under other values:", ""]
    lines += verdict_map(specs, v["baseline_p"]) + ["", "## By decision", ""]
    for key, values in (("trend", TREND), ("price", PRICE), ("volume", VOLUME), ("covid", COVID), ("stock", STOCK), ("lag", LAG), ("start", START)):
        lines += table(specs, key, values) + [""]
    lines += ["## Notes", "",
              "- Elasticity is the change in log volume per day for a change in log price index; -0.5 means a 10% price rise goes with 5% less volume.",
              "- Volume is sell-in to tobacconists. A smoker's response and a retailer's stock decision are not separated.",
              "- The trend and the price both move slowly, which is why the estimate leans on the three price steps and why the choice of "
              "trend matters most.", ""]
    return "\n".join(lines)


if __name__ == "__main__":
    db = sqlite_utils.Database(sys.argv[1] if len(sys.argv) > 1 else "tobacco.db")
    periods, series = load(db)
    specs = [r for r in (run_spec(periods, series, s) for s in grid()) if r]
    base = run_spec(periods, series, BASELINE)
    placebo = circular_shift_placebo(base["_y"], base["_logp"], base["_moy"], BASELINE["trend"], LAGS_HAC, MIN_SHIFT, base["_time"], base["_extras"])
    baseline_p = sum(abs(d - np.mean(placebo)) >= abs(base["beta"] - np.mean(placebo)) for d in placebo) / len(placebo)
    v = verdict(specs, baseline_p)
    keep = [{k: x for k, x in s.items() if not k.startswith("_")} for s in specs]
    db["result_market_curve"].drop(ignore=True)
    db["result_market_curve"].insert_all(keep)
    figure(keep)
    (HERE / "report.md").write_text(render(keep, v, base, placebo), encoding="utf-8")
    print((HERE / "report.md").read_text())
