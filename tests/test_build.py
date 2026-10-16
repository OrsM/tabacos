from pathlib import Path
import sqlite_utils
from tabacos.build import TABLES, build
from tabacos.regional import parse_regional
from tabacos.segments import parse_segments

FIX = Path(__file__).parent / "fixtures"


def test_build_logs_each_table_per_report_and_keeps_going(tmp_path):
    raw = tmp_path / "raw"
    raw.mkdir()
    (raw / "good.pdf").touch()
    (raw / "empty.pdf").touch()
    texts = {"good.pdf": {"-layout": (FIX / "ccaa-2025-06.txt").read_text(), "-raw": ""},
             "empty.pdf": {"-layout": "nothing", "-raw": "nothing"}}
    db_path = tmp_path / "t.db"
    tables = {"regional_sales": ([(parse_regional, "-layout")], TABLES["regional_sales"][1]),
              "segment_sales": ([(parse_segments, "-layout")], TABLES["segment_sales"][1])}
    build(raw, db_path, extract=lambda pdf, mode: texts[pdf.name][mode], tables=tables, cache_dir=None)
    db = sqlite_utils.Database(db_path)
    assert db["regional_sales"].count == 32        # 16 communities, this year and the prior-year column
    log = {(r["source"], r["table"]): r["status"] for r in db["parse_log"].rows}
    assert log[("good.pdf", "regional_sales")] == "ok"
    assert log[("good.pdf", "segment_sales")] == "absent"
    assert log[("empty.pdf", "regional_sales")] == "absent"


def _setup(tmp_path):
    raw = tmp_path / "raw"
    raw.mkdir()
    (raw / "good.pdf").write_bytes(b"report one")
    tables = {"regional_sales": ([(parse_regional, "-layout")], TABLES["regional_sales"][1])}
    calls = []

    def extract(pdf, mode):
        calls.append((pdf.name, mode))
        return (FIX / "ccaa-2025-06.txt").read_text()
    return raw, tables, calls, extract


def test_second_build_reuses_cached_parses_and_a_changed_file_or_parser_reparses(tmp_path):
    raw, tables, calls, extract = _setup(tmp_path)
    cache = tmp_path / "cache"
    build(raw, tmp_path / "a.db", extract=extract, tables=tables, cache_dir=cache, fingerprint="v1")
    assert len(calls) == 1
    build(raw, tmp_path / "b.db", extract=extract, tables=tables, cache_dir=cache, fingerprint="v1")
    assert len(calls) == 1                                              # cached
    assert sqlite_utils.Database(tmp_path / "b.db")["regional_sales"].count == 32
    build(raw, tmp_path / "c.db", extract=extract, tables=tables, cache_dir=cache, fingerprint="v2")
    assert len(calls) == 2                                              # parser code changed
    (raw / "good.pdf").write_bytes(b"report one, revised")
    build(raw, tmp_path / "d.db", extract=extract, tables=tables, cache_dir=cache, fingerprint="v2")
    assert len(calls) == 3                                              # file changed
