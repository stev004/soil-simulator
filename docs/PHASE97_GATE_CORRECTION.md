# Phase 9.7 scientific-gate correction

## Leakage

The leakage gate is computed from the effect-dataset artifacts. It verifies
empirical-location isolation, descendant isolation by empirical seed,
training-only preprocessing groups, separation of validation calibration from
test/OOD evaluation, and absence of exact or near-duplicate fields across
groups. Missing columns or evidence fail closed.

## Independent empirical effect validation

This gate passes only for an identified empirical intervention-effect dataset
with at least 30 observations, compatible supported treatments, coverage of all
primary target/horizon pairs, independent collection, and no use in calibration
or model development. No such dataset currently exists, so the computed gate
correctly fails with dataset identity, source, sample size, compatibility,
independence and reason fields recorded.

## Uncertainty and downstream execution

Nominal 90% coverage is evaluated separately for every target and test/OOD
regime. Supported regimes use the exact central 95% Binomial(n, 0.90) count
range, Wilson confidence intervals and an excessive-width diagnostic; regimes
with fewer than 20 rows or four independent groups explicitly abstain. No
target can hide another target's undercoverage.

Downstream eligibility is the conjunction of prediction, OOD, target-specific
uncertainty, leakage and independent-validation gates. It is neither forced
true nor forced false. Missing evidence fails closed. The current lack of
independent empirical effect evidence blocks selection/oracle/regret work even
if other gates pass.

## Computed result

The artifact-derived leakage gate passes with no empirical-seed, descendant,
preprocessing, calibration or duplicate-field crossover. Every primary
target/regime meets the target-specific coverage criterion. Effect prediction
and OOD performance do not pass for every target, and independent empirical
effect validation is non-computable because no eligible dataset exists. The
computed downstream gate therefore fails and no selection/oracle/regret work is
executed.
