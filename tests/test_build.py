from pathlib import Path
import sqlite_utils
from tabacos.build import build

FIX = Path(__file__).parent / "fixtures"


def test_build_logs_each_table_per_report_and_keeps_going(tmp_path):
    raw = tmp_path / "raw"
    raw.mkdir()
    (raw / "good.pdf").touch()
    (raw / "empty.pdf").touch()
    texts = {"good.pdf": {"-layout": (FIX / "ccaa-2025-06.txt").read_text(), "-raw": ""},
             "empty.pdf": {"-layout": "nothing", "-raw": "nothing"}}
    db_path = tmp_path / "t.db"
    build(raw, db_path, extract=lambda pdf, mode: texts[pdf.name][mode])
    db = sqlite_utils.Database(db_path)
    assert db["regional_sales"].count == 16
    log = {(r["source"], r["table"]): r["status"] for r in db["parse_log"].rows}
    assert log[("good.pdf", "regional_sales")] == "ok"
    assert log[("good.pdf", "segment_sales")] == "absent"
    assert log[("empty.pdf", "regional_sales")] == "absent"
