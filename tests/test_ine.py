import json
from pathlib import Path
from tabacos.ine import parse_arrivals

FIX = Path(__file__).parent / "fixtures"


def test_keeps_only_the_monthly_base_series_with_region_and_month():
    rows = parse_arrivals(json.loads((FIX / "frontur-mini.json").read_text()))
    assert sorted((r["region"], r["month"], r["arrivals"]) for r in rows) == [
        ("Balears, Illes", "2026-08", 2100000), ("Total Nacional", "2026-07", 11538796), ("Total Nacional", "2026-08", 12256087)]
