# L1: Privacy Runtime Layer

Cross-cutting privacy enforcement for the DUALEXIS six-layer framework.

## Purpose

Validate and gate all data crossing trust boundaries **TB1–TB5** before perception fusion, event publication, LLM reasoning, or network egress. DUALEXIS processes **events**, not identities.

## Inputs

- `PerceptionFrame` — ephemeral edge buffers (TB1)
- `PerceptionSignal` — zone-level perception outputs (TB2)
- `SafetyEvent` — structured semantic events (TB3)
- Arbitrary egress payloads (TB4/TB5)
- `PrivacyPolicy` — machine-readable retention and minimization rules

## Outputs

- Validated frames, signals, and events (unchanged if compliant)
- `PrivacyCheckResult` — pass/fail at each boundary
- `PrivacyViolationError` on forbidden content

## Privacy constraints

- No facial recognition or biometric feature fields
- No student profiling or persistent identity linkage
- No persistent raw media storage paths in events
- Rejects forbidden keys in signals, evidence, and egress payloads

## Future implementation plan

- Pluggable policy packs for institutional DPIA templates
- Automated buffer TTL enforcement hooks with audit correlation
- Federated egress validation for cross-node event exchange
- Formal verification tests against adversarial schema fuzz corpora

## Module map

| File | Role |
| ---- | ---- |
| `interfaces.py` | `PrivacyRuntimeService` ABC |
| `models.py` | Trust boundaries, forbidden key sets, layer metadata |
| `service.py` | `DefaultPrivacyRuntimeService` (placeholder-grade runtime guard) |

## Usage

```python
from dualexis.privacy_runtime import DefaultPrivacyRuntimeService

runtime = DefaultPrivacyRuntimeService()
runtime.validate_frame(frame)
```
