# Phase 8.6 repeated synthetic intervention-effect evidence

## Claim boundary

Every result in this document is measured against synthetic simulator outcomes.
It is non-causal, is not real-field validation and is not an intervention
recommendation. `protected_soc` remains a model proxy, not measured MAOC.
Phase 8.6 does not rank or select interventions and changes no Phase 3--6
biological equation.

## Frozen protocol and population design

Ten development experiments each contain 75 synthetic fields from 75 seed
groups. Foundation and field-population seeds are distinct in every experiment;
five weather-resampling seeds and five latent-biological seeds rotate as
separate streams. In total, the development evidence contains 750 generated
fields and 15,750 field-policy-horizon rows. These are variations of the local
synthetic fixture, not 750 empirical observations.

Each foundation reserves five seed groups for each complete dry, hot, wet, cool
and compound hot-dry weather condition, plus five complete-archetype groups.
The remaining groups retain train, validation and repeated-test roles. The
observable registry is unchanged from Phase 8.5; no hidden pool or latent draw
is exposed.

After all validation distributions, target-specific model families,
hyperparameters, preprocessing, interval widths and applicability decisions
were fixed, `frozen_protocol.json` was written. A new foundation and population
then used four seed commitments absent from development. This final population
has 150 fields and 3,150 rows. Its outcomes did not revise any preceding
decision.

## Predeclared selection

The fixed complexity order is policy mean, pooled ridge, separate-policy ridge,
pooled forest and separate-policy forest. Selection minimises median validation
RMSE divided by outcome SD, then chooses the least complex model within 5% of
the best. R-squared and test/OOD/final outcomes do not select a model. Ridge is
a valid ML model; nonlinear complexity receives no preference.

| Paired-effect task | Selected family | Repeat median MAE/SD | IQR | Best | Worst | Failure frequency vs policy mean | Frozen-final MAE/SD |
|---|---|---:|---:|---:|---:|---:|---:|
| yield, 24 months | separate-policy ridge | 0.1905 | 0.1043 | 0.1110 | 0.4204 | 0% | 0.1222 |
| total SOC, 5 years | separate-policy forest | 0.1274 | 0.0544 | 0.0909 | 0.1692 | 0% | 0.0809 |
| total SOC, 10 years | separate-policy forest | 0.0896 | 0.0287 | 0.0564 | 0.0999 | 10% | 0.0746 |
| protected-SOC proxy, 5 years | separate-policy ridge | 0.1372 | 0.0218 | 0.0833 | 0.1585 | 0% | 0.0832 |
| protected-SOC proxy, 10 years | separate-policy ridge | 0.0807 | 0.0330 | 0.0474 | 0.1370 | 10% | 0.0626 |

Policy-mean median MAE/SD is respectively 0.3283, 0.2041, 0.1093, 0.2426 and
0.1503. The selected model improves on policy mean in all ten repeats for
yield, 5-year total SOC and 5-year protected proxy, and in nine of ten repeats
for both 10-year carbon tasks. Full per-run MAE, RMSE, R-squared, MAE/SD, best
run, worst run and candidate validation distributions are retained in
`evaluation_report.json`.

The untouched final population also improves on policy mean for every task.
Selected-model R-squared values are 0.889 for yield, 0.964 and 0.970 for total
SOC at 5 and 10 years, and 0.968 and 0.983 for the protected proxy. These are
synthetic predictive diagnostics, not biological validation.

## Weather OOD and applicability

Applicability was frozen from development error and independent calibration-
group counts, not from final OOD outcomes. Cool, hot and wet are supported for
all five targets. The domain is target-specific beyond those common regimes:

- yield at 24 months abstains for dry and hot-dry;
- 5-year total-SOC effect supports dry and hot-dry;
- 10-year total-SOC effect supports dry but abstains for hot-dry;
- both protected-proxy effects support dry and hot-dry.

The abstentions are material. On the final population, yield MAE/SD is 1.306 in
dry and 1.133 in hot-dry, with negative R-squared. The 10-year total-SOC effect
has final hot-dry MAE/SD 0.720 and R-squared -1.089. The model must not emit an
uncertainty claim for those combinations. In the universally supported cool,
hot and wet regimes, final MAE/SD ranges from 0.071 to 0.188 across tasks.

## Uncertainty

Absolute residual widths are fitted separately for each target and regime.
Temperate calibration uses 110 namespaced validation seed groups; each
dedicated weather regime uses 50 development OOD seed groups. No final row
calibrates a width or support decision.

At 90% nominal coverage, supported final weather-regime coverage is 0.957 to
1.000. Untouched-core coverage is 0.980 to 0.989. These satisfy the predeclared
0.12 tolerance but remain conservative. Width is a serious limitation: for
example, the supported wet yield interval is 2.50 t dry matter/ha wide despite
a final wet yield-effect MAE of 0.068. Coverage here concerns synthetic
prediction residuals only; it excludes simulator structural error and real-
field uncertainty.

## Gate decision

All revised gates pass:

1. selected observable models beat policy mean at the permitted repeat failure
   frequency;
2. repeated MAE/SD IQR stays below 0.20;
3. all five untouched-final MAE/SD values stay below 0.50 and beat policy mean;
4. supported uncertainty is within tolerance and unsupported combinations
   abstain;
5. cool, hot and wet are supported for all five primary targets;
6. no gate requires a nonlinear model to beat ridge;
7. final outcomes are unused for selection or calibration.

This justifies only a restricted Phase 9 *regret benchmark inside the synthetic
applicability domain*. It does not justify a universal selector, farmer-facing
recommendations or claims outside the simulator.

## Reproducibility

The production run took 839 seconds. Maximum absolute monthly residuals were
5.68e-14 t C/ha and 1.42e-14 kg P/ha. Key hashes are:

- protocol: `ce05594c82f995f0815b806eb34eb78605e84ab2a733595e391d785db9faeb05`;
- frozen decision: `61dc9fcac47109d2ea833ce9763869b0269d7210b394dd52ea2654cd31f3d96a`;
- deterministic report: `f76597a8f4d89929170c1fa564fe06908f1e066394bd622021c02460c274e49e`.

Reproduce with:

```bash
uv run soil-simulator run-phase86-benchmark \
  --output-dir outputs/phase86_v0.8.6
```

