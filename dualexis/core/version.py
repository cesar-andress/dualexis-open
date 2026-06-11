"""Package version - single source of truth for DUALEXIS releases."""

from __future__ import annotations

__version__ = "1.0.4"


def get_version() -> str:
    """Return the current DUALEXIS package version string."""
    return __version__
