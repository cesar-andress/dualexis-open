# Open-source readiness

Repository: **TSGG Reference Implementation**
URL: https://github.com/cesar-andress/dualexis-open
Version: v1.0.0
Audit date: 2026-06-01

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

- Zenodo DOI not yet minted; see `CITATION.cff` message: "Zenodo DOI will be added after archival."

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

- **PASS** — file README.md
- **PASS** — file LICENSE
- **PASS** — file CITATION.cff
- **PASS** — file CONTRIBUTING.md
- **PASS** — file CODE_OF_CONDUCT.md
- **PASS** — file CHANGELOG.md
- **PASS** — file Dockerfile
- **PASS** — file Makefile
- **PASS** — file requirements.txt
- **PASS** — file environment.yml
- **PASS** — file .zenodo.json
- **PASS** — file artifact/INSTALL.md
- **PASS** — file artifact/REPRODUCE.md
- **PASS** — file artifact/ARTIFACT_EVALUATION.md
- **PASS** — file artifact/expected_outputs.md
- **PASS** — file artifact/EXPECTED_OUTPUTS.md
- **PASS** — file artifact/commands.sh
- **PASS** — file artifact/clean.sh
- **PASS** — file artifact/environment.yml
- **PASS** — file artifact/LICENSE
- **PASS** — file artifact/requirements.txt
- **PASS** — file artifact/Dockerfile
- **PASS** — file results_reference/baseline_comparison/results.csv
- **PASS** — file tests/artifact/test_jss_reproduce_outputs.py
- **PASS** — no ESWA paths outside legacy_archive: []
- **PASS** — no paper/ directory
- **PASS** — no legacy_archive/ directory

## Required artefact paths

- `README.md`
- `LICENSE`
- `CITATION.cff`
- `environment.yml` (root; mirrored in `artifact/environment.yml`)
- `artifact/INSTALL.md`, `artifact/REPRODUCE.md`, `artifact/commands.sh`, `artifact/expected_outputs.md`

## Overall: **PASS**

## Audit actions (2026-06-01)

- Synchronized public tree from monorepo via `scripts/build_dualexis_open.py`.
- Removed legacy extension modules, ESWA docs, and app-layer integration tests/examples.
- Completed `artifact/` bundle: `INSTALL.md`, `REPRODUCE.md`, `commands.sh`, `clean.sh`, `expected_outputs.md`, `ARTIFACT_EVALUATION.md`, `environment.yml`, `LICENSE`, `Dockerfile`, `requirements.txt`.
- Deleted internal reports: `EXPORT_REPORT.md`, `OPEN_SOURCE_READINESS_REPORT.md` (superseded by this file).
- Purged caches and regeneratable `results/` before verification (`artifact/clean.sh full`).
- Verified: `591 passed` in JSS artifact pytest suite; `artifact/commands.sh` exit code 0.

