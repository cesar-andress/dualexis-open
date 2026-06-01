#!/usr/bin/env bash
# Reproduce JSS validation — see artifact/REPRODUCE.md
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "==> pip install -e ."
python3.12 -m pip install -e ".[dev]" -q

echo "==> validate-tsgg"
python3.12 -m dualexis.cli experiment validate-tsgg

echo "==> leakage-audit --fast"
python3.12 -m dualexis.cli experiment leakage-audit --fast

echo "==> formal-governance-audit"
python3.12 -m dualexis.cli experiment formal-governance-audit

echo "==> pytest tests/unit"
python3.12 -m pytest tests/unit -q

echo "==> Done. See artifact/expected_outputs.md"
