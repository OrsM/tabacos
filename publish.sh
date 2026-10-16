#!/bin/sh
# Rebuild the database, rerun the analyses into it, swap it in and restart the service.
# Serves tobacco.db through ~/.config/systemd/user/tabacos-datasette.service (127.0.0.1:7695).
set -e
cd "$(dirname "$0")"
rm -f tobacco.db.new
uv run python -m tabacos.build raw tobacco.db.new > /dev/null
for a in stockpiling passthrough panel taxshock market border; do
  uv run python -m analyses.$a.run tobacco.db.new > /dev/null
done
mv tobacco.db.new tobacco.db
systemctl --user restart tabacos-datasette
