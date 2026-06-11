# Open-source readiness

Repository: **TSGG Reference Implementation**
URL: https://github.com/cesar-andress/dualexis-open
Version: v1.0.3
Audit date: 2026-06-02

## Repository quality score

**99/100**

| Dimension | Score |
|-----------|------:|
| Documentation completeness | 100/100 |
| Reproducibility | 100/100 |
| Testability | 100/100 |
| Repository hygiene | 100/100 |
| Licensing clarity | 100/100 |
| Metadata quality | 95/100 |

## Missing files

- None detected.

## Missing metadata

- None: Zenodo DOI https://doi.org/10.5281/zenodo.20499184 in `CITATION.cff` (release v1.0.3).

## Licensing issues

- None: Apache-2.0 `LICENSE` at repository root and in `artifact/`.

## Reproducibility issues

- None: `bash artifact/commands.sh` completed with exit code 0.

## Language audit

- User-facing documentation and comments: **English**.
- Author names retain diacritics in `CITATION.cff` (proper names only).

## Removed from public tree

- `dualexis/paper`
- `dualexis/counterfactual`
- `dualexis/institutional_memory`
- `dualexis/ontology_drift`
- `dualexis/robustness`
- `dualexis/adversarial_privacy`
- `dualexis/narratives`
- `tests/unit/test_paper_check.py`
- `tests/unit/test_edge_runtime.py`
- `tests/legacy_archive/test_dataset_adapters.py`
- `tests/unit/test_counterfactual.py`
- `tests/unit/test_institutional_memory.py`
- `tests/unit/test_ontology_drift.py`
- `tests/unit/test_robustness.py`
- `tests/unit/test_adversarial_privacy.py`
- `tests/unit/test_cssg.py`
- `tests/unit/test_sssg.py`
- `tests/unit/test_narratives.py`
- `docs/privacy_fuzz_eswa_contribution.md`

## Verification checks

- Pass: file README.md
- Pass: file LICENSE
- Pass: file CITATION.cff
- Pass: file CONTRIBUTING.md
- Pass: file CODE_OF_CONDUCT.md
- Pass: file CHANGELOG.md
- Pass: file Dockerfile
- Pass: file Makefile
- Pass: file requirements.txt
- Pass: file environment.yml
- Pass: file .zenodo.json
- Pass: file artifact/INSTALL.md
- Pass: file artifact/REPRODUCE.md
- Pass: file artifact/ARTIFACT_EVALUATION.md
- Pass: file artifact/expected_outputs.md
- Pass: file artifact/EXPECTED_OUTPUTS.md
- Pass: file artifact/commands.sh
- Pass: file artifact/clean.sh
- Pass: file artifact/environment.yml
- Pass: file artifact/LICENSE
- Pass: file artifact/requirements.txt
- Pass: file artifact/Dockerfile
- Pass: file results_reference/baseline_comparison/results.csv
- Pass: file tests/artifact/test_jss_reproduce_outputs.py
- Pass: no ESWA paths outside legacy_archive: []
- Pass: no paper/ directory
- Pass: no legacy_archive/ directory

## Required artefact paths

- `README.md`
- `LICENSE`
- `CITATION.cff`
- `environment.yml` (root; mirrored in `artifact/environment.yml`)
- `artifact/INSTALL.md`, `artifact/REPRODUCE.md`, `artifact/commands.sh`, `artifact/expected_outputs.md`

## Overall: Pass

## Audit actions (2026-06-01)

- Synchronized public tree from monorepo via `scripts/build_dualexis_open.py`.
- Removed legacy extension modules, ESWA docs, and app-layer integration tests/examples.
- Completed `artifact/` bundle: `INSTALL.md`, `REPRODUCE.md`, `commands.sh`, `clean.sh`, `expected_outputs.md`, `ARTIFACT_EVALUATION.md`, `environment.yml`, `LICENSE`, `Dockerfile`, `requirements.txt`.
- Deleted internal reports: `EXPORT_REPORT.md`, `OPEN_SOURCE_READINESS_REPORT.md` (superseded by this file).
- Purged caches and regeneratable `results/` before verification (`artifact/clean.sh full`).
- Verified: `591 passed` in JSS artifact pytest suite; `artifact/commands.sh` exit code 0.

