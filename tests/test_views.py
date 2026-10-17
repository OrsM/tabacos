import pytest
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
    got = {r["period_end"]: (r["packs"], r["months"]) for r in db.query("select * from monthly_packs_pdf")}
    assert got == {"2024-01-31": (15, 1), "2024-02-29": (22, 1), "2025-01-31": (10, 1)}


def test_a_missing_month_makes_the_next_row_cover_two_months():
    db = make([("A", "2024-06-30", 60), ("A", "2024-08-31", 100)])
    got = {r["period_end"]: (r["packs"], r["months"]) for r in db.query("select * from monthly_packs_pdf")}
    assert got["2024-08-31"] == (40, 2)


def test_annual_price_and_volume_join_on_year():
    db = make([("A", "2024-12-31", 1000)])
    db["avg_price"].insert_all([{"product": "cigarrillos", "period": "2024", "price": 5.07}])
    create_views(db)
    assert [dict(r) for r in db.query("select * from annual_cigarettes")] == [
        {"year": "2024", "packs": 1000, "price": 5.07}]


def test_brand_month_merges_a_brands_tiers_with_a_share_weighted_price():
    db = sqlite_utils.Database(memory=True)
    db["segment_sales"].insert_all([
        {"month": "2025-01", "tier": "PREMIUM", "brand": "MARLBORO", "company": "PM", "price": 6.0, "share_pct": 12.0, "source": "x"},
        {"month": "2025-01", "tier": "BAJO", "brand": "MARLBORO", "company": "PM", "price": 5.0, "share_pct": 4.0, "source": "x"},
        {"month": "2025-01", "tier": "MEDIO", "brand": "CAMEL", "company": "JTI", "price": 5.5, "share_pct": 8.0, "source": "x"}])
    create_views(db)
    got = {r["brand"]: r for r in db.query("select * from brand_month")}
    assert got["MARLBORO"]["share_pct"] == 16.0 and got["MARLBORO"]["price"] == pytest.approx((6 * 12 + 5 * 4) / 16)
    assert got["MARLBORO"]["rows"] == 2 and got["CAMEL"]["price"] == 5.5


def test_tourist_monthly_differences_each_area_and_flags_a_missing_month():
    db = sqlite_utils.Database(memory=True)
    rows = []
    for end, nat, tour in [("2024-01-31", 10, 4), ("2024-02-29", 25, 6), ("2024-04-30", 60, 9)]:     # March missing
        rows.append({"area": "Girona", "kind": "province", "period_end": end, "national_ytd": nat, "tourist_ytd": tour,
                     "basis": "current", "source": "x"})
    db["tourist_sales"].insert_all(rows)
    create_views(db)
    got = {r["period_end"]: (r["national"], r["tourist"], r["months"]) for r in db.query("select * from tourist_monthly")}
    assert got == {"2024-01-31": (10, 4, 1), "2024-02-29": (15, 2, 1), "2024-04-30": (35, 3, 2)}


def test_monthly_packs_and_unit_price_come_from_the_brand_files():
    db = sqlite_utils.Database(memory=True)
    db["brand_sales"].insert_all([
        {"month": "2016-02", "brand": "A", "packs": 100.0, "euros": 440.0},
        {"month": "2016-02", "brand": "B", "packs": 300.0, "euros": 1380.0},
        {"month": "2016-07", "brand": "A", "packs": 50.0, "euros": None},          # euros missing that month
        {"month": "2015-03", "brand": "A", "packs": None, "euros": 500.0}])           # packs missing that month
    create_views(db)
    packs = {r["period_end"]: (r["packs"], r["months"]) for r in db.query("select * from monthly_packs")}
    assert packs == {"2016-02-29": (400.0, 1), "2016-07-31": (50.0, 1)}
    price = {r["month"]: r["unit_price"] for r in db.query("select * from monthly_unit_price")}
    assert price == {"2016-02": pytest.approx(1820.0 / 400.0)}
