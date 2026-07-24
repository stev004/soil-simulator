# Phase 8.5 synthetic intervention-outcome diagnostics

## Claim boundary

All performance described here is measured against synthetic simulator
outcomes. It is non-causal, is not real-field validation, and must not be used
as an intervention recommendation. `protected_soc` is a model proxy, not
measured MAOC. Phase 8.5 does not select, rank or optimise interventions.

Package, configuration, dataset and artifact version `0.8.5` add no Phase 3--6
biological equation or management effect.

## Population design

The ten Phase 7 local demonstration templates are expanded deterministically
to 50 distinct synthetic seed groups. This is a stress-test foundation, not an
increase in empirical representativeness. Texture, SOC, bulk density,
available P and AMF use diversified donors and independent residuals. The
legacy shared soil factor SD is reduced from `0.10` to `0.035`; its implicit
SOC--bulk-density coefficient is reduced from `0.55` to `0.10`; independent SOC
log SD is `0.11`; independent bulk-density SD is `0.075 g cm-3`; and AMF log SD
is `0.32`. All are scenario assumptions A044--A045.

The default run creates 250 fields. Generation retries rejected candidates
until every seed group is represented. The fixed group partition is:

| Partition | Seed groups | Purpose |
|---|---:|---|
| train | 25 | preprocessing and fitting |
| validation | 10 | hyperparameter selection and interval calibration |
| final test | 5 | one frozen in-distribution evaluation |
| archetype OOD | 5 | complete acidic/low-productivity archetype holdout |
| weather OOD | 5 | complete extreme-dry weather holdout |

No final-test or OOD outcome is used for preprocessing, fitting, selection or
uncertainty calibration.

## Dataset and horizons

`training_dataset_v0.8.5.csv` has one row per field, eligible policy and
simulation horizon. The default artifact has 5,250 rows and 250 fields. Every
row carries field/seed/split metadata, 47 full-state columns and all 14 explicit
direct/paired targets. Target-specific models use only valid horizons:

- crop yield and paired yield effect: 24 months;
- final total SOC, final protected-SOC proxy, cumulative respiration and their
  paired effects: 60 and 120 months;
- available P, cost, emissions and their paired effects: 24, 60 and 120 months.

Paired effects are outcome minus the baseline for the same field and horizon.
A missing or duplicate baseline is fatal. Existing Phase 6 intervention event
dates are retained; events are not silently repeated to fill longer horizons.

## Observable feature audit

The 28-column `observable_features` registry contains routine soil-test-like
properties, baseline total SOC stock and concentration, seasonal climate
indices computed from the forcing available through the requested horizon,
coarse management-history indicators, drainage class, coarse soil-test P
status, policy identity and horizon. The dataset manifest gives a measurement
rationale for every column.

It excludes raw simulator available-P stock, coordinates and region ID,
archetype and weather-regime labels, initial AMF/RothC pools, spin-up state,
latent biological draws, identifiers, split labels and targets. The 47-column
`full_simulator_state` registry adds these hidden mechanistic quantities only
for diagnostic comparison and is never deployable.

## Models and selection

Each target/horizon task compares:

1. global training-target mean;
2. policy-specific training-target mean;
3. pooled ridge;
4. separate ridge per policy;
5. pooled deterministic random forest;
6. separate deterministic random forest per policy.

Ridge strength and forest tree/depth settings use validation groups only. The
reported nonlinear primary is the pooled or separate-policy forest with lower
validation RMSE divided by validation target SD. It is not selected because it
is more complex. A full-state ridge/forest diagnostic is selected separately.
All preprocessors and models are JSON, not executable pickle artifacts.

## Group-aware uncertainty

For each target/horizon, validation residuals are first reduced to one
finite-sample absolute-residual quantile per empirical-seed group. A conformal
rank is then applied across groups, preventing groups with more policy rows
from dominating calibration. The default nominal coverage is 90%. Calibration
claims require at least eight validation groups. Coverage is reported overall
and by empirical seed and archetype; subgroups below the configured row count
explicitly abstain.

These intervals cover synthetic prediction residuals only. They do not cover
simulator structural error, parameter epistemic uncertainty or real fields.

## Diagnostics

Every task reports MAE, RMSE, R-squared, MAE divided by natural outcome SD,
policy/archetype/weather/P-status/seed errors, residual distributions, feature
importance, group-aware interval coverage/width, untouched archetype/weather
OOD errors and the observable/full-state MAE gap. Yield and respiration reports
rank correlations between observable-model residuals and hidden simulator
state as candidate missing-measurement diagnostics, not estimates of true
irreducible error.

Engineered-correlation tests record the population correlation and prediction
degradation after deterministic field-level permutation for clay--SOC,
SOC--bulk density and available-P--AMF. Test outcomes score the frozen model but
never refit it.

## Phase 9 gates

All gates were declared before final evaluation:

1. no final-test/OOD leakage;
2. primary interval coverage within 0.10 of nominal;
3. nonlinear primary effect error below policy mean and the best pooled or
   separate-policy ridge;
4. acceptable effect error on at least one untouched OOD partition;
5. selection not based only on in-distribution R-squared.

The v0.8.5 run passes gates 1, 2, 4 and 5 but fails gate 3. Aggregate primary
effect MAE/SD is `0.1055`, versus `0.1751` for policy mean and `0.0811` for the
best regularised-linear baseline. Therefore an ML intervention selector must
not be built yet.

## Artifacts and commands

The versioned directory contains:

- saved complete population manifest/fields and multi-horizon Phase 6 batch;
- `training_dataset_v0.8.5.csv` and `dataset_manifest.json`;
- training-only observable/full-state preprocessors;
- per-task serialized means, ridge models and forests;
- `evaluation_report.json`, `evaluation_report.md`, `MODEL_CARD.md` and
  `benchmark_table.txt`.

Reproduce the complete run with:

```bash
uv run soil-simulator run-phase85-benchmark \
  --output-dir outputs/phase85_v0.8.5
```

## Phase 8.6 repeated-evidence extension

Phase 8.6 retains the Phase 8.5 observable registry and the same five primary
paired-effect tasks. It does not add latent simulator state or target proxies.
The candidate set and complexity order are frozen as policy mean, pooled ridge,
separate-policy ridge, pooled forest and separate-policy forest. For each task,
the selected family is the least complex candidate whose median validation
normalised RMSE is within 5% of the best candidate. Ridge is an ML candidate;
there is no gate requiring a nonlinear model to beat it.

Ten development experiments independently vary the synthetic foundation and
field-population seed. Weather-resampling and latent-biological seeds are
separate streams and each takes multiple values. Each experiment retains
grouped train, validation and test partitions plus five dedicated complete
weather regimes: dry, hot, wet, cool and compound hot-dry. Reported repeated
test evidence includes median, quartiles, best, worst and failure frequency
against policy mean.

After aggregate validation selection, final hyperparameters, training-only
preprocessing, target/regime calibration widths and the applicability domain
are serialized in `frozen_protocol.json`. Only then is a distinct final
foundation/population generated from four seed commitments unused during
development. That population is scored once and cannot revise any preceding
decision.

Uncertainty is calibrated separately by primary target and regime. A regime is
supported only when repeated development MAE/SD is below the configured limit
and the calibration pool has enough independent seed groups. Unsupported
target-regime pairs explicitly abstain; interval width or coverage is not
claimed there. These are synthetic residual intervals, not structural,
mechanistic or real-field uncertainty.

Reproduce with:

```bash
uv run soil-simulator run-phase86-benchmark \
  --output-dir outputs/phase86_v0.8.6
```

Or replay ML from the saved population/batch without re-running the simulator:

```bash
uv run soil-simulator benchmark-intervention-ml \
  outputs/phase85_v0.8.5/saved_population_and_batch.json \
  outputs/phase85_v0.8.5/saved_population_and_batch.json \
  --output-dir outputs/phase85_v0.8.5
```

## Phase 9 frozen-consumer boundary

Phase 9 loads these exact Phase 8.6 JSON models and preprocessor and rejects any
version, protocol, decision, preprocessing or model hash mismatch. It does not
retrain from the Phase 8.6 final population. All five targets are required for
the configured multi-horizon utilities, so any unsupported target causes
field-level ML abstention. Objective scaling and simple selector baselines use
only new Phase 9 train/validation groups. See `PHASE9_EVIDENCE.md`.
