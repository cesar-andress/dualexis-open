# Development Guide

## Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) package manager

## Setup

```bash
git clone https://github.com/your-org/dualexis.git
cd dualexis
uv sync --all-extras
uv run pre-commit install
```

## Project Layout

```
dualexis/           # Core library
apps/               # Runnable applications
tests/              # Unit and integration tests
docs/               # Documentation
examples/           # Usage examples
paper/              # LaTeX research paper
```

## Common Commands

```bash
# Run all tests
uv run pytest

# Run unit tests only
uv run pytest tests/unit -m unit

# Lint and format
uv run ruff format --check dualexis apps tests
uv run ruff check dualexis apps tests

# Type checking
uv run mypy dualexis apps
```

Continuous integration (`.github/workflows/ci.yml`) runs the same checks on every push and pull request.

```bash
# Start API server
uv run dualexis-api

# Run edge node demo
uv run dualexis-edge

# Run simulator
uv run dualexis-simulator

# Basic example
uv run python examples/basic_event_flow/run.py
```

## Environment Variables

All settings use the `DUALEXIS_` prefix:

| Variable | Default | Description |
| -------- | ------- | ----------- |
| `DUALEXIS_ENVIRONMENT` | `development` | Runtime environment |
| `DUALEXIS_DEBUG` | `false` | Debug mode |
| `DUALEXIS_EDGE_BUFFER_TTL_SECONDS` | `30` | Ephemeral buffer TTL |
| `DUALEXIS_ALLOW_PERSISTENT_MEDIA` | `false` | Allow media persistence |
| `DUALEXIS_API_HOST` | `0.0.0.0` | API bind host |
| `DUALEXIS_API_PORT` | `8000` | API bind port |

Copy `.env.example` to `.env` for local overrides (never commit `.env`).

## Adding a Perception Pipeline

1. Subclass `BasePerceptionPipeline` in `dualexis/perception/<modality>/`
2. Implement `_extract_signals()` returning zone-level `PerceptionSignal` objects
3. Never include biometric features or identity labels
4. Add unit tests in `tests/unit/test_perception.py`

## Adding a Reasoning Backend

1. Implement the `ReasoningEngine` interface
2. Accept `ReasoningRequest` with structured events only
3. Return `ReasoningResponse` with explainable summaries
4. Wire into `SafetyOrchestrator` via dependency injection

## Testing Standards

- All new code must pass `mypy --strict`
- Unit tests for individual modules; integration tests for pipelines
- Use `@pytest.mark.unit` and `@pytest.mark.integration` markers
- Target 80%+ coverage (configured in `pyproject.toml`)

## Code Style

- English for all code, comments, and docstrings
- Line length: 100 characters
- Ruff for linting and formatting
- Pre-commit hooks enforce checks on commit

See [CONTRIBUTING.md](../CONTRIBUTING.md) for the full contribution workflow.
