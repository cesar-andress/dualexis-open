"""DUALEXIS LaTeX paper utilities."""

from dualexis.paper.check import (
    REQUIRED_PAPER_FILES,
    REQUIRED_PAPER_SECTIONS,
    PaperCheckResult,
    paper_directory,
    repo_root,
    run_paper_check,
    verify_paper_structure,
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
