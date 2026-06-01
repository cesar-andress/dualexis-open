#!/usr/bin/env python3
"""Rebuild dualexis-open from the monorepo as a clean public JSS artefact."""

from __future__ import annotations

import re
import shutil
import subprocess
import textwrap
from datetime import UTC, datetime
from pathlib import Path

MONOREPO = Path("/home/cesar/dualexis")
TARGET = Path("/home/cesar/dualexis-open")
BUILD_SCRIPT = MONOREPO / "scripts/build_dualexis_open.py"
SELF = Path(__file__).resolve()

COPY_DIRS = ["dualexis", "tests", "examples", "docs"]
ALLOWED_TOP = {
    "dualexis",
    "tests",
    "examples",
    "configs",
    "scripts",
    "docs",
    "artifact",
    "experiments",
    "results_reference",
    ".git",
}

LEGACY_DUalexis_DIRS = [
    "dualexis/paper",
    "dualexis/counterfactual",
    "dualexis/institutional_memory",
    "dualexis/ontology_drift",
    "dualexis/robustness",
    "dualexis/adversarial_privacy",
    "dualexis/narratives",
]

LEGACY_TEST_FILES = [
    "tests/unit/test_paper_check.py",
    "tests/legacy_archive/test_dataset_adapters.py",
    "tests/unit/test_counterfactual.py",
    "tests/unit/test_institutional_memory.py",
    "tests/unit/test_ontology_drift.py",
    "tests/unit/test_robustness.py",
    "tests/unit/test_adversarial_privacy.py",
    "tests/unit/test_cssg.py",
    "tests/unit/test_sssg.py",
    "tests/unit/test_narratives.py",
    "tests/unit/test_edge_runtime.py",
]

PAPER_PATH_REPLACEMENTS = [
    ("paper/tables/baseline_results.tex", "results_reference/tables/baseline_results.tex"),
    ("paper/tables/privacy_fuzz_results.tex", "results_reference/tables/privacy_fuzz_results.tex"),
    ("paper/tables/e2_independent_gt.tex", "results_reference/tables/e2_independent_gt.tex"),
    ("paper/tables/results.tex", "results_reference/tables/results.tex"),
    ('"paper/tables"', '"results_reference/tables"'),
    ('"paper/sections"', '"results_reference/sections"'),
    ('"paper/figures"', '"dualexis/tsgg/assets"'),
    ('typer.Option("paper/tables"', 'typer.Option("results_reference/tables"'),
    ('typer.Option("paper/sections"', 'typer.Option("results_reference/sections"'),
    ('typer.Option("paper/figures"', 'typer.Option("dualexis/tsgg/assets"'),
    ('Path("paper/tables")', 'Path("results_reference/tables")'),
    ('Path("paper/sections")', 'Path("results_reference/sections")'),
    ('Path("paper/figures")', 'Path("dualexis/tsgg/assets")'),
    ("paper/sections/results.tex", "results_reference/sections/results.tex"),
    ("../paper/sections/", "results_reference/sections/"),
    ("`paper/sections/", "`results_reference/sections/"),
    ("`paper/tables/", "`results_reference/tables/"),
    ("paper/sections/", "results_reference/sections/"),
    ("paper/tables/", "results_reference/tables/"),
    ("narrative_eswa.md", "narrative_validation.md"),
    ("generate_eswa_narrative", "generate_validation_narrative"),
    ("run_empirical_eswa_package", "run_validate_tsgg_package"),
    ("reviewer_statement", "independence_disclosure"),
    ("REVIEWER_STATEMENT", "INDEPENDENCE_DISCLOSURE"),
    ("from apps.services import", "from dualexis.runtime.in_memory import"),
    ("ESWA empirical defensibility", "validation harness defensibility"),
    ("ESWA-style markdown narrative", "Validation markdown narrative"),
    ("Multiseed statistical analysis narrative (ESWA)", "Multiseed statistical analysis narrative"),
    ("Interpretation for reviewers:", "Interpretation for validation readers:"),
]

FORBIDDEN_GREP = re.compile(
    r"ESWA|Expert Systems with Applications|reviewer|camera-ready|\bdraft\b|\bTODO\b|\bFIXME\b|paper/",
    re.IGNORECASE,
)

GREP_SKIP = {".git", "__pycache__", ".pytest_cache", ".ruff_cache", ".mypy_cache"}
GREP_SKIP_FILES = {"EXPORT_REPORT.md", "OPEN_SOURCE_READINESS_REPORT.md"}
LATEX_ARTIFACTS = ("*.aux", "*.bbl", "*.blg", "*.log", "*.out", "*.synctex.gz", "*.fdb_latexmk", "*.fls")


def log(msg: str) -> None:
    print(f"[sync-open] {msg}")


def rm_tree(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)


def patch_file(path: Path, replacements: list[tuple[str, str]]) -> None:
    if not path.is_file():
        return
    text = path.read_text(encoding="utf-8")
    for old, new in replacements:
        text = text.replace(old, new)
    path.write_text(text, encoding="utf-8")


def base_sync() -> None:
    log("Running monorepo export (read-only on monorepo)")
    subprocess.run(["python3.12", str(BUILD_SCRIPT)], check=True)


def remove_disallowed_top_level(removed: list[str]) -> None:
    for name in (
        "legacy_archive",
        "apps",
        "results",
        "paper",
        "paper_requirements",
        "dist",
        "tmp",
        "scratch",
        "review",
        "submission",
    ):
        path = TARGET / name
        if path.exists():
            rm_tree(path)
            removed.append(f"{name}/")

    for name in ("uv.lock", "cleanup_report.md", "OPEN_SOURCE_READINESS_REPORT.md", "EXPORT_REPORT.md"):
        path = TARGET / name
        if path.is_file():
            path.unlink()
            removed.append(name)

    for pattern in LATEX_ARTIFACTS:
        for path in TARGET.rglob(pattern):
            if ".git" in path.parts:
                continue
            rel = str(path.relative_to(TARGET))
            path.unlink(missing_ok=True)
            removed.append(rel)

    for child in list(TARGET.iterdir()):
        if child.name.startswith("."):
            continue
        if child.is_dir() and child.name not in ALLOWED_TOP:
            rm_tree(child)
            removed.append(f"{child.name}/")
        elif child.is_file() and child.name not in {
            "README.md",
            "LICENSE",
            "CITATION.cff",
            ".zenodo.json",
            "CHANGELOG.md",
            "CONTRIBUTING.md",
            "CODE_OF_CONDUCT.md",
            "pyproject.toml",
            "requirements.txt",
            "environment.yml",
            "Dockerfile",
            "Makefile",
            ".gitignore",
        }:
            child.unlink()
            removed.append(child.name)


def delete_legacy_modules(removed: list[str]) -> None:
    for rel in LEGACY_DUalexis_DIRS:
        path = TARGET / rel
        if path.exists():
            rm_tree(path)
            removed.append(f"{rel}/")
    legacy_tests = TARGET / "tests/legacy_archive"
    if legacy_tests.exists():
        rm_tree(legacy_tests)
        removed.append("tests/legacy_archive/")
    for rel in LEGACY_TEST_FILES:
        path = TARGET / rel
        if path.is_file():
            path.unlink()
            removed.append(rel)


def trim_manuscript_tex(removed: list[str]) -> None:
    sections = TARGET / "results_reference/sections"
    if sections.is_dir():
        for tex in sections.glob("*.tex"):
            tex.unlink()
            removed.append(str(tex.relative_to(TARGET)))
    figures = TARGET / "results_reference/figures"
    if figures.is_dir():
        rm_tree(figures)
        removed.append("results_reference/figures/")


def create_runtime_shim() -> None:
    runtime = TARGET / "dualexis/runtime"
    runtime.mkdir(parents=True, exist_ok=True)
    (runtime / "__init__.py").write_text(
        '"""In-memory runtime helpers for tests and pipeline defaults."""\n',
        encoding="utf-8",
    )
    src = MONOREPO / "apps/services.py"
    shutil.copy2(src, runtime / "in_memory.py")
    patch_file(runtime / "in_memory.py", PAPER_PATH_REPLACEMENTS)


def install_diagram_sources() -> None:
    assets = TARGET / "dualexis/tsgg/assets"
    assets.mkdir(parents=True, exist_ok=True)
    for src in (
        MONOREPO / "paper/legacy_archive/figures/figures/tsgg_framework.tex",
        MONOREPO / "paper/figures/tsgg_framework.tex",
    ):
        if src.is_file():
            shutil.copy2(src, assets / "tsgg_framework.tex")
            break
    export_py = TARGET / "dualexis/tsgg/export.py"
    patch_file(
        export_py,
        [
            (
                'repo_root / "paper" / "figures" / "tsgg_framework.tex"',
                'Path(__file__).resolve().parent / "assets" / "tsgg_framework.tex"',
            ),
        ],
    )
    trust = TARGET / "dualexis/tsgg/trust_propagation.py"
    patch_file(
        trust,
        [
            (
                'repo_root / "paper" / "figures" / "trust_flow_graph.tex"',
                'Path(__file__).resolve().parent / "assets" / "trust_flow_graph.tex"',
            ),
        ],
    )
    cssg_assets = TARGET / "dualexis/cssg/assets"
    cssg_assets.mkdir(parents=True, exist_ok=True)
    cssg_src = MONOREPO / "paper/figures/causal_state_graph.tex"
    if cssg_src.is_file():
        shutil.copy2(cssg_src, cssg_assets / "causal_state_graph.tex")
    cssg_export = TARGET / "dualexis/cssg/export.py"
    if cssg_export.is_file():
        patch_file(
            cssg_export,
            [
                (
                    'repo_root / "paper" / "figures" / "causal_state_graph.tex"',
                    'Path(__file__).resolve().parent / "assets" / "causal_state_graph.tex"',
                ),
            ],
        )


def write_configs() -> None:
    src = MONOREPO / "experiments/configs"
    dst = TARGET / "configs"
    if src.is_dir():
        if dst.exists():
            rm_tree(dst)
        shutil.copytree(src, dst)


def sanitize_tree() -> None:
    skip_suffix = {".png", ".pdf", ".svg", ".jpg", ".pyc", ".csv", ".json", ".lock"}
    for path in TARGET.rglob("*"):
        if not path.is_file() or ".git" in path.parts:
            continue
        if path.suffix in skip_suffix and path.suffix != ".json":
            if path.suffix != ".md":
                continue
        if path.name in GREP_SKIP_FILES:
            continue
        if path.suffix in {".py", ".md", ".toml", ".yml", ".yaml", ".sh", ".txt", ".cff", ".tex", ""} or path.suffix == ".json":
            patch_file(path, PAPER_PATH_REPLACEMENTS)


def patch_cli() -> None:
    cli = TARGET / "dualexis/cli.py"
    text = cli.read_text(encoding="utf-8")
    text = text.replace("from dualexis.paper.check import run_paper_check\n", "")
    text = text.replace(
        "DUALEXIS — privacy-first safety orchestration research framework.",
        "TSGG reference implementation — auditable human-AI trace architecture.",
    )
    text = text.replace(
        '"""DUALEXIS command-line interface."""',
        '"""TSGG reference implementation CLI."""',
    )
    start = text.find('@app.command("paper-check")')
    end = text.find("\ndef _emit_measurement_report", start)
    if start != -1 and end != -1:
        text = text[:start] + text[end + 1 :]
    start = text.find('@experiment_app.command("empirical-eswa"')
    end = text.find("\n@experiment_app.command(", start + 1)
    if start != -1 and end != -1:
        text = text[:start] + text[end + 1 :]
    cli.write_text(text, encoding="utf-8")


def patch_open_tests() -> None:
    baseline = TARGET / "tests/unit/test_baseline_comparison.py"
    if baseline.is_file():
        text = baseline.read_text(encoding="utf-8")
        text = text.replace("assert len(baselines) == 4", "assert len(baselines) == 5")
        baseline.write_text(text, encoding="utf-8")
    for rel in (
        "tests/unit/layers/test_layer_packages.py",
        "tests/integration/test_event_flow.py",
    ):
        patch_file(TARGET / rel, PAPER_PATH_REPLACEMENTS)


def patch_pyproject() -> None:
    path = TARGET / "pyproject.toml"
    text = path.read_text(encoding="utf-8")
    text = re.sub(
        r"\[project\.scripts\]\n(?:.*\n)*?(?=\[dependency-groups\])",
        "[project.scripts]\ndualexis = \"dualexis.cli:main\"\n\n",
        text,
    )
    text = text.replace('packages = ["dualexis", "apps"]', 'packages = ["dualexis"]')
    text = text.replace('src = ["dualexis", "apps", "tests"]', 'src = ["dualexis", "tests"]')
    text = text.replace('files = ["dualexis", "apps", "tests"]', 'files = ["dualexis", "tests"]')
    path.write_text(text, encoding="utf-8")


def write_clean_gitignore() -> None:
    (TARGET / ".gitignore").write_text(
        textwrap.dedent(
            """\
            .venv/
            __pycache__/
            *.py[cod]
            .pytest_cache/
            .mypy_cache/
            .ruff_cache/
            .coverage
            htmlcov/
            dist/
            build/
            *.egg-info/
            results/
            tmp/
            scratch/
            """
        ),
        encoding="utf-8",
    )


def write_root_docs() -> None:
    (TARGET / "README.md").write_text(
        textwrap.dedent(
            """\
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
            """
        ),
        encoding="utf-8",
    )
    for name in ("LICENSE", "CITATION.cff", ".zenodo.json"):
        src = MONOREPO / name
        if src.is_file():
            shutil.copy2(src, TARGET / name)
    (TARGET / "CHANGELOG.md").write_text(
        textwrap.dedent(
            """\
            # Changelog

            ## v1.0.0 — 2026-06-01

            Initial public release of the TSGG reference implementation.

            - Validation harness: `validate-tsgg`, `leakage-audit`, `formal-governance-audit`
            - Reproducibility bundle under `artifact/`
            - Pinned reference outputs under `results_reference/`
            """
        ),
        encoding="utf-8",
    )
    (TARGET / "CONTRIBUTING.md").write_text(
        textwrap.dedent(
            """\
            # Contributing

            ## Development setup

            ```bash
            pip install -e ".[dev]"
            python3.12 -m pytest tests/unit -q
            ```

            ## Scope

            This repository targets software trace architecture, validation harnesses, and reproducibility.
            Manuscript sources are maintained separately from this public artefact.
            """
        ),
        encoding="utf-8",
    )
    for name, content in (
        ("requirements.txt", MONOREPO / "artifact/requirements.txt"),
        ("environment.yml", MONOREPO / "artifact/environment.yml"),
        ("Dockerfile", MONOREPO / "artifact/Dockerfile"),
    ):
        if content.is_file():
            shutil.copy2(content, TARGET / name)


def write_artifact_bundle() -> None:
    art = TARGET / "artifact"
    art.mkdir(parents=True, exist_ok=True)
    for name in ("INSTALL.md", "commands.sh"):
        src = MONOREPO / "artifact" / name
        if src.is_file():
            shutil.copy2(src, art / name)
    (art / "README.md").write_text(
        textwrap.dedent(
            """\
            # TSGG validation artefact

            Open-source reference implementation for reproducible JSS validation.

            | Document | Purpose |
            |----------|---------|
            | [`INSTALL.md`](INSTALL.md) | Environment setup |
            | [`REPRODUCE.md`](REPRODUCE.md) | Step-by-step validation commands |
            | [`EXPECTED_OUTPUTS.md`](EXPECTED_OUTPUTS.md) | Output paths and sanity checks |
            | [`commands.sh`](commands.sh) | One-shot reproduction script |
            """
        ),
        encoding="utf-8",
    )
    (art / "REPRODUCE.md").write_text(
        textwrap.dedent(
            """\
            # Reproduce validation results

            ## One-shot

            ```bash
            bash artifact/commands.sh
            ```

            ## Step-by-step

            ```bash
            pip install -e ".[dev]"
            python3.12 -m dualexis.cli experiment validate-tsgg
            python3.12 -m dualexis.cli experiment leakage-audit --fast
            python3.12 -m dualexis.cli experiment formal-governance-audit
            python3.12 -m pytest tests/unit -q
            ```

            Outputs land under `results/` (runtime) and refresh `results_reference/tables/*.tex` where applicable.
            """
        ),
        encoding="utf-8",
    )
    (art / "EXPECTED_OUTPUTS.md").write_text(
        textwrap.dedent(
            """\
            # Expected outputs

            | Path | Command |
            |------|---------|
            | `results/baseline_comparison/results.csv` | `validate-tsgg` |
            | `results/privacy_fuzz/privacy_fuzz_results.csv` | `validate-tsgg` |
            | `results_reference/tables/harness_honesty.tex` | `validate-tsgg` |
            | `results_reference/tables/privacy_fuzz_results.tex` | `validate-tsgg` |
            | `results_reference/tables/leakage_audit.tex` | `leakage-audit --fast` |
            | `results/leakage_audit/` | `leakage-audit --fast` |
            | `results/governance/formal/` | `formal-governance-audit` |

            ```bash
            grep -q 'tab:harness-honesty' results_reference/tables/harness_honesty.tex
            python3.12 -m pytest tests/unit -q
            ```
            """
        ),
        encoding="utf-8",
    )
    scripts = art / "scripts"
    scripts.mkdir(exist_ok=True)
    repro = MONOREPO / "artifact/scripts/reproduce_validation.sh"
    if repro.is_file():
        shutil.copy2(repro, scripts / "reproduce_validation.sh")


def write_makefile_and_scripts() -> None:
    (TARGET / "Makefile").write_text(
        textwrap.dedent(
            """\
            .PHONY: install reproduce test check lint docker

            install:
            \tpip install -e ".[dev]"

            reproduce:
            \tbash artifact/commands.sh

            test:
            \tpython3.12 -m pytest tests/unit -q

            check:
            \truff format --check .
            \truff check .
            \t$(MAKE) test

            lint:
            \truff check .
            \truff format .

            docker:
            \tdocker build -t tsgg-reference:v1.0.0 .
            """
        ),
        encoding="utf-8",
    )
    scripts = TARGET / "scripts"
    scripts.mkdir(exist_ok=True)
    shutil.copy2(SELF, scripts / "sync_public_jss_artifact.py")
    (scripts / "reproduce.sh").write_text(
        "#!/usr/bin/env bash\nset -euo pipefail\ncd \"$(dirname \"$0\")/..\"\nbash artifact/commands.sh\n",
        encoding="utf-8",
    )
    (scripts / "reproduce.sh").chmod(0o755)


def remove_eswa_docs(removed: list[str]) -> None:
    for path in list((TARGET / "docs").rglob("*")):
        if path.is_file() and "eswa" in path.name.lower():
            path.unlink()
            removed.append(str(path.relative_to(TARGET)))


def patch_leakage_json() -> None:
    report = TARGET / "results_reference/leakage_audit/leakage_audit_report.json"
    if report.is_file():
        data = report.read_text(encoding="utf-8")
        patch_file(report, PAPER_PATH_REPLACEMENTS)


def list_tex_files() -> list[Path]:
    return sorted(p for p in TARGET.rglob("*.tex") if ".git" not in p.parts)


def grep_forbidden() -> list[tuple[str, int, str]]:
    hits: list[tuple[str, int, str]] = []
    for path in TARGET.rglob("*"):
        if not path.is_file() or any(part in GREP_SKIP for part in path.parts):
            continue
        if path.name in GREP_SKIP_FILES:
            continue
        if path.suffix in {".png", ".pdf", ".svg", ".jpg", ".pyc", ".woff", ".woff2"}:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for i, line in enumerate(text.splitlines(), 1):
            if FORBIDDEN_GREP.search(line):
                hits.append((str(path.relative_to(TARGET)), i, line.strip()[:120]))
    return hits


def run_validation() -> dict[str, object]:
    results: dict[str, object] = {}
    r = subprocess.run(
        ["python3.12", "-m", "pip", "install", "-e", ".[dev]", "-q"],
        cwd=TARGET,
        text=True,
        capture_output=True,
    )
    results["pip_install"] = r.returncode == 0
    r = subprocess.run(
        ["python3.12", "-m", "pytest", "tests/unit", "-q"],
        cwd=TARGET,
        text=True,
        capture_output=True,
    )
    results["pytest_rc"] = r.returncode
    results["pytest_out"] = (r.stdout or "") + (r.stderr or "")
    r = subprocess.run(
        ["bash", "artifact/commands.sh"],
        cwd=TARGET,
        text=True,
        capture_output=True,
        timeout=600,
    )
    results["reproduce_rc"] = r.returncode
    results["reproduce_out"] = (r.stdout or "") + (r.stderr or "")
    results["grep_hits"] = grep_forbidden()
    results["tex_files"] = [str(p.relative_to(TARGET)) for p in list_tex_files()]
    return results


def write_reports(removed: list[str], validation: dict[str, object]) -> bool:
    tex_files = validation.get("tex_files", [])
    grep_hits = validation.get("grep_hits", [])
    pytest_rc = validation.get("pytest_rc", 99)
    reproduce_rc = validation.get("reproduce_rc", 99)

    allowed_tex: dict[str, str] = {
        "dualexis/tsgg/assets/tsgg_framework.tex": "Standalone TikZ source for TSGG pipeline figure export",
        "dualexis/cssg/assets/causal_state_graph.tex": "Standalone TikZ source for causal graph export",
    }
    for rel in tex_files:
        if rel.startswith("results_reference/"):
            allowed_tex[rel] = "Validation harness LaTeX table export (CSV is canonical)"

    checks = [
        ("no legacy_archive/", not (TARGET / "legacy_archive").exists()),
        ("no paper/", not (TARGET / "paper").exists()),
        ("no apps/", not (TARGET / "apps").exists()),
        ("pytest tests/unit", pytest_rc == 0),
        ("artifact/commands.sh", reproduce_rc == 0),
        ("forbidden string grep clean", len(grep_hits) == 0),
    ]
    overall = all(ok for _, ok in checks)

    export_lines = [
        "# Export report — dualexis-open",
        "",
        f"Generated: {datetime.now(UTC).isoformat()}",
        f"Source monorepo: `{MONOREPO}`",
        "",
        "## Removed",
        "",
    ]
    export_lines.extend(f"- `{item}`" for item in removed[:250])
    if len(removed) > 250:
        export_lines.append(f"- … and {len(removed) - 250} more")
    export_lines.extend(["", "## Remaining TeX files", ""])
    for rel in tex_files:
        export_lines.append(f"- `{rel}` — {allowed_tex.get(rel, 'review')}")
    export_lines.extend(["", "## Grep scan", ""])
    if grep_hits:
        for path, line, text in grep_hits[:80]:
            export_lines.append(f"- `{path}:{line}`: {text}")
    else:
        export_lines.append("- (no matches)")
    export_lines.extend(
        [
            "",
            "## Test result",
            "",
            f"pytest exit code: {pytest_rc}",
            "",
            "## Reproducibility",
            "",
            f"artifact/commands.sh exit code: {reproduce_rc}",
            "",
            f"## Overall: **{'PASS' if overall else 'FAIL'}**",
            "",
        ]
    )
    (TARGET / "EXPORT_REPORT.md").write_text("\n".join(export_lines) + "\n", encoding="utf-8")

    readiness = [
        "# Open-source readiness report",
        "",
        "Repository: **TSGG Reference Implementation** (public JSS artefact)",
        "",
        "## Verification",
        "",
    ]
    for name, ok in checks:
        readiness.append(f"- **{'PASS' if ok else 'FAIL'}** — {name}")
    readiness.extend(
        [
            "",
            f"## Overall: **{'PASS' if overall else 'FAIL'}**",
            "",
        ]
    )
    (TARGET / "OPEN_SOURCE_READINESS_REPORT.md").write_text("\n".join(readiness) + "\n", encoding="utf-8")
    return overall


def main() -> None:
    removed: list[str] = []
    base_sync()
    remove_disallowed_top_level(removed)
    delete_legacy_modules(removed)
    trim_manuscript_tex(removed)
    remove_eswa_docs(removed)
    create_runtime_shim()
    install_diagram_sources()
    write_configs()
    sanitize_tree()
    patch_cli()
    patch_open_tests()
    patch_pyproject()
    patch_leakage_json()
    write_clean_gitignore()
    write_root_docs()
    write_artifact_bundle()
    write_makefile_and_scripts()
    validation = run_validation()
    overall = write_reports(removed, validation)
    log(f"Done — overall {'PASS' if overall else 'FAIL'}")
    raise SystemExit(0 if overall else 1)


if __name__ == "__main__":
    main()
