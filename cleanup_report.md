            # Cleanup report — dualexis-open

            Target: https://github.com/cesar-andress/dualexis-open

            ## Excluded from open repository

            - `paper/` (LaTeX manuscript, submission material, reviews)
            - `dist/` submission packages
            - JSS build scripts (`build_jss_submission.py`)

            ## Moved to `legacy_archive/`

            - `dualexis/paper`
- `dualexis/counterfactual`
- `dualexis/institutional_memory`
- `dualexis/ontology_drift`
- `dualexis/robustness`
- `dualexis/adversarial_privacy`
- `dualexis/narratives`
- `tests/unit/test_paper_check.py`
- `tests/unit/test_dataset_adapters.py`
- `tests/unit/test_counterfactual.py`
- `tests/unit/test_institutional_memory.py`
- `tests/unit/test_ontology_drift.py`
- `tests/unit/test_robustness.py`
- `tests/unit/test_adversarial_privacy.py`
- `tests/unit/test_cssg.py`
- `tests/unit/test_sssg.py`
- `tests/unit/test_narratives.py`
- `docs/privacy_fuzz_eswa_contribution.md`
- `infrastructure/ (from monorepo)`
- `paper_requirements/ (from monorepo)`

            ## Active paths

            - `dualexis/` — TSGG core implementation
            - `artifact/` — reproducibility
            - `tests/` — unit/integration tests (legacy tests archived)
            - `results_reference/` — pinned validation outputs

            ## ESWA hygiene

            ESWA-named files only under `legacy_archive/` (if present).
