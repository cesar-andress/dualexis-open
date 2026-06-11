#!/usr/bin/env bash
# Reproduce JSS validation — see artifact/REPRODUCE.md
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "==> clean regeneratable outputs"
bash "$ROOT/artifact/clean.sh" results-only

echo "==> pip install -e ."
python3.12 -m pip install -e ".[dev]" -q

echo "==> validate-tsgg"
python3.12 -m dualexis.cli experiment validate-tsgg

echo "==> leakage-audit --fast"
python3.12 -m dualexis.cli experiment leakage-audit --fast

echo "==> formal-governance-audit"
python3.12 -m dualexis.cli experiment formal-governance-audit

echo "==> tsgg-trust-propagation --fast"
python3.12 -m dualexis.cli experiment tsgg-trust-propagation --fast --seeds 1,2,3

echo "==> export-harness-honesty"
python3.12 -m dualexis.cli experiment export-harness-honesty

echo "==> export-harness-b5-labels"
python3.12 -m dualexis.cli experiment export-harness-b5-labels

echo "==> pytest (JSS artifact suite)"
python3.12 -m pytest tests/artifact tests/unit \
  --ignore=tests/unit/test_paper_check.py \
  --ignore=tests/unit/test_pipeline.py \
  --ignore=tests/unit/test_edge_runtime.py \
  -q

echo "==> Done. See artifact/expected_outputs.md"
