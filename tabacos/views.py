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
    # A brand listed in two tiers (the table splits a brand by price band) as one series. The listed
    # rows are the best sellers only, so a brand can drop out of the list in a month.
    "brand_month": """
        select month, brand, company, sum(share_pct) as share_pct,
               sum(price * share_pct) / sum(share_pct) as price, count(*) as rows
        from segment_sales group by month, brand, company""",
    # National and tourist/border packs per report from year-to-date differences; months > 1 where a report is missing.
    "tourist_monthly": f"""
        with ytd as (
          select area, kind, period_end, substr(period_end, 1, 4) as year, {_MONTH} as month, national_ytd, tourist_ytd
          from tourist_sales)
        select area, kind, period_end,
               national_ytd - coalesce(lag(national_ytd) over w, 0) as national,
               tourist_ytd - coalesce(lag(tourist_ytd) over w, 0) as tourist,
               month - coalesce(lag(month) over w, 0) as months
        from ytd window w as (partition by area, kind, year order by period_end)""",
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
