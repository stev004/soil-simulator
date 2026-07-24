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

### Phase 3 implementation boundary

The deterministic Phase 3 core implements the official RothC temperature,
accumulated topsoil-moisture-deficit and cover modifiers, multiplies them with
each active pool's decay rate, and applies the official clay-dependent split
between CO2 and retained BIO+HUM. Retained carbon is routed 46% to microbial
biomass and 54% to the humified/protected proxy. IOM remains unchanged. Every
positive external input, respiration loss and internal retained-carbon
transfer is recorded immutably, with monthly and cumulative mass balance.
See `CARBON_CORE.md` for equations, sign conventions, authoritative sources,
worked-example parity. Phase 4 resolves the input-order question in favour of
official post-decomposition additions, while retaining an explicit
`legacy_pre_decomposition` compatibility mode for Phase 3 input-bearing runs.

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

### Phase 4 implemented baseline

The Phase 4 scalar baseline implements this equation without the optional AMF
term. Potential NPP is the configured annual value multiplied by a validated
12-month profile. Temperature stress uses a configured piecewise-linear
WOFOST EU15 spring-barley assimilation table. Water stress provisionally maps
the verified RothC moisture modifier linearly from its configured minimum and
maximum onto `[0, 1]`. Available-P stress is the fraction of configured tissue-P
demand that the available pool can meet. The three bounded modifiers are
multiplied and the product is bounded to `[0, 1]`.

P input precedes uptake; uptake cannot exceed either demand or stock. The
remaining available-P pool is non-negative and has its own immutable flux
records and monthly/cumulative balance. Plant P is outside the available-P
boundary after uptake; P recycling, sorption, weathering and loss processes
remain deferred.

Realised NPP is split into shoot/root carbon using the configured root
fraction. A scenario-scheduled harvest applies configured harvest index,
above-ground residue-retention fraction, root-residue fraction and carbon to
dry-matter conversion. Grain and removed biomass leave explicit boundaries;
retained shoot and root residues enter DPM/RPM using the configured 1.44 ratio.
Generated residues enter after that month's decomposition and first become
available for decay in the following month. Full equations, units, source
qualifications and migration behaviour are in `PLANT_PHOSPHORUS_BASELINE.md`.

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

### Phase 5 implemented boundary

Version `0.5.0` implements sections 7.1--7.6 as a separate deterministic
orchestrator over the verified Phase 4 interfaces. Root and fungal P pathways
use separate aggregate Michaelis--Menten kinetics but withdraw from one
available-P stock. Gross realised plant carbon is calculated from P actually
received; AMF allocation is then subtracted before shoot/root partitioning.
The CUE complement is recorded as growth plus an operational maintenance share
associated with replacing current turnover. Pre-existing necromass decays and
routes to DPM, RPM and the protected/humified proxy after the current RothC
decomposition step. A parallel no-AMF path reports beneficial, neutral or
harmful plant-carbon and yield effects. Full equations, qualifications and
sources are in `AMF_EXTENSION.md`.

No direct equation links live fungal biomass to protected carbon. Protection
requires necromass decay and a configured routing fraction. The root P kinetic
scale, environmental coupling, respiration split and necromass fractions are
provisional assumptions A021--A025, not calibrated biological constants.

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

### Phase 6 implemented boundary

Version `0.6.0` implements immutable date- or month-scheduled management
events, deterministic same-month ordering, conventional/reduced/no-till
disturbance, seasonal generic AMF-compatible cover cropping, exact available-P
application and post-decomposition FYM carbon/P input. Tillage effect sizes,
cover growth/water/P routing, FYM P content, cost and emissions values remain
explicit provisional scenario assumptions. Carbon and P boundaries include
carried cover stocks, and every represented transfer is immutable and
traceable. See `MANAGEMENT_INTERVENTIONS.md` for equations and ordering.

### Phase 7 population boundary

Version `0.7.0` constructs validated Phase 6 inputs without changing any
mechanistic equation. Each virtual field starts from one jointly coherent,
versioned seed record. Texture is perturbed in additive-log-ratio space;
SOC, CEC, total N and bulk density share a latent soil factor; available P and
AMF stocks retain seed and management context. Every variable is bounded.
Monthly temperature, rainfall and PET are sampled only as complete regional
weather years.

AMF allocation, CUE, turnover, necromass stabilisation, P-acquisition scale,
tillage mortality and a future cover-establishment latent are explicit draws
with distribution, classification, seed and provenance. The cover-establishment
draw is recorded but does not alter deterministic Phase 6 cover equations.
Field-specific copied configurations apply the active draws; simulator
equations and shared defaults are immutable.

RothC active pools are spun to a periodic cycle under the sampled coherent
weather sequence and a reference historical carbon input, then the linear
equilibrium state and input are scaled to the requested SOC after IOM and AMF
stocks are accounted for. This is a scenario-assumption initialisation, not a
calibration. See `SYNTHETIC_POPULATIONS.md` and assumptions A032--A039.

### Phase 8/8.5/8.6 ML boundary

Versions `0.8.5` and `0.8.6` add no biological equation, parameter effect or carbon/P
transfer. A separate downstream ML package joins saved Phase 7 field records
to saved Phase 6 outcomes and predicts fourteen explicit targets: seven final
or cumulative outcomes and their same-field, same-horizon differences from
baseline. The primary observable registry excludes initial AMF/RothC pools,
spin-up diagnostics, latent biological draws, IDs, split labels, archetypes and
all target-derived quantities. A full-state registry includes hidden simulator
information for diagnostic comparison only. See `ML_BENCHMARKING.md` and
assumptions A040--A043.

Phase 8.5 changes only population covariance, evaluation partitions, horizons,
observable summaries and downstream modelling. The verified Phase 3--6
equations and event effects are unchanged. Ten-year weather forcing resamples
complete coherent synthetic weather years; management events remain the
existing Phase 6 schedules and are not silently repeated beyond their dates.
See assumptions A044--A049.

Phase 8.6 changes only repeated experiment orchestration, independent seed
streams, downstream model selection, five weather stress fixtures,
target/regime residual calibration and the final-evaluation freeze. It does not
alter Phase 3--6 state transitions, fluxes, parameters or event effects. See
assumptions A051--A056.

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

## 13. Phase 9 selection boundary

Version `0.9.0` adds no biological equation, state transition, carbon or
phosphorus route, or hidden feature. It consumes exact frozen Phase 8.6
observable artifacts in a separate offline selection package. Training/
validation-only normalisation combines 24-month yield, 5/10-year total SOC,
5/10-year protected-SOC proxy, cost and emissions proxy under four explicit
scenario profiles. Oracle outcomes are inaccessible until selection is fixed.
See assumptions A057--A064 and `PHASE9_EVIDENCE.md`.

## 14. Phase 9.5 scientific/accounting boundary

Version `0.9.5` does not change a carbon or phosphorus equation. It changes the
benchmark boundary in four explicit ways:

1. the biologically null `no_till` marker is removed from the policy set;
2. intervention events recur at explicit schedule intervals through the
   requested horizon, with complete cover establishment/termination pairs;
3. cost, operational-emissions and partial lifecycle-emissions totals are
   accrued from external event schedules and never enter carbon or phosphorus
   mass balance;
4. ML primary targets are paired biological effects only. Stock levels and
   deterministic accounting identities are diagnostics, not skill targets.

Phosphorus ablations alter only declared event dose or the registered
half-saturation assumptions. They do not recalibrate the growth equation.
`protected_soc` remains a model proxy and is not measured MAOC. See assumptions
A065--A076 and `PHASE95_REMEDIATION.md`.

## 15. Phase 9.6 model status

Version `0.9.6` changes no mechanistic carbon, phosphorus, AMF or management
equation. It replaces an authored Hoosfield weather pattern only in the
validation reconstruction, and optional calibration varies two explicit
historical carbon-input factors rather than RothC constants. Empirical
soil-climate covariance affects population inputs; latent AMF/P priors and
mechanistic relationships remain separately labelled. `protected_soc` remains
a model proxy and is not measured MAOC. See assumptions A077--A085.

## 16. Phase 9.7 audit-closure status

Version `0.9.7` changes no mechanistic carbon, phosphorus, AMF or management
equation and does not widen the FYM calibration bound. It replaces only
downstream sampling, estimator, evidence-gate, manifest and reporting logic.
See assumptions A086--A092.
