# Artifact Evaluation Guide (JSS)

This document supports **Journal of Systems and Software** artifact evaluation for the TSGG reference implementation. It describes what the repository contains, how to install and run it, what to expect, and what reproducibility guarantees apply.

**Release:** v1.0.3 · **GitHub:** https://github.com/cesar-andress/dualexis-open · **Zenodo:** https://doi.org/10.5281/zenodo.20499184

**Canonical entry point:** `bash artifact/commands.sh`  
**Full clean before evaluation:** `bash artifact/clean.sh full`

---

## 1. Repository structure (artifact scope)

Evaluators should use the repository root (parent of `artifact/`). Core layout:

| Path | Role in AE | Required for `commands.sh` |
| --- | --- | --- |
| `artifact/` | Install, reproduce, evaluation docs | Yes |
| `dualexis/` | Reference implementation (CLI, harness, invariants) | Yes |
| `configs/` | Pre-registered synthetic scenario YAML | Yes |
| `experiments/` | Ground-truth YAML for bundled scenarios | Yes |
| `tests/unit/` | Unit tests (JSS artifact subset) | Yes |
| `tests/artifact/` | Post-reproduction output smoke tests | Yes |
| `results_reference/` | Pinned reference outputs and harness-generated LaTeX fragments | Yes |
| `results/` | CSV/JSON audit outputs (regenerable, gitignored) | Output |
| `pyproject.toml` | Package metadata and dependencies | Yes |

**Not included in this public repository:**

| Item | Reason |
| --- | --- |
| Manuscript LaTeX sources | Maintained in a separate private monorepo |
| Editorial or peer-review correspondence | Out of artefact scope |
| Legacy deprecated experiment batteries | Removed from public tree |

**Removed by `artifact/clean.sh full`:** Python caches, legacy experiment outputs under `results/`, and regenerable JSS result directories.

---

## 2. Installation steps

### 2.1 Requirements

| Component | Version / note |
| --- | --- |
| Python | **3.12+** (tested with 3.12) |
| OS | Linux or macOS recommended; Windows supported for CLI/tests |
| Network | Required once for `pip install` |
| External datasets | **None** — bundled synthetic scenarios only |
| GPU / CUDA | **Not required** |
| LaTeX | **Not required** for `commands.sh` |

### 2.2 Recommended procedure

```bash
# From repository root
bash artifact/clean.sh full          # optional but recommended for AE
python3.12 -m pip install -U pip
python3.12 -m pip install -e ".[dev]"
bash artifact/commands.sh
```

Alternative paths: see `INSTALL.md` (conda `artifact/environment.yml`, Docker `artifact/Dockerfile`).

### 2.3 Verify installation only

```bash
python3.12 -m pip install -e ".[dev]"
python3.12 -m dualexis.cli --help
python3.12 -m pytest tests/artifact -q
```

---

## 3. Reproduction commands

`artifact/commands.sh` performs, in order:

1. `artifact/clean.sh results-only` — remove regeneratable JSS outputs  
2. `pip install -e ".[dev]"`  
3. `python3.12 -m dualexis.cli experiment validate-tsgg`  
4. `python3.12 -m dualexis.cli experiment leakage-audit --fast`  
5. `python3.12 -m dualexis.cli experiment formal-governance-audit`  
6. JSS artifact test suite (`tests/artifact` + `tests/unit`, excluding legacy manuscript-check and non-deterministic pipeline snapshot test)

Equivalent: `make reproduce` from repository root.

---

## 4. Runtime

Measured on a clean virtual environment (Linux, Python 3.12, laptop-class CPU, 2026-06-01):

| Step | Approx. time |
| --- | ---: |
| `pip install -e ".[dev]"` | 5–30 s (network-dependent) |
| `validate-tsgg` | 30–45 s |
| `leakage-audit --fast` | 5–10 s |
| `formal-governance-audit` | 2–5 s |
| Pytest (640 tests) | 12–18 s |
| **Total `commands.sh`** | **~1 min** (after install) |

Full multiseed validation without `--fast` flags can take several minutes; the JSS paper uses pre-registered fast modes for leakage Monte Carlo where noted.

---

## 5. Hardware assumptions

- **CPU:** 2+ cores recommended; single-core sufficient but slower  
- **RAM:** ≥ 2 GiB free  
- **Disk:** ≥ 500 MiB for venv + regenerated `results/`  
- **Network:** Only for initial dependency install  
- **Containers:** Docker image built from `artifact/Dockerfile` runs the same `commands.sh` inside `python:3.12-slim`

No cluster, GPU, or proprietary hardware is assumed.

---

## 6. Expected outputs

After successful `commands.sh`, verify with `artifact/expected_outputs.md` or:

```bash
grep -q 'tab:harness-honesty' results_reference/tables/harness_honesty.tex
grep -q 'tab:privacy-fuzz' results_reference/tables/privacy_fuzz_results.tex
grep -q 'tab:leakage-audit' results_reference/tables/leakage_audit.tex
python3.12 -m pytest tests/artifact -q
```

### 6.1 Harness-generated LaTeX fragments

| File | Generator |
| --- | --- |
| `results_reference/tables/harness_honesty.tex` | `export-harness-honesty` |
| `results_reference/tables/privacy_fuzz_results.tex` | `validate-tsgg` |
| `results_reference/tables/leakage_audit.tex` | `leakage-audit --fast` |
| `results_reference/tables/baseline_results.tex` | `validate-tsgg` (supplementary) |

### 6.2 CSV / JSON artefacts

| Path | Content |
| --- | --- |
| `results/baseline_comparison/results.csv` | Multiseed baseline grid |
| `results/privacy_fuzz/results.csv` | Privacy fuzz probe outcomes (10 probes + header) |
| `results/leakage_audit/leakage_audit_report.json` | Leakage score and independence layers |
| `results/leakage_audit/overlap_metrics.csv` | Structural overlap metrics |
| `results/governance/formal/formal_governance_metrics.csv` | FSM compliance metrics |
| `results/governance/formal/governance_audit_report.json` | Full audit report |
| `results/governance/formal/traces/*.json` | **Exactly 100** sample governance traces |
| `results/tsgg/trust/trust_propagation_report.json` | Trust propagation metrics (`mean_path_trust`) |

### 6.3 Reference metric values (sanity checks)

Values below are from a verified clean run (seed 42, default iterations). Small floating-point drift (±0.01) is acceptable; structural properties must hold.

| Metric | Expected (approx.) |
| --- | ---: |
| Privacy fuzz pass rate | 10/10 probes pass (see CSV) |
| Leakage score \(L_S\) | 0.30 |
| Procedural independence | 1.00 |
| Semantic independence | ~0.71 |
| Distributional independence | ~0.70 |
| `governance_compliance_score` | ~0.44 |
| `institutional_reliance_index` | ~0.47 |
| `human_override_resilience` | ~0.10 |
| `decision_traceability` | **1.00** |
| Mean path trust \(\bar{T}_\pi\) | ~0.06 |
| Governance trace JSON count | **100** |
| Pytest | **640 passed**, 0 failed |

### 6.4 Tests

| Suite | Command | Expected |
| --- | --- | --- |
| Artifact smoke | `pytest tests/artifact -q` | 6 passed |
| Full JSS AE suite | as in `commands.sh` | 640 passed |

Legacy tests excluded from AE path:

- `tests/unit/test_paper_check.py` — legacy manuscript structure check (not shipped in this repo)
- `tests/unit/test_pipeline.py` — full JSON snapshot (UUID edge IDs non-stable across runs)

---

## 7. Reproducibility guarantees

| Guarantee | Mechanism |
| --- | --- |
| **Fixed randomness** | Default `--seed 42` on harness commands; deterministic scenario loaders |
| **No external data** | All inputs from `experiments/` YAML and in-repo simulators |
| **Clean regeneration** | `clean.sh` removes prior `results/` artefacts before reproduction |
| **No trace accumulation** | `formal-governance-audit` clears `results/governance/formal/traces/` before export (≤100 JSON files per run) |
| **Versioned dependencies** | Lower bounds in `pyproject.toml` / `artifact/requirements.txt` |
| **Fail-closed privacy** | Unit + fuzz tests assert forbidden keys never reach trace projections |
| **Idempotent tables** | Regenerated LaTeX fragments overwrite `results_reference/tables/` deterministically for fixed seeds |

**Not guaranteed (explicit non-claims):**

- Bit-identical JSON across Python patch releases if hash or float formatting changes  
- Field deployment outcomes or user-study results  
- PDF byte identity unless LaTeX distribution is pinned  

---

## 8. Artifact checklist (evaluator)

- [ ] Clone repository; confirm `artifact/INSTALL.md`, `REPRODUCE.md`, `commands.sh`, `expected_outputs.md` present  
- [ ] Run `bash artifact/clean.sh full`  
- [ ] Create fresh venv; run `bash artifact/commands.sh`  
- [ ] Confirm exit code 0 and 640 pytest passes  
- [ ] Confirm 100 governance trace JSON files (not hundreds from stale runs)  
- [ ] Spot-check tables contain expected `\label{tab:…}` markers  

---

## 9. Support files in `artifact/`

| File | Purpose |
| --- | --- |
| `INSTALL.md` | Detailed install (pip, conda, Docker) |
| `REPRODUCE.md` | Step-by-step reproduction |
| `commands.sh` | One-shot AE script |
| `clean.sh` | Remove caches, legacy outputs, duplicate results |
| `expected_outputs.md` | Path checklist |
| `requirements.txt` | Runtime dependency summary |
| `environment.yml` | Conda environment |
| `Dockerfile` | Container reproduction |
| `CITATION.cff` / `LICENSE` | Citation and license |

---

## 10. Contact and scope statement

This artifact validates **software trace structure, privacy ingress, governance FSM exports, benchmark leakage disclosure, and reproducible harness diagnostics** on synthetic data. It does not reproduce operational safety outcomes in deployed environments.

For questions during artifact evaluation, refer to `artifact/REPRODUCE.md`.
