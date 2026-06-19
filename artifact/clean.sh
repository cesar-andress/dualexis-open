#!/usr/bin/env bash
# Remove caches, temporary build artefacts, legacy experiment outputs, and duplicate results.
# See artifact/ARTIFACT_EVALUATION.md
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

MODE="${1:-full}"

echo "==> Python caches"
find "$ROOT/dualexis" "$ROOT/tests" -type d -name __pycache__ -print0 2>/dev/null \
  | xargs -0 rm -rf 2>/dev/null || true
rm -rf "$ROOT/.pytest_cache" "$ROOT/.ruff_cache" "$ROOT/.mypy_cache" 2>/dev/null || true

if [[ "$MODE" == "full" ]]; then
  echo "==> Legacy experiment outputs (not in reproduction path)"
  LEGACY_RESULTS=(
    results/adversarial_privacy
    results/counterfactuals
    results/cssg
    results/sssg
    results/institutional_memory
    results/ontology_drift
    results/narratives
    results/experiments
    results/reports
    results/robustness
    results/validation_s2a
    results/measurements
    results/e2_independent_gt
    results/tsgg
  )
  for d in "${LEGACY_RESULTS[@]}"; do
    rm -rf "$ROOT/$d"
  done
fi

echo "==> regeneratable results"
rm -rf \
  "$ROOT/results/baseline_comparison" \
  "$ROOT/results/privacy_fuzz" \
  "$ROOT/results/leakage_audit" \
  "$ROOT/results/governance/formal"

if [[ "$MODE" == "full" ]]; then
  echo "==> Regenerable distribution bundles"
  rm -rf "$ROOT/dist"
fi

echo "Clean complete ($MODE)."
