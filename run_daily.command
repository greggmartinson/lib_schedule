#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

if [[ ! -d ".venv" ]]; then
  echo "Missing .venv. Run setup steps in README.md first."
  exit 1
fi

source ".venv/bin/activate"
python3 generate_report.py

LATEST_REPORT="$(ls -1t output/daily_schedule_*.html 2>/dev/null | head -n1 || true)"
if [[ -n "$LATEST_REPORT" ]]; then
  open "$LATEST_REPORT"
fi
