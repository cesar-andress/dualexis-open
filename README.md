# TSGG Reference Implementation

**Trusted Safety State Governance Graph (TSGG)** — open-source trace architecture for auditable human–AI systems.

This repository is the **reference implementation** supporting the *Journal of Systems and Software* manuscript. It is **not** the manuscript.

## Trace chain

```
Evidence → Safety State → Causal Transition → Recommendation → Governance Decision → Audit Trace
```

## Quick start

```bash
pip install -e ".[dev]"
bash artifact/commands.sh
```

See [`artifact/INSTALL.md`](artifact/INSTALL.md) and [`artifact/REPRODUCE.md`](artifact/REPRODUCE.md).

## Repository

- **URL:** https://github.com/cesar-andress/dualexis-open
- **Version:** v1.0.0
- **License:** Apache-2.0
- **Citation:** [`CITATION.cff`](CITATION.cff)

## Layout

| Path | Purpose |
|------|---------|
| `dualexis/` | Python reference implementation |
| `artifact/` | Reproducibility documentation and commands |
| `tests/` | Unit and integration tests |
| `examples/` | Minimal usage examples |
| `docs/` | Architecture and developer documentation |
| `configs/` | Synthetic scenario configuration |
| `experiments/` | Independent ground truth fixtures |
| `results_reference/` | Pinned validation table exports |
