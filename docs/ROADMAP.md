# Implementation Roadmap

## Current engineering status

Engineering has reached Phase 9.5 scientific remediation. The audited v0.9.0
selection results remain frozen. Phase 9.5 corrects target framing, duplicate
policy structure and event accounting, and adds phosphorus ablation, global
mechanistic sensitivity and uncalibrated multi-decade Hoosfield validation.
Publication readiness still fails because a reproducible 50-location empirical
soil-climate pilot was unavailable, covariance sensitivity is incomplete and
downstream effect-only ML/regret reruns are therefore blocked. The exact next
task is remaining scientific remediation, not selector tuning or manuscript
drafting.

## Working estimate

- Focused full-time build with heavy Codex use: 6–8 weeks
- Alongside university and other work: 10–14 weeks
- Research-grade validation beyond MVP: several additional months

AI can accelerate implementation, tests and documentation. It does not remove the need to validate equations, inspect mass balance, assess outputs and control scientific assumptions.

## Milestone 0 — Repository and scientific contracts

Estimated: 2–3 days

Deliver:

- project skeleton
- package/environment setup
- domain schemas
- assumptions register
- configuration loader
- CI
- lint/type/test gates
- empty CLI

Exit gate:

- clean install
- all quality checks pass
- no simulator code yet

## Milestone 1 — Verified RothC-inspired carbon core

Estimated: 5–7 days

Deliver:

- DPM/RPM/BIO/HUM/IOM pools
- temperature modifier
- moisture-deficit modifier
- cover modifier
- clay-dependent partitioning
- plant/manure inputs
- carbon ledger
- worked-example parity
- spin-up utility

Exit gate:

- parity tests pass
- mass balance passes
- Hoosfield-style baseline can run

## Milestone 2 — Simplified plant and phosphorus module

Estimated: 4–6 days

Deliver:

- spring-barley monthly growth profile
- weather stress
- P stress
- roots/residues/harvest
- yield proxy
- available-P balance

Exit gate:

- sensible seasonal crop trajectory
- no-AMF baseline stable
- harvest/residue mass balance passes

Status: implemented and verified in package/configuration version `0.4.0`.

## Milestone 3 — Explicit AMF extension

Estimated: 5–8 days

Deliver:

- plant-to-AMF allocation
- AMF growth/respiration
- AMF turnover
- necromass
- P-for-C feedback
- protected-carbon routing
- uncertainty distributions
- scenario-direction tests

Exit gate:

- AMF can help, harm or be neutral depending on context
- no universal monotonic benefit
- all fluxes traceable

Status: implemented and verified in package/configuration version `0.5.0`.

## Milestone 4 — Management interventions

Estimated: 4–6 days

Deliver:

- tillage
- cover crop
- P input
- organic amendment
- costs and emissions proxies
- scenario manifests

Exit gate:

- policies produce interpretable and non-identical trajectories
- effects are parameterised, not hard-coded into objective

Status: implemented and verified in package/configuration version `0.6.0`.

## Milestone 5 — Synthetic population generator

Estimated: 5–8 days

Deliver:

- empirical seed schema
- SoilGrids/ERA5 adapters or cached sample data
- stratified resampling
- uncertainty perturbation
- stochastic weather
- population quality report
- named archetypes

Exit gate:

- 1,000 fields pass QC
- joint distributions are plotted and reviewed
- no train/test seed leakage

Status: implemented and verified in package/configuration version `0.7.0`.
The checked-in local research fixture verifies adapter/generator behaviour but
does not complete the separate empirical representativeness review.

## Milestone 6 — Experiments and optimisation

Estimated: 5–7 days

Deliver:

- exhaustive policy grid
- random search
- best-global baseline
- oracle
- proposed optimiser
- Pareto analysis
- regret and stability metrics

Exit gate:

- held-out comparison complete
- optimiser only wins when it actually reduces regret
- objective weights visible

## Milestone 7 — Validation, sensitivity and report

Estimated: 5–8 days

Deliver:

- Hoosfield data adapter
- observed/simulated SOC plots
- Morris/Sobol analyses
- uncertainty decomposition
- circularity audit
- reproducible flagship experiment

Exit gate:

- validation failures are visible
- dominant uncertain assumptions documented
- one defensible research narrative exists

## Milestone 8 — API and portfolio dashboard

Estimated: 7–12 days

Deliver:

- FastAPI service
- Next.js dashboard
- saved scenarios
- charts
- validation page
- assumptions browser
- Docker setup

Exit gate:

- a reviewer can reproduce the flagship experiment
- dashboard never presents synthetic results as field truth

## Recommended Codex workflow

Use one task per milestone slice, not “build the whole platform.”

For each task:

1. Give Codex the relevant docs and exact acceptance tests.
2. Ask it to inspect before editing.
3. Require a plan for changes exceeding a few files.
4. Require tests and commands run.
5. Review the diff and simulation outputs.
6. Commit only after the scientific behaviour is understood.
7. Use separate Codex worktrees/tasks for independent modules, but do not parallelise coupled model equations before the interfaces are stable.

## First three engineering tasks

1. Bootstrap repository, schemas, configuration and CI.
2. Implement first-order carbon-pool decay plus ledger and mass-balance properties.
3. Implement RothC modifiers and reproduce the official worked example.

Do not ask Codex to implement the AMF module until those three tasks are passing.

## Exact recommended fifth Codex task

Implement Phase 5 only: add an explicit deterministic AMF live-biomass,
carbon-allocation, respiration, turnover, necromass and plant-P-benefit module
on the verified Phase 4 interfaces; keep every AMF parameter configuration
validated and source-classified, preserve carbon and available-P mass balance,
RothC parity, official post-decomposition residue timing, deterministic replay
and configuration provenance, add uncertainty-ready immutable flux records and
tests showing AMF can help, harm or be neutral, and do not implement management
interventions, optimisation, populations, API or dashboard functionality.

## Exact recommended sixth Codex task

Implement Phase 6 only: add deterministic, scheduled tillage, AM-compatible
cover-crop, phosphorus-input and farmyard-manure interventions to the verified
Phase 5 soil--crop--AMF simulator; keep every effect size, timing rule, cost,
emissions proxy and nutrient/carbon route validated, source-classified and
explicit in configuration; preserve carbon and available-phosphorus mass
balance, immutable flux records, non-negative finite states, RothC parity,
official post-decomposition input timing, deterministic replay, configuration
hashing and the ability for AMF effects to help, harm or be neutral; add unit,
property, integration and scenario-direction tests for each intervention and
their event ordering; update the CLI, documentation, assumptions, references,
roadmap and versions; and do not implement synthetic populations,
optimisation, machine-learning recommendations, API or dashboard functionality.

## Exact recommended seventh Codex task

Implement Phase 7 only: add a reproducible synthetic-field population generator
on the verified Phase 6 simulator using versioned empirical seed records and
cached/local adapters for jointly coherent 0--23 cm soil and monthly climate
covariates; implement named field archetypes, compositional texture handling,
bounded uncertainty-aware perturbation, deterministic whole-year weather
resampling, explicit latent-parameter draws, carbon-pool spin-up/initialisation
contracts, train/validation/test grouping by empirical seed, rejection and QC
diagnostics, manifests and configuration/data hashes; demonstrate that 1,000
fields preserve plausible joint distributions, contain no impossible or
non-finite states, replay exactly for fixed seeds and pass Phase 6 carbon/P
balance and scenario-direction gates; document every data version, uncertainty
class and unsupported assumption; and do not implement optimisation,
machine-learning recommendations, API or dashboard functionality.

## Exact recommended eighth Codex task

Implement Phase 8 only: build the first reproducible intervention-outcome ML
training and benchmarking pipeline from saved Phase 7 field manifests and
Phase 6 batch outcomes; define explicit per-policy targets for final yield,
total SOC, protected-SOC proxy and paired intervention-minus-baseline effects;
freeze the existing empirical-seed group train/validation/test assignments and
reject any feature, preprocessing fit or target transform that leaks across
groups; add transparent naive-mean and regularised-linear baselines before one
tree-based nonlinear model; tune only on training/validation groups; report
held-out MAE, RMSE, R-squared, calibration/coverage where uncertainty is
estimated, subgroup errors by archetype/region, residual diagnostics, feature
availability, model/data/configuration hashes and deterministic replay; compare
performance against field-to-field and mechanistic outcome variation; preserve
units, uncertainty and the synthetic-not-causal claim boundary; export a
versioned training dataset and model card; add tests for target construction,
group leakage, preprocessing isolation, reproducibility and baseline honesty;
and do not implement policy optimisation, recommendations, causal claims, API
or dashboard functionality.

Status: superseded by the Phase 8.5 diagnostic in package/configuration version
`0.8.5`.
See `ML_BENCHMARKING.md` for the frozen feature registries, leakage controls,
models, conformal intervals, OOD tests and artifacts.

## Exact recommended ninth Codex task

Implement Phase 9 only: add intervention selection and regret benchmarking on
top of the frozen Phase 8 observable-feature predictor without changing Phase
3--7 simulator equations or exposing full-state latent features; define an
explicit multi-objective utility and constraint configuration with visible
units and weights; compare status quo, random selection, best single global
policy, simple transparent rule, observable-ML selection and a field-specific
exhaustive simulator oracle; run repeated deterministic experiments with new
population, empirical-seed-group, weather and biological seeds; evaluate only
on untouched synthetic groups using per-objective outcomes, paired effects,
oracle regret, constraint violations, worst-decile outcomes, policy stability,
selection frequency, uncertainty-aware abstention and runtime; propagate Phase
8 conformal uncertainty without treating it as causal or mechanistic
uncertainty; audit sensitivity to engineered correlations, hidden-state gaps,
utility weights and simulator assumptions; serialize experiment manifests and
policy-selection results; add deterministic replay, no-test-tuning, oracle,
regret and abstention tests; and do not add farmer recommendations, real-field
claims, online learning, API or dashboard functionality.

Status: superseded by the restricted Phase 9 task below. Phase 8.6 passes the
revised synthetic gates only inside its target-specific applicability domain.

## Exact recommended next task: Phase 8.6

Implement Phase 8.6 only: increase independent synthetic support within each
seed group and validation/OOD subgroup; revise the nonlinear benchmark without
using final-test or OOD outcomes for architecture or hyperparameter choice;
test whether separate-policy ridge superiority persists across repeated
population, weather and biological seeds; reduce the width and conservatism of
group-aware intervals while preserving nominal coverage; improve observable
predictors for yield and respiration only where a defensible pre-intervention
measurement already exists; freeze a completely new final-test/archetype-OOD/
weather-OOD set; rerun every Phase 8.5 gate and artifact hash; and do not build
an intervention selector, regret benchmark, optimiser, recommendation, API or
dashboard unless all gates pass.

Status: complete in package/configuration version `0.8.6`. See
`PHASE86_EVIDENCE.md`. The repeated and frozen-final gates pass with mandatory
abstention for yield under dry/hot-dry conditions and for 10-year total-SOC
effect under hot-dry conditions.

## Exact recommended Phase 9 task: restricted selection and regret benchmarking

Implement Phase 9 only as a synthetic, offline intervention-selection and
regret benchmark over the frozen Phase 8.6 observable models. Do not alter the
verified Phase 3--6 biological equations, retrain from Phase 8.6 final outcomes
or expose hidden simulator state. Predeclare a transparent multi-objective
utility and hard yield/cost/emissions constraints with units and visible
weights; compare status quo, random selection, best single global policy,
policy-mean selection, the selected observable model and a field-specific
exhaustive-simulator oracle. Run repeated new population, weather and latent-
biological seeds, keep tuning groups separate from untouched regret groups and
report per-objective outcomes, oracle regret, constraint violations,
worst-decile regret, policy stability, selection frequency and runtime.

Enforce the Phase 8.6 target-specific applicability domain before scoring a
policy: all five primary targets are usable only in cool, hot and wet regimes;
yield must abstain in dry and hot-dry regimes; 10-year total-SOC effect must
abstain in hot-dry; other dry/hot-dry carbon effects may be used only with their
frozen target/regime intervals. An abstention must fall back to status quo or a
predeclared non-ML baseline and be counted, never silently imputed. Propagate
the frozen synthetic residual intervals into constraint checks without calling
them causal, mechanistic or real-field uncertainty. Add no farmer
recommendation, policy optimisation beyond finite benchmark comparison, API,
dashboard, online learning or deployment claim.

Phase 9 succeeds only if the observable selector reduces median and worst-
decile oracle regret versus every simple baseline across repeated untouched
synthetic experiments without increasing constraint violations, remains stable
across seed streams, preserves abstention, and reports any failure by target and
climate regime. Passing would demonstrate only internal synthetic decision-
benchmark value, not real-field validity.

Status: completed in package/configuration version `0.9.0`. The uncertainty-
aware tail-safety gate fails, while applicability enforcement has zero
unsupported non-abstaining selections. See `PHASE9_EVIDENCE.md`. Do not proceed
to recommendation-system development.

## Phase 9.5 scientific remediation

Status: implemented with blockers in package version `0.9.5`. The v0.9.0
artifacts remain frozen. Effect-only target framing, duplicate-policy removal,
recurring accounting, phosphorus ablation and multi-decade validation are
implemented. Morris/Sobol mechanistic sensitivity is reported, but the global
sensitivity gate remains incomplete because no defensible 50-location
empirical pilot was available for covariance re-estimation and propagation.
No downstream ML or regret rerun is claimed.

Exact next task: **remaining scientific remediation**. Obtain and independently
verify a versioned paired soil/climate pilot; estimate observable covariance;
repeat population-level sensitivity; then rebuild the effect-only dataset and
run predictor gates. Restricted selection/regret may be rerun only if those
gates pass. An independent re-audit follows successful remediation. Manuscript
drafting does not precede re-audit.
