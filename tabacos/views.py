import sqlite_utils

_MONTH = "cast(substr(period_end, 6, 2) as integer)"

VIEWS = {
    # National packs per report; `months` > 1 where a report is missing (July is never published).
    "monthly_packs": f"""
        with national as (
          select period_end, substr(period_end, 1, 4) as year, {_MONTH} as month, sum(packs_ytd) as ytd
          from regional_sales group by period_end)
        select period_end,
               ytd - coalesce(lag(ytd) over w, 0) as packs,
               month - coalesce(lag(month) over w, 0) as months
        from national window w as (partition by year order by period_end)""",
    "annual_cigarettes": """
        select substr(s.period_end, 1, 4) as year, sum(s.packs_ytd) as packs, p.price
        from regional_sales s
        join avg_price p on p.period = substr(s.period_end, 1, 4) and p.product = 'cigarrillos'
        where substr(s.period_end, 6, 2) = '12'
        group by year""",
}


def create_views(db: sqlite_utils.Database) -> None:
    for name, sql in VIEWS.items():
        db.create_view(name, sql, replace=True)
