"""Battery runner for counterfactual safety reasoning exports."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from dualexis.counterfactual.evaluation import evaluate_counterfactual_battery
from dualexis.counterfactual.export import (
    export_counterfactual_battery,
    pick_example_summary,
    write_counterfactual_reasoning_section,
)
from dualexis.counterfactual.models import CounterfactualEvaluationReport
from dualexis.experiments.sssg_battery import PAPER_SCENARIOS


@dataclass(frozen=True)
class CounterfactualBatteryReport:
    output_dir: Path
    section_tex: Path
    report: CounterfactualEvaluationReport


def run_counterfactual_battery(
    *,
    output_dir: Path,
    paper_sections: Path,
    scenarios: tuple[str, ...] = PAPER_SCENARIOS,
    seeds: tuple[int, ...] = (1, 2, 3),
) -> CounterfactualBatteryReport:
    report = evaluate_counterfactual_battery(scenarios, seeds=seeds)
    export_counterfactual_battery(report, output_dir)
    section_tex = paper_sections / "counterfactual_reasoning.tex"
    write_counterfactual_reasoning_section(
        report,
        section_tex,
        example_summary=pick_example_summary(report),
    )
    return CounterfactualBatteryReport(
        output_dir=output_dir,
        section_tex=section_tex,
        report=report,
    )


__all__ = ["CounterfactualBatteryReport", "run_counterfactual_battery"]
