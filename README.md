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
- Synthetic field populations grounded in a 56-location paired soil-climate pilot
- RothC-inspired soil-carbon core with explicit AMF live-biomass and necromass pools
- Four initial interventions: tillage intensity, cover crop, phosphorus input and organic amendment
- Multi-objective optimisation over protected carbon, yield, emissions proxy and cost
- No claim of real-world agronomic validation

## Documents

- `docs/provenance/RESEARCH_ARCHIVE.md` — navigable Phase 9.8 research archive
- `manuscript/PRISM_HANDOFF.md` — bounded Prism starting point and claim controls
- `docs/audits/README.md` — formal independent-audit archive
- `docs/PHASE97_PUBLICATION_READINESS.md` — current audited scientific boundary

- `docs/MVP_SPEC.md` — scientific and product scope
- `docs/MODEL_SPEC.md` — state variables, equations and parameters
- `docs/SYNTHETIC_POPULATIONS.md` — generation of realistic virtual fields
- `docs/VALIDATION_PLAN.md` — verification, validation and optimiser evaluation
- `docs/ARCHITECTURE.md` — codebase and technology design
- `docs/PLANT_PHOSPHORUS_BASELINE.md` — Phase 4 crop/P equations and accounting
- `docs/AMF_EXTENSION.md` — Phase 5 AMF carbon/P equations and accounting
- `docs/MANAGEMENT_INTERVENTIONS.md` — Phase 6 schedules, accounting and ordering
- `docs/PHASE7_DEMONSTRATION.md` — reproducible 1,000-field verification results
- `docs/ML_BENCHMARKING.md` — Phase 8 dataset, leakage, models and evaluation
- `docs/PHASE8_DEMONSTRATION.md` — reproducible 1,000-field Phase 8 results
- `docs/PHASE85_DIAGNOSTIC.md` — expanded-group, multi-horizon Phase 8.5 diagnosis
- `docs/PHASE86_EVIDENCE.md` — repeated-population and frozen-final Phase 8.6 evidence
- `docs/PHASE9_EVIDENCE.md` — offline synthetic selection and oracle-regret evidence
- `docs/PHASE95_REMEDIATION.md` — audited-baseline preservation and scientific remediation
- `docs/PHASE95_SENSITIVITY.md` — Morris/Sobol specification, results and limitations
- `docs/PHASE95_PHOSPHORUS_ABLATION.md` — phosphorus structural-loop ablations
- `docs/PHASE95_LONG_TERM_VALIDATION.md` — uncalibrated Hoosfield validation
- `docs/PHASE95_PUBLICATION_READINESS.md` — fail-closed manuscript-readiness gates
- `docs/PHASE96_EMPIRICAL_GROUNDING.md` — paired-source pilot and covariance evidence
- `docs/PHASE96_LONG_TERM_DIAGNOSIS.md` — source-corrected Hoosfield diagnosis
- `docs/PHASE96_CALIBRATION_VALIDATION.md` — optional bounded/held-out validation
- `docs/PHASE96_POPULATION_SENSITIVITY.md` — population-aware Morris/Sobol evidence
- `docs/PHASE96_PUBLICATION_READINESS.md` — independent re-audit readiness gates
- `docs/PHASE97_AUDIT_CLOSURE.md` — targeted clean-slate re-audit defect closure
- `docs/PHASE97_SENSITIVITY_CORRECTION.md` — genuine Sobol design and convergence rule
- `docs/PHASE97_GATE_CORRECTION.md` — computed leakage, validation and coverage gates
- `docs/PHASE97_CALIBRATION_BOUNDARY.md` — FYM boundary-objective profile
- `docs/PHASE97_PUBLICATION_READINESS.md` — corrected publication claim boundary
- `docs/ROADMAP.md` — build sequence and realistic schedule
- `docs/REFERENCES.md` — primary and official sources
- `AGENTS.md` — instructions for Codex and other coding agents
- `docs/prompts/01_bootstrap_soil_simulator.md` — first implementation task
- `config/model_defaults.yaml` — initial, explicitly provisional model parameters

## Project structure

- `src/` — authoritative Python package source
- `config/` — validated model and experiment configuration
- `data/` — input and validation data
- `outputs/` — frozen generated scientific outputs
- `manuscript/current/` — authoritative current manuscript package
- `docs/specifications/` — consolidated project specifications
- `docs/provenance/` — research-provenance indexes
- `docs/prompts/` — preserved historical prompts
- `audits/incoming/` — immutable incoming audit material
- `docs/maintenance/REPOSITORY_STRUCTURE.md` — complete repository layout and
  preservation rules

## Scientific claim boundary

This MVP can demonstrate internal coherence, sensitivity, robust optimisation and hypothesis generation. It cannot demonstrate that a recommended intervention will work on a real farm until the model is calibrated and tested against independent field observations.

## Implementation status

Phase 9.8 packages the verified v0.9.7 evidence into `docs/audits/` and
`manuscript/` without changing scientific equations, parameters, datasets,
results, gates or frozen historical outputs. See
`docs/provenance/RESEARCH_ARCHIVE.md`.
The independent v0.9.0, Phase 9.6 clean-slate and Phase 9.7 focused re-audit
deliverables are archived. The ten restored deliverables match their supplied
export-manifest hashes and byte sizes. The focused re-audit cleared bounded
methodological/software/portfolio drafting while retaining all scientific
claim prohibitions.

Package version `0.9.7` implements targeted Phase 9.7 audit closure while
preserving `outputs/phase9_v0.9.0/` and `outputs/phase95_v0.9.5/` as historical
baselines and retaining `outputs/phase96_v0.9.6/` unchanged. Phase 9.7 replaces
the incorrectly labelled pseudorandom Sobol design with SciPy's scrambled Sobol
engine and Saltelli/Jansen estimators, runs a power-of-two convergence sequence,
computes every ML/readiness gate from artifacts, applies target/regime-specific
coverage rules, and profiles the FYM calibration boundary.

The 56 paired real soil--climate locations are an empirical pilot, not a
nationally representative sample. Generated descendants retain synthetic
within-location perturbations and latent AMF/P priors. The source-corrected
Hoosfield forcing improves uncalibrated total-SOC performance, but held-out FYM
cessation performance remains weak and the upper-bound FYM calibration is not
successful general calibration. `protected_soc` remains a model proxy, not
measured MAOC.

Phase 9.7 remains blocked as an agricultural prediction system: effect-
prediction/OOD gates do not all pass and no independent empirical intervention-
effect dataset validates management responses. Consequently no new selector,
oracle-agreement or regret benchmark is run. The current evidence supports a
portfolio case study and supports a bounded methodological or software paper
under the focused independent re-audit; it does not support an agricultural
prediction paper. See
`docs/PHASE97_PUBLICATION_READINESS.md`.

The frozen version `0.9.0` implements Phase 9 offline synthetic
intervention-selection and oracle-regret benchmarking using the exact frozen
Phase 8.6 observable models. Ten new populations plus one later-instantiated
frozen-final population compare simple, observable-ML, uncertainty-aware and
simulator-oracle selectors across four visible scenario utility profiles.

Applicability enforcement produces zero unsupported non-abstaining selections.
Point ML is competitive with simple baselines, but every uncertainty-aware
variant worsens worst-decile or catastrophic regret. The predeclared Phase 9
gates therefore fail and further recommendation-system development is not
justified. See `docs/PHASE9_EVIDENCE.md`; no synthetic result establishes field
validity.

The underlying simulator retains explicit living fungal biomass,
fungal necromass, plant carbon allocation, growth/maintenance respiration,
turnover, necromass routing and stock-capped AMF phosphorus acquisition and
transfer. A parallel no-AMF counterfactual reports beneficial, neutral or
harmful net plant-carbon and yield effects without assuming AMF is beneficial.
Immutable carbon and P records verify monthly and cumulative mass balance, and
deterministic results retain configuration hashes, units and provenance.

The January 1852 Hoosfield RothC example remains within published precision.
See `docs/CARBON_CORE.md`, `docs/PLANT_PHOSPHORUS_BASELINE.md`,
`docs/AMF_EXTENSION.md` and `docs/MANAGEMENT_INTERVENTIONS.md` for equations,
source traceability, migration details, units and claim boundaries.

AMF species/community biology, fungal P storage/recycling, a general crop water
balance beyond provisional RothC-TSMD coupling, soil-P chemistry, real-field
recommendations, API and dashboard functionality are not implemented.
`protected_soc` remains a model proxy and is not measured MAOC. Passing
verification is not field validation or evidence of real-world causality.

The project uses [uv](https://docs.astral.sh/uv/) with a committed lockfile. From the repository root:

```bash
uv sync --frozen --extra dev
uv run ruff format --check .
uv run ruff check .
uv run mypy
uv run pytest
```

The CLI validates configuration, displays the scientific boundary, runs the
versioned carbon-core/spring-barley scenarios, compares predefined Phase 6
management policies without ranking them, generates populations, or runs
eligible interventions across a population. Phase 7 commands print readable
tables and write complete JSON only when `--json-output` is supplied. Phase 8.5
remains reproducible for historical comparison. Phase 8.6 builds repeated
development populations, freezes its protocol, evaluates one new final
population and writes deterministic model/data/configuration hashes:

```bash
uv run soil-simulator validate-config
uv run soil-simulator show-model-info
uv run soil-simulator run-carbon-core
uv run soil-simulator run-spring-barley
uv run soil-simulator compare-management
uv run soil-simulator generate-population --count 1000 --json-output population.json
uv run soil-simulator run-population-batch --count 1000 --json-output batch.json
uv run soil-simulator benchmark-intervention-ml batch.json batch.json \
  --output-dir outputs/phase85_v0.8.5 --json-output phase85-report.json
uv run soil-simulator run-phase85-benchmark \
  --output-dir outputs/phase85_v0.8.5
uv run soil-simulator run-phase86-benchmark \
  --output-dir outputs/phase86_v0.8.6 --json-output phase86-report.json
uv run soil-simulator run-phase9-benchmark \
  --output-dir outputs/phase9_v0.9.0 --json-output phase9-report.json
.venv/bin/python -m soil_simulator.phase95.pipeline
.venv/bin/python -m soil_simulator.phase97.pipeline
```

The checked-in Phase 7 data path is
`data/processed/phase7_empirical_seed_fixture_v1.yaml`; tests never download
changing external data. Synthetic population, intervention or ML benchmark
success is not field validation, causal evidence or an agronomic
recommendation. The full-state model is diagnostic only.
