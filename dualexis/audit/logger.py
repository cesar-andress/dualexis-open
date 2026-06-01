"""In-memory audit logger with integrity hashing."""

from __future__ import annotations

import hashlib
import json

from dualexis.core.interfaces import AuditLogger
from dualexis.schemas.audit import AuditEntry


class InMemoryAuditLogger(AuditLogger):
    """Append-only in-memory audit store for development and testing."""

    def __init__(self, max_entries: int = 10_000) -> None:
        self._entries: list[AuditEntry] = []
        self._max_entries = max_entries

    async def log(self, entry: AuditEntry) -> None:
        integrity_hash = self._compute_hash(entry)
        stored = entry.model_copy(update={"integrity_hash": integrity_hash})
        self._entries.append(stored)
        if len(self._entries) > self._max_entries:
            self._entries = self._entries[-self._max_entries :]

    async def query(
        self,
        *,
        event_id: str | None = None,
        limit: int = 100,
    ) -> list[AuditEntry]:
        results = self._entries
        if event_id is not None:
            results = [e for e in results if e.event_id is not None and str(e.event_id) == event_id]
        return results[-limit:]

    def _compute_hash(self, entry: AuditEntry) -> str:
        payload = entry.model_dump(mode="json", exclude={"integrity_hash"})
        encoded = json.dumps(payload, sort_keys=True, default=str)
        return hashlib.sha256(encoded.encode()).hexdigest()
