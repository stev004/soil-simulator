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

### RothCForcing / CarbonCoreMonth

Phase 3 uses an immutable monthly RothC forcing contract containing mean air
temperature, precipitation, open-pan evaporation equivalent, physical soil
cover, clay content, soil depth and provenance. `CarbonCoreMonth` pairs that
forcing with explicit external carbon inputs. Accumulated TSMD remains in the
immutable field state so moisture history is replayable.

Phase 4 adds immutable `PlantMonth`, `PlantStepResult`,
`PlantSimulationResult`, plant-stress diagnostics, a phosphorus flux record
and separate carbon/P mass-balance diagnostics. Pure plant and P equations
remain under `processes/`; `simulator/plant_baseline.py` composes them with the
scalar RothC kernel.

Phase 5 adds immutable `AmfStepResult`, `AmfSimulationResult`, an AMF-aware P
balance diagnostic and explicit AMF carbon/P flux records. Pure allocation,
growth/respiration, turnover, necromass and fungal P equations live in
`processes/amf.py`; `simulator/amf_extension.py` composes them with the fixed
plant and RothC kernels and advances a parallel no-AMF counterfactual.

Phase 6 adds immutable `ManagementEvent`, `ManagementPolicy`,
`ManagementScenarioSet`, carried `ManagementRuntimeState`, monthly managed
balance diagnostics and policy comparison results. Phase 3--5 entry points
remain unchanged. `simulator/management.py` composes scheduled transfers and
temporary configured multipliers around the verified Phase 5 step; the CLI
contains reporting only.

Phase 7 adds immutable `EmpiricalDataset`, `SyntheticField`, uncertainty draw,
spin-up, QC, manifest and batch-result contracts. `population/adapters.py` is
the only empirical seed/weather filesystem boundary and performs no downloads;
`population/generator.py` owns deterministic perturbation, weather resampling,
group splits and manifests; `population/spinup.py` initialises RothC pools;
`population/quality.py` rejects invalid candidates; `population/batch.py`
constructs field-specific Phase 6 scenarios and copied parameter draws;
`population/reporting.py` contains summaries and tables. None is imported by
the scalar mechanistic kernel.

Phase 8 adds a downstream `ml/` package with explicit dataset, preprocessing,
model, evaluation and pipeline modules. It consumes serialized Phase 7/6
contracts and is not imported by the scalar mechanistic kernel. Artifacts use
stable CSV/JSON/Markdown rather than Python object pickles: feature registries,
training-fit preprocessing state, baseline/linear/tree models, conformal
calibration, evaluation and hashes are inspectable without executing code.

Phase 8.5 adds `population/foundation.py` as a deterministic synthetic fixture
expander and extends the existing batch boundary to accept explicit horizons.
Neither is imported by the mechanistic kernel. `PopulationSplit` includes
dedicated archetype/weather OOD values; preprocessing still accepts training
rows only. Models are serialized per target and valid horizon so 24-month yield
cannot silently train on 5- or 10-year rows. The CLI end-to-end command writes
the saved population/batch before fitting any ML artifact.

### ManagementEvent

Typed event with date, parameters, cost and emissions proxy.

### ModelParameters

Validated, versioned parameter set with source classification.

### FluxLedger

Append-only carbon transfer records.

### SimulationResult

State time series, fluxes, diagnostics and manifest.

The Phase 3/4 scalar kernels remain independent of CLI and configuration I/O.
Pure modifier and partition functions live in `processes/rothc.py`; monthly
orchestration, immutable flux creation and mass-balance checks live under
`simulator/`.

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

For the implemented no-AMF Phase 4 baseline, the concrete order is:

1. Resolve calendar-month potential NPP and RothC moisture history.
2. Apply temperature and water stress.
3. Add optional external available P, calculate P demand/stress and withdraw
   bounded uptake.
4. Multiply bounded stress modifiers and allocate realised NPP to shoot/root.
5. Decompose and route RothC pools present before this month's residue return.
6. Apply scheduled harvest and route retained shoot/root residues to DPM/RPM.
7. Validate immutable state and monthly carbon/P balances.

Step 5 before step 6 is the official-compatible RothC input-order decision.
The older Phase 3 pre-decomposition external-input behaviour remains available
only through explicit `legacy_pre_decomposition` configuration.

For Phase 5, AMF P acquisition and transfer precede finite direct-root uptake;
both withdraw from the same available-P stock. Plant carbon allocation,
fungal respiration and turnover are then resolved before RothC decomposition.
Only pre-existing necromass routes after decomposition, followed by harvest
residues, so neither new necromass nor residues decay in their creation month.

For Phase 6, same-month events are ordered P application, tillage, cover
termination, manure staging and cover establishment, with event ID as the
within-type tie-breaker. P application enters before Phase 5 uptake. Tillage
mortality is an immediate live-AMF-to-necromass transfer. Tillage-incorporated
biomass, terminated cover residue and FYM carbon are staged until after Phase 5
decomposition; FYM and returned cover P are added after the month's uptake.
Active-cover growth then uses remaining P and is carried separately. This
scientifically consequential order has unit and integration tests.

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

Phase 7 keeps the verified scalar loop for correctness. Phase 8 exports a
stable versioned CSV because the current 1,000-field fixture is compact; a
partitioned Parquet backend remains appropriate when repeated populations or
10,000-field experiments make CSV impractical.

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

## 11. Phase 9 downstream selection boundary

Phase 9 adds a downstream `selection/` package. `artifacts.py` verifies exact
Phase 8.6 semantic hashes and enforces target/weather, observable-feature,
uncertainty and eligibility contracts. `core.py` contains pure unit-labelled
utility, constraint, oracle, regret and catastrophic-failure calculations.
`selectors.py` cannot receive simulator outcomes; `benchmark.py` freezes
training/validation-only normalisation and simple selector state before
revealing untouched outcomes. The mechanistic kernel imports none of these
modules, and the oracle is called only after non-oracle decisions are fixed.

## 12. Phase 9.6 evidence boundary

`phase96/empirical.py` is an offline adapter over immutable raw JSON caches;
network access exists only in `scripts/download_phase96_empirical.py`.
`phase96/statistics.py`, `validation.py`, `sensitivity.py` and `effect_ml.py`
remain downstream of the unchanged mechanistic simulator. `pipeline.py`
regenerates processed records, manifests, evidence tables, figures and hashes.
It cannot alter simulator equations or hidden parameters. Group assignments are
made by empirical location before ML fitting, and selector/regret work is
fail-closed when any required gate is false.

## 13. Phase 9.7 correction boundary

`phase97/sensitivity.py` uses SciPy's Sobol engine and pure downstream
Saltelli/Jansen analysis. `phase97/gates.py` computes leakage, independent-
validation, target/regime coverage and downstream eligibility from artifacts.
`phase97/calibration.py` profiles the existing bounded FYM objective without
widening it. `phase97/manifests.py` preserves the historical Phase 9.6 manifest
while issuing a transparent current-byte correction. The mechanistic kernel
imports none of these modules.
