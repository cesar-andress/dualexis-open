"""Repository alignment checks — code, tests, docs, and paper sections."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import click
import pytest
from typer.main import get_command

from dualexis.cli import app
from dualexis.paper.check import REQUIRED_PAPER_SECTIONS

REPO_ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class ModuleAlignment:
    """Expected artifacts for a core functional module."""

    name: str
    package_dir: str
    doc_paths: tuple[str, ...]
    test_fragments: tuple[str, ...]
    paper_section: str


# Closed registry — update docs/alignment_policy.md when changing this table.
CORE_MODULE_ALIGNMENT: tuple[ModuleAlignment, ...] = (
    ModuleAlignment(
        name="privacy_runtime",
        package_dir="dualexis/privacy_runtime",
        doc_paths=("docs/privacy.md", "dualexis/privacy_runtime/README.md"),
        test_fragments=("privacy_runtime",),
        paper_section="sections/privacy_threats_governance.tex",
    ),
    ModuleAlignment(
        name="edge_perception",
        package_dir="dualexis/edge_perception",
        doc_paths=("dualexis/edge_perception/README.md", "docs/framework.md"),
        test_fragments=("edge_perception",),
        paper_section="sections/framework.tex",
    ),
    ModuleAlignment(
        name="semantic_events",
        package_dir="dualexis/semantic_events",
        doc_paths=("docs/event_taxonomy.md", "dualexis/semantic_events/README.md"),
        test_fragments=("semantic_events", "event_taxonomy"),
        paper_section="sections/event_model.tex",
    ),
    ModuleAlignment(
        name="temporal_graph",
        package_dir="dualexis/temporal_graph",
        doc_paths=("docs/temporal_graph.md", "dualexis/temporal_graph/README.md"),
        test_fragments=("temporal_graph",),
        paper_section="sections/temporal_graph.tex",
    ),
    ModuleAlignment(
        name="local_reasoning",
        package_dir="dualexis/local_reasoning",
        doc_paths=("docs/local_reasoning.md", "dualexis/local_reasoning/README.md"),
        test_fragments=("local_reasoning",),
        paper_section="sections/local_reasoning.tex",
    ),
    ModuleAlignment(
        name="orchestration",
        package_dir="dualexis/orchestration",
        doc_paths=("dualexis/orchestration/README.md", "docs/framework.md"),
        test_fragments=("orchestration",),
        paper_section="sections/framework.tex",
    ),
    ModuleAlignment(
        name="pipeline",
        package_dir="dualexis/pipeline",
        doc_paths=("docs/pipeline.md",),
        test_fragments=("pipeline",),
        paper_section="sections/pipeline.tex",
    ),
    ModuleAlignment(
        name="simulation",
        package_dir="dualexis/simulation",
        doc_paths=("docs/simulation.md", "dualexis/simulation/README.md"),
        test_fragments=("simulation",),
        paper_section="sections/methodology.tex",
    ),
    ModuleAlignment(
        name="evaluation",
        package_dir="dualexis/evaluation",
        doc_paths=("docs/evaluation.md", "dualexis/evaluation/README.md"),
        test_fragments=("evaluation",),
        paper_section="sections/metrics.tex",
    ),
)

README_CLI_PATTERN = re.compile(r"`dualexis\s+([\w-]+)")


def _test_file_stems() -> set[str]:
    return {path.stem for path in (REPO_ROOT / "tests").rglob("test_*.py")}


def _registered_cli_commands() -> set[str]:
    click_app = get_command(app)
    if isinstance(click_app, click.Group):
        return {name for name in click_app.commands if name is not None}
    return set()


def _readme_cli_references() -> set[str]:
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    return set(README_CLI_PATTERN.findall(readme))


@pytest.mark.parametrize("module", CORE_MODULE_ALIGNMENT, ids=lambda m: m.name)
def test_core_module_package_exists(module: ModuleAlignment) -> None:
    package_path = REPO_ROOT / module.package_dir
    assert package_path.is_dir(), f"{module.name}: missing package {module.package_dir}"


@pytest.mark.parametrize("module", CORE_MODULE_ALIGNMENT, ids=lambda m: m.name)
def test_core_module_has_documentation(module: ModuleAlignment) -> None:
    existing = [path for rel in module.doc_paths if (path := REPO_ROOT / rel).is_file()]
    assert existing, (
        f"{module.name}: no documentation found; expected one of: {', '.join(module.doc_paths)}"
    )


@pytest.mark.parametrize("module", CORE_MODULE_ALIGNMENT, ids=lambda m: m.name)
def test_core_module_has_tests(module: ModuleAlignment) -> None:
    stems = _test_file_stems()
    matches = [
        stem for stem in stems if any(fragment in stem for fragment in module.test_fragments)
    ]
    assert matches, (
        f"{module.name}: no test file under tests/ matching fragments "
        f"{module.test_fragments}; stems checked: {sorted(stems)}"
    )


@pytest.mark.parametrize("module", CORE_MODULE_ALIGNMENT, ids=lambda m: m.name)
def test_core_module_paper_section_exists(module: ModuleAlignment) -> None:
    paper_path = REPO_ROOT / "paper" / module.paper_section
    assert paper_path.is_file(), (
        f"{module.name}: missing paper section paper/{module.paper_section}"
    )


def test_required_paper_sections_exist() -> None:
    missing = [
        section
        for section in REQUIRED_PAPER_SECTIONS
        if not (REPO_ROOT / "paper" / section).is_file()
    ]
    assert not missing, f"Missing required paper sections: {missing}"


def test_readme_cli_commands_are_registered() -> None:
    referenced = _readme_cli_references()
    registered = _registered_cli_commands()
    unknown = sorted(referenced - registered)
    assert not unknown, (
        f"README references unknown CLI commands: {unknown}; registered: {sorted(registered)}"
    )


def test_alignment_policy_document_exists() -> None:
    assert (REPO_ROOT / "docs" / "alignment_policy.md").is_file()
