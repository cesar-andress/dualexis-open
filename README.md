# TSGG Reference Implementation

Open-source reference code and validation harness for **Trusted Safety State Governance Graph (TSGG)** — a software trace architecture for auditable human–AI systems.

**Repository:** https://github.com/cesar-andress/dualexis-open  
**Version:** v1.0.3 · **Zenodo:** https://doi.org/10.5281/zenodo.20499184 · **License:** Apache-2.0

This repository does not contain the manuscript, journal correspondence, editorial reports, or publication packaging.

## What is TSGG?

TSGG specifies a typed trace pipeline for systems that must export privacy-bounded evidence, state evolution, recommendations, governance disposition, and append-only audit in one inspectable artefact:

```
Evidence → Safety State → Causal Transition → Recommendation → Governance Decision → Audit Trace
```

The reference implementation covers fail-closed privacy ingress (A1), governance FSM semantics (A4), append-only audit (A5), benchmark leakage auditing, and scripted synthetic validation.

## What this repository contains

| Path | Purpose |
|------|---------|
| `dualexis/` | Python reference implementation and CLI |
| `artifact/` | Install, reproduce, and artifact-evaluation documentation |
| `tests/` | Unit and artifact smoke tests |
| `configs/` | Pre-registered synthetic scenario YAML configs |
| `experiments/` | Ground-truth definitions for bundled scenarios |
| `results_reference/` | Pinned reference outputs (CSV, JSON, regenerated LaTeX fragments) |
| `examples/` | Minimal usage examples |
| `docs/` | Architecture and developer documentation |
| `scripts/` | Helper scripts (`reproduce.sh`) |

## What this repository does not contain

- Manuscript LaTeX, figures, or peer-review correspondence
- Editorial or internal readiness reports (see `artifact/reports/` for maintainer audit notes only)
- Field-deployment datasets or production system claims
- Legacy deprecated experiment batteries

## Quick start

```bash
python3.12 -m pip install -e ".[dev]"
python3.12 -m dualexis.cli --help
```

## Reproduce validation artefacts

From the repository root:

```bash
bash artifact/commands.sh
```

This cleans regeneratable outputs, installs the package, runs `validate-tsgg`, `leakage-audit --fast`, `formal-governance-audit`, `tsgg-trust-propagation --fast`, `export-harness-honesty`, and the JSS artifact test suite.

See [`artifact/INSTALL.md`](artifact/INSTALL.md) and [`artifact/REPRODUCE.md`](artifact/REPRODUCE.md) for alternatives (conda, Docker).

## Expected outputs

After `artifact/commands.sh`:

| Output | Command |
|--------|---------|
| `results_reference/tables/harness_honesty.tex` | `export-harness-honesty` |
| `results/tsgg/trust/trust_propagation_report.json` | `tsgg-trust-propagation --fast` |
| `results_reference/tables/privacy_fuzz_results.tex` | `validate-tsgg` |
| `results_reference/tables/leakage_audit.tex` | `leakage-audit --fast` |
| `results/governance/formal/governance_audit_report.json` | `formal-governance-audit` |
| `results/privacy_fuzz/results.csv` | `validate-tsgg` |

Regeneratable runtime outputs under `results/` are gitignored. Pinned snapshots for diff review live under `results_reference/`. Details: [`artifact/expected_outputs.md`](artifact/expected_outputs.md).

## Citation

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

Machine-readable metadata: [`CITATION.cff`](CITATION.cff) · Zenodo: https://doi.org/10.5281/zenodo.20499184

## License

Apache License 2.0 — see [`LICENSE`](LICENSE).
