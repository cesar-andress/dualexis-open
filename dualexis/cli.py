"""TSGG reference implementation CLI."""

from __future__ import annotations

import json
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path

import typer

from dualexis.core.version import get_version
from dualexis.edge_runtime import (
    edge_health,
    edge_status,
    emit_synthetic_events,
    run_node,
)
from dualexis.evaluation import (
    UnknownBaselineError,
    UnknownProtocolError,
    format_experiment_summary,
    format_report_summary,
    run_evaluation,
    run_experiment,
)
from dualexis.evaluation.comparison import run_baseline_comparison
from dualexis.experiments.config import load_experiment_config
from dualexis.experiments.multiseed import parse_seed_list, run_multiseed_batteries
from dualexis.experiments.runner import (
    generate_latex_table,
    generate_markdown_report,
    load_battery_results,
    run_all_batteries,
    run_battery_from_config,
    write_battery_json,
)
from dualexis.measurement import (
    format_measurement_summary,
    measure_all,
    measure_latency_report,
    measure_privacy_report,
    measure_robustness_report,
    measure_scenario,
    resolve_output_path,
    write_combined_json,
)
from dualexis.pipeline import run_pipeline
from dualexis.simulation import run_scenario
from dualexis.simulation.runner import SimulationResult
from dualexis.simulation.scenario import ScenarioId, UnknownScenarioError

app = typer.Typer(
    name="dualexis",
    help="TSGG reference implementation — auditable human-AI trace architecture.",
    no_args_is_help=True,
)

measure_app = typer.Typer(
    name="measure",
    help="Collect reproducible pipeline measurements (latency, privacy, robustness).",
    no_args_is_help=True,
)
app.add_typer(measure_app, name="measure")

experiment_app = typer.Typer(
    name="experiment",
    help="Run reproducible experimental batteries and generate reports.",
    no_args_is_help=True,
)
app.add_typer(experiment_app, name="experiment")

edge_app = typer.Typer(
    name="edge",
    help="Edge node runtime — status, health, and semantic event emission.",
    no_args_is_help=True,
)
app.add_typer(edge_app, name="edge")


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _run_step(label: str, command: Sequence[str], *, cwd: Path | None = None) -> None:
    """Run a subprocess step; exit with its code on failure."""
    display = " ".join(command)
    typer.echo(f"[{label}] $ {display}")
    result = subprocess.run(command, cwd=cwd or _repo_root(), check=False)
    if result.returncode != 0:
        typer.secho(f"[{label}] failed (exit {result.returncode})", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=result.returncode)
    typer.secho(f"[{label}] ok", fg=typer.colors.GREEN)


def _python_module(module: str, *args: str) -> list[str]:
    return [sys.executable, "-m", module, *args]


def _simulation_result_to_json(result: SimulationResult) -> dict[str, object]:
    return {
        "scenario_id": result.scenario_id.value,
        "seed": result.seed,
        "location_id": result.graph.location_id,
        "zones": [zone.zone_id for zone in result.graph.zones],
        "exits": [exit_node.exit_id for exit_node in result.graph.exits],
        "event_count": len(result.events),
        "ground_truth": {
            "primary_label": result.ground_truth.primary_label,
            "recommended_review": result.ground_truth.recommended_review,
            "label_count": len(result.ground_truth.labels),
        },
        "events": [
            {
                "event_id": str(event.event_id),
                "event_type": event.event_type.value,
                "source": event.source.value,
                "zone_id": event.zone_id,
                "timestamp": event.timestamp.isoformat(),
                "confidence": event.confidence,
                "severity": event.severity.value,
                "privacy_level": event.privacy_level.value,
                "explanation": event.explanation,
                "metadata": event.metadata,
            }
            for event in result.events
        ],
    }


@app.command("version")
def version_cmd() -> None:
    """Print the installed DUALEXIS version."""
    typer.echo(get_version())


@app.command("check")
def check_cmd() -> None:
    """Run the same quality gates as CI (format, lint, types, tests)."""
    steps: tuple[tuple[str, list[str]], ...] = (
        ("format", _python_module("ruff", "format", "--check", ".")),
        ("lint", _python_module("ruff", "check", ".")),
        ("types", [sys.executable, "-m", "mypy", "dualexis", "tests"]),
        (
            "tests",
            [
                sys.executable,
                "-m",
                "pytest",
                "--cov=dualexis",
                "--cov-report=term-missing",
            ],
        ),
    )
    for label, command in steps:
        _run_step(label, command)
    typer.secho("All checks passed.", fg=typer.colors.GREEN, bold=True)


@app.command("test")
def test_cmd(
    args: list[str] = typer.Argument(None, help="Extra arguments forwarded to pytest."),
) -> None:
    """Run the test suite."""
    command = _python_module("pytest", *args)
    _run_step("test", command)


@app.command("lint")
def lint_cmd() -> None:
    """Run Ruff linter."""
    _run_step("lint", _python_module("ruff", "check", "."))


@app.command("format")
def format_cmd(
    check: bool = typer.Option(False, "--check", help="Check formatting without writing."),
) -> None:
    """Format code with Ruff."""
    command = _python_module("ruff", "format", *(["--check", "."] if check else ["."]))
    _run_step("format", command)


@app.command("simulate")
def simulate_cmd(
    scenario: str = typer.Option(
        ScenarioId.NORMAL_FLOW.value,
        "--scenario",
        "-s",
        help="Simulation scenario identifier.",
    ),
    seed: int = typer.Option(42, "--seed", help="Deterministic random seed."),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Emit the full simulation result as JSON.",
    ),
) -> None:
    """Run a reproducible confined-space simulation scenario."""
    try:
        result = run_scenario(scenario, seed=seed)
    except UnknownScenarioError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc

    if json_output:
        typer.echo(json.dumps(_simulation_result_to_json(result), indent=2))
        return

    typer.echo(f"scenario={result.scenario_id.value} seed={result.seed}")
    typer.echo(f"events={len(result.events)}")
    typer.echo(f"ground_truth={result.ground_truth.primary_label}")


@app.command("evaluate")
def evaluate_cmd(
    scenario: str = typer.Option(
        "exit_blockage",
        "--scenario",
        "-s",
        help="Simulation scenario identifier.",
    ),
    baseline: str = typer.Option(
        "rule_based",
        "--baseline",
        "-b",
        help="Evaluation baseline identifier.",
    ),
    seed: int = typer.Option(42, "--seed", help="Deterministic random seed."),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Emit the full evaluation report as JSON.",
    ),
) -> None:
    """Run a reproducible evaluation scaffold for a scenario and baseline."""
    try:
        report = run_evaluation(scenario, baseline, seed=seed)
    except UnknownBaselineError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc
    except UnknownScenarioError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc

    if json_output:
        typer.echo(json.dumps(report.model_dump(mode="json"), indent=2))
        return

    typer.echo(format_report_summary(report))


@experiment_app.command("protocol")
def experiment_protocol_cmd(
    scenario: str = typer.Option(
        "exit_blockage",
        "--scenario",
        "-s",
        help="Simulation scenario identifier.",
    ),
    protocol: str = typer.Option(
        "dualexis_full_pipeline",
        "--protocol",
        "-p",
        help="Experimental protocol identifier.",
    ),
    seed: int = typer.Option(42, "--seed", help="Deterministic random seed."),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Emit the full experiment report as JSON.",
    ),
) -> None:
    """Run a single protocol scaffold (legacy evaluation API)."""
    try:
        report = run_experiment(scenario, protocol, seed=seed)
    except UnknownProtocolError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc
    except UnknownScenarioError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc

    if json_output:
        typer.echo(json.dumps(report.model_dump(mode="json"), indent=2))
        return

    typer.echo(format_experiment_summary(report))


@experiment_app.command("run")
def experiment_run_cmd(
    config: str = typer.Option(
        ...,
        "--config",
        "-c",
        help="Path to a YAML experimental battery config.",
    ),
    output: str | None = typer.Option(
        None,
        "--output",
        "-o",
        help="Optional JSON output path (default: results/experiments/<experiment_id>.json).",
    ),
    json_output: bool = typer.Option(False, "--json", help="Emit battery JSON to stdout."),
) -> None:
    """Run a configured experimental battery on synthetic inputs."""
    try:
        config_path = Path(config).resolve()
        battery_config = load_experiment_config(config_path)
        result = run_battery_from_config(config_path)
    except FileNotFoundError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc
    except UnknownScenarioError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc
    except UnknownProtocolError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc

    default_out = Path("results/experiments") / f"{battery_config.experiment_id}.json"
    out_path = Path(output) if output else default_out
    written = write_battery_json(result, out_path)
    typer.echo(f"Wrote {written}", err=True)

    if json_output:
        typer.echo(json.dumps(result.model_dump(mode="json"), indent=2))
    else:
        typer.echo(
            f"experiment={result.experiment_id} scenario={result.scenario} "
            f"events={result.pipeline_event_count} "
            f"privacy_validation={'pass' if result.privacy_validation_passed else 'fail'}"
        )


@experiment_app.command("run-all")
def experiment_run_all_cmd(
    output: str = typer.Option(
        "results/experiments",
        "--output",
        "-o",
        help="Directory for JSON battery outputs.",
    ),
) -> None:
    """Run all YAML configs under experiments/configs/."""
    try:
        results = run_all_batteries(output)
    except FileNotFoundError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc

    typer.echo(f"Completed {len(results)} battery runs -> {Path(output).resolve()}")


@experiment_app.command("run-multiseed")
def experiment_run_multiseed_cmd(
    config_dir: str = typer.Option(
        "experiments/configs",
        "--config-dir",
        help="Directory containing YAML experiment configs.",
    ),
    seeds: str = typer.Option(
        "1,2,3,4,5,10,20,42,100,500",
        "--seeds",
        help="Comma-separated deterministic seeds.",
    ),
    output: str = typer.Option(
        "results/experiments_multiseed",
        "--output",
        "-o",
        help="Directory for multi-seed JSON, Markdown, and LaTeX outputs.",
    ),
) -> None:
    """Run every experiment config for every seed and emit descriptive aggregates."""
    try:
        seed_list = parse_seed_list(seeds)
        report = run_multiseed_batteries(output, config_dir=config_dir, seeds=seed_list)
    except (FileNotFoundError, ValueError) as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc

    typer.echo(
        f"Completed {report.run_count} runs across {len(report.seeds)} seeds "
        f"-> {Path(output).resolve()}"
    )


@experiment_app.command("report")
def experiment_report_cmd(
    input_dir: str = typer.Option(
        "results/experiments",
        "--input",
        "-i",
        help="Directory containing battery JSON results.",
    ),
    format: str = typer.Option(
        "markdown",
        "--format",
        "-f",
        help="Report format (markdown).",
    ),
    output: str | None = typer.Option(
        None,
        "--output",
        "-o",
        help="Output file (default: results/reports/battery_report.md).",
    ),
) -> None:
    """Generate a Markdown report from measured battery JSON results."""
    if format.lower() != "markdown":
        typer.secho(f"Unsupported report format: {format}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)

    try:
        results = load_battery_results(input_dir)
    except FileNotFoundError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc

    if not results:
        typer.secho(f"No battery JSON files found in {input_dir}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)

    out_path = Path(output) if output else Path("results/reports/battery_report.md")
    generate_markdown_report(results, output_path=out_path)
    typer.echo(f"Wrote {out_path.resolve()}")


@experiment_app.command("paper-table")
def experiment_paper_table_cmd(
    input_dir: str = typer.Option(
        "results/experiments",
        "--input",
        "-i",
        help="Directory containing battery JSON results.",
    ),
    output: str = typer.Option(
        "results_reference/tables/results.tex",
        "--output",
        "-o",
        help="LaTeX table output path.",
    ),
) -> None:
    """Generate a LaTeX table placeholder populated with measured scaffold values."""
    try:
        results = load_battery_results(input_dir)
    except FileNotFoundError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc

    if not results:
        typer.secho(f"No battery JSON files found in {input_dir}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)

    generate_latex_table(results, output_path=Path(output))
    typer.echo(f"Wrote {Path(output).resolve()}")


@experiment_app.command("compare")
def experiment_compare_cmd(
    scenario: str = typer.Option(
        "exit_blockage",
        "--scenario",
        "-s",
        help="Synthetic scenario shared by all comparable baselines.",
    ),
    seeds: str = typer.Option(
        "1,2,3,4,5,10,20,42,100,500",
        "--seeds",
        help="Comma-separated deterministic seeds.",
    ),
    output: str = typer.Option(
        "results/comparisons/",
        "--output",
        "-o",
        help="Directory for JSON, Markdown, and LaTeX comparison artifacts.",
    ),
) -> None:
    """Run all comparable baselines on identical scenarios and seeds."""
    try:
        seed_list = parse_seed_list(seeds)
        report = run_baseline_comparison(scenario, seed_list, output_dir=output)
    except (FileNotFoundError, ValueError, UnknownScenarioError) as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc

    typer.echo(
        f"Compared {len(report.aggregates)} baselines across {len(report.seeds)} seeds "
        f"-> {Path(output).resolve()}"
    )


@experiment_app.command("e2")
def experiment_e2_cmd(
    output: str = typer.Option(
        "results/e2_independent_gt",
        "--output",
        help="Directory for E2 CSV and JSON aggregates.",
    ),
    paper_tex: str = typer.Option(
        "results_reference/tables/e2_independent_gt.tex",
        "--paper-tex",
        help="LaTeX table output path.",
    ),
    results_tex: str = typer.Option(
        "results_reference/sections/results.tex",
        "--results-tex",
        help="Manuscript results section (auto-sync E2 table input only).",
    ),
    seeds: str = typer.Option(
        ",".join(str(s) for s in range(1, 31)),
        "--seeds",
        help="Comma-separated seeds (default 1--30).",
    ),
    scenarios: str = typer.Option(
        ",".join(
            [
                "normal_flow",
                "crowd_acceleration",
                "exit_blockage",
                "audio_stress_signal",
                "multimodal_conflict",
                "evacuation_recommendation",
            ]
        ),
        "--scenarios",
        help="Comma-separated scenario identifiers.",
    ),
    skip_regenerate: bool = typer.Option(
        False,
        "--skip-regenerate-yaml",
        help="Do not rewrite experiments/ground_truth/*.yaml from rules.",
    ),
) -> None:
    """E2: regenerate independent GT from rules and run multiseed evaluation vs. YAML labels."""
    from dualexis.experiments.e2_independent_gt import run_e2_package
    from dualexis.experiments.multiseed import parse_seed_list

    try:
        seed_list = parse_seed_list(seeds)
        scenario_list = tuple(s.strip() for s in scenarios.split(",") if s.strip())
        summary = run_e2_package(
            output_dir=output,
            paper_tex=paper_tex,
            results_tex=results_tex,
            scenarios=scenario_list,
            seeds=seed_list,
            regenerate_yaml=not skip_regenerate,
        )
    except (FileNotFoundError, ValueError, UnknownScenarioError) as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc

    typer.echo(f"E2 runs: {summary['runs']}")
    if summary.get("yaml_paths"):
        typer.echo(f"Regenerated {len(summary['yaml_paths'])} ground-truth YAML files")
    typer.echo(f"Wrote {summary['csv']}")
    typer.echo(f"Wrote {summary['tex']}")
    typer.echo(f"results.tex synced: {summary['results_tex_synced']}")


@experiment_app.command("sssg-artifacts")
def experiment_sssg_artifacts_cmd(
    output: str = typer.Option(
        "results/sssg",
        "--output",
        "-o",
        help="Directory for SSSG traces and metrics CSV.",
    ),
    paper_tables: str = typer.Option(
        "results_reference/tables",
        "--paper-tables",
        help="Directory for state_transition_examples.tex.",
    ),
    paper_figures: str = typer.Option(
        "results_reference/figures",
        "--paper-figures",
        help="Directory for semantic_state_graph.pdf.",
    ),
    seeds: str = typer.Option(
        "1,2,3",
        "--seeds",
        help="Comma-separated seeds for trace export (default: 1,2,3).",
    ),
    scenarios: str = typer.Option(
        "normal_flow,exit_blockage,multimodal_conflict,evacuation_recommendation,crowd_acceleration,audio_stress_signal",
        "--scenarios",
        help="Comma-separated scenario identifiers.",
    ),
) -> None:
    """Generate SSSG traces, metrics, and paper artefacts (table + figure)."""
    from dualexis.experiments.multiseed import parse_seed_list
    from dualexis.experiments.sssg_battery import run_sssg_battery

    try:
        seed_list = parse_seed_list(seeds)
        scenario_list = tuple(s.strip() for s in scenarios.split(",") if s.strip())
        report = run_sssg_battery(
            output_dir=Path(output),
            paper_tables=Path(paper_tables),
            paper_figures=Path(paper_figures),
            scenarios=scenario_list,
            seeds=seed_list,
        )
    except (FileNotFoundError, ValueError, UnknownScenarioError) as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc

    typer.echo(f"Traces: {report.traces_dir}")
    typer.echo(f"Metrics CSV: {report.metrics_csv}")
    typer.echo(f"Table: {report.examples_tex}")
    typer.echo(f"Figure: {report.figure_pdf}")


@experiment_app.command("tsgg-framework")
def experiment_tsgg_framework_cmd(
    output: str = typer.Option(
        "results/tsgg",
        "--output",
        "-o",
        help="Directory for TSGG traces, leakage sub-audit, and JSON report.",
    ),
    paper_tables: str = typer.Option(
        "results_reference/tables",
        "--paper-tables",
        help="Directory for tsgg_unified_metrics.tex.",
    ),
    paper_sections: str = typer.Option(
        "results_reference/sections",
        "--paper-sections",
        help="Directory for tsgg_framework.tex and tsgg_figure.tex.",
    ),
    paper_figures: str = typer.Option(
        "results_reference/figures",
        "--paper-figures",
        help="Directory for tsgg_framework.pdf.",
    ),
    seeds: str = typer.Option(
        "1,2,3",
        "--seeds",
        help="Comma-separated seeds (default: 1,2,3).",
    ),
    scenarios: str = typer.Option(
        "normal_flow,exit_blockage,multimodal_conflict,evacuation_recommendation,crowd_acceleration,audio_stress_signal",
        "--scenarios",
        help="Comma-separated scenario identifiers.",
    ),
    fast: bool = typer.Option(
        False,
        "--fast",
        help="Fast leakage Monte Carlo (50 iterations).",
    ),
) -> None:
    """TSGG unified framework: pipeline, metrics, figure, and paper section."""
    from dualexis.experiments.multiseed import parse_seed_list
    from dualexis.tsgg.audit import run_tsgg_framework

    try:
        seed_list = parse_seed_list(seeds)
        scenario_list = tuple(s.strip() for s in scenarios.split(",") if s.strip())
        report = run_tsgg_framework(
            output_dir=Path(output),
            paper_tables=Path(paper_tables),
            paper_sections=Path(paper_sections),
            paper_figures=Path(paper_figures),
            scenarios=scenario_list,
            seeds=seed_list,
            leakage_fast=fast,
        )
    except (FileNotFoundError, ValueError) as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc

    typer.echo(f"Report: {report.framework_json}")
    typer.echo(f"Metrics: {report.metrics_csv}")
    typer.echo(f"Section: {report.section_tex}")
    typer.echo(f"Table: {report.table_tex}")
    typer.echo(f"Figure: {report.figure_pdf}")
    if report.trust_section_tex is not None:
        typer.echo(f"Trust section: {report.trust_section_tex}")
    if report.trust_figure_pdf is not None:
        typer.echo(f"Trust figure: {report.trust_figure_pdf}")


@experiment_app.command("tsgg-trust-propagation")
def experiment_tsgg_trust_propagation_cmd(
    output: str = typer.Option(
        "results/tsgg/trust",
        "--output",
        "-o",
        help="Directory for trust propagation JSON report.",
    ),
    paper_tables: str = typer.Option("results_reference/tables", "--paper-tables"),
    paper_sections: str = typer.Option("results_reference/sections", "--paper-sections"),
    paper_figures: str = typer.Option("results_reference/figures", "--paper-figures"),
    seeds: str = typer.Option("1,2,3", "--seeds"),
    scenarios: str = typer.Option(
        "normal_flow,exit_blockage,multimodal_conflict,evacuation_recommendation,crowd_acceleration,audio_stress_signal",
        "--scenarios",
    ),
    fast: bool = typer.Option(False, "--fast", help="Fast leakage MC for benchmark prior."),
) -> None:
    """TSGG trust propagation: T(v), path trust, consistency/decay/recovery metrics."""
    from dualexis.experiments.multiseed import parse_seed_list
    from dualexis.leakage_audit.audit import run_leakage_audit
    from dualexis.tsgg.pipeline import run_tsgg_record
    from dualexis.tsgg.trust_propagation import (
        export_trust_propagation_artifacts,
        propagate_trust_batch,
    )

    try:
        seed_list = parse_seed_list(seeds)
        scenario_list = tuple(s.strip() for s in scenarios.split(",") if s.strip())
        leakage = run_leakage_audit(
            output_dir=Path(output) / "leakage",
            scenarios=scenario_list,
            fast=fast,
        )
        records = [
            run_tsgg_record(scenario, seed=seed)
            for scenario in scenario_list
            for seed in seed_list
        ]
        trust_report = propagate_trust_batch(records, leakage=leakage)
        paths = export_trust_propagation_artifacts(
            trust_report,
            Path(output),
            paper_sections=Path(paper_sections),
            paper_tables=Path(paper_tables),
            paper_figures=Path(paper_figures),
        )
    except (FileNotFoundError, ValueError) as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc

    m = trust_report.metrics
    typer.echo(f"trust_consistency={m.trust_consistency:.4f}")
    typer.echo(f"trust_decay={m.trust_decay:.4f}")
    typer.echo(f"trust_recovery={m.trust_recovery:.4f}")
    typer.echo(f"mean_recommendation_trust={m.mean_recommendation_trust:.4f}")
    for key, value in paths.items():
        typer.echo(f"{key}: {value}")


@experiment_app.command("institutional-memory")
def experiment_institutional_memory_cmd(
    output: str = typer.Option(
        "results/institutional_memory",
        "--output",
        "-o",
        help="Directory for IMG report, DOT graph, and pattern JSON.",
    ),
    paper_sections: str = typer.Option("results_reference/sections", "--paper-sections"),
    paper_figures: str = typer.Option("results_reference/figures", "--paper-figures"),
    seeds: str = typer.Option("1,2,3,4,5", "--seeds"),
    scenarios: str = typer.Option(
        "normal_flow,exit_blockage,multimodal_conflict,evacuation_recommendation,crowd_acceleration,audio_stress_signal",
        "--scenarios",
    ),
    min_support: int = typer.Option(2, "--min-support", help="Minimum pattern support count."),
) -> None:
    """Institutional Memory Graphs from historical TSGG governance traces."""
    from dualexis.experiments.multiseed import parse_seed_list
    from dualexis.institutional_memory import run_institutional_memory

    try:
        seed_list = parse_seed_list(seeds)
        scenario_list = tuple(s.strip() for s in scenarios.split(",") if s.strip())
        report = run_institutional_memory(
            output_dir=Path(output),
            paper_sections=Path(paper_sections),
            paper_figures=Path(paper_figures),
            scenarios=scenario_list,
            seeds=seed_list,
            min_support=min_support,
        )
    except (FileNotFoundError, ValueError) as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc

    m = report.metrics
    typer.echo(f"memory_coverage={m.memory_coverage:.4f}")
    typer.echo(f"pattern_recurrence={m.pattern_recurrence:.4f}")
    typer.echo(f"governance_learning_index={m.governance_learning_index:.4f}")
    typer.echo(f"governance_patterns={len(report.graph.governance_patterns)}")
    typer.echo(f"near_miss_patterns={len(report.graph.near_miss_patterns)}")
    typer.echo(f"escalation_chains={len(report.graph.escalation_chains)}")
    typer.echo(f"override_patterns={len(report.graph.override_patterns)}")
    typer.echo(f"output_dir: {output}")


@experiment_app.command("longitudinal-narratives")
def experiment_longitudinal_narratives_cmd(
    output: str = typer.Option(
        "results/narratives",
        "--output",
        "-o",
        help="Directory for narrative timelines, JSON, and metrics CSV.",
    ),
    paper_sections: str = typer.Option(
        "results_reference/sections",
        "--paper-sections",
        help="Directory for longitudinal_explanations.tex.",
    ),
    seeds: str = typer.Option("1,2,3", "--seeds"),
    scenarios: str = typer.Option(
        "normal_flow,exit_blockage,multimodal_conflict,evacuation_recommendation,crowd_acceleration,audio_stress_signal",
        "--scenarios",
    ),
) -> None:
    """Longitudinal safety narratives from full TSGG traces."""
    from dualexis.experiments.multiseed import parse_seed_list
    from dualexis.narratives import run_longitudinal_narratives

    try:
        seed_list = parse_seed_list(seeds)
        scenario_list = tuple(s.strip() for s in scenarios.split(",") if s.strip())
        report = run_longitudinal_narratives(
            output_dir=Path(output),
            paper_sections=Path(paper_sections),
            scenarios=scenario_list,
            seeds=seed_list,
        )
    except (FileNotFoundError, ValueError) as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc

    typer.echo(f"narrative_completeness={report.mean_completeness:.4f}")
    typer.echo(f"narrative_consistency={report.mean_consistency:.4f}")
    typer.echo(f"narrative_fidelity={report.mean_fidelity:.4f}")
    typer.echo(f"traces={len(report.traces)}")
    typer.echo(f"output_dir: {output}")


@experiment_app.command("leakage-audit")
def experiment_leakage_audit_cmd(
    output: str = typer.Option(
        "results/leakage_audit",
        "--output",
        "-o",
        help="Directory for leakage audit CSV, JSON, and DOT graph.",
    ),
    paper_tables: str = typer.Option(
        "results_reference/tables",
        "--paper-tables",
        help="Directory for leakage_audit.tex.",
    ),
    paper_sections: str = typer.Option(
        "results_reference/sections",
        "--paper-sections",
        help="Directory for leakage_analysis.tex.",
    ),
    seed: int = typer.Option(1, "--seed", help="Simulation seed for MC baseline."),
    iterations: int = typer.Option(
        1000,
        "--iterations",
        help="Monte Carlo threshold perturbations (default 1000).",
    ),
    fast: bool = typer.Option(
        False,
        "--fast",
        help="Use 50 MC iterations for quick smoke runs.",
    ),
) -> None:
    """E2 leakage audit: overlap metrics, LS score, Monte Carlo sensitivity, paper export."""
    from dualexis.leakage_audit import run_leakage_audit

    try:
        report = run_leakage_audit(
            output_dir=Path(output),
            paper_tables=Path(paper_tables),
            paper_sections=Path(paper_sections),
            seed=seed,
            monte_carlo_iterations=iterations,
            fast=fast,
        )
    except (FileNotFoundError, ValueError) as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc

    typer.echo(f"Leakage score L_S={report.leakage_score}")
    typer.echo(f"Procedural independence={report.independence.procedural_independence}")
    typer.echo(f"Semantic independence={report.independence.semantic_independence}")
    typer.echo(f"Distributional independence={report.independence.distributional_independence}")
    typer.echo(report.independence_disclosure)
    typer.echo(f"Wrote {output}/")


@experiment_app.command("ontology-drift")
def experiment_ontology_drift_cmd(
    output: str = typer.Option(
        "results/ontology_drift",
        "--output",
        "-o",
        help="Directory for ontology drift snapshots and metrics.",
    ),
    paper_sections: str = typer.Option(
        "results_reference/sections",
        "--paper-sections",
        help="Directory for ontology_drift.tex.",
    ),
    seeds: str = typer.Option(
        "1,2,3,4,5",
        "--seeds",
        help="Comma-separated seeds for drift measurement.",
    ),
    scenarios: str = typer.Option(
        "normal_flow,exit_blockage,multimodal_conflict,evacuation_recommendation,crowd_acceleration,audio_stress_signal",
        "--scenarios",
        help="Comma-separated scenario identifiers.",
    ),
    versions: str = typer.Option(
        "",
        "--versions",
        help="Optional comma-separated versions; defaults to current package version.",
    ),
) -> None:
    """Ontology drift: semantic labels, safety states, recommendations across seeds/versions."""
    from dualexis.experiments.multiseed import parse_seed_list
    from dualexis.ontology_drift import export_ontology_drift_report, run_ontology_drift_detection

    try:
        seed_list = parse_seed_list(seeds)
        scenario_list = tuple(s.strip() for s in scenarios.split(",") if s.strip())
        version_list = (
            tuple(v.strip() for v in versions.split(",") if v.strip()) if versions.strip() else None
        )
        report = run_ontology_drift_detection(
            scenarios=scenario_list,
            seeds=seed_list,
            versions=version_list,
            registry_dir=Path(output) / "registry",
        )
        paths = export_ontology_drift_report(
            report,
            Path(output),
            paper_sections=Path(paper_sections),
            registry_dir=Path(output) / "registry",
        )
    except (FileNotFoundError, ValueError) as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc

    typer.echo(f"ontology_stability={report.ontology_stability:.4f}")
    typer.echo(f"semantic_drift={report.semantic_drift:.4f}")
    typer.echo(f"recommendation_drift={report.recommendation_drift:.4f}")
    typer.echo(f"cross_version_semantic_drift={report.cross_version_semantic_drift:.4f}")
    for warning in report.registry_warnings:
        typer.secho(f"warning: {warning}", fg=typer.colors.YELLOW, err=True)
    for key, value in paths.items():
        typer.echo(f"{key}: {value}")


@experiment_app.command("adversarial-privacy")
def experiment_adversarial_privacy_cmd(
    output: str = typer.Option(
        "results/adversarial_privacy",
        "--output",
        "-o",
        help="Directory for adversarial privacy CSV, JSON, and fuzz baseline.",
    ),
    paper_sections: str = typer.Option(
        "results_reference/sections",
        "--paper-sections",
        help="Directory for adversarial_privacy.tex.",
    ),
) -> None:
    """Adversarial privacy stress: linkage attacks + metrics beyond forbidden-key fuzz."""
    from dualexis.adversarial_privacy import export_adversarial_privacy_stress, run_adversarial_privacy_stress

    report = run_adversarial_privacy_stress()
    paths = export_adversarial_privacy_stress(
        report,
        Path(output),
        paper_sections=Path(paper_sections),
    )
    m = report.metrics
    typer.echo(f"privacy_resilience_index={m.privacy_resilience_index:.4f}")
    typer.echo(f"attack_success_rate={m.privacy_attack_success_rate:.4f}")
    typer.echo(f"reidentification_risk={m.reidentification_risk:.4f}")
    typer.echo(f"semantic_leakage={m.semantic_leakage_score:.4f}")
    typer.echo(f"fuzz_pass_rate={m.fuzz_pass_rate:.4f}")
    for key, value in paths.items():
        typer.echo(f"{key}: {value}")


@experiment_app.command("robustness-audit")
def experiment_robustness_audit_cmd(
    output: str = typer.Option(
        "results/robustness",
        "--output",
        "-o",
        help="Directory for robustness JSON, CSV, and plot copies.",
    ),
    paper_figures: str = typer.Option(
        "results_reference/figures",
        "--paper-figures",
        help="Directory for robustness_vs_seed.pdf.",
    ),
    paper_sections: str = typer.Option(
        "results_reference/sections",
        "--paper-sections",
        help="Directory for robustness_analysis.tex.",
    ),
    seeds: str = typer.Option(
        "1,2,3,4,5",
        "--seeds",
        help="Comma-separated seeds (N) for the audit.",
    ),
    scenarios: str = typer.Option(
        "normal_flow,exit_blockage,multimodal_conflict,evacuation_recommendation,crowd_acceleration,audio_stress_signal",
        "--scenarios",
        help="Comma-separated scenario identifiers.",
    ),
) -> None:
    """Multiseed robustness audit: event/state/recommendation/explanation stability."""
    from dualexis.experiments.multiseed import parse_seed_list
    from dualexis.experiments.robustness_battery import run_robustness_battery

    try:
        seed_list = parse_seed_list(seeds)
        scenario_list = tuple(s.strip() for s in scenarios.split(",") if s.strip())
        report = run_robustness_battery(
            output_dir=Path(output),
            paper_figures=Path(paper_figures),
            paper_sections=Path(paper_sections),
            seeds=seed_list,
            scenarios=scenario_list,
        )
    except (FileNotFoundError, ValueError) as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc

    typer.echo(f"Robustness score R={report.report.robustness_score:.4f}")
    for dist in report.report.aggregate_distributions:
        typer.echo(
            f"  {dist.metric.value}: mean={dist.mean:.3f} std={dist.std:.3f} "
            f"cv={dist.coefficient_of_variation:.3f}"
        )
    typer.echo(f"Plot: {report.plot_pdf}")
    typer.echo(f"Section: {report.section_tex}")
    typer.echo(f"Wrote {output}/")


@experiment_app.command("counterfactual-artifacts")
def experiment_counterfactual_artifacts_cmd(
    output: str = typer.Option(
        "results/counterfactuals",
        "--output",
        "-o",
        help="Directory for counterfactual JSON traces and metrics CSV.",
    ),
    paper_sections: str = typer.Option(
        "results_reference/sections",
        "--paper-sections",
        help="Directory for counterfactual_reasoning.tex.",
    ),
    seeds: str = typer.Option(
        "1,2,3",
        "--seeds",
        help="Comma-separated seeds for stability measurement.",
    ),
    scenarios: str = typer.Option(
        "normal_flow,exit_blockage,multimodal_conflict,evacuation_recommendation,crowd_acceleration,audio_stress_signal",
        "--scenarios",
        help="Comma-separated scenario identifiers.",
    ),
) -> None:
    """Counterfactual what-if reasoning for every recommendation (SSSG-backed)."""
    from dualexis.experiments.counterfactual_battery import run_counterfactual_battery
    from dualexis.experiments.multiseed import parse_seed_list

    try:
        seed_list = parse_seed_list(seeds)
        scenario_list = tuple(s.strip() for s in scenarios.split(",") if s.strip())
        report = run_counterfactual_battery(
            output_dir=Path(output),
            paper_sections=Path(paper_sections),
            scenarios=scenario_list,
            seeds=seed_list,
        )
    except (FileNotFoundError, ValueError) as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc

    typer.echo(
        f"consistency={report.report.mean_counterfactual_consistency:.3f} "
        f"stability={report.report.mean_counterfactual_stability:.3f} "
        f"coverage={report.report.mean_counterfactual_explanation_coverage:.3f}"
    )
    typer.echo(f"recommendations={report.report.recommendation_count}")
    typer.echo(f"Section: {report.section_tex}")
    typer.echo(f"Wrote {output}/")


@experiment_app.command("cssg-artifacts")
def experiment_cssg_artifacts_cmd(
    output: str = typer.Option(
        "results/cssg",
        "--output",
        "-o",
        help="Directory for CSSG traces and metrics CSV.",
    ),
    paper_tables: str = typer.Option(
        "results_reference/tables",
        "--paper-tables",
        help="Directory for causal_metrics.tex.",
    ),
    paper_figures: str = typer.Option(
        "results_reference/figures",
        "--paper-figures",
        help="Directory for causal_state_graph.pdf.",
    ),
    paper_sections: str = typer.Option(
        "results_reference/sections",
        "--paper-sections",
        help="Directory for causal_reasoning.tex.",
    ),
    seeds: str = typer.Option(
        "1,2,3,4,5",
        "--seeds",
        help="Comma-separated seeds for stability measurement.",
    ),
    scenarios: str = typer.Option(
        "normal_flow,exit_blockage,multimodal_conflict,evacuation_recommendation,crowd_acceleration,audio_stress_signal",
        "--scenarios",
        help="Comma-separated scenario identifiers.",
    ),
) -> None:
    """CSSG: causal state graph metrics, explanation chains, paper export."""
    from dualexis.experiments.cssg_battery import run_cssg_battery
    from dualexis.experiments.multiseed import parse_seed_list

    try:
        seed_list = parse_seed_list(seeds)
        scenario_list = tuple(s.strip() for s in scenarios.split(",") if s.strip())
        report = run_cssg_battery(
            output_dir=Path(output),
            paper_tables=Path(paper_tables),
            paper_figures=Path(paper_figures),
            paper_sections=Path(paper_sections),
            scenarios=scenario_list,
            seeds=seed_list,
        )
    except (FileNotFoundError, ValueError) as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc

    typer.echo(f"Metrics: {report.metrics_csv}")
    typer.echo(f"Table: {report.metrics_tex}")
    typer.echo(f"Section: {report.section_tex}")
    typer.echo(f"Figure: {report.figure_pdf}")


@experiment_app.command("governance-artifacts")
def experiment_governance_artifacts_cmd(
    output: str = typer.Option(
        "results/governance",
        "--output",
        "-o",
        help="Directory for governance simulation CSV, JSON, and DOT graph.",
    ),
    paper_tables: str = typer.Option(
        "results_reference/tables",
        "--paper-tables",
        help="Directory for governance_metrics.tex.",
    ),
    paper_sections: str = typer.Option(
        "results_reference/sections",
        "--paper-sections",
        help="Directory for governance_evaluation.tex.",
    ),
    seed: int = typer.Option(42, "--seed", help="RNG seed for review resampling."),
    iterations: int = typer.Option(
        1000,
        "--iterations",
        help="Simulated review decisions per operator profile (default 1000).",
    ),
    fast: bool = typer.Option(
        False,
        "--fast",
        help="Use 50 decisions per profile and a smaller case pool.",
    ),
) -> None:
    """Human-AI governance layer: operator simulation, metrics, paper export."""
    from dualexis.governance import run_governance_evaluation

    try:
        report = run_governance_evaluation(
            output_dir=Path(output),
            paper_tables=Path(paper_tables),
            paper_sections=Path(paper_sections),
            seed=seed,
            simulation_iterations=iterations,
            fast=fast,
        )
    except (FileNotFoundError, ValueError) as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc

    typer.echo(report.contribution_title)
    for metrics in report.profile_metrics:
        typer.echo(
            f"  {metrics.profile.value}: accept={metrics.acceptance_rate:.3f} "
            f"override={metrics.override_rate:.3f} "
            f"escalate={metrics.escalation_rate:.3f} "
            f"latency={metrics.mean_review_latency_seconds:.1f}s"
        )
    typer.echo(f"Wrote {output}/")

    from dualexis.governance import export_governance_audit_report, run_formal_governance_audit

    formal_dir = Path(output) / "formal"
    audit = run_formal_governance_audit(
        simulation_iterations=iterations,
        seed=seed,
        fast=fast,
    )
    formal_paths = export_governance_audit_report(
        audit,
        formal_dir,
        paper_sections=Path(paper_sections),
    )
    typer.echo(f"Formal governance: compliance={audit.metrics.governance_compliance_score:.3f}")
    typer.echo(f"  institutional_reliance={audit.metrics.institutional_reliance_index:.3f}")
    typer.echo(f"  override_resilience={audit.metrics.human_override_resilience:.3f}")
    typer.echo(f"  traceability={audit.metrics.decision_traceability:.3f}")
    typer.echo(f"Formal artefacts: {formal_dir}/")
    typer.echo(f"Section: {formal_paths.get('section_tex', '')}")


@experiment_app.command("formal-governance-audit")
def experiment_formal_governance_audit_cmd(
    output: str = typer.Option(
        "results/governance/formal",
        "--output",
        "-o",
        help="Directory for GovernanceAuditReport and formal graph DOT.",
    ),
    paper_sections: str = typer.Option(
        "results_reference/sections",
        "--paper-sections",
        help="Directory for formal_governance_model.tex.",
    ),
    seed: int = typer.Option(42, "--seed"),
    iterations: int = typer.Option(1000, "--iterations"),
    fast: bool = typer.Option(False, "--fast"),
) -> None:
    """Formal Human-AI governance FSM: graph, traces, compliance metrics."""
    from dualexis.governance import export_governance_audit_report, run_formal_governance_audit

    audit = run_formal_governance_audit(
        simulation_iterations=iterations,
        seed=seed,
        fast=fast,
    )
    paths = export_governance_audit_report(
        audit,
        Path(output),
        paper_sections=Path(paper_sections),
    )
    m = audit.metrics
    typer.echo(audit.framework_title)
    typer.echo(f"governance_compliance_score={m.governance_compliance_score:.4f}")
    typer.echo(f"institutional_reliance_index={m.institutional_reliance_index:.4f}")
    typer.echo(f"human_override_resilience={m.human_override_resilience:.4f}")
    typer.echo(f"decision_traceability={m.decision_traceability:.4f}")
    for key, value in paths.items():
        typer.echo(f"{key}: {value}")


@experiment_app.command("validate-tsgg")
def experiment_validate_tsgg_cmd(
    output: str = typer.Option(
        "results/baseline_comparison",
        "--baseline-output",
        help="Directory for baseline CSV and summary.",
    ),
    privacy_output: str = typer.Option(
        "results/privacy_fuzz",
        "--privacy-output",
        help="Directory for privacy fuzz CSV.",
    ),
    seeds: str = typer.Option(
        ",".join(str(s) for s in range(1, 31)),
        "--seeds",
        help="Comma-separated seeds (default 1--30).",
    ),
    scenarios: str = typer.Option(
        ",".join(
            [
                "normal_flow",
                "exit_blockage",
                "multimodal_conflict",
                "evacuation_recommendation",
                "crowd_acceleration",
                "audio_stress_signal",
            ]
        ),
        "--scenarios",
        help="Comma-separated scenario identifiers.",
    ),
) -> None:
    """Run TSGG/JSS validation package: multiseed diagnostics, fuzz exports, paper tables."""
    from dualexis.experiments.empirical_battery import run_validate_tsgg_package
    from dualexis.experiments.multiseed import parse_seed_list

    try:
        seed_list = parse_seed_list(seeds)
        scenario_list = tuple(s.strip() for s in scenarios.split(",") if s.strip())
        summary = run_validate_tsgg_package(
            baseline_output=output,
            privacy_output=privacy_output,
            scenarios=scenario_list,
            seeds=seed_list,
        )
    except (FileNotFoundError, ValueError, UnknownScenarioError) as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc

    typer.echo(f"Baseline runs: {summary['baseline_runs']}")
    typer.echo(f"Wrote {summary['baseline_csv']}")
    typer.echo(f"Wrote {summary['baseline_tex']}")
    typer.echo(f"Wrote {summary['privacy_csv']}")
    typer.echo(f"Wrote {summary['privacy_tex']}")


@experiment_app.command("analyze-multiseed")
def experiment_analyze_multiseed_cmd(
    input_csv: str = typer.Option(
        "results/baseline_comparison/results.csv",
        "--input",
        help="Multiseed baseline results CSV.",
    ),
    output: str = typer.Option(
        "results/baseline_comparison/analysis",
        "--output",
        "-o",
        help="Directory for analysis CSV, LaTeX, figures, and narrative.",
    ),
    bootstrap_resamples: int = typer.Option(
        5000,
        "--bootstrap-resamples",
        help="Bootstrap resamples for percentile CIs.",
    ),
) -> None:
    """Post-hoc multiseed statistics (stability, bootstrap CIs, paired deltas, figures)."""
    from dualexis.experiments.multiseed_statistics import export_analysis_bundle

    try:
        out_path = export_analysis_bundle(
            input_csv,
            output,
            bootstrap_resamples=bootstrap_resamples,
        )
    except FileNotFoundError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc

    typer.echo(f"Analysis written to {out_path}")
    typer.echo(f"LaTeX: {out_path / 'multiseed_statistics.tex'}")
    typer.echo(f"Narrative: {out_path / 'narrative_validation.md'}")


@experiment_app.command("validate-s2a")
def experiment_validate_s2a_cmd(
    output: str = typer.Option(
        "results/validation_s2a",
        "--output",
        "-o",
        help="Directory for CSV, JSON, and LaTeX validation outputs.",
    ),
    seeds: str = typer.Option(
        ",".join(str(seed) for seed in range(1, 31)),
        "--seeds",
        help="Comma-separated seeds (default: 1--30).",
    ),
    scenarios: str = typer.Option(
        "normal_flow,exit_blockage,multimodal_conflict,evacuation_recommendation",
        "--scenarios",
        help="Comma-separated scenario identifiers.",
    ),
    skip_ablations: bool = typer.Option(
        False,
        "--skip-ablations",
        help="Run only C1--C4 (skip L1/L4/L5 ablations).",
    ),
    paper_tables: str = typer.Option(
        "results_reference/tables/results.tex",
        "--paper-tables",
        help="LaTeX file to update with validation tables.",
    ),
) -> None:
    """Run synthetic validation battery (independent GT, C1--C4, ablations)."""
    from dualexis.experiments.multiseed import parse_seed_list
    from dualexis.experiments.validation_battery import run_validation_battery

    try:
        seed_list = parse_seed_list(seeds)
        scenario_list = tuple(part.strip() for part in scenarios.split(",") if part.strip())
        report = run_validation_battery(
            output,
            scenarios=scenario_list,
            seeds=seed_list,
            include_ablations=not skip_ablations,
        )
        tables_src = Path(output).resolve() / "validation_tables.tex"
        paper_path = Path(paper_tables).resolve()
        paper_path.parent.mkdir(parents=True, exist_ok=True)
        paper_path.write_text(tables_src.read_text(encoding="utf-8"), encoding="utf-8")
    except (FileNotFoundError, ValueError, UnknownScenarioError) as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc

    typer.echo(
        f"Validation complete: {len(report.runs)} runs, "
        f"{len(report.aggregates)} aggregate rows -> {Path(output).resolve()}"
    )
    typer.echo(f"Wrote LaTeX tables -> {paper_path.resolve()}")


def _pipeline_output_to_json(output: object) -> dict[str, object]:
    from dualexis.pipeline.models import PipelineOutput

    if isinstance(output, PipelineOutput):
        return output.model_dump(mode="json")
    msg = "Expected PipelineOutput"
    raise TypeError(msg)


@app.command("run-pipeline")
def run_pipeline_cmd(
    scenario: str = typer.Option(
        "exit_blockage",
        "--scenario",
        "-s",
        help="Simulation scenario used to build synthetic pipeline inputs.",
    ),
    seed: int = typer.Option(42, "--seed", help="Deterministic random seed."),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Emit the full pipeline output as JSON.",
    ),
) -> None:
    """Run the end-to-end DUALEXIS pipeline on synthetic inputs."""
    try:
        output = run_pipeline(scenario, seed=seed)
    except UnknownScenarioError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc

    if json_output:
        typer.echo(json.dumps(_pipeline_output_to_json(output), indent=2))
        return

    typer.echo(f"scenario={scenario} seed={seed}")
    typer.echo(f"events={len(output.normalized_events)}")
    typer.echo(f"recommendations={len(output.recommendations)}")
    typer.echo(f"audit_records={len(output.audit_records)}")
    typer.echo(f"privacy_compliant={output.privacy_report.policy_compliant}")


def _emit_measurement_report(report: object, *, json_output: bool) -> None:
    from dualexis.measurement.models import CombinedMeasurementReport, MeasurementReport

    if json_output:
        if isinstance(report, MeasurementReport | CombinedMeasurementReport):
            typer.echo(json.dumps(report.model_dump(mode="json"), indent=2))
            return
        typer.echo(json.dumps(report, indent=2))
        return

    if isinstance(report, CombinedMeasurementReport):
        typer.echo(
            f"scenario={report.scenario} seed={report.seed} runs={report.runs} "
            f"reports=scenario,latency,privacy,robustness"
        )
        return

    if isinstance(report, MeasurementReport):
        typer.echo(format_measurement_summary(report))
        return

    typer.echo(str(report))


def _handle_scenario_error(exc: UnknownScenarioError) -> None:
    typer.secho(str(exc), fg=typer.colors.RED, err=True)
    raise typer.Exit(code=1) from exc


@measure_app.command("scenario")
def measure_scenario_cmd(
    scenario: str = typer.Option(
        "exit_blockage",
        "--scenario",
        "-s",
        help="Simulation scenario identifier.",
    ),
    seed: int = typer.Option(42, "--seed", help="Deterministic random seed."),
    json_output: bool = typer.Option(False, "--json", help="Emit measurement JSON."),
) -> None:
    """Measure full pipeline metrics for a single scenario run."""
    try:
        report = measure_scenario(scenario, seed=seed)
    except UnknownScenarioError as exc:
        _handle_scenario_error(exc)
    _emit_measurement_report(report, json_output=json_output)


@measure_app.command("latency")
def measure_latency_cmd(
    scenario: str = typer.Option(
        "exit_blockage",
        "--scenario",
        "-s",
        help="Simulation scenario identifier.",
    ),
    seed: int = typer.Option(42, "--seed", help="Deterministic random seed."),
    runs: int = typer.Option(1, "--runs", min=1, help="Number of timed repetitions."),
    json_output: bool = typer.Option(False, "--json", help="Emit measurement JSON."),
) -> None:
    """Measure averaged stage latencies over repeated pipeline runs."""
    try:
        report = measure_latency_report(scenario, seed=seed, runs=runs)
    except UnknownScenarioError as exc:
        _handle_scenario_error(exc)
    _emit_measurement_report(report, json_output=json_output)


@measure_app.command("privacy")
def measure_privacy_cmd(
    scenario: str = typer.Option(
        "exit_blockage",
        "--scenario",
        "-s",
        help="Simulation scenario identifier.",
    ),
    seed: int = typer.Option(42, "--seed", help="Deterministic random seed."),
    json_output: bool = typer.Option(False, "--json", help="Emit measurement JSON."),
) -> None:
    """Measure privacy posture metrics for a scenario run."""
    try:
        report = measure_privacy_report(scenario, seed=seed)
    except UnknownScenarioError as exc:
        _handle_scenario_error(exc)
    _emit_measurement_report(report, json_output=json_output)


@measure_app.command("robustness")
def measure_robustness_cmd(
    scenario: str = typer.Option(
        "multimodal_conflict",
        "--scenario",
        "-s",
        help="Simulation scenario identifier.",
    ),
    seed: int = typer.Option(42, "--seed", help="Deterministic random seed."),
    runs: int = typer.Option(1, "--runs", min=1, help="Number of robustness repetitions."),
    drop_modality: str = typer.Option(
        "audio",
        "--drop-modality",
        help="Modality to drop during robustness testing.",
    ),
    json_output: bool = typer.Option(False, "--json", help="Emit measurement JSON."),
) -> None:
    """Measure pipeline robustness under modality dropout."""
    try:
        report = measure_robustness_report(
            scenario,
            seed=seed,
            runs=runs,
            drop_modality=drop_modality,
        )
    except UnknownScenarioError as exc:
        _handle_scenario_error(exc)
    _emit_measurement_report(report, json_output=json_output)


@measure_app.command("all")
def measure_all_cmd(
    scenario: str = typer.Option(
        "exit_blockage",
        "--scenario",
        "-s",
        help="Simulation scenario identifier.",
    ),
    seed: int = typer.Option(42, "--seed", help="Deterministic random seed."),
    runs: int = typer.Option(1, "--runs", min=1, help="Number of repetitions for timed probes."),
    drop_modality: str = typer.Option(
        "audio",
        "--drop-modality",
        help="Modality to drop during robustness testing.",
    ),
    output: str | None = typer.Option(
        None,
        "--output",
        "-o",
        help="Write combined JSON to this path (default: results/measurements/<scenario>.json).",
    ),
    json_output: bool = typer.Option(False, "--json", help="Emit combined measurement JSON."),
) -> None:
    """Run scenario, latency, privacy, and robustness measurements."""
    try:
        report = measure_all(
            scenario,
            seed=seed,
            runs=runs,
            drop_modality=drop_modality,
        )
    except UnknownScenarioError as exc:
        _handle_scenario_error(exc)

    out_path = resolve_output_path(
        output or f"{scenario}_measurements.json",
        subdir="measurements",
    )
    written = write_combined_json(report, out_path)
    typer.echo(f"Wrote {written}", err=True)

    if json_output:
        _emit_measurement_report(report, json_output=True)


@edge_app.command("status")
def edge_status_cmd(
    json_output: bool = typer.Option(False, "--json", help="Emit status JSON."),
) -> None:
    """Show edge node operational status."""
    status = edge_status()
    if json_output:
        typer.echo(json.dumps(status.model_dump(mode="json"), indent=2))
        return
    typer.echo(
        f"node_id={status.node_id} state={status.state.value} "
        f"policy={status.policy_id} gpu={status.gpu.available}"
    )


@edge_app.command("health")
def edge_health_cmd(
    json_output: bool = typer.Option(False, "--json", help="Emit health JSON."),
) -> None:
    """Run edge node health probes."""
    health = edge_health()
    if json_output:
        typer.echo(json.dumps(health.model_dump(mode="json"), indent=2))
        return
    typer.echo(f"node_id={health.node_id} healthy={health.healthy} state={health.state.value}")


@edge_app.command("run-node")
def edge_run_node_cmd(
    config: str = typer.Option(
        "infrastructure/edge/node.yaml",
        "--config",
        "-c",
        help="Path to edge node YAML manifest.",
    ),
) -> None:
    """Start the edge node runtime from a YAML manifest."""
    try:
        node = run_node(config)
    except FileNotFoundError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc

    status = node.status()
    typer.echo(
        f"Edge node started: node_id={status.node_id} zones={','.join(status.zone_ids)} "
        f"gpu={status.gpu.available}"
    )


@edge_app.command("emit-synthetic")
def edge_emit_synthetic_cmd(
    scenario: str = typer.Option(
        "exit_blockage",
        "--scenario",
        "-s",
        help="Synthetic simulation scenario identifier.",
    ),
    seed: int = typer.Option(42, "--seed", help="Deterministic random seed."),
    config: str = typer.Option(
        "infrastructure/edge/node.yaml",
        "--config",
        "-c",
        help="Edge node manifest (auto-starts the node if not running).",
    ),
    json_output: bool = typer.Option(False, "--json", help="Emit emission batch JSON."),
) -> None:
    """Emit privacy-validated semantic events from a synthetic scenario."""
    try:
        batch = emit_synthetic_events(scenario, seed=seed, config_path=config)
    except UnknownScenarioError as exc:
        _handle_scenario_error(exc)
    except FileNotFoundError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc

    if json_output:
        payload = batch.model_dump(mode="json")
        typer.echo(json.dumps(payload, indent=2))
        return

    typer.echo(
        f"node_id={batch.node_id} emitted={len(batch.emitted_events)} blocked={batch.blocked_count}"
    )


def main() -> None:
    """Console script entry point."""
    app()


if __name__ == "__main__":
    main()
