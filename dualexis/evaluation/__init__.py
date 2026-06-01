"""Evaluation layer — reproducible benchmark and experiment scaffold."""

from dualexis.evaluation.baselines import (
    Baseline,
    BaselineId,
    BaselineOutput,
    DualexisSemanticBaseline,
    RuleBasedFusionBaseline,
    SingleModalityBaseline,
    UnknownBaselineError,
    get_baseline,
    list_baselines,
)
from dualexis.evaluation.experiment import run_experiment
from dualexis.evaluation.interfaces import EvaluationService
from dualexis.evaluation.metrics import (
    EvaluationMetricSet,
    compute_experiment_metrics,
    compute_metrics,
)
from dualexis.evaluation.models import (
    DEFAULT_METRIC_TARGETS,
    EVALUATION_LAYER,
    EvaluationMetric,
    EvaluationPhase,
    LayerMetadata,
    MetricTarget,
)
from dualexis.evaluation.protocol import (
    ExperimentProtocol,
    ExperimentProtocolId,
    UnknownProtocolError,
    execute_protocol,
    get_protocol,
    list_protocols,
)
from dualexis.evaluation.report import EvaluationReport, format_report_summary, run_evaluation
from dualexis.evaluation.results import (
    SCAFFOLD_DISCLAIMER,
    ExperimentMetrics,
    ExperimentReport,
    format_experiment_summary,
)
from dualexis.evaluation.service import PlaceholderEvaluationService

__all__ = [
    "DEFAULT_METRIC_TARGETS",
    "EVALUATION_LAYER",
    "SCAFFOLD_DISCLAIMER",
    "Baseline",
    "BaselineId",
    "BaselineOutput",
    "DualexisSemanticBaseline",
    "EvaluationMetric",
    "EvaluationMetricSet",
    "EvaluationPhase",
    "EvaluationReport",
    "EvaluationService",
    "ExperimentMetrics",
    "ExperimentProtocol",
    "ExperimentProtocolId",
    "ExperimentReport",
    "LayerMetadata",
    "MetricTarget",
    "PlaceholderEvaluationService",
    "RuleBasedFusionBaseline",
    "SingleModalityBaseline",
    "UnknownBaselineError",
    "UnknownProtocolError",
    "compute_experiment_metrics",
    "compute_metrics",
    "execute_protocol",
    "format_experiment_summary",
    "format_report_summary",
    "get_baseline",
    "get_protocol",
    "list_baselines",
    "list_protocols",
    "run_evaluation",
    "run_experiment",
]
