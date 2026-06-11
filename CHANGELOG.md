# Changelog

## v1.0.3 — 2026-06-02

**Tag:** `v1.0.3`  
**Zenodo:** https://doi.org/10.5281/zenodo.20499184  
**GitHub:** https://github.com/cesar-andress/dualexis-open

### Changes

- Published Zenodo archival release (`10.5281/zenodo.20499184`).
- Updated `CITATION.cff`, `.zenodo.json`, README, and artifact documentation with DOI and version `v1.0.3`.

### Citation

```bibtex
@software{sanchez2026tsggsoftware,
  author  = {S{\'a}nchez, C{\'e}sar Andr{\'e}s and Mart{\'i}n Moncunill, David},
  title   = {Trusted Safety State Governance Graph ({TSGG}) Reference Implementation},
  year    = {2026},
  version = {1.0.3},
  doi     = {10.5281/zenodo.20499184},
  url     = {https://github.com/cesar-andress/dualexis-open}
}
```

---

## v1.0.0 — 2026-06-01

**Title:** TSGG Reference Implementation  
**Repository:** https://github.com/cesar-andress/dualexis-open  
**Tag:** `v1.0.0`  
**Date:** 2026-06-01  
**License:** Apache-2.0

First public release of the TSGG reference implementation and validation harness for JSS software-artefact evaluation.

### What this release contained

- Python package `dualexis` — trace export, privacy ingress (A1), governance FSM (A4), append-only audit (A5)
- Validation harness CLI — `validate-tsgg`, `leakage-audit`, `formal-governance-audit`
- Reproduction scripts — `artifact/commands.sh`, `artifact/REPRODUCE.md`, `artifact/expected_outputs.md`
- Pinned reference outputs under `results_reference/`

Superseded for citation purposes by **v1.0.3** and Zenodo DOI `10.5281/zenodo.20499184`.

### Authors

- David Martín Moncunill — Conceptualization, Methodology, Software, Formal analysis, Investigation, Writing
- César Andrés Sánchez — Conceptualization, Methodology, Validation, Investigation, Supervision, Writing
