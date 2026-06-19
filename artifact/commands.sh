#!/usr/bin/env bash
# Reproduce validation results — see artifact/REPRODUCE.md
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

echo "==> verify-benchmark-manifest"
python3.12 -m dualexis.cli experiment verify-benchmark-manifest

echo "==> decoupled-benchmark"
python3.12 -m dualexis.cli experiment decoupled-benchmark

echo "==> shared-spec-regression"
python3.12 -m dualexis.cli experiment shared-spec-regression

echo "==> export-harness-b5-labels (shared-spec regression supplementary)"
python3.12 -m dualexis.cli experiment export-harness-b5-labels

echo "==> audit-comparison"
python3.12 -m dualexis.cli experiment audit-comparison

echo "==> coupling-controlled-par (diagnostic)"
python3.12 -m dualexis.cli experiment coupling-controlled-par

echo "==> pytest (reproduction test suite)"
python3.12 -m pytest tests/artifact tests/unit \
  --ignore=tests/unit/test_paper_check.py \
  --ignore=tests/unit/test_pipeline.py \
  --ignore=tests/unit/test_edge_runtime.py \
  -q

echo "==> Done. See artifact/expected_outputs.md"
