# Installation

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
conda activate tsgg-jss
pip install -e ".[dev]"
```

## Optional Docker

```bash
docker build -f artifact/Dockerfile -t tsgg-jss .
docker run --rm tsgg-jss
```

## Verify installation

```bash
python3.12 -m dualexis.cli --help
python3.12 -m pytest tests/artifact -q
```

Expected: CLI help prints; artifact smoke tests pass.

For the full JSS artifact evaluation checklist, see **`ARTIFACT_EVALUATION.md`**.
