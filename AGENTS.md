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
