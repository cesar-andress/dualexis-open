# External Dataset Adapters

DUALEXIS provides **adapter interfaces only** for well-known public datasets.
Adapters read user-supplied local annotation or metadata files and convert records
into `SemanticEvent` objects where mapping is possible.

Adapters **do not download** datasets, **do not** load raw video or audio bytes,
and **do not** imply ethics approval for a specific institution.

Implementation: `dualexis/datasets/`.

## Quick start

```python
from pathlib import Path
from dualexis.datasets import DatasetId, get_dataset_adapter

result = get_dataset_adapter(DatasetId.VADERE).adapt(
    Path("exports/vadere/summary/")
)
print(result.converted_count, result.skipped_count)
```

## Adapter registry

| Dataset | Adapter ID | Modalities | Typical roles |
| ------- | ---------- | ---------- | ------------- |
| UCF-Crime | `ucf_crime` | video | benchmarking, validation |
| ShanghaiTech Campus | `shanghaitech_campus` | video | benchmarking, validation |
| DCASE audio | `dcase_audio` | audio | training*, benchmarking, validation |
| Vadere outputs | `vadere` | simulation | training, validation, benchmarking |

\*Training use only when the original dataset license permits and privacy review is complete.

---

## UCF-Crime

### Purpose

Surveillance anomaly classification benchmark. Maps clip-level crime category
labels (Fighting, Explosion, etc.) to coarse DUALEXIS `EventType` values for
protocol development.

### Privacy risks

- Source videos contain identifiable persons and sensitive criminal acts.
- **Never** load raw UCF-Crime video into DUALEXIS.
- Use annotation exports only under institutional review.

### Allowed usage

- Offline benchmarking of event-mapping and fusion protocols.
- Validation of evaluation harness wiring.
- **Not** for training identity-linked perception inside DUALEXIS.

### Limitations

- Generic zone (`surveillance-zone`); no spatial calibration.
- Many classes map to `EventType.UNKNOWN` and are skipped.
- Timestamps are approximate when not provided in annotations.

### Local file format

Place `annotations.csv` under the dataset root:

```csv
class_name,video_id,start_seconds,end_seconds
Fighting,Fighting001_x264,10.0,25.0
```

Alternative: `annotations.txt` with `Class/Video.mp4` lines.

### Supported roles

**Benchmarking**, **validation** — not training.

---

## ShanghaiTech Campus

### Purpose

Campus CCTV anomaly detection benchmark. Converts frame-level anomaly indicators
into zone-scoped semantic events.

### Privacy risks

- Campus footage may identify students and staff.
- Adapter consumes CSV annotation tables only.

### Allowed usage

- Benchmarking anomaly-detection pipelines on semantic events.
- Validation under ethics-approved research agreements.

### Limitations

- Single generic zone (`campus-zone`).
- Normal frames are skipped (`label=normal`).
- Frame indices mapped to synthetic timestamps without camera metadata.

### Local file format

`annotations.csv`:

```csv
video_id,frame_index,timestamp_seconds,label
01_0014,100,3.33,anomaly
```

### Supported roles

**Benchmarking**, **validation** — not training.

---

## DCASE audio datasets

### Purpose

DCASE challenge metadata (scene / event labels) for audio-modality benchmarking.
Stress-related labels map to `AUDIO_STRESS_SIGNAL`.

### Privacy risks

- Field recordings may capture voices and identifiable ambient sound.
- Metadata-only ingestion; no raw audio persistence in DUALEXIS.

### Allowed usage

- Benchmarking audio fusion and modality-dropout robustness.
- Training **only** when license permits and under privacy review.

### Limitations

- Label taxonomy varies by DCASE task and year; unmapped labels skipped.
- Generic acoustic zone unless extended columns provide spatial context.

### Local file format

`metadata.tsv` (tab-separated):

```text
filename	start_seconds	end_seconds	scene_label
stress_clip.wav	2.5	8.0	scream
```

Mapped stress labels include: `scream`, `gun_shot`, `glass_breaking`, `siren`,
`alarm`, `distress`, `anomaly`, `stress`.

### Supported roles

**Training** (license-dependent), **benchmarking**, **validation**.

---

## Vadere simulation outputs

### Purpose

Microscopic pedestrian simulation exports. Zone-level density and flow signals
align with DUALEXIS synthetic simulation benchmarks.

### Privacy risks

- Low when using zone-aggregated JSON summaries.
- Agent-level trajectories may enable re-identification if exported with persistent IDs;
  prefer zone metrics.

### Allowed usage

- Training scenario generators and graph-reasoning tests.
- Validation and benchmarking under synthetic-only posture.

### Limitations

- Expects pre-summarized JSON (`scenario_output.json`); native Vadere formats
  must be converted externally.
- Zone names must be aligned with confined-space topology manually.

### Local file format

`scenario_output.json`:

```json
{
  "scenario": "exit_blockage",
  "events": [
    {"zone": "exit-a", "type": "exit_blocked", "time": 45.0, "value": 0.82}
  ]
}
```

Supported `type` values include: `density_spike`, `exit_blocked`, `multimodal_conflict`,
`evacuation_signal`, `normal_flow`.

### Supported roles

**Training**, **validation**, **benchmarking**.

---

## Related documentation

- `docs/evaluation.md` — experimental protocols and baselines
- `docs/simulation.md` — native DUALEXIS synthetic scenarios
- `docs/privacy.md` — privacy invariants and prohibited data
