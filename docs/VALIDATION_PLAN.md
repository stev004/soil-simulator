# Verification, Validation and Evaluation Plan

## 1. Three distinct questions

### Verification

Does the code implement the specified equations correctly?

### Validation

Can the model reproduce independent observed patterns and time series?

### Policy evaluation

Can an optimiser identify good policies in the simulated environment, including on held-out synthetic fields?

These must never be conflated.

## 2. Verification tests

### Unit tests

- temperature modifier at known temperatures
- moisture-deficit update
- first-order decay
- DPM/RPM split
- manure split
- IOM calculation
- AMF allocation bounds
- P uptake bounded by available P
- harvest and residue transfer
- intervention event timing

### Property-based tests

For valid inputs:

- no pool becomes negative;
- total outflow cannot exceed source stock;
- increasing a decay constant cannot increase remaining stock;
- zero inputs and zero initial stock remain zero;
- fixed seed reproduces identical output;
- carbon ledger balances;
- texture fractions remain valid;
- objective components remain finite.

### Reference parity

The Phase 3 parity test reproduces the January 1852 Hoosfield unmanured monthly
pool update from section 2.2 of the February 2024 official RothC model
description. Expected, observed and tolerance values are recorded in
`CARBON_CORE.md`. This is equation verification, not external validation.
The official-compatible Phase 4 input timing does not alter this no-input
month. A compatibility test separately proves the expected difference between
official and legacy timing modes.

### Phase 4 plant and available-P verification

Implemented tests cover zero potential NPP; full/severe temperature and water
stress; bounded multiplicative stress; P limitation, uptake, external input,
depletion and non-negative stock; shoot/root allocation; harvest and yield;
shoot/root residue transfer; DPM/RPM ratio; monthly/cumulative carbon and P
mass balance; deterministic 20-year replay; and configuration provenance.

### Phase 5 AMF verification

Implemented tests cover zero realised-carbon allocation; zero live-fungal P
acquisition; bounded plant carbon cost; CUE growth plus maintenance/growth
respiration; exponential turnover; delayed necromass routing to DPM, RPM and
the protected proxy; stock-capped AMF P acquisition and configurable transfer;
immutable C/P records; monthly and cumulative C/P balance; finite non-negative
states; configuration provenance; official residue timing; RothC parity; and
deterministic 20-year replay.

### Phase 6 management verification

Implemented tests cover immutable date/month events; event-specific units;
out-of-horizon, duplicate, conflicting and unpaired schedules; deterministic
same-month ordering; each tillage intensity; pulse AMF mortality and temporary
turnover effects; cover establishment, growth, P uptake, host support,
termination and residue/P return; exact P application/depletion;
post-decomposition FYM 49/49/2 carbon routing and explicit P input; additive
cost/emissions accounting; non-negative finite states; monthly/cumulative
carbon and P balance; configuration/schedule hashes; RothC parity; and
deterministic 20-year replay.

### Phase 7 population verification

Implemented tests cover versioned local and hash-checked cached adapters;
additive-log-ratio texture composition; correlated, bounded perturbation;
complete regional weather-year sampling; all five named archetypes; explicit
latent draw classifications; periodic RothC spin-up and SOC closure; finite,
non-negative and impossible-combination QC; Phase 6 execution probes; seed-level
split leakage prevention; complete manifests and deterministic hashes; batch
baseline/intervention execution; carbon/P balance; deterministic replay;
human-readable CLI tables and optional JSON export. The 1,000-field acceptance
run is generator and simulator verification, not empirical validation.

### Phase 8 ML verification and evaluation

Implemented tests cover direct and paired-baseline target construction;
same-field/same-horizon baseline matching; immutable empirical-seed group
splits; field/group leakage rejection; training-only preprocessing statistics
and categories; observable/full-state feature separation; target-derived
feature exclusion; honest global and policy means; deterministic ridge/tree
training; JSON model and preprocessing replay; exact/near-duplicate field
audits; held-out archetype and weather-regime experiments; boundary scoring;
split-conformal rank, coverage and width calculations; feature importance;
engineered clay--SOC, SOC--bulk-density and available-P--AMF correlation
disruption; human-readable CLI tables; and versioned dataset/model/report
artifacts.

The final primary observable model is tuned on training/validation
empirical-seed groups only. Validation residuals calibrate uncertainty. Frozen
serialized models are then scored on held-out test groups without fitting any
preprocessing, target transform, hyperparameter or interval width on test
outcomes. Full-state performance is a diagnostic hidden-information upper
comparison, not deployable evidence. All results remain synthetic and
non-causal.

### Phase 8.5 diagnostic verification and success gates

Phase 8.5 tests require at least 50 distinct seed groups; exact group isolation
across train, validation, final test, complete-archetype OOD and extreme-
weather OOD partitions; 24/60/120-month paired baselines; weakened seed-level
SOC--bulk-density correlation; training-only preprocessing; horizon-specific
targets; deterministic pooled and separate-policy models; group-aware
validation calibration; coverage abstention for small groups; untouched OOD
evaluation; success-gate arithmetic; serialization; artifact hashes; replay;
and unchanged carbon/P balance and RothC parity.

Before any Phase 9 selector, all of these gates must pass:

1. no final-test or OOD leakage;
2. primary-target coverage within configured tolerance of nominal;
3. nonlinear primary intervention-effect error below policy mean and the best
   pooled or separate-policy regularised-linear baseline;
4. acceptable aggregate effect error on at least one untouched OOD partition;
5. no selection based only on in-distribution R-squared.

The v0.8.5 run fails gate 3. Therefore Phase 9 intervention selection is
blocked even though the other gates pass.

## 3. Scenario-direction tests

These are regression tests of model intent, not empirical proof.

Holding all else equal:

1. No plant inputs should deplete active SOC pools over time.
2. Warmer non-extreme temperature should increase the RothC decomposition modifier.
3. Severe water deficit should suppress plant NPP and decomposition relative to adequate moisture.
4. Higher clay should increase the retained fraction of decomposed carbon in the RothC core.
5. Conventional tillage should cause a larger AMF disturbance than no till under default assumptions.
6. A successful AM-compatible cover crop should increase living-host months and below-ground carbon input.
7. High phosphorus should relieve P limitation but reduce AMF allocation incentive.
8. Removing the AMF module should eliminate AMF-derived necromass and protected-carbon flux.
9. Increasing AMF turnover should not automatically increase protected carbon if stabilisation is low.
10. The best policy should be allowed to differ among field archetypes.

The implemented no-AMF Phase 4 subset additionally requires:

11. Drought reduces realised biomass and grain yield.
12. Available-P limitation reduces realised biomass and grain yield.
13. Complete residue retention increases soil-carbon inputs relative to
    complete shoot/root residue removal.

These directions verify encoded provisional intent, not empirical agronomic
validity.

The implemented Phase 5 subset additionally requires:

14. AMF can be beneficial under P limitation when transferred P benefit
    exceeds plant carbon cost.
15. AMF can be neutral when P is effectively sufficient and allocation tends
    to zero.
16. AMF can be harmful when carbon cost exceeds P benefit.
17. More live fungal biomass does not directly or automatically increase the
    protected-carbon proxy.

These are equation-direction checks, not AMF field validation.

The implemented Phase 6 subset additionally requires:

18. Intensive tillage can reduce AMF biomass relative to the configured
    no-till endpoint.
19. Cover cropping can add plant-derived carbon without guaranteed yield gain.
20. P input can relieve limitation while suppressing AMF allocation.
21. FYM can increase soil carbon while adding cost and emissions.
22. Different policies lead yield, soil carbon and cost; no universal optimum
    is encoded.

The implemented Phase 7 subset additionally requires:

23. Texture remains compositional under every perturbation.
24. High clay/SOC/CEC and low SOC/high bulk-density relationships survive
    bounded perturbation at population scale.
25. Weather forcing is composed only of observed-as-a-block fixture years.
26. Perturbations from one empirical seed never cross population splits.
27. All generated fields execute the Phase 6 baseline with C/P balance.

These are generator-intent and integration checks. They do not establish that
the bundled fixture represents the UK arable population.

The implemented Phase 8 subset additionally requires:

28. Test targets and paired baselines cannot enter training features.
29. Observable models cannot access latent biological parameters or hidden
    initial pool states.
30. Hyperparameter tuning cannot use held-out empirical-seed groups.
31. Complete archetype/weather holdouts and sampled-boundary fields remain
    visible even when performance deteriorates.
32. Disrupting designed generator correlations reports degradation rather than
    being interpreted as independent biological discovery.
33. Uncertainty coverage is measured on held-out synthetic outcomes and is not
    presented as mechanistic or real-field uncertainty.

These directions verify honest predictive evaluation of the current synthetic
system. They do not validate an intervention effect, policy selector or causal
relationship.

The implemented Phase 8.6 subset additionally requires:

34. At least ten repeated development experiments use distinct population and
    foundation seeds plus multiple separately controlled weather and latent-
    biological seeds.
35. Model families and their simplicity order are fixed before outcomes are
    compared; ridge is eligible without a nonlinear superiority requirement.
36. Dry, hot, wet, cool and compound hot-dry groups are kept outside fitting
    and scored separately.
37. Target/regime uncertainty calibration uses development groups only and
    unsupported or undersized regimes abstain.
38. Model, preprocessing, calibration and applicability hashes are written
    before the separately seeded final population is generated.
39. The final population cannot affect selection, calibration, applicability
    or success gates, and its simulator trajectories retain the Phase 3--6
    carbon and phosphorus balance tolerances.

Phase 8.6 performance remains synthetic prediction evidence. Passing any gate
would justify only a restricted simulator regret experiment, not a deployed
selector or an agronomic claim.

The v0.8.6 production run passes the revised gates with a restricted,
target-specific domain. Cool, hot and wet are supported for all five primary
paired-effect targets. Yield abstains in dry and hot-dry conditions; 10-year
total-SOC effect abstains in hot-dry. Supported final coverage is conservative
at 0.957--1.000 by weather regime and 0.980--0.989 on the untouched core.
Phase 9 may therefore benchmark regret only under the restrictions in
`ROADMAP.md`; this is not external validation.

## 4. External soil-carbon validation

### Hoosfield

Use spring-barley SOC trajectories under:

- unmanured treatment;
- annual farmyard manure;
- manure followed by cessation.

Assess:

- RMSE/MAE of total SOC;
- trajectory direction;
- equilibrium behaviour;
- treatment ordering.

### Broadbalk

Use long-term winter-wheat SOC/yield treatments as a secondary carbon-core test.

### Ley–arable experiments

Test whether the model reproduces broad SOC changes when land use changes between arable and grass/ley systems.

The AMF extension may be disabled for pure RothC parity, then enabled for hypothesis experiments.

## 5. AMF plausibility checks

Because longitudinal AMF-carbon validation data are sparse, use several weaker constraints rather than pretending to have one definitive dataset:

- initial AMF density distribution overlaps the 2026 global dataset for the relevant biome/land use;
- lower-intensity tillage and cover cropping have positive expected effects on colonisation under the default priors;
- high P has a negative expected effect on allocation/colonisation;
- turnover spans published uncertainty;
- plant carbon allocation centres near the current cross-system estimate but is broadly uncertain;
- AMF effects can be neutral or negative under some contexts.

## 6. Uncertainty analysis

### Aleatory uncertainty

- weather-year sequence
- cover-crop establishment
- process noise where justified

### Epistemic uncertainty

- AMF allocation
- AMF turnover
- fungal CUE
- P acquisition
- necromass stabilisation
- tillage disturbance
- protected-carbon capacity

Use Monte Carlo sampling and clearly separate these categories in outputs.

## 7. Sensitivity analysis

Run:

- Morris screening during development;
- Sobol analysis on the final reduced parameter set.

Report:

- total-order and first-order effects;
- interactions;
- sensitivity of carbon, yield and policy choice;
- parameters whose uncertainty changes the recommended policy.

A parameter that dominates output but has no defensible data is a research priority, not a result to hide.

## 8. Optimiser evaluation

### Baselines

1. Status quo
2. Random policy search
3. Best single policy across all development fields
4. Field-specific exhaustive-grid oracle
5. Simple rule-based agronomy policy
6. Proposed optimiser

### Metrics

- protected-carbon gain
- yield difference
- cost
- objective score
- probability of outperforming baseline
- regret relative to oracle
- recommendation stability
- worst-decile outcome
- compute time

### Held-out evaluation

The optimiser must be evaluated on seed field archetypes not used during tuning. Weather and biological random seeds must also be unseen.

## 9. Circularity audit

For every headline finding, ask:

1. Was this outcome explicitly encoded as an assumption?
2. Did the optimiser merely rediscover an imposed ordering?
3. Does the result survive broad parameter uncertainty?
4. Does it survive removal of one contested mechanism?
5. Is there independent evidence supporting the direction?
6. Is the finding a model implication or an empirical prediction?

The report must label each conclusion accordingly.

## 10. MVP validation dashboard

Display:

- test status
- mass-balance residual distribution
- parity against RothC worked example
- Hoosfield observed versus simulated SOC
- sensitivity ranking
- policy regret
- policy stability
- known unsupported mechanisms

The validation page is more important than a glossy recommendation page.

## 11. Phase 9 selection verification and gate result

Version `0.9.0` tests exact frozen-artifact versions/hashes, observable-only
access, no oracle leakage, utility and training-only normalisation, hard
constraints, eligibility, applicability and uncertainty abstention, exhaustive
oracle and regret arithmetic, catastrophic classification, perturbation
stability, no-final-tuning, deterministic replay and artifact hashing.

Ten new repeated populations and a later frozen-final population preserve
carbon/P balance. Point observable ML passes median-regret, simple-baseline,
constraint, applicability, seed-stability and frozen-final gates. All tested
uncertainty-aware methods worsen worst-decile or catastrophic regret, so the
overall Phase 9 gate fails. Under the predeclared rule, recommendation-system
development must stop. This is synthetic policy evaluation, not validation.

## 12. Phase 9.5 remediation verification and gate result

Version `0.9.5` adds byte-level v0.9.0 preservation tests; effect-only headline
target tests; deterministic-identity exclusion; biological duplicate-policy
detection; recurring event accounting at 24/60/120 months; operational versus
partial lifecycle accounting; explicit phosphorus pathway ablations; seeded
Morris/Sobol replay and convergence; local-fixture hashes; complete seed-group
isolation; uncalibrated Hoosfield metrics; no-calibration-leakage checks; and
fail-closed publication-readiness gates.

The Hoosfield exercise is independent of the one-step parity test. It reports
MAE, RMSE and bias for unmanured, annual-FYM and FYM-cessation treatments over
1852--1998. The 1852 values initialize trajectories only. The negative FYM
bias is retained as evidence against current performance.

The empirical-pilot and population-covariance sensitivity requirements are
blocked. Therefore complete global sensitivity and downstream deterministic
population/benchmark replay are not claimed, and the publication-readiness
gate fails. The exact next task is remaining scientific remediation.

## 13. Phase 9.6 remediation verification

Phase 9.6 requires at least 50 complete paired SoilGrids/NASA POWER locations,
source and processed hashes, explicit depth/unit harmonisation, covariance and
PCA coverage, and location-group isolation. Long-term validation reports both
the frozen Phase 9.5 forcing and official RothC v2.1.1 source forcing. Optional
calibration uses only unmanured and annual-FYM observations through 1965;
post-1965 observations and the entire FYM-cessation treatment remain held out.

Population Morris/Sobol analysis includes location, intact weather-year,
spin-up, AMF/P and management assumptions. Effect-only ML must beat the
policy-mean baseline on isolated test groups, remain acceptable on weather OOD,
show validation-calibrated interval coverage, and have independent empirical
effect validation before selector/oracle/regret analysis may run. Publication
readiness additionally requires exact original-audit reconciliation and an
independent re-audit; failure of either keeps manuscript drafting closed.

## 14. Phase 9.7 corrected verification and gates

Phase 9.7 requires a scrambled SciPy Sobol design with power-of-two base sizes,
Saltelli/Jansen first- and total-order estimators, deterministic confidence
intervals, retained negative estimates and a predeclared 128/256/512/1,024
convergence rule. Every leakage, independent-validation, coverage and
downstream gate is computed from artifacts and fails closed when evidence is
missing. Coverage is evaluated separately for each primary target and supported
test/OOD regime. The FYM boundary profile must retain the 0.90--1.10 bound and
report held-out cessation error. Passing verification does not authorize a
selector, real-field claim or agricultural prediction paper.
