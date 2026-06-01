"""Unit tests for the DUALEXIS evaluation scaffold."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from typer.testing import CliRunner

from dualexis.cli import app
from dualexis.evaluation.baselines import (
    BaselineId,
    BaselineOutput,
    DualexisSemanticBaseline,
    RuleBasedFusionBaseline,
    SingleModalityBaseline,
    UnknownBaselineError,
    get_baseline,
    list_baselines,
)
from dualexis.evaluation.metrics import (
    EvaluationMetricSet,
    compute_average_confidence,
    compute_event_count,
    compute_false_negative_rate,
    compute_false_positive_rate,
    compute_high_severity_rate,
    compute_human_review_compliance_rate_from_baseline,
    compute_metrics,
    compute_personal_data_exposure_score_from_baseline,
    compute_raw_media_retention_score,
    count_false_positives_and_negatives,
)
from dualexis.evaluation.report import EvaluationReport, format_report_summary, run_evaluation
from dualexis.orchestration.models import SeverityLevel
from dualexis.privacy_runtime.models import PrivacyLevel
from dualexis.semantic_events.models import EventSource, EventType, SemanticEvent
from dualexis.simulation import run_scenario
from dualexis.simulation.ground_truth import GroundTruthLabel, ScenarioGroundTruth
from dualexis.simulation.scenario import ScenarioId

runner = CliRunner()


def _event(
    *,
    zone_id: str = "hall-a",
    category: str = "density_elevated",
    confidence: float = 0.8,
    severity: SeverityLevel = SeverityLevel.MEDIUM,
) -> SemanticEvent:
    return SemanticEvent(
        event_id=uuid4(),
        event_type=EventType.CROWD_ACCELERATION,
        source=EventSource.SIMULATOR,
        zone_id=zone_id,
        timestamp=datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC),
        confidence=confidence,
        severity=severity,
        explanation="Synthetic evaluation event for metric testing.",
        privacy_level=PrivacyLevel.SEMANTIC_ONLY,
        metadata={"category": category},
    )


def _ground_truth(*labels: tuple[str, str]) -> ScenarioGroundTruth:
    return ScenarioGroundTruth(
        scenario_id=ScenarioId.CROWD_ACCELERATION,
        primary_label="crowd_density_elevated",
        labels=tuple(
            GroundTruthLabel(
                scenario_id=ScenarioId.CROWD_ACCELERATION,
                tick=1,
                zone_id=zone_id,
                semantic_label=category,
                expected_severity=SeverityLevel.MEDIUM,
                expected_event_type=EventType.CROWD_ACCELERATION,
            )
            for zone_id, category in labels
        ),
    )


@pytest.mark.unit
class TestMetricComputations:
    def test_event_count(self) -> None:
        events = (_event(), _event(category="other"))
        assert compute_event_count(events) == 2.0

    def test_average_confidence(self) -> None:
        events = (_event(confidence=0.6), _event(confidence=0.8))
        assert compute_average_confidence(events) == pytest.approx(0.7)

    def test_high_severity_rate(self) -> None:
        events = (
            _event(severity=SeverityLevel.HIGH),
            _event(severity=SeverityLevel.LOW),
        )
        assert compute_high_severity_rate(events) == pytest.approx(0.5)

    def test_false_positive_and_negative_counts(self) -> None:
        predicted = (
            _event(zone_id="cafeteria", category="density_elevated"),
            _event(zone_id="hall-a", category="spurious_alert"),
        )
        ground_truth = _ground_truth(("cafeteria", "density_elevated"))
        fp, fn = count_false_positives_and_negatives(predicted, ground_truth)
        assert fp == 1
        assert fn == 0
        assert compute_false_positive_rate(predicted, ground_truth) == pytest.approx(0.5)
        assert compute_false_negative_rate(predicted, ground_truth) == pytest.approx(0.0)

    def test_privacy_metric_helpers(self) -> None:
        output = BaselineOutput(
            events=(_event(),),
            time_to_recommendation_ms=100.0,
            raw_media_bytes_persisted=0,
            personal_data_violations=0,
            human_review_compliant_count=2,
            human_review_required_count=2,
        )
        assert compute_raw_media_retention_score(output, output.events) == 1.0
        assert compute_personal_data_exposure_score_from_baseline(output) == 0.0
        assert compute_human_review_compliance_rate_from_baseline(output) == 1.0

    def test_compute_metrics_bundle(self) -> None:
        events = (_event(),)
        output = BaselineOutput(events=events, time_to_recommendation_ms=150.0)
        metrics = compute_metrics(output, _ground_truth(("hall-a", "density_elevated")))
        assert isinstance(metrics, EvaluationMetricSet)
        assert metrics.event_count == 1.0
        assert metrics.time_to_recommendation_ms == 150.0


@pytest.mark.unit
class TestBaselines:
    def test_registered_baselines(self) -> None:
        assert {baseline.value for baseline in list_baselines()} == {
            "single_modality",
            "rule_based",
            "dualexis_semantic",
        }

    def test_get_baseline_instances(self) -> None:
        assert isinstance(get_baseline("single_modality"), SingleModalityBaseline)
        assert isinstance(get_baseline("rule_based"), RuleBasedFusionBaseline)
        assert isinstance(get_baseline("dualexis_semantic"), DualexisSemanticBaseline)

    def test_unknown_baseline_raises(self) -> None:
        with pytest.raises(UnknownBaselineError, match="Unknown baseline"):
            get_baseline("not_a_baseline")

    @pytest.mark.parametrize("baseline_name", [baseline.value for baseline in BaselineId])
    def test_baselines_run_on_simulation(self, baseline_name: str) -> None:
        simulation = run_scenario("normal_flow", seed=42)
        output = get_baseline(baseline_name).run(simulation)
        assert isinstance(output, BaselineOutput)


@pytest.mark.unit
class TestReportGeneration:
    def test_run_evaluation_returns_report(self) -> None:
        report = run_evaluation("exit_blockage", "rule_based", seed=42)
        assert isinstance(report, EvaluationReport)
        assert report.scenario_name == "exit_blockage"
        assert report.baseline_name == "rule_based"
        assert report.seed == 42
        assert report.metrics.event_count >= 0.0
        assert "Scaffold" in report.notes
        assert "No empirical conclusions" in report.notes

    def test_format_report_summary(self) -> None:
        report = run_evaluation("crowd_acceleration", "dualexis_semantic", seed=7)
        summary = format_report_summary(report)
        assert "scenario=crowd_acceleration" in summary
        assert "false_positive_rate=" in summary

    def test_reproducible_metrics_for_same_seed(self) -> None:
        first = run_evaluation("multimodal_conflict", "rule_based", seed=99)
        second = run_evaluation("multimodal_conflict", "rule_based", seed=99)
        assert first.metrics.model_dump() == second.metrics.model_dump()


@pytest.mark.unit
class TestEvaluateCli:
    def test_cli_evaluate_command(self) -> None:
        result = runner.invoke(
            app,
            ["evaluate", "--scenario", "exit_blockage", "--baseline", "rule_based", "--seed", "42"],
        )
        assert result.exit_code == 0
        assert "event_count=" in result.stdout
        assert "false_negative_rate=" in result.stdout

    def test_cli_evaluate_json_output(self) -> None:
        result = runner.invoke(
            app,
            [
                "evaluate",
                "--scenario",
                "exit_blockage",
                "--baseline",
                "rule_based",
                "--seed",
                "42",
                "--json",
            ],
        )
        assert result.exit_code == 0
        payload = json.loads(result.stdout)
        assert payload["scenario_name"] == "exit_blockage"
        assert payload["baseline_name"] == "rule_based"
        assert "metrics" in payload

    def test_cli_evaluate_invalid_baseline(self) -> None:
        result = runner.invoke(
            app,
            ["evaluate", "--scenario", "normal_flow", "--baseline", "invalid", "--seed", "1"],
        )
        assert result.exit_code == 1
        assert "Unknown baseline" in result.stderr or "Unknown baseline" in result.stdout
