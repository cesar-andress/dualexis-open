# Contributing

Thank you for contributing to the TSGG reference implementation.

## Development setup

```bash
pip install -e ".[dev]"
python3.12 -m pytest tests/unit -q
```

## Pull requests

1. Fork https://github.com/cesar-andress/dualexis-open
2. Create a feature branch from `main`
3. Run `make check` before opening a PR
4. Describe validation impact (commands in `artifact/REPRODUCE.md`)

## Scope

This repository targets software trace architecture, validation harnesses, and reproducibility.
Paper/LaTeX changes belong in the separate manuscript repository.
