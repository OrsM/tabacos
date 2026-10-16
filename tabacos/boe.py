"""Consolidated-law articles from the BOE open-data API. Usage: python -m tabacos.boe  (rewrites sources/boe/)"""
import urllib.request
from pathlib import Path

API = "https://www.boe.es/datosabiertos/api/legislacion-consolidada/id/{law}/texto/bloque/{block}"
ARTICLES = {                       # file -> (law id, block)
    "ley-38-1992-art-60.xml": ("BOE-A-1992-28741", "a60"),      # tobacco excise rates
    "ley-37-1992-art-90.xml": ("BOE-A-1992-28740", "a90"),      # VAT general rate
}
DIR = Path(__file__).parent.parent / "sources" / "boe"


def fetch(law: str, block: str) -> str:
    req = urllib.request.Request(API.format(law=law, block=block), headers={"Accept": "application/xml"})
    return urllib.request.urlopen(req, timeout=60).read().decode("utf-8")


if __name__ == "__main__":
    for name, (law, block) in ARTICLES.items():
        (DIR / name).write_text(fetch(law, block), encoding="utf-8")
        print(name)
