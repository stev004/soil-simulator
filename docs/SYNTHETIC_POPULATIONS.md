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

## 8. Phase 7 implemented boundary

Version `0.7.0` implements the scalar pipeline above without adding ML,
optimisation, recommendations, an API or a dashboard.

### Dataset and adapters

`VersionedLocalYamlAdapter` loads a caller-selected immutable YAML file and
validates dataset, adapter, seed and complete-weather-year versions.
`CachedYamlDatasetAdapter` additionally requires an exact caller-supplied
SHA-256 before loading. Neither performs network access. The bundled
`phase7_empirical_seed_fixture_v1.yaml` supplies ten joint soil/management seed
records and ten complete regional weather years for deterministic tests and the
1,000-field demonstration. It follows SoilGrids/ERA5-Land adapter schemas but
is a local research fixture, not a traceable national extraction and not a
validation dataset (A039). Replacing it with a real cached extraction requires
no generator changes, but does require an explicit new dataset version and
provenance.

### Joint perturbation and archetypes

Seed rows are cycled evenly to avoid frequency dominance. Clay, silt and sand
are perturbed jointly in additive-log-ratio space and always sum to 100%.
A shared Gaussian soil factor induces positive SOC--CEC--total-N and negative
SOC--bulk-density dependence; clay displacement also informs CEC and bulk
density. Available P uses bounded log noise. AMF initial stocks use bounded log
noise and retain a provisional negative high-P coupling. All values remain
within both seed-relative and configured mineral-soil limits.

Implemented named archetypes are:

1. `low-carbon-sandy-field`;
2. `clay-rich-high-carbon-field`;
3. `phosphorus-limited-field`;
4. `drought-prone-field`;
5. `intensively-tilled-low-amf-field`.

They label interpretable strata; they do not assert nationally representative
prevalence.

### Weather, uncertainty and spin-up

Each field samples two complete years from its seed region. Temperature,
rainfall and PET months are never mixed across source years. Separate derived
seeds control field perturbation, weather blocks and biology. Draws record
their distributions, parameters, classification and seed for AMF allocation,
CUE, turnover, necromass stabilisation, P acquisition, tillage mortality and
future cover establishment. The final draw is recorded only; it does not add
stochastic establishment to Phase 6 (A037).

IOM uses the established RothC equation. Active pools are spun under the
repeated complete-weather sequence and a configured reference input until the
periodic-cycle change is at most `2e-5`; the linear active state and implied
annual input are then scaled to target SOC after AMF/IOM stocks. Achieved SOC,
years, residual change, scaled input, classification and provenance are stored.
This initialisation is coherent but provisional, not historical calibration.

### Leakage prevention, QC and batch execution

The deterministic 60/20/20 split is assigned once per empirical seed; all its
perturbations stay together. QC checks finite values, non-negative stocks,
texture, ranges, SOC concentration/stock consistency, specified impossible
combinations, drainage/climate domain, spin-up convergence/closure and a
one-month Phase 6 baseline execution with carbon/P balance. Rejections and
reasons are manifest records.

The population manifest includes generation/config/model/data/adapter versions
and hashes, seed/region/archetype/split/weather IDs, uncertainty draws and all
rejections. The batch runner copies each field's explicit draws into validated
configuration, builds field-specific Phase 6 forcing and runs every eligible
predefined policy. It reports failures and maximum monthly C/P residuals.
Readable CLI tables are the default; complete JSON is written only on explicit
request.

### Remaining scientific limitations

- The local fixture does not establish UK population representativeness.
- Perturbation covariance is designed, not estimated from residual data.
- Initial AMF stocks and their available-P coupling are uncalibrated.
- Spin-up assumes periodic climate and an equilibrium historical carbon input.
- Available P is a model stock, not a direct conversion from a named soil test.
- Latent biological priors can dominate simulated intervention effects.
- `protected_soc_c` remains a model proxy and is not measured MAOC.
- Synthetic execution and balance success are verification, not field validation.
