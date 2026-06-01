# DUALEXIS Formal Threat Model

This document specifies a formal threat model for **DUALEXIS**: a privacy-preserving
semantic orchestration framework for safety-critical situational awareness in
confined spaces.

It complements:

- `docs/privacy.md` and `results_reference/sections/privacy_threats_governance.tex` (privacy, threats, governance; TB1–TB5)
- `results_reference/sections/threats_to_validity.tex` (evaluation validity, not operational security)

The threat model is **normative** for the reference architecture. It does **not**
claim field-validated security or safety effectiveness.

---

## Scope and explicit non-capabilities

DUALEXIS supports accountable staff review via zone-level semantic events and
**advisory** recommendations. The following are **out of scope**:

| Non-capability | Statement |
| -------------- | --------- |
| Individual identification | **DUALEXIS does not identify individuals.** Outputs reference zones and aggregate descriptors only. |
| Psychological-state inference | **DUALEXIS does not infer psychological states**, intent, or mental-health conditions. |
| Predictive policing | **DUALEXIS does not perform predictive policing**, pre-crime scoring, or longitudinal occupant risk profiling. |
| Autonomous enforcement | **DUALEXIS does not autonomously enforce actions** (physical intervention, access control, disciplinary workflow initiation, or punitive measures). |

Violations of these constraints are **misuse scenarios**, not intended framework behavior.

---

## 1. System assumptions

| ID | Assumption |
| -- | ---------- |
| **A1** | Processing occurs within a governed confined-space topology with registered zone identifiers. |
| **A2** | Raw video and audio exist only in ephemeral edge buffers with TTL enforcement (TB1); persistent media is disabled by default. |
| **A3** | Authorized staff access semantic events for safety review; insiders may misconfigure but are not modeled as omniscient adversaries of all layers. |
| **A4** | `PrivacyPolicy` objects are version-controlled; weakening default `strict-v1` requires explicit, auditable change. |
| **A5** | Elevated-severity recommendations require human review before operational follow-up. |
| **A6** | Edge nodes operate in governed enclaves; egress is limited to structured events passing TB5 filters. |

Assumptions may fail under misconfiguration or adversarial deployment.

---

## 2. Threat actors

| Actor | Capability | Objectives |
| ----- | ---------- | ---------- |
| **External attacker** | Network access to edge APIs or federation bus | Inject false events, exfiltrate logs, disrupt availability |
| **Malicious insider** | Operator or administrator privileges | Misconfigure policies, improper export, suppress alerts |
| **Sensor adversary** | Physical/RF access to cameras, microphones, IoT | Spoof modalities, blind sensors, adversarial perturbations |
| **Downstream integrator** | Code modification outside core invariants | Re-enable identity features, bypass review, automate enforcement |
| **Curious occupant** | Limited observational knowledge | Infer monitoring scope (not modeled as breaking crypto roots) |

Schema validators and fail-closed privacy checks mitigate **accidental** misconfiguration; they do not guarantee resistance to a fully compromised administrator.

---

## 3. Trust boundaries

Trust boundaries TB1–TB5 structure transitions from ephemeral input to auditable semantic publication (`results_reference/sections/privacy_threats_governance.tex`):

| Boundary | Control |
| -------- | ------- |
| **TB1** | Ephemeral buffer — raw media must not persist beyond TTL |
| **TB2** | Perception validation — only zone-level signals enter fusion |
| **TB3** | Event publication — `SemanticEvent` privacy and retention validation |
| **TB4** | Reasoning input — LLM receives structured events and graph context only |
| **TB5** | Egress — structured events and audit metadata only; no raw media |

Compromise upstream of a boundary may propagate unless downstream gates detect violations.

---

## 4. Privacy threats

| ID | Threat | Description |
| -- | ------ | ----------- |
| **P1** | Identity re-identification | Covert identity metadata + timestamps enable linkage |
| **P2** | Raw-media retention | TTL misconfiguration or crash dumps retain frames/audio |
| **P3** | Cross-session profiling | Longitudinal event storage without purpose limitation |
| **P4** | LLM prompt leakage | Unstructured logs in reasoning inputs leak context |
| **P5** | Audit log exposure | Over-broad access or tampering of audit trails |

Mitigations: schema rejection, TB1–TB5 gates, default `strict-v1` policy, DPIA templates.

---

## 5. Failure scenarios and operational limitations

### False positives

Noisy or ambiguous descriptors may yield high-severity events without ground truth,
increasing review burden and alert fatigue if workflows are not calibrated.

### Missing modalities

Audio, video, or sensor dropout reduces fusion confidence and may hide multimodal
conflicts. Robustness probes (`modality_drop_tolerance`) do not guarantee all edge cases.

### Adversarial inputs

Crafted visual or acoustic patterns may trigger spurious signals. DUALEXIS does not
claim adversarial robustness certification in v0.1.

### Noisy sensor streams

Occlusion, drift, and environmental noise degrade descriptors and propagate
uncertainty into fusion and graph confidence.

### Graph inconsistencies

Stale occupancy, timestamp conflicts, or incomplete topology yield inconsistent
temporal subgraphs for local reasoning.

### Hallucination risks in local reasoning

Local LLMs may produce plausible but incorrect explanations despite grounding checks.
TB4 filters and mandatory human review mitigate but do not eliminate impact.

### Edge-node failure modes

Crash, resource exhaustion, clock skew, or network partition may delay publication,
lose ephemeral buffers, or duplicate events if idempotency is misconfigured.

| Scenario | Layers | Effect |
| -------- | ------ | ------ |
| False positive | L2–L6 | Unnecessary review; alert fatigue |
| Modality dropout | L2–L3 | Reduced confidence; delayed detection |
| Adversarial spoof | L2 | Spurious events if perception fails |
| Noisy descriptors | L2–L3 | Severity/confidence variance |
| Graph inconsistency | L4–L5 | Incorrect reasoning context |
| LLM hallucination | L5 | Ungrounded explanation (advisory only) |
| Edge node crash | L1–L2 | Event loss in ephemeral window |
| Policy misconfiguration | L1 | Privacy bypass (integrator responsibility) |

---

## 6. Misuse scenarios

| ID | Misuse | Description |
| -- | ------ | ----------- |
| **M1** | Surveillance repurposing | Persist raw media despite TB1/TB5 |
| **M2** | Identity analytics overlay | Attach face recognition upstream of fusion |
| **M3** | Automated enforcement | Wire recommendations to locks/alarms without review |
| **M4** | Predictive profiling | Longitudinal occupant risk scores from event history |
| **M5** | Psychological labeling | Map descriptors to mental-state or intent categories |

Documentation and validators raise the cost of casual misuse; **institutional governance remains necessary**.

---

## 7. Human oversight assumptions

| ID | Assumption |
| -- | ---------- |
| **H1** | Staff interpret zone-level events without assuming individual identification |
| **H2** | Medium+ severities require `requires_human_review`; no automated actuation |
| **H3** | Review workflows record disposition for audit |
| **H4** | Institutions maintain escalation paths independent of the framework |
| **H5** | Periodic calibration of false-positive rates and modality-drop tolerance |

Failure of H1–H5 shifts residual risk to organizational process.

---

## Implementation references

| Component | Location |
| --------- | -------- |
| Privacy runtime | `dualexis/privacy_runtime/` |
| Schema validators | `dualexis/schemas/domain/validators.py` |
| Semantic events | `dualexis/semantic_events/models.py` |
| Local reasoning | `dualexis/local_reasoning/` |
| Orchestration | `dualexis/orchestration/` |

---

## Related evaluation

Threat categories inform metrics in `docs/evaluation.md` and the pre-registered
protocol in `results_reference/sections/evaluation_plan.tex`. Empirical validation of
mitigations under adversarial and field conditions remains future work
(`results_reference/sections/future_work.tex`).
