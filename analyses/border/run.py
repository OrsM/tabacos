"""python -m analyses.border.run [db] -> result_border_curve, report.md and curve.png"""
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

from analyses.market.model import circular_shift_placebo, design_matrix, fit_hac       # noqa: E402
from analyses.market.run import mi, months_covered, price_at, price_series            # noqa: E402
from tabacos.workdays import working_days                                              # noqa: E402

from .model import group_series                                                         # noqa: E402

HERE = Path(__file__).parent
GROUPS = {"border": ["Girona", "Guipúzcoa", "Navarra", "Lleida", "Huesca"],
          "tourist": ["Balears (Illes)", "Málaga", "Alicante/Alacant"]}
ARRIVAL_REGIONS = {"tourist": ["Balears, Illes", "Andalucía", "Comunitat Valenciana"]}
OUTCOME, VOLUME, PRICE = ("ratio", "tourist", "national"), ("per_month", "per_weekday", "per_monsat_day"), ("chain_index", "weighted_mean")
TREND, COVID, STOCK, LAG, START = ("linear", "quadratic", "cubic"), ("ignore", "dummy", "drop"), ("dummy", "drop"), (1, 3, 6), ("2019-01", "2021-07")
LAGS_HAC, MIN_SHIFT = 6, 12
MIN_SD, MAX_SE, AGREE, BASELINE_P = 0.02, 0.35, 0.9, 0.10
BASELINE = dict(price="chain_index", volume="per_month", trend="quadratic", covid="dummy", stock="dummy", lag=3, start="2019-01", arrivals=True)
INK, MUTED, GRID, ACCENT = "#1f2328", "#59636e", "#e1e4e8", "#1f6feb"


def load(db):
    rows = list(db.query("select area, period_end, national, tourist, months from tourist_monthly where kind = 'province'"))
    arrivals = {(r["region"], r["month"]): r["arrivals"] for r in db.query("select region, month, arrivals from tourist_arrivals")}
    series = {g: group_series(rows, areas) for g, areas in GROUPS.items()}
    return series, arrivals, price_series(db)


def arrivals_at(arrivals, regions, end, months):
    vals = [arrivals.get((r, m)) for m in months_covered(end, months) for r in regions]
    return None if any(v is None for v in vals) else float(sum(vals))


def run_spec(series, arrivals, prices, spec):
    rows = []
    for p in series[spec["group"]]:
        if mi(p["end"]) < mi(spec["start"]):
            continue
        covid = mi("2020-03") <= mi(p["end"]) <= mi("2021-06")
        stock = p["end"] in ("2024-12", "2025-01")
        if (spec["covid"] == "drop" and covid) or (spec["stock"] == "drop" and stock):
            continue
        lp = price_at(prices[spec["price"]], p["end"], spec["lag"])
        if lp is None:
            continue
        cov = months_covered(p["end"], p["months"])
        wd = sum(working_days(int(m[:4]), int(m[5:])) for m in cov)
        ms = sum(working_days(int(m[:4]), int(m[5:]), True) for m in cov)
        div = {"per_month": p["months"], "per_weekday": wd, "per_monsat_day": ms}[spec["volume"]]
        if spec["outcome"] == "ratio":
            y = math.log(p["tourist"] / p["national"])
        else:
            y = math.log(p[spec["outcome"]] / div)
        arr = None
        if spec.get("arrivals"):
            arr = arrivals_at(arrivals, ARRIVAL_REGIONS["tourist"], p["end"], p["months"])
            if arr is None:
                continue
        rows.append((p["end"], y, lp, covid, p["end"] == "2024-12", p["end"] == "2025-01", arr))
    if len(rows) < 30:
        return None
    y = np.array([r[1] for r in rows])
    logp = np.array([r[2] for r in rows])
    moy = [int(r[0][5:]) for r in rows]
    time = [mi(r[0]) - mi(rows[0][0]) for r in rows]
    extras = []
    if spec["covid"] == "dummy" and spec["start"] < "2021-07":
        extras.append([float(r[3]) for r in rows])
    if spec["stock"] == "dummy":
        extras += [[float(r[4]) for r in rows], [float(r[5]) for r in rows]]
    if spec.get("arrivals"):
        extras.append([math.log1p(r[6]) for r in rows])         # arrivals are zero in the first Covid months
    X = design_matrix(logp, moy, spec["trend"], time, extras)
    if X.shape[0] < X.shape[1] + 15:
        return None
    fit = fit_hac(y, X, LAGS_HAC)
    others = np.delete(X, 1, axis=1)
    resid = logp - others @ np.linalg.lstsq(others, logp, rcond=None)[0]
    beta, se = float(fit["beta"][1]), float(fit["se"][1])
    return {**spec, "beta": beta, "se": se, "lo": beta - 1.96 * se, "hi": beta + 1.96 * se, "n": fit["n"],
            "identifying_sd": float(resid.std()), "_y": y, "_logp": logp, "_moy": moy, "_time": time, "_extras": extras}


def grid():
    for group, outcome, price, trend, covid, stock, lag, start in itertools.product(GROUPS, OUTCOME, PRICE, TREND, COVID, STOCK, LAG, START):
        if start >= "2021-07" and covid != "ignore":
            continue
        for volume in ((VOLUME[0],) if outcome == "ratio" else VOLUME):
            for arr in ((False, True) if group == "tourist" else (False,)):
                yield dict(group=group, outcome=outcome, volume=volume, price=price, trend=trend, covid=covid, stock=stock,
                           lag=lag, start=start, arrivals=arr)


def verdict(specs, baseline_p):
    betas = [s["beta"] for s in specs]
    neg = sum(b < 0 for b in betas) / len(betas)
    excl = sum(s["hi"] < 0 or s["lo"] > 0 for s in specs) / len(specs)
    med_sd, med_se = st.median(s["identifying_sd"] for s in specs), st.median(s["se"] for s in specs)
    q = np.percentile(betas, [10, 50, 90])
    if med_sd < MIN_SD:
        outcome = "no verdict: price barely moves independently of trend and season"
    elif med_se > MAX_SE:
        outcome = "no verdict: too imprecise to separate a modest from a large difference"
    elif max(neg, 1 - neg) >= AGREE and excl >= AGREE and baseline_p <= BASELINE_P:
        outcome = "tourist and border purchases are " + ("MORE" if neg >= AGREE else "LESS") + " price-responsive than residents' purchases"
    else:
        outcome = "not determined by the data"
    return {"outcome": outcome, "n": len(specs), "share_negative": neg, "share_excluding_zero": excl, "median_sd": med_sd,
            "median_se": med_se, "p10": float(q[0]), "median": float(q[1]), "p90": float(q[2]), "baseline_p": baseline_p}


def figure(specs):
    fig, axes = plt.subplots(1, 2, figsize=(9, 3.4), dpi=150, sharey=True)
    for ax, g in zip(axes, GROUPS):
        s = sorted((x for x in specs if x["group"] == g and x["outcome"] == "ratio"), key=lambda x: x["beta"])
        ax.axhline(0, color=MUTED, linewidth=0.8)
        ax.vlines(range(len(s)), [x["lo"] for x in s], [x["hi"] for x in s], color="#a5c8ff", linewidth=0.6, zorder=1)
        ax.scatter(range(len(s)), [x["beta"] for x in s], s=6, color=ACCENT, zorder=3)
        ax.set_title(f"{g} provinces", fontsize=9, color=INK, loc="left")
        ax.set_xticks([])
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
        ax.tick_params(colors=MUTED, labelsize=8)
    axes[0].set_ylabel("tourist and border minus national\nelasticity (95% interval)", color=MUTED, fontsize=8)
    axes[0].set_ylim(-4, 4)
    fig.suptitle("Every specification of the ratio model", x=0.01, ha="left", fontsize=9.5, color=INK)
    fig.tight_layout()
    fig.savefig(HERE / "curve.png")
    plt.close(fig)


def summary_row(label, g):
    b = [s["beta"] for s in g]
    return (f"| {label} | {len(g)} | {st.median(b):+.2f} | {np.percentile(b, 10):+.2f} to {np.percentile(b, 90):+.2f} | "
            f"{sum(x < 0 for x in b) / len(b):.0%} | {sum(s['hi'] < 0 or s['lo'] > 0 for s in g) / len(g):.0%} | {st.median(s['se'] for s in g):.2f} |")


def render(specs, verdicts, bases, placebos):
    lines = ["# Tourist and border purchases against residents', by Spanish price", "",
             "Generated by `python -m analyses.border.run`. See question.md: decisions are parameters and the rules came first.", ""]
    for g in GROUPS:
        v = verdicts[g]
        lines += [f"## {g.title()} provinces: **{v['outcome']}**", "",
                  f"- {v['n']} specifications of the ratio model. Central 80%: {v['p10']:+.2f} to {v['p90']:+.2f} (median {v['median']:+.2f}); "
                  f"{v['share_negative']:.0%} negative; {v['share_excluding_zero']:.0%} with a 95% interval excluding zero.",
                  f"- Median HAC s.e. {v['median_se']:.2f} (rule: above {MAX_SE} no verdict); median residual spread of log price {v['median_sd']:.3f} (rule: below {MIN_SD}).",
                  f"- Baseline specification {bases[g]['beta']:+.2f} (s.e. {bases[g]['se']:.2f}); placebo rotations "
                  f"{np.percentile(placebos[g], 5):+.2f} to {np.percentile(placebos[g], 95):+.2f} (5th-95th percentile), {v['baseline_p']:.0%} as extreme.", ""]
    lines += ["![Specification curves](curve.png)", "", "## Elasticities by outcome", "",
              "| Group, outcome | Specs | Median | Central 80% | Share negative | CI excludes 0 | Median s.e. |", "|---|---|---|---|---|---|---|"]
    for g in GROUPS:
        for o in OUTCOME:
            lines.append(summary_row(f"{g}, {o}", [s for s in specs if s["group"] == g and s["outcome"] == o]))
    lines += ["", "## Ratio model by group and sample start", "",
              "| Group, sample start | Specs | Median | Central 80% | Share negative | CI excludes 0 | Median s.e. |", "|---|---|---|---|---|---|---|"]
    for g in GROUPS:
        for start in START:
            lines.append(summary_row(f"{g}, from {start}", [s for s in specs if s["group"] == g and s["outcome"] == "ratio" and s["start"] == start]))
    lines += ["", "The sign can depend on whether the Covid collapse and recovery of tourist and border purchases is in the sample; "
              "a post-Covid start leans on the price steps of 2022-23 and 2025, years in which arrivals were also recovering.",
              "", "## By decision, ratio model", ""]
    for key, values in (("trend", TREND), ("covid", COVID), ("lag", LAG), ("start", START), ("price", PRICE), ("arrivals", (False, True))):
        lines += [f"| {key} | Specs | Median | Central 80% | Share negative | CI excludes 0 | Median s.e. |", "|---|---|---|---|---|---|---|"]
        for val in values:
            g = [s for s in specs if s["outcome"] == "ratio" and s[key] == val]
            if g:
                lines.append(summary_row(str(val), g))
        lines.append("")
    lines += ["## Notes", "",
              "- A negative differential means tourist and border purchases fall more than residents' when the Spanish price rises.",
              "- The price that matters for cross-border buying is the gap to neighbouring countries' prices, which are not in the data.",
              "- Tourist and border consumption collapsed in 2020 and recovered through 2022; the Covid choices and the arrivals control matter.", ""]
    return "\n".join(lines)


if __name__ == "__main__":
    db = sqlite_utils.Database(sys.argv[1] if len(sys.argv) > 1 else "tobacco.db")
    series, arrivals, prices = load(db)
    specs = [r for r in (run_spec(series, arrivals, prices, s) for s in grid()) if r]
    verdicts, bases, placebos = {}, {}, {}
    for g in GROUPS:
        b = run_spec(series, arrivals, prices, {**BASELINE, "group": g, "outcome": "ratio", "arrivals": g == "tourist"})
        pl = circular_shift_placebo(b["_y"], b["_logp"], b["_moy"], BASELINE["trend"], LAGS_HAC, MIN_SHIFT, b["_time"], b["_extras"])
        p = sum(abs(d - np.mean(pl)) >= abs(b["beta"] - np.mean(pl)) for d in pl) / len(pl)
        bases[g], placebos[g] = b, pl
        verdicts[g] = verdict([s for s in specs if s["group"] == g and s["outcome"] == "ratio"], p)
    keep = [{k: v for k, v in s.items() if not k.startswith("_")} for s in specs]
    db["result_border_curve"].drop(ignore=True)
    db["result_border_curve"].insert_all(keep)
    figure(keep)
    (HERE / "report.md").write_text(render(keep, verdicts, bases, placebos), encoding="utf-8")
    print((HERE / "report.md").read_text())
