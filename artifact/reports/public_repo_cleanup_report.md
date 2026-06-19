# Public repository cleanup report (historical audit, 2026-06-01)

Update (2026-06-11): current public release is v1.0.4. Zenodo DOI `10.5281/zenodo.20638103` remains the archival identifier; citation metadata is in `CITATION.cff`, `.zenodo.json`, and README.

---

**Repository:** https://github.com/cesar-andress/dualexis-open  
**Date:** 2026-06-01 (final pass)  
**Commit message:** `Finalize clean public artifact`

## Summary

| Check | Result |
|-------|--------|
| `EXPORT_REPORT.md` absent from root | Pass (not tracked; `.gitignore` blocks re-add) |
| `OPEN_SOURCE_READINESS_REPORT.md` absent from root | Pass (not tracked; `.gitignore` blocks re-add) |
| Fake Zenodo DOI placeholders removed | Pass |
| `legacy_archive` removed from `pyproject.toml` norecursedirs | Pass |
| `.tex` files limited to `results_reference/` | Pass (9 files, all harness-generated) |
| `bash artifact/commands.sh` | Pass (591 tests) |
| `python3.12 -m pytest tests/unit -q` | Partial (594 passed, 1 failed: `test_pipeline.py`) |
| Forbidden-string scan | Pass with justified residuals (see section 4) |
| Overall | Pass |

---

## 1. Removed files (this pass)

| Path | Action |
|------|--------|
| `EXPORT_REPORT.md` | Confirmed absent from repository root and git index; added to `.gitignore` |
| `OPEN_SOURCE_READINESS_REPORT.md` | Confirmed absent from repository root and git index; added to `.gitignore` |

No legacy modules or deleted artefact material were restored.

---

## 2. Zenodo / fake DOI cleanup

Removed all placeholder DOI identifiers:

| File | Before | After |
|------|--------|-------|
| `CITATION.cff` | `identifiers` entry `doi: pending-zenodo-archival` | DOI block removed; `message` includes **"Zenodo DOI will be added after archival."** |
| `artifact/CITATION.cff` | `doi: 10.5281/zenodo.TBD` | DOI block removed; same archival message |
| `CHANGELOG.md` | BibTeX `doi = {10.5281/zenodo.TBD}` | Removed; note **"Zenodo DOI will be added after archival."** |
| `README.md` | Generic “assign DOI after archival” | Explicit **"Zenodo DOI will be added after archival."** |

Verification:

```bash
grep -rn "10.5281/zenodo.TBD\|pending-zenodo-archival" .   # no matches
```

---

## 3. `pyproject.toml`

Removed `"legacy_archive"` from `[tool.pytest.ini_options].norecursedirs`; that directory does not exist in the public tree.

---

## 4. Remaining `.tex` files (9)

```bash
find /home/cesar/dualexis-open -name "*.tex"
```

| File | Generator / use | Keep? |
|------|-----------------|-------|
| `results_reference/tables/harness_honesty.tex` | `validate-tsgg` | Yes (reproducibility diff) |
| `results_reference/tables/privacy_fuzz_results.tex` | `validate-tsgg` | Yes |
| `results_reference/tables/leakage_audit.tex` | `leakage-audit --fast` | Yes |
| `results_reference/tables/baseline_results.tex` | `validate-tsgg` | Yes |
| `results_reference/tables/multiseed_statistics.tex` | multiseed statistics export | Yes |
| `results_reference/sections/formal_governance_model.tex` | `formal-governance-audit` | Yes |
| `results_reference/sections/leakage_analysis.tex` | `leakage-audit` | Yes |
| `results_reference/figures/tsgg_signature.tex` | TSGG TikZ source (`dualexis/tsgg/export.py`) | Yes |
| `results_reference/figures/trust_flow_graph.tex` | Trust-flow TikZ source (`dualexis/tsgg/trust_propagation.py`) | Yes |

All are harness-generated reproducibility outputs or TikZ sources referenced by code. Marked `linguist-generated` in `.gitattributes`. No manuscript `.tex` remains.

---

## 5. Forbidden-string grep scan

```bash
grep -Rni "ESWA|Expert Systems with Applications|reviewer|camera-ready|draft|TODO|FIXME|paper/|main_jss|submission" .
```

| Metric | Value |
|--------|------:|
| Total hits (excluding `.git/`) | 82 |
| Hits excluding this report file | 61 |

| Pattern | Disposition |
|---------|-------------|
| `TODO` / `FIXME` / `camera-ready` / `draft` / `main_jss` | None in artefact-critical paths |
| `paper/` in `docs/*.md` | Justified (cross-refs to private monorepo manuscript, not shipped) |
| `paper/` in `.gitignore` | Justified (ignore rule) |
| `ESWA` / `run_empirical_eswa_package` | Justified (hidden legacy CLI; not in `commands.sh`) |
| `reviewer` in `multiseed_statistics.py` | Justified (author-only narrative markdown in legacy battery) |
| `submission` in `LICENSE` | Justified (Apache 2.0 legal wording) |
| `TBD` in `docs/evaluation.md` | Justified (research-ethics placeholder policy, not a Zenodo DOI) |

---

## 6. Test results

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

`test_pipeline.py` is excluded from the JSS artifact suite (`artifact/commands.sh` uses `--ignore=tests/unit/test_pipeline.py`) because pipeline JSON includes non-deterministic UUID edge IDs.

---

## Final verdict: Pass

Public artefact is clean: no root export reports, no fake Zenodo DOIs, pytest norecursedirs aligned with tree, `.tex` confined to reproducibility outputs under `results_reference/`, validation harness green.
