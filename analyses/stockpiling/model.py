"""Pull-forward ahead of a tax change, read from year-on-year growth of two adjacent months."""


def swings(packs: dict[tuple[int, int], float], pre_month: int, post_month: int, event_year: int,
           days: dict[tuple[int, int], float] | None = None) -> list[dict]:
    """For each year Y with data: yoy growth of the month before the change (pre) and after it (post).

    Stockpiling shows as high pre_yoy and low post_yoy: swing = pre_yoy - post_yoy. net_yoy is growth of
    the two months together; if the pull-forward is only timing it stays near trend. Years other than
    event_year are placebos, except event_year + 1, whose comparison base is distorted (after_event).
    pre_month=12, post_month=1: the pre month belongs to the previous calendar year.
    With `days` (trading days per month) the statistic is on packs per trading day.
    """
    if days is not None:
        packs = {k: v / days[k] for k, v in packs.items() if k in days}
    rows = []
    for year in sorted({y for y, _ in packs}):
        pre_y = year - 1 if pre_month > post_month else year
        keys = [(pre_y, pre_month), (year, post_month), (pre_y - 1, pre_month), (year - 1, post_month)]
        if not all(k in packs for k in keys):
            continue
        pre, post, pre_prev, post_prev = (packs[k] for k in keys)
        rows.append({"year": year, "pre_yoy": pre / pre_prev - 1, "post_yoy": post / post_prev - 1,
                     "swing": (pre / pre_prev - 1) - (post / post_prev - 1),
                     "net_yoy": (pre + post) / (pre_prev + post_prev) - 1,
                     "is_event": year == event_year, "after_event": year == event_year + 1})
    return rows


def yoy_noise(packs: dict[tuple[int, int], float], days: dict[tuple[int, int], float] | None = None,
              skip=lambda year, month: False) -> float:
    """Standard deviation of month-on-same-month-last-year growth, optionally per trading day.

    A day count that matches how sales really follow the calendar leaves less noise.
    """
    from statistics import pstdev
    per = dict(packs) if days is None else {k: v / days[k] for k, v in packs.items() if k in days}
    growth = [per[(y, m)] / per[(y - 1, m)] - 1 for (y, m) in per
              if (y - 1, m) in per and not skip(y, m) and not skip(y - 1, m)]
    return pstdev(growth)
