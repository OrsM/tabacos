"""International tourist arrivals by main destination region (INE FRONTUR, table 10823, monthly).
Usage: python -m tabacos.ine   (rewrites sources/ine/frontur-destination.csv)"""
import csv
import json
import re
import urllib.request
from pathlib import Path

URL = "https://servicios.ine.es/wstempus/js/ES/DATOS_TABLA/10823?nult=200"
CSV_FILE = Path(__file__).parent.parent / "sources" / "ine" / "frontur-destination.csv"
_NAME = re.compile(r"^(?:Turista\. )?(.+?)\.(?: Turista\.)? Dato base\.\s*$")


def parse_arrivals(series: list[dict]) -> list[dict]:
    """Rows (region, month, arrivals) from the 'Dato base' series; rates and cumulative series are skipped."""
    rows = []
    for s in series:
        m = _NAME.match(s["Nombre"])
        if m:
            rows += [{"region": m[1], "month": f"{p['Anyo']}-{p['FK_Periodo']:02d}", "arrivals": int(p["Valor"])} for p in s["Data"]]
    return sorted(rows, key=lambda r: (r["region"], r["month"]))


def read_arrivals() -> list[dict]:
    if not CSV_FILE.exists():
        return []
    with CSV_FILE.open(encoding="utf-8") as f:
        return [{**r, "arrivals": int(r["arrivals"])} for r in csv.DictReader(f)]


if __name__ == "__main__":
    rows = parse_arrivals(json.load(urllib.request.urlopen(URL, timeout=60)))
    CSV_FILE.parent.mkdir(parents=True, exist_ok=True)
    with CSV_FILE.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["region", "month", "arrivals"])
        w.writeheader()
        w.writerows(rows)
    print(len(rows), "rows,", len({r["region"] for r in rows}), "regions")
