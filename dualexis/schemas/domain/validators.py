"""Shared validators for privacy-preserving domain schemas."""

from __future__ import annotations

from typing import Any

FORBIDDEN_FIELD_TERMS: frozenset[str] = frozenset(
    {
        "face",
        "facial",
        "biometric",
        "identity",
        "person_id",
        "student_id",
        "speaker_id",
        "face_embedding",
        "voice_print",
    }
)

FORBIDDEN_EVIDENCE_KEYS: frozenset[str] = frozenset(
    {
        "raw_video",
        "raw_audio",
        "frame_data",
        "biometric",
        "face_embedding",
        "media_url",
        "persistent_media_ref",
    }
)

FORBIDDEN_LABEL_TERMS: frozenset[str] = frozenset(
    {
        "face",
        "identity",
        "person_name",
        "student",
        "speaker_id",
    }
)


def contains_forbidden_term(value: str) -> str | None:
    """Return the matched forbidden term if present in *value*, else None."""
    lower = value.lower()
    for term in FORBIDDEN_FIELD_TERMS | FORBIDDEN_LABEL_TERMS:
        if term in lower:
            return term
    return None


def validate_label_tuple(labels: tuple[str, ...]) -> tuple[str, ...]:
    for label in labels:
        for term in FORBIDDEN_LABEL_TERMS:
            if term in label.lower():
                msg = f"Label '{label}' contains forbidden identity-related term '{term}'"
                raise ValueError(msg)
    return labels


def validate_metadata_dict(metadata: dict[str, Any]) -> dict[str, Any]:
    for key in metadata:
        matched = contains_forbidden_term(key)
        if matched is not None:
            msg = f"Metadata key '{key}' contains forbidden term '{matched}'"
            raise ValueError(msg)
    return metadata


def validate_evidence_dict(evidence: dict[str, Any]) -> dict[str, Any]:
    for key in evidence:
        if key.lower() in FORBIDDEN_EVIDENCE_KEYS:
            msg = (
                f"Evidence key '{key}' is not permitted — "
                "no raw media or persistent media references"
            )
            raise ValueError(msg)
        matched = contains_forbidden_term(key)
        if matched is not None:
            msg = f"Evidence key '{key}' contains forbidden term '{matched}'"
            raise ValueError(msg)
    return evidence
