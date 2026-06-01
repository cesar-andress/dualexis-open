"""E2 leakage audit — quantify procedural vs distributional independence."""

from dualexis.leakage_audit.audit import run_leakage_audit
from dualexis.leakage_audit.models import LeakageAuditReport
from dualexis.leakage_audit.scoring import BENCHMARK_DISCLOSURE

__all__ = ["BENCHMARK_DISCLOSURE", "LeakageAuditReport", "run_leakage_audit"]
