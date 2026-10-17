#!/bin/sh
# Build docs/learnings.md into the website's public/reports/tabacos/; then run ./deploy.sh in the website repo.
# Refuses while the draft note is in the file; pass --draft to build a preview anyway.
set -e
cd "$(dirname "$0")"
uv run --group report python -m tabacos.report docs/learnings.md "${WEBSITE:-$HOME/claude_projects/website}/public/reports/tabacos" "$@"
