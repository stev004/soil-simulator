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
