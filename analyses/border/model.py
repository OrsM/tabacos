"""Tourist-and-border consumption against national consumption in the same provinces."""
from collections import defaultdict


def group_series(rows: list[dict], areas: list[str]) -> list[dict]:
    """Sum the provinces of a group per report period: national and tourist/border packs and months covered.

    A period is kept only if every province of the group has a row for it.
    """
    per = defaultdict(list)
    for r in rows:
        if r["area"] in areas:
            per[r["period_end"]].append(r)
    out = []
    for end in sorted(per):
        group = per[end]
        if {r["area"] for r in group} == set(areas):
            out.append({"end": end[:7], "national": sum(r["national"] for r in group),
                        "tourist": sum(r["tourist"] for r in group), "months": group[0]["months"]})
    return out
