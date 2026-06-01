"""Run multiseed robustness audit and export paper artefacts."""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

from dualexis.experiments.sssg_battery import PAPER_SCENARIOS
from dualexis.robustness.audit import run_robustness_audit
from dualexis.robustness.export import (
    export_robustness_audit,
    generate_robustness_vs_seed_pdf,
    write_robustness_analysis_section,
)
from dualexis.robustness.models import RobustnessAuditReport


@dataclass(frozen=True)
class RobustnessBatteryReport:
    output_dir: Path
    plot_pdf: Path
    section_tex: Path
    report: RobustnessAuditReport


def run_robustness_battery(
    *,
    output_dir: Path,
    paper_figures: Path,
    paper_sections: Path,
    seeds: tuple[int, ...],
    scenarios: tuple[str, ...] = PAPER_SCENARIOS,
) -> RobustnessBatteryReport:
    report = run_robustness_audit(seeds=seeds, scenarios=scenarios)
    export_robustness_audit(report, output_dir)

    plot_pdf = paper_figures / "robustness_vs_seed.pdf"
    paper_figures.mkdir(parents=True, exist_ok=True)
    generate_robustness_vs_seed_pdf(report, plot_pdf)
    shutil_copy_plot_to_results(report, output_dir, plot_pdf)

    section_tex = paper_sections / "robustness_analysis.tex"
    write_robustness_analysis_section(report, section_tex)

    return RobustnessBatteryReport(
        output_dir=output_dir,
        plot_pdf=plot_pdf,
        section_tex=section_tex,
        report=report,
    )


def shutil_copy_plot_to_results(
    report: RobustnessAuditReport,
    output_dir: Path,
    plot_pdf: Path,
) -> None:
    dest = output_dir / "robustness_vs_seed.pdf"
    if plot_pdf.is_file():
        shutil.copy(plot_pdf, dest)
    tex_src = plot_pdf.parent / "robustness_vs_seed.tex"
    if tex_src.is_file():
        shutil.copy(tex_src, output_dir / "robustness_vs_seed.tex")
    _ = report  # artefact paths already in JSON export


__all__ = ["RobustnessBatteryReport", "run_robustness_battery"]
