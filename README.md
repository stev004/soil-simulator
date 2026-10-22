# Soil Simulator

## What this is

A monthly-timestep soil-plant-mycorrhizal carbon simulator for UK temperate arable topsoil (0-23 cm, spring barley, optional winter cover crop, 20-year horizon), and a well-instrumented negative result.

The project asked whether management strategies (tillage intensity, cover crop, phosphorus input, organic amendment) can increase arbuscular-mycorrhizal-fungal (AMF) carbon transfer into persistent soil carbon without unacceptable yield or cost penalties. It did not reach that conclusion. Its own fail-closed publication gates failed, so the downstream selection, oracle and regret benchmarks were never run. Nothing in this repository supports the claim that mycorrhizal management increases persistent soil carbon.

The six gates that failed at version 0.9.7 (`outputs/phase97_v0.9.7/publication_readiness.json`):

1. `sensitivity_converged` - the predeclared Sobol convergence rule is not met at 1,024 base samples, so sensitivity indices stay diagnostic.
2. `prediction_gates_passed` - the effect-prediction and out-of-distribution gates do not all pass.
3. `independent_empirical_effect_validation` - no independent empirical intervention-effect dataset was available to validate management responses.
4. `calibration_not_boundary_constrained` - the farmyard-manure (FYM) calibration ends on a parameter boundary, so it is not a successful general calibration.
5. `held_out_cessation_performance_adequate` - performance on held-out FYM cessation is weak.
6. `focused_independent_reaudit_passed` - the focused independent re-audit has not been completed.

Four other gates pass (artifact integrity, genuine Sobol design, leakage checks, target-specific uncertainty coverage). They do not override the failures. The earlier Phase 9 selector benchmark (v0.9.0) also failed its predeclared gates: every uncertainty-aware variant worsened worst-decile or catastrophic regret.

What does hold up: the RothC-style carbon core reproduces Rothamsted's January 1852 Hoosfield unmanured worked example (official RothC_Py v1.0.0) within published precision, and carbon and phosphorus mass balance is checked monthly and cumulatively. That is a verification of the implementation against a published calculation. It is not field validation of the AMF extension or of any management response.

### Audit scope notice

These audits were AI-executed computational implementation reviews conducted in separate clean-context sessions. They were not human peer review, institutional review, or independent biological validation. They assessed implementation, reproducibility, artifact integrity, and claim alignment only. The audit archive is in `docs/audits/`.

## Quickstart

Requires Python 3.11 or later and [uv](https://docs.astral.sh/uv/). From the repository root:

```bash
uv sync --frozen --extra dev
uv run ruff format --check .
uv run ruff check .
uv run mypy
uv run pytest
uv run soil-simulator validate-config
uv run soil-simulator show-model-info
uv run soil-simulator run-carbon-core
```

## Status and limitations

- This is not an agricultural prediction tool and must not be used for farm recommendations. Passing verification is not field validation or evidence of real-world causality.
- `protected_soc` is a model proxy for a humified pool. It is not measured mineral-associated organic carbon (MAOC).
- The 56 paired soil-climate locations are an empirical pilot, not a nationally representative sample. Generated fields keep synthetic within-location perturbations and latent AMF and phosphorus priors.
- Source-corrected Hoosfield forcing improves uncalibrated total-SOC performance, but held-out FYM cessation stays weak.
- Not implemented: AMF species or community biology, fungal phosphorus storage and recycling, a crop water balance beyond the provisional RothC topsoil moisture deficit, soil-phosphorus chemistry, an API or dashboard.
- Tests without frozen outputs: `outputs/phase8_v0.8.0/`, `phase85_v0.8.5/`, `phase86_v0.8.6/` and `phase9_v0.9.0/` are gitignored and not in a fresh clone. Seven tests that read them (five in `tests/unit/test_phase9.py`, two in `tests/unit/test_phase95.py`) skip with a stated reason when the directories are absent. On a fresh clone the suite reports 227 passed and 7 skipped. The Phase 9.5 to 9.7 outputs are committed and their hash replays run.
- The `soil-simulator` CLI banner still reports version 0.9.0 although the package version is 0.9.7.

## Documents

Start with `docs/README.md`. Key files:

- `docs/PHASE97_PUBLICATION_READINESS.md` - current audited scientific boundary
- `docs/MODEL_SPEC.md` - state variables, equations and parameters
- `docs/VALIDATION_PLAN.md` and `docs/PHASE95_LONG_TERM_VALIDATION.md` - validation
- `docs/audits/README.md` - audit archive
- `docs/provenance/RESEARCH_ARCHIVE.md` - research archive
- `archive/README.md` - historical working material

## Project structure

- `src/` - Python package source
- `config/` - model and experiment configuration
- `data/` - input and validation data
- `outputs/` - frozen generated outputs (Phase 9.5 to 9.7 committed)
- `manuscript/current/` - current manuscript package
- `manuscript/archive/` - preserved manuscript bundles read by the Phase 9.8 archive tests and hash manifests
- `docs/` - specifications, evidence and audits
- `archive/` - historical working material

## Model summary

- RothC-style carbon core with explicit AMF live-biomass and necromass pools
- Plant carbon allocation, growth and maintenance respiration, turnover, necromass routing and stock-capped AMF phosphorus acquisition and transfer
- A parallel no-AMF counterfactual reports net plant-carbon and yield effects without assuming AMF is beneficial
- Immutable carbon and phosphorus records with monthly and cumulative mass-balance checks; deterministic results carry configuration hashes, units and provenance

## Command line

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
