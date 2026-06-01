"""Unit tests for ``dualexis.evaluation.comparable_baselines``."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

import pytest

from dualexis.evaluation.comparable_baselines import (
    ComparableBaseline,
    ComparableBaselineId,
    ComparableBaselineResult,
    DualexisFullPipelineBaseline,
    RuleBasedFusionComparableBaseline,
    SingleModalityAlertBaseline,
    TemporalGraphBaseline,
    get_comparable_baseline,
    list_comparable_baselines,
    run_all_comparable_baselines,
)
from dualexis.evaluation.comparison import (
    BaselineComparisonReport,
    compute_baseline_aggregates,
    generate_comparison_latex_table,
    generate_comparison_markdown,
)
from dualexis.simulation.scenario import ScenarioId

SYNTHETIC_SCENARIOS = (
    ScenarioId.EXIT_BLOCKAGE.value,
    ScenarioId.NORMAL_FLOW.value,
    ScenarioId.MULTIMODAL_CONFLICT.value,
)

ALL_BASELINE_CLASSES: tuple[type[ComparableBaseline], ...] = (
    SingleModalityAlertBaseline,
    RuleBasedFusionComparableBaseline,
    TemporalGraphBaseline,
    DualexisFullPipelineBaseline,
)

METRIC_KEYS = (
    "end_to_end_latency_ms",
    "recommendation_count",
    "privacy_violation_count",
    "explanation_completeness_score",
    "human_review_compliance_rate",
    "modality_drop_tolerance",
    "reproducibility_score",
)


def _assert_bounded_unit_interval(value: float, *, name: str) -> None:
    assert 0.0 <= value <= 1.0, f"{name}={value} is outside [0, 1]"


def _assert_result_fields_populated(result: ComparableBaselineResult) -> None:
    for slot in ComparableBaselineResult.__slots__:
        assert hasattr(result, slot), f"missing attribute {slot!r}"
        value = getattr(result, slot)
        assert value is not None, f"{slot} must not be None"

    assert isinstance(result.baseline_id, ComparableBaselineId)
    assert isinstance(result.scenario, str) and result.scenario
    assert isinstance(result.seed, int)
    assert isinstance(result.end_to_end_latency_ms, float)
    assert isinstance(result.recommendation_count, int)
    assert isinstance(result.privacy_violation_count, int)
    assert isinstance(result.explanation_completeness_score, float)
    assert isinstance(result.human_review_compliance_rate, float)
    assert isinstance(result.modality_drop_tolerance, float)
    assert isinstance(result.reproducibility_score, float)


@pytest.mark.parametrize("baseline_id", list(ComparableBaselineId))
@pytest.mark.parametrize("scenario", SYNTHETIC_SCENARIOS)
def test_each_comparable_baseline_runs_on_synthetic_scenario(
    baseline_id: ComparableBaselineId,
    scenario: str,
) -> None:
    result = get_comparable_baseline(baseline_id).run(scenario, seed=42)
    assert result.baseline_id == baseline_id
    assert result.scenario == scenario
    assert result.seed == 42


@pytest.mark.parametrize("baseline_cls", ALL_BASELINE_CLASSES)
def test_baseline_result_fields_are_populated(baseline_cls: type[ComparableBaseline]) -> None:
    result = baseline_cls().run(ScenarioId.EXIT_BLOCKAGE.value, seed=7)
    _assert_result_fields_populated(result)


@pytest.mark.parametrize("baseline_cls", ALL_BASELINE_CLASSES)
def test_privacy_violation_count_is_always_present(baseline_cls: type[ComparableBaseline]) -> None:
    result = baseline_cls().run(ScenarioId.EXIT_BLOCKAGE.value, seed=11)
    assert isinstance(result.privacy_violation_count, int)
    assert result.privacy_violation_count >= 0

    payload = result.as_dict()
    metrics = payload["metrics"]
    assert isinstance(metrics, dict)
    assert "privacy_violation_count" in metrics
    assert metrics["privacy_violation_count"] == result.privacy_violation_count


@pytest.mark.parametrize("baseline_cls", ALL_BASELINE_CLASSES)
def test_explanation_completeness_score_is_bounded(
    baseline_cls: type[ComparableBaseline],
) -> None:
    result = baseline_cls().run(ScenarioId.MULTIMODAL_CONFLICT.value, seed=3)
    _assert_bounded_unit_interval(
        result.explanation_completeness_score,
        name="explanation_completeness_score",
    )


@pytest.mark.parametrize("baseline_cls", ALL_BASELINE_CLASSES)
def test_human_review_compliance_rate_is_bounded(
    baseline_cls: type[ComparableBaseline],
) -> None:
    result = baseline_cls().run(ScenarioId.EXIT_BLOCKAGE.value, seed=3)
    _assert_bounded_unit_interval(
        result.human_review_compliance_rate,
        name="human_review_compliance_rate",
    )


@pytest.mark.parametrize("baseline_cls", ALL_BASELINE_CLASSES)
def test_modality_drop_tolerance_is_bounded(baseline_cls: type[ComparableBaseline]) -> None:
    result = baseline_cls().run(ScenarioId.AUDIO_STRESS_SIGNAL.value, seed=5)
    _assert_bounded_unit_interval(result.modality_drop_tolerance, name="modality_drop_tolerance")


@pytest.mark.parametrize("baseline_cls", ALL_BASELINE_CLASSES)
def test_reproducibility_score_is_bounded(baseline_cls: type[ComparableBaseline]) -> None:
    result = baseline_cls().run(ScenarioId.NORMAL_FLOW.value, seed=9)
    _assert_bounded_unit_interval(result.reproducibility_score, name="reproducibility_score")
    assert result.reproducibility_score in {0.0, 1.0}


def test_comparable_outputs_serialize_to_json() -> None:
    runs = run_all_comparable_baselines(ScenarioId.EXIT_BLOCKAGE.value, seed=42)
    assert len(runs) == len(list_comparable_baselines())

    for result in runs:
        serialized = json.dumps(result.as_dict())
        payload: dict[str, Any] = json.loads(serialized)
        assert payload["baseline_id"] == result.baseline_id.value
        assert payload["scenario"] == result.scenario
        assert payload["seed"] == result.seed
        metrics = payload["metrics"]
        assert isinstance(metrics, dict)
        for key in METRIC_KEYS:
            assert key in metrics


def test_comparison_reports_generate_markdown_and_latex_tables() -> None:
    runs = run_all_comparable_baselines(ScenarioId.EXIT_BLOCKAGE.value, seed=1)
    runs += run_all_comparable_baselines(ScenarioId.EXIT_BLOCKAGE.value, seed=2)
    aggregates = compute_baseline_aggregates(runs)
    report = BaselineComparisonReport(
        scenario=ScenarioId.EXIT_BLOCKAGE.value,
        seeds=(1, 2),
        generated_at=datetime.now(tz=UTC),
        output_dir="/tmp/unused",
        runs=tuple(runs),
        aggregates=aggregates,
    )

    markdown = generate_comparison_markdown(report)
    assert "| Baseline |" in markdown
    assert ScenarioId.EXIT_BLOCKAGE.value in markdown
    assert all(item.baseline_id in markdown for item in aggregates)

    latex = generate_comparison_latex_table(report)
    assert "\\begin{table}" in latex
    assert "\\begin{tabular}" in latex
    assert "tab:baseline-comparison" in latex
    assert "Single-modality alert" in latex or "DUALEXIS full pipeline" in latex
