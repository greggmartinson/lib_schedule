#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

if [[ ! -x ".venv/bin/python" ]]; then
  echo "Missing .venv. Run setup steps in README.md first."
  exit 1
fi

".venv/bin/python" login_once.py
".venv/bin/python" sync_google_slides.py --print
