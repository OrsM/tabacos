"""Find report URLs by probing. The site has no index page and filenames vary by year.

Usage: python -m tabacos.discover FROM_YEAR TO_YEAR   (prints URLs that answer 200)
"""
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor

MONTHS = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
          "septiembre", "octubre", "noviembre", "diciembre"]
BASE = "https://www.hacienda.gob.es/tabacos/informes%20comite%20consultivo/"
STYLES = ["informe-mercado-{m}{yy}", "informe-mercado-{m}{y}", "informe-mercado-{m}-{yy}",
          "informe-mercado-{m}-{y}", "informe-{m}-{y}", "informe-{m}{y}", "informe-comite-{m}{yy}",
          "informe-comite-{m}{y}", "informe-de-mercado-{m}{yy}", "informe-mercado.{m}{yy}",
          "informe-mercado-{m}{yy}-2", "informe-mercado-{m}{y}-2", "informe-mercado-{m}",
          "informe-{m}{yy}", "informe-mercado{m}{yy}", "informemercado{m}{yy}"]


def candidates(year: int, month: int):
    """URLs a report for (year, month) has been published under, across filename styles."""
    for style in STYLES:
        name = style.format(m=MONTHS[month - 1], y=year, yy=str(year)[2:])
        for folder in (f"informes{year}", f"iinformes{year}"):
            yield f"{BASE}{folder}/{name}.pdf"


def month_of(filename: str) -> int | None:
    name = filename.lower()
    return next((i + 1 for i, m in enumerate(MONTHS) if m in name), None)


def exists(url: str) -> bool:
    try:
        req = urllib.request.Request(url, method="HEAD")
        return urllib.request.urlopen(req, timeout=30).status == 200
    except OSError:
        return False


def discover(years: range) -> list[str]:
    urls = [u for y in years for m in range(1, 13) for u in candidates(y, m)]
    with ThreadPoolExecutor(12) as pool:
        return [u for u, ok in zip(urls, pool.map(exists, urls)) if ok]


if __name__ == "__main__":
    print("\n".join(discover(range(int(sys.argv[1]), int(sys.argv[2]) + 1))))
