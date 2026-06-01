"""Tests for LaTeX paper structure verification (no LaTeX required)."""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from dualexis.cli import app
from dualexis.paper.check import (
    REQUIRED_PAPER_FILES,
    REQUIRED_PAPER_SECTIONS,
    run_paper_check,
    verify_paper_structure,
)

runner = CliRunner()


@pytest.mark.unit
def test_required_sections_list_is_complete() -> None:
    assert "sections/temporal_graph.tex" in REQUIRED_PAPER_SECTIONS
    assert "sections/limitations.tex" in REQUIRED_PAPER_SECTIONS
    assert "main.tex" in REQUIRED_PAPER_FILES
    assert "references.bib" in REQUIRED_PAPER_FILES


@pytest.mark.unit
def test_verify_paper_structure_passes_in_repository() -> None:
    missing = verify_paper_structure()
    assert missing == []


@pytest.mark.unit
def test_run_paper_check_passes_without_latex(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("dualexis.paper.check.shutil.which", lambda _name: None)
    result = run_paper_check(try_compile=True)
    assert result.ok is True
    assert result.structure_ok is True
    assert result.compile_attempted is False
    assert result.compile_ok is None
    assert any("LaTeX not installed" in message for message in result.messages)


@pytest.mark.unit
def test_verify_paper_structure_detects_missing_files(tmp_path: Path) -> None:
    paper_dir = tmp_path / "paper"
    paper_dir.mkdir()
    (paper_dir / "main.tex").write_text("\\documentclass{article}\n", encoding="utf-8")
    missing = verify_paper_structure(tmp_path)
    assert "references.bib" in missing
    assert any(name.startswith("sections/") for name in missing)


@pytest.mark.unit
def test_run_paper_check_fails_when_main_tex_missing(tmp_path: Path) -> None:
    (tmp_path / "paper").mkdir()
    result = run_paper_check(tmp_path, try_compile=False)
    assert result.ok is False
    assert "main.tex" in result.missing


@pytest.mark.unit
def test_run_paper_check_compile_failure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    paper_dir = tmp_path / "paper"
    paper_dir.mkdir()
    for relative in REQUIRED_PAPER_FILES:
        target = paper_dir / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("% stub\n", encoding="utf-8")

    monkeypatch.setattr("dualexis.paper.check.shutil.which", lambda name: "/usr/bin/pdflatex")
    monkeypatch.setattr(
        "dualexis.paper.check.subprocess.run",
        lambda *args, **kwargs: type("R", (), {"returncode": 1, "stdout": "error", "stderr": ""})(),
    )

    result = run_paper_check(tmp_path, try_compile=True)
    assert result.structure_ok is True
    assert result.compile_attempted is True
    assert result.compile_ok is False
    assert result.ok is False


@pytest.mark.unit
def test_cli_paper_check_command(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("dualexis.paper.check.shutil.which", lambda _name: None)
    result = runner.invoke(app, ["paper-check"])
    assert result.exit_code == 0
    assert "structure check passed" in result.stdout.lower()
