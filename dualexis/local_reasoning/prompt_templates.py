"""Privacy-preserving prompt templates for local reasoning (L5).

Templates serialize only structured semantic events, graph context, safety
constraints, and closed protocol vocabularies. Raw media never appears.
"""

from __future__ import annotations

import json

from dualexis.local_reasoning.models import LocalReasoningInput

SYSTEM_PROMPT = """You are a safety orchestration copilot for DUALEXIS.

Rules:
- Use ONLY the structured JSON context provided below.
- Never infer or request raw video, raw audio, images, biometrics, or identities.
- Ground every recommendation in cited semantic event IDs and zone topology.
- Recommendations are advisory; flag uncertainty and human review when risk is elevated.
- Prefer applicable protocols from the closed vocabulary when selecting actions.
"""

USER_PROMPT_TEMPLATE = """Analyze the structured safety context below and produce \
an advisory recommendation.

Anchor event:
{anchor_event_json}

Context events ({context_count}):
{context_events_json}

Temporal graph snapshot:
{graph_context_json}

Active safety constraints:
{constraints_json}

Available protocols:
{protocols_json}

Respond with JSON containing: recommendation, rationale, confidence (0-1),
required_human_review, uncertainty_notes, cited_event_ids.
"""


def build_structured_prompt(reasoning_input: LocalReasoningInput) -> str:
    """Build a privacy-preserving prompt from structured reasoning input only."""
    anchor_json = json.dumps(
        reasoning_input.anchor_event.model_dump(mode="json"),
        indent=2,
        sort_keys=True,
    )
    context_json = json.dumps(
        [event.model_dump(mode="json") for event in reasoning_input.context_events],
        indent=2,
        sort_keys=True,
    )
    graph_json = (
        json.dumps(reasoning_input.graph_context.model_dump(mode="json"), indent=2, sort_keys=True)
        if reasoning_input.graph_context is not None
        else "{}"
    )
    constraints_json = json.dumps(
        [item.model_dump(mode="json") for item in reasoning_input.safety_constraints],
        indent=2,
        sort_keys=True,
    )
    protocols_json = json.dumps(
        [item.model_dump(mode="json") for item in reasoning_input.available_protocols],
        indent=2,
        sort_keys=True,
    )

    user_prompt = USER_PROMPT_TEMPLATE.format(
        anchor_event_json=anchor_json,
        context_count=len(reasoning_input.context_events),
        context_events_json=context_json,
        graph_context_json=graph_json,
        constraints_json=constraints_json,
        protocols_json=protocols_json,
    )
    return f"{SYSTEM_PROMPT.strip()}\n\n{user_prompt.strip()}\n"
