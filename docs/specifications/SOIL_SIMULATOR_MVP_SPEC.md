# Soil Simulator

A research-grade MVP specification for a synthetic-field simulator that tests whether management strategies can increase arbuscular-mycorrhizal-fungal (AMF) carbon transfer into persistent soil-carbon pools without unacceptable yield or cost penalties.

## Core question

Can a constrained, literature-informed soil–plant–AMF simulator identify management strategies that robustly improve persistent soil carbon across realistic populations of temperate arable fields?

## MVP boundary

- UK temperate, non-waterlogged arable topsoil
- 0–23 cm soil layer
- Spring barley as the first crop system
- Optional winter cover crop
- Monthly time step
- 20-year simulation horizon
- Synthetic field populations; empirical soil-climate grounding remains incomplete
- RothC-inspired soil-carbon core with explicit AMF live-biomass and necromass pools
- Four initial interventions: tillage intensity, cover crop, phosphorus input and organic amendment
- Multi-objective optimisation over protected carbon, yield, emissions proxy and cost
- No claim of real-world agronomic validation

## Documents

- `docs/MVP_SPEC.md` — scientific and product scope
- `docs/MODEL_SPEC.md` — state variables, equations and parameters
- `docs/SYNTHETIC_POPULATIONS.md` — generation of realistic virtual fields
- `docs/VALIDATION_PLAN.md` — verification, validation and optimiser evaluation
- `docs/ARCHITECTURE.md` — codebase and technology design
- `docs/ML_BENCHMARKING.md` — Phase 8 dataset, leakage, models and evaluation
- `docs/ROADMAP.md` — build sequence and realistic schedule
- `docs/REFERENCES.md` — primary and official sources
- `AGENTS.md` — instructions for Codex and other coding agents
- `docs/prompts/01_bootstrap_soil_simulator.md` — first implementation task
- `config/model_defaults.yaml` — initial, explicitly provisional model parameters

## Scientific claim boundary

This MVP can demonstrate internal coherence, sensitivity, robust optimisation and hypothesis generation. It cannot demonstrate that a recommended intervention will work on a real farm until the model is calibrated and tested against independent field observations.

## Current implementation status

Package/configuration version `0.9.7` implements targeted audit closure without
changing the verified Phase 3--6 equations. It corrects the Sobol design,
convergence study, artifact replay, computed ML/readiness gates, target-specific
coverage and FYM boundary reporting. The 56-location paired pilot is not
nationally representative and generated fields retain synthetic perturbations
and latent priors. Failed prediction/OOD and independent empirical effect-
validation gates block selection/regret work. See the Phase 9.7 reports; no
result establishes field causality or an agricultural recommendation.


---

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


---

# Model Specification

## 1. Model form

A discrete monthly state-transition model:

\[
\mathbf{x}_{t+1} = F(\mathbf{x}_t,\mathbf{u}_t,\mathbf{w}_t,\boldsymbol{\theta}) + \boldsymbol{\epsilon}_t
\]

where:

- \(\mathbf{x}_t\) is the field state;
- \(\mathbf{u}_t\) is management;
- \(\mathbf{w}_t\) is weather;
- \(\boldsymbol{\theta}\) is the parameter set;
- \(\boldsymbol{\epsilon}_t\) is optional process noise used only in stochastic experiments.

The simulation kernel must be deterministic for fixed inputs, parameters and seed.

## 2. Units

Primary carbon unit: `t C ha-1`.

Other units:

- temperature: `°C`
- precipitation/PET: `mm month-1`
- soil depth: `cm`
- clay/sand/silt: `% mass`
- bulk density: `g cm-3`
- available P: `kg P ha-1` or a documented dimensionless index in the earliest prototype
- crop yield: `t dry matter ha-1`
- rates: explicitly `month-1` or `year-1`

Never mix CO2 mass with carbon mass inside the kernel. Convert only for reporting using 44/12.

## 3. Immutable field properties

- `field_id`
- latitude and longitude or synthetic archetype
- soil depth
- clay, silt and sand fractions
- bulk density
- pH
- cation exchange capacity
- baseline total nitrogen
- baseline SOC stock
- drainage class
- climate-normal identifier

Texture fractions must approximately sum to 100%.

## 4. Dynamic state variables

### Carbon pools

1. `plant_c`
2. `root_c`
3. `amf_live_c`
4. `amf_necromass_c`
5. `dpm_c` — decomposable plant material
6. `rpm_c` — resistant plant material
7. `microbial_c` — non-AMF microbial biomass proxy
8. `protected_soc_c` — humified/protected SOC proxy
9. `iom_c` — inert organic matter

### Supporting states

10. `available_p`
11. `topsoil_moisture_deficit`
12. `crop_development`
13. `cumulative_yield`
14. `aggregate_protection_index` — optional in v0.1; otherwise derive from clay and management

## 5. RothC-inspired decomposition core

For active pool \(Y\):

\[
Y_{t+1}^{\mathrm{remaining}} =
Y_t \exp(-k_Y a_t b_t c_t / 12)
\]

and decomposed carbon:

\[
D_{Y,t} = Y_t - Y_{t+1}^{\mathrm{remaining}}
\]

Established annual rate constants used as the initial reference:

- DPM: 10.0 year⁻¹
- RPM: 0.3 year⁻¹
- microbial biomass: 0.66 year⁻¹
- protected/humified pool: 0.02 year⁻¹

These are reference-model constants, not AMF-specific measurements.

### Temperature modifier

Use the official RothC temperature modifier:

\[
a(T) = \frac{47.91}{1 + \exp(106.06/(T + 18.27))}
\]

Guard against the singularity near \(-18.27 °C\) and define behaviour outside the intended topsoil climate range.

### Moisture modifier

Implement the official RothC accumulated topsoil moisture-deficit calculation for the 0–23 cm layer in the first verified version. Required inputs are monthly precipitation and PET/open-pan evaporation equivalent. Do not substitute an undocumented generic moisture curve.

### Soil-cover modifier

Use a transparent cover modifier compatible with RothC, then separately model the AMF benefit of a living host. Soil cover and AMF host presence are not interchangeable.

### Carbon partition after decomposition

Implement the clay-dependent RothC split between CO2 and retained BIO + HUM, followed by the standard split of retained carbon into:

- 46% microbial biomass
- 54% humified/protected carbon

The exact clay-dependent equation must be copied from the official model description and covered by parity tests.

## 6. Plant module

### v0.1 approach

Use a prescribed monthly potential carbon-growth profile for spring barley, modified by:

- temperature suitability;
- water stress;
- phosphorus stress;
- optional AMF phosphorus benefit.

This is deliberately simpler than DSSAT/APSIM. It isolates the fungal-carbon hypothesis while retaining feedback between crop production and below-ground carbon input.

\[
\mathrm{NPP}_t =
\mathrm{NPP}^{pot}_t
f_T^{plant}(T_t)
f_W^{plant}(W_t)
f_P(P_t, P^{AMF}_t)
\]

Partition NPP into shoot, root and AMF transfers.

At harvest:

- remove harvested grain carbon;
- transfer configured shoot and root residue fractions to DPM/RPM;
- reset annual crop-development state;
- retain AMF according to host-loss mortality rules.

### Plant residue split

For agricultural crops and improved grassland, initialise the DPM/RPM ratio at 1.44, corresponding to approximately 59% DPM and 41% RPM in the RothC reference.

### Yield

Yield is a reporting output based on harvestable above-ground carbon and a configurable carbon-to-dry-matter conversion. It is not intended to reproduce cultivar-level yield in v0.1.

## 7. AMF module

### 7.1 Plant carbon allocation

\[
C^{plant\to AMF}_t =
\mathrm{NPP}_t \cdot q^{AMF}_t
\]

The allocation fraction is bounded:

\[
q^{AMF}_t =
\operatorname{clip}
\left(
q_0
\cdot f_{P\ limitation}
\cdot f_{host}
\cdot f_{management}
\cdot f_{stress},
q_{min}, q_{max}
\right)
\]

Initial prior:

- centre near 0.062 of photosynthate;
- broad plausible range 0.02–0.20;
- treat as uncertain and context-dependent.

Do not encode “more AMF is always better.”

### 7.2 AMF growth and respiration

\[
G^{AMF}_t = C^{plant\to AMF}_t \cdot CUE_{AMF}
\]

\[
R^{AMF}_t = C^{plant\to AMF}_t - G^{AMF}_t
\]

`CUE_AMF` is a provisional modelling prior, not a universal measured constant.

### 7.3 Turnover

\[
Turnover^{AMF}_t =
AMF^{live}_t
\left(1-\exp(-k^{AMF}_t)\right)
\]

Use a broad turnover prior because published estimates span roughly 0.1–6 turnovers per month and some experiments report a dominant short-lived hyphal fraction of days. Run this parameter through global sensitivity analysis.

Management and host-loss events may add pulse mortality.

### 7.4 Necromass

AMF turnover enters `amf_necromass_c`.

Necromass decomposition:

\[
D^{nec}_t =
AMF^{nec}_t
\left(1-\exp(-k_{nec} a_t b_t / 12)\right)
\]

Phase 5 routes decomposed necromass into configured DPM, RPM and protected SOC
proxy fractions that sum to one. This implemented routing supersedes the
earlier conceptual CO2/microbial/protected sketch: subsequent DPM/RPM decay
uses the verified RothC pathway and therefore makes respiration and microbial
transfer explicit rather than immediate.

The protected fraction is an increasing, saturating function of clay/CEC and remaining protection capacity:

\[
s_t =
s_{min} +
(s_{max}-s_{min})
\cdot f_{clay}
\cdot f_{capacity}
\cdot f_{aggregation}
\]

This relationship is explicitly a hypothesis. It must be identifiable in the assumptions registry and varied widely.

### 7.5 AMF phosphorus acquisition

Use a bounded Michaelis–Menten-style function:

\[
P^{AMF}_t =
V_{max,P}
AMF^{live}_t
\frac{P_t}{K_{m,P}+P_t}
f_W^{AMF}
f_T^{AMF}
\]

The plant receives a configurable fraction of fungal P acquisition. Fungal P uptake cannot exceed soil available P.

### 7.6 High phosphorus feedback

High available P reduces the plant’s incentive to allocate carbon to AMF. Implement as a smooth response, not a hard threshold:

\[
f_{P\ limitation} =
f_{min} +
(1-f_{min})
\frac{K_P}{K_P + P_t}
\]

This allows high P to increase plant growth directly while suppressing fungal allocation, creating a meaningful trade-off.

## 8. Inert organic matter

Initialise IOM with the RothC reference approximation when only total SOC is known:

\[
IOM = 0.049 \cdot TOC^{1.139}
\]

This approximation is for surface soils and should be flagged as uncertain.

## 9. Management interventions

### A. Tillage intensity

Levels:

- conventional inversion tillage
- reduced tillage
- no till

Effects:

- pulse mortality of AMF live biomass;
- temporary decomposition-rate multiplier;
- altered soil-cover timing;
- optional change to aggregate-protection index;
- management cost.

Numerical effect sizes are scenario assumptions until calibrated.

### B. Cover crop

Effects:

- living AMF-compatible host during otherwise bare months;
- additional NPP and root carbon;
- additional water use;
- residue input;
- possible phosphorus competition/recycling;
- establishment cost and failure probability.

Version one should use a generic AM-compatible grass/legume mixture rather than species-specific biology.

### C. Phosphorus input

Effects:

- adds available P;
- may relieve crop P limitation;
- may reduce plant carbon allocation to AMF;
- incurs financial and embodied-emissions penalties.

### D. Organic amendment

Use a farmyard-manure-style input:

- 49% to DPM
- 49% to RPM
- 2% directly to protected/humified pool

Also add a documented nutrient contribution.

### Deferred

- biochar
- direct AMF inoculation
- liming
- irrigation optimisation
- crop rotations
- pesticide effects

These add substantial uncertainty and should follow a stable core.

## 10. Carbon accounting

For each monthly step:

\[
C_{start} + C_{external\ inputs}
=
C_{end} + C_{harvested} + C_{respired} + C_{other\ exports} + \epsilon
\]

`epsilon` must remain within a strict floating-point tolerance. Report both absolute and relative residual.

All fluxes must be recorded in a ledger:

- source pool
- destination pool
- amount
- process
- time
- parameter version

## 11. Objective function

Do not collapse outcomes immediately. Preserve a multi-objective result:

- maximise 20-year change in protected SOC proxy;
- maintain or maximise mean yield;
- minimise cumulative respiration/emissions proxy;
- minimise intervention cost;
- minimise downside risk.

For simple ranking, use a transparent configurable score:

\[
Score =
w_C Z(\Delta C_{protected})
+
w_Y Z(Yield)
-
w_E Z(Emissions)
-
w_K Z(Cost)
-
w_R Z(DownsideRisk)
\]

Always show the unweighted component values and Pareto frontier. The recommendation must not depend invisibly on arbitrary weights.

## 12. Numerical safeguards

- prohibit negative pools;
- cap withdrawals at available stock;
- use stable exponential decay equations;
- validate finite values every step;
- warn when a simulation leaves calibrated/defined parameter ranges;
- never silently clip major mass-balance errors;
- store exact model/config version with every run.


---

# Synthetic Field Populations

## 1. Principle

Synthetic fields must preserve realistic relationships among soil, climate and management variables. Independently sampling every metric from a convenient distribution would create impossible fields and invalidate the optimiser experiment.

The preferred approach is:

> Empirical field archetypes + controlled perturbation + uncertain latent variables.

## 2. Empirical foundation

### Soil

Use SoilGrids properties for the upper layers and aggregate to the 0–23 cm model layer:

- soil organic carbon
- bulk density
- pH
- clay, silt and sand
- cation exchange capacity
- total nitrogen
- SOC stock where available
- uncertainty layers

SoilGrids provides 250 m predictions at standard depth intervals and includes pixel-level uncertainty. For a UK-focused model, compare against national/local data when available.

### Climate

Use ERA5-Land monthly or daily-derived monthly variables:

- mean air temperature
- total precipitation
- potential evapotranspiration or the closest documented variable
- optional soil moisture for validation only

Construct historical monthly climate normals and year-to-year anomalies.

### AMF initial condition

Use the 2026 global AMF mycelial-density dataset as a prior or covariate source. Do not treat predicted density as exact field truth. The dataset combines more than 16,000 soil cores and supplies a useful distributional anchor.

### Validation data

Use Rothamsted e-RA:

- Hoosfield spring barley SOC and yield
- Broadbalk SOC and yield
- Ley–arable SOC transitions

Use these to test soil-carbon dynamics, not to claim validation of the AMF extension unless AMF observations are available.

## 3. Population-generation pipeline

### Step 1: Create empirical seed rows

Each seed row represents a plausible field location and includes jointly observed/predicted soil and climate covariates.

Filter to:

- UK bounding area;
- arable land;
- non-waterlogged mineral soils;
- complete required variables;
- valid texture sums and physical ranges.

### Step 2: Stratify

Create strata across:

- clay content;
- baseline SOC;
- pH;
- rainfall;
- temperature;
- geographic region.

Sample across strata to avoid a population dominated by the most common soil type.

### Step 3: Perturb observed covariates

For each seed row, create synthetic variants using:

- SoilGrids uncertainty where supplied;
- truncated Gaussian/lognormal noise;
- empirical residual covariance;
- bounded perturbations.

Do not perturb sand, silt and clay independently. Use a compositional method or renormalise with explicit tests.

### Step 4: Generate stochastic weather sequences

Initial MVP:

- sample historical whole years or seasonal blocks from ERA5-Land anomalies;
- preserve within-year correlation among temperature, rainfall and PET;
- add optional warming/drying scenarios;
- use separate seeds for weather and biological parameters.

Avoid independently drawing each month from a normal distribution.

### Step 5: Draw latent biological parameters

Draw uncertain values such as:

- AMF allocation fraction;
- AMF turnover;
- AMF carbon-use efficiency;
- necromass stabilisation;
- P acquisition efficiency;
- tillage mortality;
- cover-crop establishment success.

Use hierarchical priors where field properties alter expected values.

Every draw must store:

- distribution;
- parameters;
- source category;
- random seed.

### Step 6: Initialise carbon pools

Options in order of preference:

1. Calibrate/spin up the RothC-inspired pools to the observed baseline SOC under a documented historical management regime.
2. Use inverse-mode logic to estimate annual carbon input required for equilibrium.
3. Use constrained pool fractions only for development tests.

The production population must not initialise all pools using arbitrary fixed percentages.

### Step 7: Quality control

Reject or flag fields with:

- texture total outside tolerance;
- negative stocks;
- implausible bulk density;
- IOM greater than total SOC;
- physically inconsistent SOC concentration/stock;
- climate outside model domain;
- persistent waterlogging;
- numerical instability during spin-up.

## 4. Population sizes

- Unit/development population: 10 fields
- Smoke-test population: 100 fields
- MVP experiment: 1,000 fields
- Robustness run: 10,000 fields if performance permits

For each field, run multiple:

- parameter draws;
- weather sequences;
- policies.

The effective experiment will therefore contain far more trajectories than fields.

## 5. Train/test concept

The simulator is not trained in the usual sense. However, the optimiser or surrogate model must be evaluated out of sample.

Split at the field-archetype level:

- 60% development/optimisation
- 20% validation/tuning
- 20% held-out test

Avoid leakage where near-identical perturbations of the same empirical seed occur in both development and test sets.

## 6. Initial field archetypes

Produce named archetypes for interpretability:

1. Low-clay, low-SOC, drought-prone
2. Low-clay, moderate-SOC, wet
3. Medium-clay, P-limited
4. High-clay, high-SOC
5. Acidic, low-productivity
6. High-input conventional arable
7. Reduced-tillage, cover-cropped
8. High-P, low-AMF-allocation

These are not substitutes for the population; they are explainable case studies.

## 7. Expected population behaviour

Before optimisation, plots should show:

- realistic joint soil distributions;
- different baseline SOC trajectories;
- variation in AMF benefit rather than universal benefit;
- stronger protected-carbon potential in some mineral/texture contexts;
- yield–fungal-allocation trade-offs under some P regimes;
- management effects smaller than field-to-field variation in at least some scenarios.

A simulator where one intervention wins for every field and every parameter draw is probably over-constrained or circular.


---

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

Reproduce at least one worked monthly RothC example and pool update from the official model description.

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


---

# Software Architecture

## 1. Technology choices

### Core

- Python
- NumPy
- pandas or Polars for tabular processing
- xarray for labelled climate arrays
- SciPy for numerical routines
- Pydantic for validated configuration and domain schemas
- PyYAML or TOML configuration
- Parquet for results
- DuckDB for local analytical queries

### Analysis

- scikit-learn for surrogate models and baselines
- Optuna or an evolutionary optimiser after exhaustive baselines
- SALib for global sensitivity analysis
- Matplotlib/Plotly for research plots

### Quality

- pytest
- Hypothesis
- Ruff
- mypy or Pyright
- pre-commit
- GitHub Actions

### Product layer

After the kernel is stable:

- FastAPI
- Next.js + TypeScript
- Tailwind
- a charting library
- Docker Compose

Do not start with the web interface.

## 2. Repository structure

```text
soil_simulator/
├── AGENTS.md
├── README.md
├── pyproject.toml
├── uv.lock
├── config/
│   ├── model_defaults.yaml
│   ├── scenarios/
│   └── populations/
├── docs/
│   ├── MVP_SPEC.md
│   ├── MODEL_SPEC.md
│   ├── SYNTHETIC_POPULATIONS.md
│   ├── VALIDATION_PLAN.md
│   ├── ARCHITECTURE.md
│   ├── ROADMAP.md
│   ├── REFERENCES.md
│   └── ASSUMPTIONS_REGISTER.csv
├── src/soil_simulator/
│   ├── domain/
│   │   ├── state.py
│   │   ├── parameters.py
│   │   ├── weather.py
│   │   └── management.py
│   ├── processes/
│   │   ├── rothc.py
│   │   ├── water.py
│   │   ├── plant.py
│   │   ├── amf.py
│   │   ├── phosphorus.py
│   │   └── interventions.py
│   ├── simulator/
│   │   ├── engine.py
│   │   ├── ledger.py
│   │   └── outputs.py
│   ├── population/
│   │   ├── empirical_seeds.py
│   │   ├── generator.py
│   │   └── quality.py
│   ├── experiments/
│   │   ├── runner.py
│   │   ├── scenarios.py
│   │   └── manifests.py
│   ├── optimisation/
│   │   ├── objective.py
│   │   ├── baselines.py
│   │   └── optimiser.py
│   ├── evaluation/
│   │   ├── validation.py
│   │   ├── sensitivity.py
│   │   └── metrics.py
│   ├── data/
│   │   ├── soilgrids.py
│   │   ├── era5.py
│   │   ├── era.py
│   │   └── amf_density.py
│   └── cli.py
├── tests/
│   ├── unit/
│   ├── properties/
│   ├── parity/
│   ├── scenarios/
│   └── integration/
├── apps/
│   ├── api/
│   └── web/
├── notebooks/
│   └── exploratory-only/
├── data/
│   ├── raw/
│   ├── interim/
│   └── processed/
└── outputs/
```

## 3. Domain objects

### FieldProperties

Immutable physical properties and provenance.

### FieldState

Dynamic monthly state. Must be immutable between steps or copied explicitly to avoid accidental mutation.

### WeatherMonth

Temperature, precipitation, PET and metadata.

### ManagementEvent

Typed event with date, parameters, cost and emissions proxy.

### ModelParameters

Validated, versioned parameter set with source classification.

### FluxLedger

Append-only carbon transfer records.

### SimulationResult

State time series, fluxes, diagnostics and manifest.

## 4. Simulation step order

Use an explicit, documented order:

1. Apply scheduled management events.
2. Update water balance and modifiers.
3. Calculate potential plant production.
4. Calculate P stress and AMF P contribution.
5. Allocate plant carbon.
6. Update plant and root stocks.
7. Update AMF growth, respiration and turnover.
8. Add residues and necromass to soil pools.
9. Decompose soil pools.
10. Partition decomposed carbon.
11. Apply harvest/senescence.
12. Validate stocks and mass balance.
13. Record state, fluxes and diagnostics.

The order is scientifically consequential and must have integration tests.

Phase 4 resolves the RothC integration detail in favour of official ordering:
decompose pools present before the input, then add generated harvest residues.
The earlier pre-decomposition Phase 3 input behaviour remains available only
as an explicit compatibility mode.

## 5. Configuration design

Each parameter record should contain:

- name
- value/default
- unit
- allowed range
- distribution for uncertainty
- source category
- source citation
- notes
- version introduced

Store assumptions in both machine-readable config and a human-readable register.

## 6. Performance strategy

1. Implement and verify scalar single-field simulation.
2. Add batch loops with clear profiling.
3. Vectorise only stable pure calculations.
4. Parallelise at the independent trajectory level.
5. Cache empirical covariate extraction and spin-up states.
6. Write partitioned Parquet rather than retaining every trajectory in RAM.

## 7. Reproducibility

Every experiment writes:

- Git commit
- model version
- configuration hash
- input-data versions
- field IDs
- policy definitions
- random seeds
- environment lockfile
- start/end timestamp
- test-gate status

## 8. API boundary

The API should expose:

- create/validate scenario
- simulate one field
- compare policies
- submit population experiment
- query experiment status
- retrieve summary
- retrieve timeseries

The API must not contain scientific calculations; it calls the package.

## 9. Dashboard pages

1. Project and claim boundary
2. Field builder
3. Scenario comparison
4. Population experiment
5. Optimisation/Pareto results
6. Sensitivity and uncertainty
7. Validation and mass balance
8. Assumptions and sources

## 10. Security and operational constraints

- No secrets in repository.
- External-data downloads are explicit scripts, not hidden at import time.
- Validate uploaded scenarios.
- Apply limits to simulation size in the API.
- Treat generated recommendations as research outputs.
- Include a persistent disclaimer in the interface.


---

# Implementation Roadmap

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


---

# References and Data Sources

These are starting sources, not a complete systematic review.

## Carbon-model foundations

1. Rothamsted Research. **RothC – A model for the turnover of carbon in soil: Model Description** (February 2024).
   - https://www.rothamsted.ac.uk/sites/default/files/Documents/RothC_description.pdf

2. Rothamsted Research. **Rothamsted Carbon Model (RothC)**.
   - https://www.rothamsted.ac.uk/rothamsted-carbon-model-rothc

3. DSSAT. **CENTURY soil organic matter module**.
   - https://dssat.net/models-overview/components/century-organic-matter-module/

4. APSIM. **SoilN model documentation**.
   - https://www.apsim.info/documentation/model-documentation/soil-modules-documentation/soiln/

## AMF data and mechanisms

5. Stewart, J. D. et al. (2026). **Global density and biomass of arbuscular mycorrhizal fungal networks. Science 392.**
   - https://www.science.org/doi/10.1126/science.adu4373

6. Dryad. **Arbuscular mycorrhizal fungal mycelial density database.**
   - https://datadryad.org/dataset/doi:10.5061/dryad.p2ngf1w1f

7. Hawkins, H.-J. et al. (2023). **Mycorrhizal mycelium as a global carbon pool. Current Biology.**
   - https://doi.org/10.1016/j.cub.2023.02.027

8. Staddon, P. L. et al. (2003). **Rapid turnover of hyphae of mycorrhizal fungi determined by AMS microanalysis of 14C. Science.**
   - https://pubmed.ncbi.nlm.nih.gov/12750519/

9. Horsch, C. C. A. et al. (2023). **Trait-based assembly of arbuscular mycorrhizal fungal communities determines soil carbon formation and retention. New Phytologist.**
   - https://pubmed.ncbi.nlm.nih.gov/36978279/

10. Mason, A. R. G. et al. (2025). **Enhanced stabilisation of soil carbon via arbuscular mycorrhizal fungi and biochar. Scientific Reports.**
    - https://www.nature.com/articles/s41598-025-23219-0

11. Bowles, T. M. et al. (2017). **Ecological intensification and arbuscular mycorrhizas: a meta-analysis of tillage and cover crop effects. Journal of Applied Ecology.**
    - https://doi.org/10.1111/1365-2664.12815

## Soil and climate covariates

12. ISRIC. **SoilGrids.**
    - https://isric.org/explore/soilgrids

13. de Sousa, L. M. et al. (2021). **SoilGrids 2.0: producing soil information for the globe with quantified spatial uncertainty. SOIL.**
    - https://soil.copernicus.org/articles/7/217/2021/

14. Copernicus Climate Data Store. **ERA5-Land.**
    - https://cds.climate.copernicus.eu/datasets/reanalysis-era5-land

15. Muñoz-Sabater, J. et al. (2021). **ERA5-Land: a state-of-the-art global reanalysis dataset for land applications. Earth System Science Data.**
    - https://essd.copernicus.org/articles/13/4349/2021/

## Long-term validation

16. e-RA. **Hoosfield soil organic carbon content.**
    - https://www.era.rothamsted.ac.uk/dataset/rhb2/01-HBSOC1852

17. e-RA. **Broadbalk soil organic carbon content 1843–2015.**
    - https://www.era.rothamsted.ac.uk/dataset/rbk1/02-BKSOC1843

18. e-RA. **Rothamsted Ley Arable Soil Organic Carbon 1948–2008.**
    - https://www.era.rothamsted.ac.uk/dataset/rrn1/01-HSOC4808

19. International Soil Radiocarbon Database.
    - https://www.soilradiocarbon.org/

## Codex workflow

20. OpenAI. **Codex cloud documentation.**
    - https://developers.openai.com/codex/cloud

21. OpenAI. **Codex Prompting Guide.**
    - https://developers.openai.com/cookbook/examples/gpt-5/codex_prompting_guide

22. OpenAI. **Unrolling the Codex agent loop.**
    - https://openai.com/index/unrolling-the-codex-agent-loop/


---

# AGENTS.md

## Project purpose

Build `soil_simulator`, a reproducible research simulator for fungal-mediated soil-carbon retention. Scientific correctness and traceability outrank feature speed or visual polish.

## Required reading before changes

Read the relevant files in `docs/`, especially:

- `docs/MVP_SPEC.md`
- `docs/MODEL_SPEC.md`
- `docs/VALIDATION_PLAN.md`
- `docs/ARCHITECTURE.md`

Do not introduce a biological relationship, parameter value or management effect that is absent from the model specification without documenting it in the assumptions registry.

## Non-negotiable engineering rules

1. Preserve carbon mass balance. Every carbon transfer must have an explicit source and destination.
2. Use deterministic random seeds in tests and examples.
3. Keep the mechanistic simulator independent from the optimiser, API and UI.
4. Never let the optimiser mutate simulator equations or hidden parameters.
5. All model parameters must be loaded from validated configuration objects; avoid unexplained numeric literals.
6. Label every parameter as one of:
   - `established_model`
   - `literature_informed_prior`
   - `scenario_assumption`
   - `calibrated`
7. Outputs must include units, uncertainty and provenance.
8. Do not describe `protected_soc` as measured MAOC. It is a model proxy until validated against fractionation data.
9. Do not claim real-world causal validity from synthetic experiments.
10. Add or update tests with every behavioural change.

## Test gates

Before reporting completion, run:

- formatting and linting
- static type checking
- unit tests
- property-based tests
- carbon mass-balance tests
- deterministic replay tests
- scenario-direction regression tests

## Coding style

- Python package first; UI later.
- Small pure functions for flux calculations.
- Typed dataclasses or Pydantic models for domain entities.
- NumPy arrays for population simulation only after scalar correctness is established.
- Keep I/O out of the simulation kernel.
- Write docstrings that state units and scientific assumptions.

## Change reporting

For each task, report:

- files changed
- assumptions added or changed
- tests run
- unresolved scientific uncertainties
- whether outputs changed and why


---

# Codex Task 01 — Bootstrap the Research Repository

Read `AGENTS.md` and all files in `docs/` before editing.

## Goal

Create the Python repository skeleton and scientific configuration contracts for the Soil Simulator. Do not implement biological simulation equations in this task.

## Required work

1. Initialise a modern Python package called `soil_simulator`.
2. Use a reproducible dependency manager and create a lockfile.
3. Add:
   - Pydantic models for `FieldProperties`, `FieldState`, `WeatherMonth`, `ManagementEvent`, `ModelParameter`, `ModelParameters`, `SimulationManifest` and `FluxRecord`.
   - configuration loading for `config/model_defaults.yaml`;
   - enums for parameter source classification;
   - unit-aware field descriptions in docstrings and schema metadata;
   - validation for texture sums, non-negative stocks, finite values, valid fractions and positive depth;
   - a minimal CLI with `validate-config` and `show-model-info`;
   - Ruff, type checking, pytest, Hypothesis, pre-commit and GitHub Actions.
4. Add tests for every validation rule.
5. Add a test proving configuration loading is deterministic and serialises to a stable hash.
6. Add no simulator logic and no dashboard.

## Constraints

- Keep I/O and domain objects separate.
- Avoid untyped dictionaries after configuration parsing.
- Do not add unexplained model parameters.
- Preserve all comments and scientific classifications from the YAML where practical.
- Update documentation only where implementation details require it.
- Do not weaken tests to obtain a pass.

## Acceptance commands

Document and run the repository's equivalents of:

- install/sync
- format check
- lint
- type check
- test

## Completion response

Report:

1. files changed;
2. architecture decisions;
3. commands and test results;
4. assumptions or ambiguities found;
5. exact recommended second Codex task.

Do not claim the simulator exists at the end of this task.


---
