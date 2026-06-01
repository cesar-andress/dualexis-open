"""Reproducible experimental battery for DUALEXIS."""

from __future__ import annotations

from dualexis.experiments.battery import (
    BATTERY_DISCLAIMER,
    BatteryResult,
    run_battery,
)
from dualexis.experiments.config import ExperimentConfig, load_experiment_config
from dualexis.experiments.multiseed import (
    MULTISEED_DISCLAIMER,
    MultiseedBatteryReport,
    compute_descriptive_stats,
    compute_multiseed_aggregates,
    generate_multiseed_latex_table,
    generate_multiseed_markdown,
    parse_seed_list,
    run_multiseed_batteries,
)
from dualexis.experiments.runner import (
    generate_latex_table,
    generate_markdown_report,
    load_battery_results,
    run_all_batteries,
    run_battery_from_config,
    write_battery_json,
)

__all__ = [
    "BATTERY_DISCLAIMER",
    "MULTISEED_DISCLAIMER",
    "BatteryResult",
    "ExperimentConfig",
    "MultiseedBatteryReport",
    "compute_descriptive_stats",
    "compute_multiseed_aggregates",
    "generate_latex_table",
    "generate_markdown_report",
    "generate_multiseed_latex_table",
    "generate_multiseed_markdown",
    "load_battery_results",
    "load_experiment_config",
    "parse_seed_list",
    "run_all_batteries",
    "run_battery",
    "run_battery_from_config",
    "run_multiseed_batteries",
    "write_battery_json",
]
