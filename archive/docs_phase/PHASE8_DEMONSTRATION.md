# Phase 8 1,000-field ML demonstration

> Historical v0.8.0 result. Phase 8.5 supersedes this benchmark because the
> ten-group split, 24-month carbon horizon and row-wise uncertainty calibration
> were inadequate. See `PHASE85_DIAGNOSTIC.md`. Do not use this file to justify
> intervention selection.

## Reproducibility identity

This synthetic benchmark used package/model version `0.8.0`, Phase 7
generation seed `20260721`, population hash
`b1c2d39b6a7cab26f045bc367bafd19afc7a10cac44deab352ab81f0a7fde9fd`,
model-configuration hash
`67b7404c98e79f4acf2f0973b2d1b40ac250f5374c1ad17c61d7bbfcc27307da`
and Phase 8 dataset hash
`f23489fc62b7a5964cbd4706b0c43ba04ba10ba4046ea9cc50c253b36b67b941`.

The exported dataset contains 6,401 field-policy-horizon rows from 1,000
accepted fields and ten empirical-seed groups. Frozen field counts are 600
train, 200 validation and 200 test; row counts are 3,801, 1,200 and 1,400
because policy eligibility differs. There were no exact or configured
near-duplicate field pairs.

The validation-selected primary model is observable regularised linear
regression with alpha `0.01`; its validation mean normalised RMSE is
`0.34125`. The observable tree comparator scored `0.46340`, so it was not
selected. The full-state diagnostic also selected ridge (`0.30929`). Main
training/tuning took 68.57 seconds and OOD refits took 5.77 seconds on the
recorded local run.

Primary deterministic model hashes include:

- observable ridge:
  `288127b18c480b495f00a9bb21e06bb887212e40637ec167c2231ef558af7e80`;
- observable forest:
  `e3db6725758b51c13abf57b74476461f6053b1e2adfd94139441b2573a841202`;
- full-state ridge:
  `1508018bd0e5281b6ad1de6568285939af157f0f2fd873c04c6b0e6f1329ef55`.

## Ordinary held-out results

Selected results from the 200-field test groups are:

| Target | Observable ridge MAE | RMSE | R-squared | MAE / test SD |
|---|---:|---:|---:|---:|
| Final total SOC | 2.5340 | 2.5400 | 0.9328 | 0.2586 |
| Final protected-SOC proxy | 0.6287 | 0.6347 | 0.9932 | 0.0819 |
| Crop yield | 0.6262 | 0.6722 | -1.5718 | 1.4938 |
| Cumulative respiration | 2.1495 | 2.1695 | -9.1343 | 3.1540 |
| Final available P | 4.0169 | 4.3091 | 0.6570 | 0.5459 |
| Paired total-SOC effect | 0.2004 | 0.2331 | 0.4331 | 0.6472 |
| Paired protected-proxy effect | 0.03667 | 0.04219 | 0.4385 | 0.6512 |
| Paired yield effect | 0.2323 | 0.2789 | -1.0528 | 1.1932 |

Units are defined in the dataset manifest and `ML_BENCHMARKING.md`. Cost and
emissions are almost exactly recovered from policy identity. Good final SOC
stock prediction does not imply good intervention-effect, yield or respiration
prediction. In particular, the policy-mean baseline achieved R-squared
`0.809` for the paired protected-proxy effect, exceeding the primary ridge's
`0.439`. The nonlinear observable tree failed to extrapolate final stocks to
the held-out seed groups (final-SOC R-squared `-18.4`). This benchmark therefore
does not establish that nonlinear ML improves on transparent baselines.

## Uncertainty calibration

Nominal 90% split-conformal intervals calibrated on validation groups were not
well calibrated on the two held-out empirical-seed groups. Coverage was:

- final total SOC: `0.000` (mean width `1.168 t C ha-1`);
- final protected proxy: `0.020` (width `0.958 t C ha-1`);
- yield: `0.323` (width `1.030 t DM ha-1`);
- cumulative respiration: `0.000` (width `1.781 t C ha-1`);
- final available P: `0.349` (width `6.842 kg P ha-1`);
- paired protected-proxy effect: `0.611` (width `0.0656 t C ha-1`);
- paired yield effect: `0.879` (width `0.767 t DM ha-1`).

Mean coverage across all fourteen targets was about 56.1%, far below nominal.
This failure is visible rather than repaired with test outcomes. It indicates
that validation residuals are not exchangeable with this small group-held-out
test set and that the current intervals must not be used for decisions.

## Hidden-state and engineered-correlation dependence

Relative to the observable ridge, full-state ridge reduced MAE by 78.4% for
final total SOC, 92.7% for final protected proxy, 27.8% for paired total-SOC
effect and 32.3% for paired protected-proxy effect. Full state made yield and
final-P errors worse in this test. Apparent stock/effect performance therefore
depends materially—but not uniformly—on hidden simulator information.

On held-out fields, deterministic correlation disruption produced:

- clay--SOC: correlation `+0.299` to `-0.138`; mean normalised RMSE worsened
  30.7%;
- SOC--bulk density: `-0.991` to `+0.029`; error worsened only 0.17%;
- available-P--initial-AMF in the full-state diagnostic: `-0.147` to `+0.109`;
  error worsened 1.02%.

The primary model therefore shows material aggregate dependence on baseline SOC
in the clay--SOC audit, but little aggregate dependence on bulk density once SOC
is retained. The full-state model shows little aggregate dependence on the
available-P--AMF pairing under this disruption. These are generator diagnostics,
not empirical biological conclusions.

## Hard generalisation

Mean normalised RMSE for complete archetype holdouts ranged from `0.704` for
clay-rich high-carbon fields to `6.259` for drought-prone fields. Other values
were `4.980` low-carbon sandy, `4.353` intensively tilled low-AMF and `2.479`
phosphorus-limited. Complete weather-regime holdouts scored `24.898` for dry,
`0.925` for temperate and `1.118` for wet. The sampled-boundary diagnostic
included 190 of 200 test fields because the current ten-seed fixture is highly
stratified and the boundary definition uses sampled feature ranges.

These failures show that ordinary held-out metrics overstate robustness to some
archetype and weather shifts. They also show that a ten-group fixture is too
small for precise generalisation or interval claims.

## Interpretation boundary

All outcomes are synthetic model implications. The fixture is not a
representative UK sample, the protected-SOC output is not measured MAOC, and no
result is causal or a recommendation. Phase 8 provides evidence that some
stocks are predictable within the current generator, alongside strong evidence
that effects, crop/respiration targets, uncertainty calibration and harder
generalisation remain inadequate. Full details are in
`outputs/phase8_v0.8.0/evaluation_report.json`.
