# Phase 9 offline synthetic intervention-selection evidence

## Claim boundary

Phase 9 benchmarks selection only inside the synthetic simulator. Results are
non-causal, are not real-field validation and are not agronomic
recommendations. `protected_soc` remains a model proxy, not measured MAOC.

## Frozen design

Package/configuration version `0.9.0` consumes the exact Phase 8.6 observable
preprocessor, selected models, target/regime residual widths and applicability
contract with strict version and semantic-hash enforcement. Missing
observations, unknown categories, numeric observations outside the frozen
training-scale envelope, unsupported weather, unavailable uncertainty and
ineligible interventions produce explicit abstention.

Ten new 75-field populations vary independent foundation, field, weather and
latent-biological seeds. Objective normalisation, policy means and global
policies use train/validation groups only. A 150-field final population is
generated after the Phase 9 selector/utility decision hash is frozen.

Four scenario profiles expose every utility weight, carbon-horizon mixture and
hard threshold. They are preference experiments, not definitions of agronomic
best practice. Catastrophic failure is predeclared as normalised regret at
least 0.5 or any revealed hard-constraint violation.

## Result

Point observable ML beats status quo and random on repeated median utility
regret, is median-competitive with the best-global and policy-mean selectors,
and has zero hard-constraint violations. However, the simple selectors remain
strong: their repeated worst-decile regret is 0.3096 versus 0.3392 for ML.

The final point selector has 84.0% exact oracle match, median regret 0, mean
regret 0.0299, worst-decile regret 0.1792, catastrophic frequency 5.5%, 12.67%
abstention and zero violations. Unsupported non-abstaining decisions are zero.

Uncertainty-aware selection fails its purpose. Frozen-width LCB, ranking-
overlap and no-confident-improvement variants increase final catastrophic
frequency to 12.83%, 35.33% and 46.0%. The predeclared Phase 9 success gates
therefore **fail**.

## Stress evidence

Observable-correlation disruption raises mean point-ML regret from 0.0299 to
0.0468. High versus low hidden necromass-stabilisation draws show a regret gap,
but hidden values are used only after selection for diagnosis. Policy choices
are stable under the 2% measurement perturbation. Dry and hot-dry fields
abstain as required. Registered endpoint variation of the conventional-
tillage decomposition multiplier changes outcome dataset hashes but not the
aggregate selector metrics, because that policy is rarely decisive here.

## Decision

The project must report the failed uncertainty gate plainly. Under the frozen
success rule, further recommendation-system or product-facing development is
not scientifically justified. Independent real-field calibration, protected-
fraction validation and structural uncertainty work must precede any renewed
selection effort.

