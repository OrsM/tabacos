import sqlite_utils
from tabacos.views import create_views


def make(rows):
    db = sqlite_utils.Database(memory=True)
    db["regional_sales"].insert_all(
        [{"region": r, "period_end": d, "packs_ytd": v, "source": "x"} for r, d, v in rows])
    create_views(db)
    return db


def test_monthly_packs_differences_the_year_to_date_and_resets_each_january():
    db = make([("A", "2024-01-31", 10), ("B", "2024-01-31", 5),
               ("A", "2024-02-29", 25), ("B", "2024-02-29", 12),
               ("A", "2025-01-31", 7), ("B", "2025-01-31", 3)])
    got = {r["period_end"]: (r["packs"], r["months"]) for r in db.query("select * from monthly_packs")}
    assert got == {"2024-01-31": (15, 1), "2024-02-29": (22, 1), "2025-01-31": (10, 1)}


def test_a_missing_month_makes_the_next_row_cover_two_months():
    db = make([("A", "2024-06-30", 60), ("A", "2024-08-31", 100)])
    got = {r["period_end"]: (r["packs"], r["months"]) for r in db.query("select * from monthly_packs")}
    assert got["2024-08-31"] == (40, 2)


def test_annual_price_and_volume_join_on_year():
    db = make([("A", "2024-12-31", 1000)])
    db["avg_price"].insert_all([{"product": "cigarrillos", "period": "2024", "price": 5.07}])
    create_views(db)
    assert [dict(r) for r in db.query("select * from annual_cigarettes")] == [
        {"year": "2024", "packs": 1000, "price": 5.07}]
