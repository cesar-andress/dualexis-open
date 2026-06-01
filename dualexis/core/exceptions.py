"""Domain-specific exception hierarchy."""


class DUALEXISError(Exception):
    """Base exception for all DUALEXIS errors."""


class PerceptionError(DUALEXISError):
    """Raised when a perception pipeline fails."""


class FusionError(DUALEXISError):
    """Raised when multimodal fusion fails."""


class ReasoningError(DUALEXISError):
    """Raised when local reasoning over structured events fails."""


class PrivacyViolationError(DUALEXISError):
    """Raised when an operation violates privacy policy constraints."""


class OrchestrationError(DUALEXISError):
    """Raised when orchestration or workflow execution fails."""


class FederationError(DUALEXISError):
    """Raised when cross-node federation communication fails."""


class AuditError(DUALEXISError):
    """Raised when audit logging fails."""
