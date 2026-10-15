#!/bin/sh
# Download every URL in sources/es.urls into raw/ (skips files already present).
mkdir -p raw
grep -v '^#' sources/es.urls | while read -r url; do
  f="raw/$(basename "$url")"
  [ -s "$f" ] || curl -fsSL -o "$f" "$url"
done
