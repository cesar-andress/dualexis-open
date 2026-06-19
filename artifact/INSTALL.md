# Installation

Release: v1.0.4 | GitHub: https://github.com/cesar-andress/dualexis-open | Zenodo: https://doi.org/10.5281/zenodo.20638103

## Requirements

- Python **3.12+**
- Linux or macOS recommended (Windows supported for CLI/tests)
- Optional: Docker, conda

## Editable install (recommended)

From the repository root:

```bash
python3.12 -m pip install -e ".[dev]"
```

This installs the `dualexis` CLI and development tools (`pytest`, `ruff`, `mypy`).

## Minimal runtime install

```bash
python3.12 -m pip install -e .
```

See `requirements.txt` for core dependencies (also declared in `pyproject.toml`).

## Optional conda environment

```bash
conda env create -f artifact/environment.yml
conda activate tsgg-repro
pip install -e ".[dev]"
```

## Optional Docker

```bash
docker build -f artifact/Dockerfile -t tsgg-repro .
docker run --rm tsgg-repro
```

## Verify installation

```bash
python3.12 -m dualexis.cli --help
python3.12 -m pytest tests/artifact -q
```

Expected: CLI help prints; artifact smoke tests pass.

For the full reproduction package checklist, see **`ARTIFACT_EVALUATION.md`**.
