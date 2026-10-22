# Phase 8.5 diagnostic demonstration

## Reproducible run

The checked-in v0.8.5 artifacts contain 250 synthetic fields from 50 distinct
synthetic seed groups and 5,250 field-policy-horizon outcomes. Dataset hash:

`f0b43194dc11231f5ecd873832ee13c32eaed2d27dda204572b31d5ba8e639ce`

There were no batch failures. Maximum absolute monthly residuals were
`5.68e-14 t C ha-1` and `1.42e-14 kg P ha-1`. These demonstrate numerical
balance, not empirical validity.

## Revised covariance

Across generated fields, clay--SOC correlation is `-0.185`, SOC--bulk-density
correlation is `-0.059`, and available-P--initial-AMF correlation is `-0.124`.
The extreme Phase 8 SOC--bulk-density relationship is therefore removed in
this fixture. Permuting bulk density changes primary effect error by less than
0.2% in every headline task. Clay/SOC permutation has up to 8.0% degradation;
available-P/AMF permutation has negligible degradation.

These findings only show reduced dependence on the new engineered fixture.
They do not validate the revised covariance against field observations.

## Final-test primary results

| Target/horizon | Nonlinear primary | MAE | R² | MAE / outcome SD |
|---|---|---:|---:|---:|
| yield, 24 months | pooled forest | 0.4673 | 0.3945 | 0.5086 |
| respiration, 5 years | pooled forest | 0.9139 | 0.5886 | 0.4999 |
| respiration, 10 years | pooled forest | 1.0613 | 0.7346 | 0.4042 |
| paired yield effect, 24 months | separate-policy forest | 0.0865 | 0.7856 | 0.1692 |
| paired total-SOC effect, 5 years | separate-policy forest | 0.0395 | 0.9564 | 0.0912 |
| paired total-SOC effect, 10 years | pooled forest | 0.0252 | 0.9769 | 0.0865 |
| paired protected-proxy effect, 5 years | separate-policy forest | 0.0133 | 0.9398 | 0.1238 |
| paired protected-proxy effect, 10 years | separate-policy forest | 0.0078 | 0.9877 | 0.0570 |

Direct yield and respiration remain materially harder than paired effects.
The full-state model reduces respiration MAE by 46.7% at five years and 79.9%
at ten years, evidence that hidden simulator state matters strongly. Full
state does not consistently improve paired effects; its reductions range from
negative values to 10.7%, so it is not a universal upper bound in finite data.

## Baselines and pooled/separate models

The nonlinear primary beats policy mean on aggregate headline effect MAE/SD:
`0.1055` versus `0.1751`. It does not beat the strongest regularised-linear
baseline: the best pooled/separate-policy ridge reaches `0.0811`. In particular,
separate-policy ridge is better than the selected nonlinear model on paired
yield and most carbon-effect tasks. The nonlinear benchmark therefore fails
the predeclared Phase 9 gate despite high in-distribution R².

## Uncertainty

Ten validation seed groups calibrate every primary interval. Final-test
coverage is 94.9% for paired yield and 100% for the four primary carbon-effect
tasks at a 90% nominal level. Corresponding widths are `1.089`, `1.136`,
`0.446`, `0.287` and `0.181` in target units. The carbon intervals are
conservative and wide relative to their MAEs. Small subgroup claims abstain as
configured. Coverage is synthetic residual coverage only.

## Untouched OOD results

Aggregate headline effect MAE/SD is `0.1053` on the complete-archetype holdout
and `0.5212` on the extreme-weather holdout. Individual weather-OOD results are
substantially weaker: paired 10-year total-SOC effect has MAE/SD `0.801` and
R² `-1.574`; paired 10-year protected-proxy effect has MAE/SD `0.591` and R²
`-0.296`; paired 24-month yield effect has MAE/SD `0.591` and R² `-0.841`.
No model was selected from these OOD scores.

## Decision

Phase 9 gates do not all pass. Do not build an ML intervention selector yet.
The next task is the Phase 8.6 evidence-strengthening task in `ROADMAP.md`.
Nothing in this report supports farmer advice, a causal claim or real-field
validity.
