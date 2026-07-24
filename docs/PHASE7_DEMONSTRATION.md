# Phase 7 1,000-field demonstration

## Reproducibility identity

This verification run used package/model version `0.7.0`, generation seed
`20260721`, population configuration hash
`db293bbf11f3ba8b39c0b34c22636b2f2f4742d1379319e2de845fcba9b643ee`,
model configuration hash
`d59e9af2cd913dd0ef179f825b4343076fb355574b02d9fdaba5eb71e65123ce`,
dataset `phase7_local_joint_seed_fixture@1.0.0` and adapter
`versioned_local_yaml@1.0.0`.

The deterministic population hash was:

`b1c2d39b6a7cab26f045bc367bafd19afc7a10cac44deab352ab81f0a7fde9fd`

The run can be reproduced with:

```bash
uv run soil-simulator generate-population --count 1000 --seed 20260721
uv run soil-simulator run-population-batch --count 1000 --seed 20260721
```

## Generation and QC

- Accepted fields: 1,000
- Rejected candidates: 1
- Rejection reason: one `spinup_not_converged`
- Accepted fields with converged spin-up: 1,000/1,000
- Maximum accepted spin-up length: 800 repeated years
- Maximum accepted periodic relative change: `1.999974e-5`
- Phase 6 eligible-policy trajectories: 6,401
- Simulator failures: 0
- Maximum monthly carbon residual: `4.263256e-14 t C ha-1`
- Maximum monthly phosphorus residual: `1.421085e-14 kg P ha-1`

## Descriptive distributions

| Variable | Min | P05 | Mean | Median | P95 | Max |
|---|---:|---:|---:|---:|---:|---:|
| Clay (%) | 5.853 | 7.944 | 25.575 | 25.379 | 47.065 | 54.510 |
| Silt (%) | 14.245 | 16.737 | 33.132 | 35.086 | 46.155 | 52.221 |
| Sand (%) | 16.045 | 18.808 | 41.293 | 31.534 | 75.232 | 78.892 |
| pH | 5.210 | 5.633 | 6.488 | 6.553 | 7.111 | 7.454 |
| SOC (t C ha-1) | 22.542 | 29.176 | 56.187 | 51.112 | 100.887 | 122.500 |
| Bulk density (g cm-3) | 1.021 | 1.141 | 1.359 | 1.370 | 1.544 | 1.682 |
| Available P (kg P ha-1) | 3.375 | 4.499 | 21.145 | 20.809 | 40.930 | 48.750 |
| Live AMF C (t C ha-1) | 0.0154 | 0.0238 | 0.0803 | 0.0780 | 0.1470 | 0.2224 |
| Mean temperature (deg C) | 9.067 | 9.067 | 10.458 | 10.433 | 11.567 | 11.567 |
| Annual rainfall (mm) | 464.0 | 464.0 | 685.3 | 663.0 | 910.5 | 932.0 |
| Annual PET (mm) | 461.0 | 461.0 | 545.0 | 542.5 | 628.0 | 628.0 |

## Correlations and group composition

Pearson correlations across accepted fields were:

- clay--SOC: `+0.8674`
- clay--bulk density: `-0.8202`
- SOC--bulk density: `-0.9552`
- SOC--live AMF C: `+0.6081`
- available P--live AMF C: `-0.4895`
- annual rainfall--annual PET: `-0.8242`

These directions partly reflect designed Phase 7 assumptions A033--A034 and
seed/archetype separation. They are not independently learned empirical
relationships.

Archetype counts were 201 low-carbon sandy, 200 clay-rich high-carbon, 200
phosphorus-limited, 199 drought-prone and 200 intensively tilled low-AMF fields.
The one rejected candidate caused the small 201/199 imbalance. Split counts
were exactly 600 train, 200 validation and 200 test. Every perturbation from an
empirical seed remained in one split.

## Phase 6 intervention comparison

No policy is ranked or recommended. Mean paired differences use only fields
eligible for that policy and compare its 24-month result with the same field's
baseline.

| Policy | Trajectories | Mean yield (t DM ha-1) | Mean protected-proxy difference (t C ha-1) | Mean yield difference (t DM ha-1) |
|---|---:|---:|---:|---:|
| Baseline | 1,000 | 1.6526 | 0.0000 | 0.0000 |
| Conventional tillage | 800 | 1.8661 | -0.04469 | -0.00064 |
| Reduced tillage | 1,000 | 1.6524 | -0.00284 | -0.00020 |
| No-till marker | 1,000 | 1.6526 | 0.0000 | 0.0000 |
| Cover crop | 1,000 | 1.6508 | +0.05872 | -0.00179 |
| Available-P application | 601 | 2.2239 | +0.07213 | +1.03910 |
| Farmyard manure | 1,000 | 1.8463 | +0.10059 | +0.19369 |

Different eligible subsets explain why unpaired policy mean yields cannot be
compared directly. No-till is an explicit Phase 6 null-effect marker apart from
cost metadata. The intervention directions are encoded model implications,
not causal agronomic evidence.

## Interpretation boundary

This run verifies deterministic generation, internal coherence, manifest
traceability, Phase 6 execution and numerical carbon/P conservation. The local
fixture is not representative empirical sampling, `protected_soc_c` is not
measured MAOC, and none of these results validates field outcomes or supports
recommendations.
