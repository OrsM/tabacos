#!/bin/sh
# Download every URL in sources/es.urls into raw/ (skips files already present).
mkdir -p raw
grep -v '^#' sources/es.urls | while read -r url; do
  f="raw/$(echo "${url##*onsultivo/}" | sed 's|/|_|g; s|%20|_|g' | tr 'A-Z' 'a-z')"
  [ -s "$f" ] || curl -fsSL -o "$f" "$url" || echo "FAILED $url" >&2
done
