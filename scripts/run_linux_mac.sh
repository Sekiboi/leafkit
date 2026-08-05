#!/usr/bin/env bash
# Run Sekikit from source on Linux or macOS (offline, free forever).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ ! -d .venv ]]; then
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate
pip install -q -r requirements.txt

if [[ "${1:-}" == "cli" ]]; then
  shift
  exec python -m sekikit.cli "$@"
fi

if [[ "${1:-}" == "test" ]]; then
  pip install -q pytest
  exec pytest -q
fi

exec python run.py
