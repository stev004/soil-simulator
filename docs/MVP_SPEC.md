# MVP Specification

## 1. Research objective

Develop a computational digital twin that can generate realistic populations of virtual temperate arable fields, simulate monthly soil–plant–AMF carbon dynamics under competing management strategies, and evaluate whether an optimiser can identify robust policies that increase a protected-soil-carbon proxy while retaining crop productivity.

The MVP is a hypothesis-generating research demonstrator. It is not a commercial agronomy product and not evidence that any simulated policy causes carbon sequestration in real fields.

## 2. Primary research question

> Can a hybrid mechanistic and uncertainty-aware simulator identify field-specific management strategies predicted to increase fungal-mediated protected soil carbon without unacceptable yield loss?

## 3. Secondary questions

1. Which field properties most strongly alter the predicted benefit of AMF-supporting management?
2. Does maximising AMF biomass also maximise protected carbon?
3. How often does a single global policy underperform a field-specific policy?
4. How robust are recommendations to uncertain fungal turnover, carbon allocation and necromass stabilisation?
5. Which measurement would reduce recommendation uncertainty most: AMF biomass, available phosphorus, soil carbon fractions, soil moisture or plant carbon inputs?

## 4. Scope

### Included

- Temperate UK arable systems
- Non-waterlogged mineral topsoil
- 0–23 cm layer, matching the standard RothC reference and Hoosfield validation data
- Spring barley as the first crop
- Optional winter cover crop
- Monthly time step
- 20-year simulations, with configurable 1–100 year support
- Soil carbon turnover
- Plant carbon inputs and harvest
- Water and temperature stress
- Available phosphorus as the principal nutrient constraint
- Explicit AMF live biomass and AMF necromass
- Fungal carbon allocation and phosphorus benefit
- Management disturbances
- Parameter uncertainty
- Synthetic populations grounded in empirical soil/climate data
- Rule-based, exhaustive and Bayesian/evolutionary optimisation baselines
- Portfolio dashboard after the simulator passes validation gates

### Explicitly excluded from v0.1

- Daily crop phenology
- Full nitrogen cycle
- Methane and mechanistic nitrous oxide models
- Soil layers below 23 cm
- Waterlogged, peat, tundra, volcanic or tropical soils
- Ectomycorrhizal fungi
- AMF species-level community ecology
- Pathogens and pesticide fate
- Genomic or metagenomic prediction
- Custom hardware or live sensors
- Carbon-credit accounting
- Real-world prescriptions
- Reinforcement learning
- Claims of true mineral-associated organic carbon without validation

## 5. Why this boundary

RothC supplies a transparent, monthly, first-order carbon-turnover structure with few required inputs. Its official implementation uses decomposable plant material, resistant plant material, microbial biomass, humified organic matter and inert organic matter pools, modified by temperature, moisture, soil cover and clay. The project extends this transparent base rather than inventing a black-box soil model.

Spring barley and a 0–23 cm layer allow comparison with the Hoosfield long-term experiment. Cover crops, tillage, phosphorus and organic amendments are biologically relevant to AMF and agricultural soil-carbon management while remaining computationally manageable.

## 6. User stories

### Researcher

- Configure or sample a virtual field.
- Inspect every state variable and parameter.
- Run a baseline and interventions.
- Trace every carbon flux.
- Run uncertainty and sensitivity analyses.
- Export tidy results and a reproducible scenario manifest.

### Portfolio reviewer

- Understand the scientific hypothesis.
- See that synthetic fields have realistic joint distributions.
- Compare management strategies visually.
- Inspect uncertainty bands and Pareto trade-offs.
- Review validation results and known limitations.

## 7. Required outputs

For every field × policy × stochastic replicate:

- monthly and annual total SOC
- DPM, RPM, microbial biomass, protected SOC proxy and inert carbon
- live AMF carbon and AMF necromass carbon
- plant biomass, residue input and harvested yield
- plant-to-AMF carbon transfer
- AMF-derived protected-carbon formation
- heterotrophic and AMF respiration proxies
- soil moisture modifier and temperature modifier
- available phosphorus
- management events
- cumulative carbon input, output and mass-balance residual
- objective score and component metrics
- parameter draw and random seed

Population outputs:

- outcome distributions
- intervention effect distributions
- probability each intervention beats baseline
- Pareto frontier
- policy regret
- recommendation stability across uncertainty draws
- global sensitivity indices
- subgroup performance by soil texture, pH, climate and baseline SOC

## 8. MVP acceptance criteria

The MVP is complete only when all of the following hold:

1. A single field runs deterministically for 20 years.
2. Carbon mass-balance error is below a configured numerical tolerance.
3. The simulator produces no negative pools or non-finite outputs.
4. One thousand synthetic fields can be generated without impossible soil combinations.
5. At least four management strategies can be compared.
6. Scenario-direction tests pass.
7. Parameter uncertainty produces output distributions rather than a single falsely precise trajectory.
8. An optimiser is compared with random, global-policy and oracle baselines.
9. Results can be exported to Parquet/CSV with a complete scenario manifest.
10. A dashboard can reproduce at least one published case study from saved configuration.
11. Documentation distinguishes verification, calibration and external validation.
12. The README contains a direct statement that synthetic success is not field validation.

## 9. Definition of scientific success

The project succeeds scientifically if it reveals:

- which recommendations are robust to plausible uncertainty;
- where recommendations are fragile or reverse;
- which parameters dominate predicted carbon outcomes;
- whether AMF-centred policies differ across field archetypes;
- what real measurements and experiments are needed next.

A dramatic carbon gain is not required. Finding that the idea is highly uncertain or only beneficial in limited field classes would still be a valid and valuable result.

## Current implementation boundary

Version `0.9.0` implements a downstream offline synthetic Phase 9 selection and
oracle-regret benchmark using exact frozen Phase 8.6 observable artifacts.
Utility weights and constraints are visible scenario choices; unsupported
inputs abstain; final outcomes cannot tune selectors. The uncertainty-aware
tail-safety gate fails, so further recommendation-system development is not
justified. See `PHASE9_EVIDENCE.md`. All evidence remains synthetic and non-
causal.

## Phase 9.6 implementation boundary

Version `0.9.6` grounds synthetic population inputs in an immutable paired
56-location soil-climate pilot and reports empirical covariance, but management
effects remain simulator-generated. The long-term exercise validates only
total SOC behaviour in the RothC-style core. It does not validate AMF dynamics
or `protected_soc` as measured MAOC. No field recommendation, deployment or
real-world causal claim is authorised, and publication remains blocked pending
independent re-audit and audit-source reconciliation.

## Phase 9.7 implementation boundary

Version `0.9.7` changes no Phase 3--6 biological equation. It corrects the
Phase 9.6 artifact replay, Sobol design, convergence study, scientific gate
computation, uncertainty-coverage rule, FYM boundary disclosure and publication
wording. The 56-location paired pilot is not nationally representative;
generated fields retain synthetic perturbations and latent priors. Failed
prediction/OOD and independent-effect-validation gates continue to block
selection/regret work and any agricultural prediction claim.
