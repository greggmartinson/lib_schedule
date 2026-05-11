#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

if [[ ! -d ".venv" ]]; then
  echo "Missing .venv. Run setup steps in README.md first."
  exit 1
fi

source ".venv/bin/activate"
python3 sync_google_slides.py
