# Unresolved methods information for version 2

The compact imported evidence supports the final claims but does not contain every method detail needed for a fully self-contained replication report. The manuscript does not infer the following:

## Model equations and parameters

- Complete governing equations for RothC modifiers and monthly transitions are indexed to source/model documentation but are not reproduced in the compact bundle.
- Complete equations and numerical defaults for crop growth, residue partitioning, phosphorus limitation, AMF uptake, allocation, carbon-use efficiency, turnover, respiration, and necromass routing are not all available as a manuscript-ready specification.
- Full parameter tables with units, defaults, provenance, and calibrated/prior status are absent.
- The assumptions register documents selected values and classifications but is not a complete executable parameter specification.

## Empirical pilot and generated fields

- Exact rule used to select the predeclared 64 Great Britain coordinates from the geographic frame.
- Full processed soil-column names and unit-conversion formulas beyond the documented nine-column harmonization, 0–23 cm weighting, SOC stock calculation, and texture renormalization.
- Numerical bounds/distributions for each within-location descendant perturbation.
- Exact parameterization of latent available-P, AMF, drainage, management-history, and spin-up pool-allocation priors.
- Exact allocation of all 56 location groups among training, validation, test, weather-OOD, and archetype-OOD regimes. Available evidence gives 31 preprocessing-training groups, 25 excluded groups, 11 test locations, and four OOD locations.
- Complete construction rules distinguishing weather-OOD from archetype-OOD regimes.

## Hoosfield evaluation

- Exact predeclared bounds and grid for the plant-residue reconstruction factor.
- Complete mathematical definition of how the two calibration factors enter reconstructed inputs, beyond the documented source paths and bounded-profile evidence.
- The bundle describes the objective as mean treatment RMSE and supplies the FYM profile, but a complete two-dimensional objective surface is not imported.

## Sensitivity

- Exact names of the four policies included in the corrected sensitivity artifact; the evidence index reports four policies but the compact methods artifacts do not enumerate them.
- Full Morris design settings, including trajectory count, grid levels, and factor-specific bounds for the final population-aware screen.
- Complete list of every simulator output field stored in the large sensitivity artifact beyond the seven indexed headline target–horizon combinations.
- Rationale for the endpoint half-weighting induced by round-based discrete transforms; the audit identifies it as a low-severity limitation.

## Machine learning and gates

- Complete candidate-model search for the final effect-only benchmark. The imported final model card documents ridge and policy-mean results; older assumptions mention other predeclared candidates but do not establish that they were evaluated in the final artifact.
- Exact alpha candidate grid and tie-breaking rule; selected alpha is 0.1 for all indexed targets.
- Exact row counts for training and validation and exact policy composition within each split.
- Exact rule by which OOD regimes were pooled for the target-level OOD gate.
- Complete formula for the prediction gate beyond the audited requirement that every ridge target beat policy-mean test RMSE.
- Exact interval-quantile construction and Wilson-interval reporting formula are indexed to source but not reproduced as a standalone methods specification.

These gaps should be resolved from the complete repository or a verified expanded evidence export before journal submission.
