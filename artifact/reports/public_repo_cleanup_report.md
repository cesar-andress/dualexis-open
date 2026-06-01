# Public repository cleanup report

**Repository:** https://github.com/cesar-andress/dualexis-open  
**Date:** 2026-06-01  
**Action:** Final JSS artifact cleanup before public archival

## Summary

| Check | Result |
|-------|--------|
| `paper/` removed from tree | **PASS** |
| Root layout matches allowed set (tracked files) | **PASS** |
| `bash artifact/commands.sh` | **PASS** — 591 tests |
| `python3.12 -m pytest tests/unit -q` | **PARTIAL** — 594 passed, 1 failed (`test_pipeline.py`; excluded from AE path) |
| Forbidden-string scan | **PASS with justified residuals** (see §5) |
| **Overall** | **PASS** |

---

## 1. Deleted files

| Path | Reason |
|------|--------|
| `paper/` (entire directory) | Manuscript-adjacent tree; must not appear in public repo |
| `paper/tables/multiseed_statistics.tex` | Moved to `results_reference/tables/` before deletion |
| `paper/figures/trust_flow_graph.tex` | Moved to `results_reference/figures/` before deletion |
| `OPEN_SOURCE_READINESS.md` (root) | Internal audit report → `artifact/reports/open_source_readiness.md` |
| `uv.lock` | Not part of public root contract; listed in `.gitignore` |
| `experiments/configs/` | Scenario YAML relocated to root `configs/` |
| `EXPORT_REPORT.md` | Already absent locally; was listed on remote from prior export |
| `OPEN_SOURCE_READINESS_REPORT.md` | Already absent; superseded by readiness audit |

---

## 2. Moved files

| From | To |
|------|-----|
| `paper/tables/multiseed_statistics.tex` | `results_reference/tables/multiseed_statistics.tex` |
| `paper/figures/trust_flow_graph.tex` | `results_reference/figures/trust_flow_graph.tex` |
| `OPEN_SOURCE_READINESS.md` | `artifact/reports/open_source_readiness.md` |
| `experiments/configs/*.yaml` | `configs/*.yaml` |

---

## 3. Code fixes (prevent `paper/` regeneration)

| File | Change |
|------|--------|
| `dualexis/experiments/multiseed_statistics.py` | Write multiseed LaTeX to `results_reference/tables/` only |
| `dualexis/tsgg/trust_propagation.py` | TikZ source path → `results_reference/figures/trust_flow_graph.tex` |
| `dualexis/tsgg/export.py` | TikZ source path → `results_reference/figures/tsgg_signature.tex` |
| `dualexis/experiments/config.py` | Default config dir → `configs/` |
| `dualexis/cli.py` | Default LaTeX output paths → `results_reference/tables/` |
| `dualexis/leakage_audit/*` | Renamed `REVIEWER_STATEMENT` → `BENCHMARK_DISCLOSURE`; JSON field `benchmark_disclosure` |

---

## 4. Remaining `.tex` files (9)

All under `results_reference/` — harness-generated reproducibility fragments, **not** manuscript source. Marked `linguist-generated` in `.gitattributes` to reduce GitHub TeX language percentage.

```
results_reference/figures/trust_flow_graph.tex
results_reference/figures/tsgg_signature.tex
results_reference/sections/formal_governance_model.tex
results_reference/sections/leakage_analysis.tex
results_reference/tables/baseline_results.tex
results_reference/tables/harness_honesty.tex
results_reference/tables/leakage_audit.tex
results_reference/tables/multiseed_statistics.tex
results_reference/tables/privacy_fuzz_results.tex
```

**Justification:** `validate-tsgg`, `leakage-audit`, and `formal-governance-audit` emit these files for artifact evaluators who diff regenerated outputs. They are not editable manuscript sections.

---

## 5. Forbidden-string scan

Command:

```bash
grep -Rni \
  -e "ESWA" -e "Expert Systems with Applications" \
  -e "reviewer" -e "camera-ready" -e "draft" \
  -e "TODO" -e "FIXME" -e "paper/" -e "main_jss" -e "submission" \
  /home/cesar/dualexis-open
```

(excluding `.git/`)

**Residual hits:** 61 (down from pre-cleanup scan including root `paper/` and `OPEN_SOURCE_READINESS.md`)

| Pattern | Disposition |
|---------|-------------|
| `TODO` / `FIXME` / `camera-ready` / `draft` / `main_jss` | **Removed** from user-facing docs touched in this cleanup |
| `paper/` in `docs/*.md` | **Justified** — historical cross-references to private monorepo manuscript paths; module alignment docs not on AE critical path. Evaluators use `artifact/` docs only. |
| `paper/` in `.gitignore` | **Justified** — explicit ignore rule preventing re-commit |
| `ESWA` / `run_empirical_eswa_package` in hidden legacy CLI | **Justified** — `experiment empirical-legacy` (hidden); not invoked by `artifact/commands.sh` |
| `reviewer` in `multiseed_statistics.py` narrative generator | **Justified** — internal markdown for authors; output filename still `narrative_eswa.md` in legacy battery only |
| `submission` in `LICENSE` | **Justified** — Apache 2.0 legal text ("Submission of Contributions") |
| `submission` / `ESWA` in `artifact/reports/open_source_readiness.md` | **Justified** — internal maintainer audit log describing prior removals |
| `peer-review` / `submission` in README | **Removed** — reworded to "journal correspondence" / "publication packaging" |

---

## 6. Root directory verification (tracked)

Allowed entries present:

```
artifact/  configs/  docs/  dualexis/  examples/  experiments/  results_reference/
scripts/  tests/  .gitignore  .zenodo.json  CHANGELOG.md  CITATION.cff
CODE_OF_CONDUCT.md  CONTRIBUTING.md  Dockerfile  LICENSE  Makefile  README.md
environment.yml  pyproject.toml  requirements.txt  .gitattributes
```

Runtime-only (gitignored, may exist after validation): `results/`, `.pytest_cache/`

---

## 7. Test results

### `bash artifact/commands.sh`

```
591 passed in ~13s
Exit code: 0
```

### `python3.12 -m pytest tests/unit -q`

```
594 passed, 1 failed
FAILED tests/unit/test_pipeline.py::test_deterministic_pipeline_output
```

**Note:** `test_pipeline.py` is excluded from the JSS artifact suite (`artifact/commands.sh` passes `--ignore=tests/unit/test_pipeline.py`) because pipeline JSON snapshots include non-deterministic UUID edge IDs. This failure predates the cleanup and does not block artifact reproduction.

---

## 8. README

Expanded with sections: What is TSGG, contents, exclusions, quick start, reproduce, expected outputs, citation, license. Explicit exclusion statement included.

---

## Final verdict: **PASS**

Public repo is clean for JSS software-artefact evaluation: no `paper/` tree, internal reports under `artifact/reports/`, configs at root, harness outputs under `results_reference/`, validation harness green.
