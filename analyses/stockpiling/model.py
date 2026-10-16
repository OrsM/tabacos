"""Pull-forward ahead of a tax change, read from year-on-year growth of two adjacent months."""


def swings(packs: dict[tuple[int, int], float], pre_month: int, post_month: int, event_year: int) -> list[dict]:
    """For each year Y with data: yoy growth of the month before the change (pre) and after it (post).

    Stockpiling shows as high pre_yoy and low post_yoy: swing = pre_yoy - post_yoy. net_yoy is growth of
    the two months together; if the pull-forward is only timing it stays near trend. Years other than
    event_year are placebos, except event_year + 1, whose comparison base is distorted (after_event).
    pre_month=12, post_month=1: the pre month belongs to the previous calendar year.
    """
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
