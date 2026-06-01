"""LaTeX paper structure verification and optional compilation."""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path


REQUIRED_PAPER_SECTIONS: tuple[str, ...] = (
    "sections/abstract.tex",
    "sections/introduction.tex",
    "sections/box_boundaries.tex",
    "sections/contributions.tex",
    "sections/background_related_work.tex",
    "sections/related_work.tex",
    "sections/research_gap.tex",
    "sections/problem_formulation.tex",
    "sections/human_factors_emergency_coordination.tex",
    "sections/human_factors_metrics.tex",
    "sections/orchestration_framework.tex",
    "sections/orchestration_model.tex",
    "sections/privacy_threats_governance.tex",
    "sections/pilot_readiness.tex",
    "sections/pre_pilot_evaluation.tex",
    "sections/laboratory_validation_plan.tex",
    "sections/appendix_lab_study_protocol.tex",
    "sections/validity_and_limitations.tex",
    "sections/future_work.tex",
    "sections/conclusion.tex",
    "sections/appendix_related_supplementary.tex",
    "sections/appendix_online_material.tex",
    "sections/appendix_supplementary_material.tex",
    "sections/appendix_event_schema.tex",
    "sections/appendix_evaluation_protocol_body.tex",
    "sections/appendix_baselines_body.tex",
    "sections/appendix_deployment_internals.tex",
    "sections/appendix_reproducibility_detail.tex",
    "sections/event_taxonomy.tex",
    "sections/metrics_appendix.tex",
    "sections/appendix_innovation.tex",
)

REQUIRED_PAPER_FILES: tuple[str, ...] = (
    "main.tex",
    "references.bib",
    "references_eswa.bib",
    "tables/eswa_related_work_matrix.tex",
    "tables/results.tex",
    *REQUIRED_PAPER_SECTIONS,
)


@dataclass(frozen=True)
class PaperCheckResult:
    """Outcome of a paper structure / compile check."""

    ok: bool
    missing: tuple[str, ...] = ()
    structure_ok: bool = False
    compile_attempted: bool = False
    compile_ok: bool | None = None
    messages: tuple[str, ...] = field(default_factory=tuple)


def repo_root(start: Path | None = None) -> Path:
    """Return repository root (parent of ``dualexis/`` package)."""
    if start is not None:
        return start
    return Path(__file__).resolve().parent.parent.parent


def paper_directory(root: Path | None = None) -> Path:
    return repo_root(root) / "paper"


def verify_paper_structure(root: Path | None = None) -> list[str]:
    """Return relative paths of missing required paper files."""
    paper_dir = paper_directory(root)
    missing: list[str] = []
    for relative in REQUIRED_PAPER_FILES:
        if not (paper_dir / relative).is_file():
            missing.append(relative)
    return missing


def _run_compile(paper_dir: Path) -> tuple[bool, str]:
    latexmk = shutil.which("latexmk")
    if latexmk is not None:
        command = [latexmk, "-pdf", "-interaction=nonstopmode", "main.tex"]
        label = "latexmk"
    else:
        pdflatex = shutil.which("pdflatex")
        if pdflatex is None:
            return False, "No LaTeX engine found (latexmk or pdflatex)."
        command = [pdflatex, "-interaction=nonstopmode", "main.tex"]
        label = "pdflatex"

    result = subprocess.run(
        command,
        cwd=paper_dir,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip().splitlines()
        tail = "\n".join(detail[-8:]) if detail else f"{label} exited {result.returncode}"
        return False, tail
    return True, f"{label} completed successfully."


def run_paper_check(
    root: Path | None = None,
    *,
    try_compile: bool = True,
) -> PaperCheckResult:
    """Verify paper files and optionally compile when LaTeX is available."""
    messages: list[str] = []
    missing = verify_paper_structure(root)
    if missing:
        messages.append(f"Missing {len(missing)} required paper file(s).")
        return PaperCheckResult(
            ok=False,
            missing=tuple(missing),
            structure_ok=False,
            messages=tuple(messages),
        )

    messages.append("Paper structure check passed.")
    structure_ok = True

    if not try_compile:
        return PaperCheckResult(
            ok=True,
            structure_ok=structure_ok,
            messages=tuple(messages),
        )

    latexmk = shutil.which("latexmk")
    pdflatex = shutil.which("pdflatex")
    if latexmk is None and pdflatex is None:
        messages.append(
            "LaTeX not installed; skipping compile step (structure check only). "
            "Install TeX Live, MacTeX, or latexmk to build paper/main.pdf."
        )
        return PaperCheckResult(
            ok=True,
            structure_ok=structure_ok,
            compile_attempted=False,
            compile_ok=None,
            messages=tuple(messages),
        )

    compile_ok, compile_message = _run_compile(paper_directory(root))
    messages.append(compile_message)
    return PaperCheckResult(
        ok=compile_ok,
        structure_ok=structure_ok,
        compile_attempted=True,
        compile_ok=compile_ok,
        messages=tuple(messages),
    )


__all__ = [
    "REQUIRED_PAPER_FILES",
    "REQUIRED_PAPER_SECTIONS",
    "PaperCheckResult",
    "paper_directory",
    "repo_root",
    "run_paper_check",
    "verify_paper_structure",
]
