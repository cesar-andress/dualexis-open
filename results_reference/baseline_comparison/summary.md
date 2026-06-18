# DUALEXIS baseline comparison (synthetic, independent GT)

> Synthetic empirical battery with independent ground-truth YAML labels. Descriptive statistics over matched seeds; no field deployment, legal compliance, or superiority claims.

Generated: 2026-06-18T18:55:01.925997+00:00
Seeds: 30 (1--30)

## B1--B5 aggregates (mean detection accuracy)

| Baseline | Scenario | Acc. mean | FPR mean | FNR mean | Expl. mean |
| -------- | -------- | --------- | -------- | -------- | ---------- |
| B1 | audio_stress_signal | 1.000 | 0.000 | 0.000 | 1.000 |
| B1 | crowd_acceleration | 1.000 | 0.000 | 0.000 | 1.000 |
| B1 | evacuation_recommendation | 1.000 | 0.000 | 0.000 | 1.000 |
| B1 | exit_blockage | 1.000 | 0.000 | 0.000 | 1.000 |
| B1 | multimodal_conflict | 1.000 | 0.000 | 0.000 | 1.000 |
| B1 | normal_flow | 1.000 | 0.000 | 0.000 | 1.000 |
| B2 | audio_stress_signal | 0.075 | 0.000 | 0.925 | 0.800 |
| B2 | crowd_acceleration | 0.098 | 0.000 | 0.902 | 1.000 |
| B2 | evacuation_recommendation | 0.100 | 0.000 | 0.900 | 1.000 |
| B2 | exit_blockage | 0.080 | 0.000 | 0.920 | 0.800 |
| B2 | multimodal_conflict | 0.080 | 0.000 | 0.920 | 0.800 |
| B2 | normal_flow | 0.000 | 0.000 | 1.000 | 0.000 |
| B3 | audio_stress_signal | 1.000 | 0.000 | 0.000 | 1.000 |
| B3 | crowd_acceleration | 1.000 | 0.000 | 0.000 | 1.000 |
| B3 | evacuation_recommendation | 1.000 | 0.000 | 0.000 | 1.000 |
| B3 | exit_blockage | 1.000 | 0.000 | 0.000 | 1.000 |
| B3 | multimodal_conflict | 1.000 | 0.000 | 0.000 | 1.000 |
| B3 | normal_flow | 1.000 | 0.000 | 0.000 | 1.000 |
| B4 | audio_stress_signal | 0.000 | 1.000 | 1.000 | 0.000 |
| B4 | crowd_acceleration | 0.000 | 1.000 | 1.000 | 0.000 |
| B4 | evacuation_recommendation | 0.000 | 1.000 | 1.000 | 0.000 |
| B4 | exit_blockage | 0.000 | 1.000 | 1.000 | 0.000 |
| B4 | multimodal_conflict | 0.000 | 1.000 | 1.000 | 0.000 |
| B4 | normal_flow | 0.000 | 1.000 | 1.000 | 0.000 |
| B5 | audio_stress_signal | 1.000 | 0.000 | 0.000 | 1.000 |
| B5 | crowd_acceleration | 1.000 | 0.000 | 0.000 | 1.000 |
| B5 | evacuation_recommendation | 1.000 | 0.000 | 0.000 | 1.000 |
| B5 | exit_blockage | 1.000 | 0.000 | 0.000 | 1.000 |
| B5 | multimodal_conflict | 1.000 | 0.000 | 0.000 | 1.000 |
| B5 | normal_flow | 1.000 | 0.000 | 0.000 | 1.000 |

## Layer ablations (exit_blockage)

| Condition | Acc. mean | Expl. mean | Privacy viol. mean |
| --------- | --------- | ---------- | ------------------ |
| Full reference pipeline (B5) | 1.000 | 1.000 | 0.0 |
| No L1 privacy runtime | 1.000 | 1.000 | 0.0 |
| No L4 temporal graph | 1.000 | 1.000 | 0.0 |
| No L5 explanation layer | 1.000 | 0.000 | 0.0 |

> Privacy fuzz battery on representative payloads. Reports pass/fail for fail-closed validation only; not a certification audit.

