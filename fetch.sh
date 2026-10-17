#!/bin/sh
# Download every URL in sources/es.urls into raw/ (skips files already present).
mkdir -p raw
grep -v '^#' sources/es.urls | while read -r url; do
  f="raw/$(echo "${url##*onsultivo/}" | sed 's|/|_|g; s|%20|_|g' | tr 'A-Z' 'a-z')"
  [ -s "$f" ] || curl -fsSL -o "$f" "$url" || echo "FAILED $url" >&2
done

# BOE retail-price resolutions (ids listed in sources/boe/pvp-resolutions.tsv; refresh the list with
# `python -m tabacos.pvp discover FROM TO`).
mkdir -p raw/boe
cut -f1 sources/boe/pvp-resolutions.tsv | while read -r id; do
  [ -s "raw/boe/$id.xml" ] || curl -fsSL -o "raw/boe/$id.xml" "https://www.boe.es/diario_boe/xml.php?id=$id" || echo "FAILED $id" >&2
done

# Monthly sales by brand (Excel); files that do not exist are skipped.
mkdir -p raw/xlsx
grep -v '^#' sources/es-xlsx.urls | while read -r url; do
  f="raw/xlsx/$(echo "${url##*Ventas/}" | sed 's|/|_|g; s|%20|_|g')"
  [ -s "$f" ] || curl -fsSL -o "$f" "$url" 2>/dev/null || rm -f "$f"
done
