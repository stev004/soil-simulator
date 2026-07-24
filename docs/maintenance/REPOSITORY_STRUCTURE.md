# Repository structure

## Authoritative locations

The repository is organized so that scientific inputs, executable source,
generated evidence, manuscript material, audits, and reproducible package
builds remain distinct.

| Path | Purpose and authority |
|---|---|
| `src/` | Authoritative Python package source. The mechanistic simulator and downstream modules remain separated within `src/soil_simulator/`. |
| `tests/` | Unit, property, parity, integration, deterministic-replay, mass-balance, and scenario-direction verification. |
| `config/` | Validated model, scenario, population, ML, selection, and remediation configuration. |
| `data/` | Input data: immutable raw caches, processed empirical inputs, and validation observations. |
| `scripts/` | Explicit download and archive-packaging scripts. Scientific calculations do not belong here unless already part of a documented pipeline. |
| `outputs/` | Generated scientific outputs and frozen evidence. These are not package builds and must not be treated as disposable. |
| `manuscript/` | Current and historical manuscript material. |
| `manuscript/current/` | Authoritative manuscript package. It contains the v3 Markdown, LaTeX, bibliography, six local figure PDFs, and canonical PDF. |
| `docs/` | Scientific documentation, specifications, evidence reports, and maintenance records. |
| `docs/specifications/` | Consolidated or root-origin project specifications. Existing established specifications remain at `docs/*.md` to preserve stable project contracts. |
| `docs/provenance/` | Research-provenance and archive navigation. |
| `docs/prompts/` | Immutable historical prompts. |
| `docs/maintenance/` | Repository inventory, cleanup manifest, and structure rules. |
| `docs/audits/` | Existing canonical Phase 9.8 audit archive and audit manifest. |
| `audits/incoming/` | Immutable incoming independent-audit deliverables and their supplied export manifest. |
| `artifacts/builds/` | Preserved package-build artifacts, separated from scientific outputs. |
| `.github/` | Continuous-integration configuration. |

The canonical manuscript PDF is
`manuscript/current/manuscript_v3.pdf`, SHA-256
`c2db01f4130865570a924262dbdf120d6dcfcebcdfac66d3425b0882b5797d10`.
The earlier Prism PDF hash
`f374e93b43e27f63892a82c54c05f243d45957252feb4322851c5760de3a8b3d`
is historical provenance only.

## Evidence classes

- Source evidence is an authoritative input, specification, audit, manuscript
  source, or provenance record. It is not regenerated during cleanup.
- Generated scientific output is the saved result of simulation, validation,
  sensitivity, calibration, population, ML, or evidence generation. It belongs
  under `outputs/` and is not disposable build clutter.
- Package-build output is a wheel, source distribution, or related packaging
  metadata. Preserved snapshots belong under `artifacts/builds/`.
- Historical archives preserve earlier manuscript packages, Prism imports,
  audits, and their manifests. Moving or copying an archived file does not
  strengthen its scientific status.

## Immutability and versioning rules

`manuscript/current/` is authoritative. Historical manuscript versions,
evidence bundles, Prism imports, and package ZIPs are stored under
`manuscript/archive/`. Material under `manuscript/archive/` is immutable:
future work must not normalize, deduplicate, replace, or silently correct it.

Add a future manuscript version by:

1. preserving the outgoing current package under a clearly versioned
   `manuscript/archive/` directory with hashes and provenance;
2. placing the complete successor package in `manuscript/current/`;
3. updating `manuscript/MANUSCRIPT_INDEX.md`, the manuscript cleanup manifest,
   and a version-specific local PDF build record;
4. verifying every figure and bibliography path locally.

Incoming audits belong in a new immutable, clearly named subdirectory under
`audits/incoming/`, with the supplied manifest retained. Canonical audit copies
and navigation may remain under `docs/audits/`; audit wording, conclusions, and
historical source-path records must not be edited.

Future package builds should be produced in the tool-default transient
`dist/` directory, then copied or moved into a versioned snapshot under
`artifacts/builds/` together with checksums and release metadata. The transient
root `dist/` path remains ignored. Scientific outputs must never be mixed with
package builds.

## Deliberate deviations

- Existing scientific specifications such as `docs/MODEL_SPEC.md`,
  `docs/MVP_SPEC.md`, `docs/VALIDATION_PLAN.md`, and `docs/ARCHITECTURE.md`
  remain at their established paths because `AGENTS.md`, documentation,
  tests, and code use those stable contracts. Only the formerly root-level
  combined specification was moved to `docs/specifications/`.
- Existing canonical audits remain under `docs/audits/`; moving them would
  disturb established manifests and archive validation. New incoming audit
  material is separated under `audits/incoming/`.
- Historical path strings in immutable archive packages and
  `docs/PHASE98_RESTRUCTURING_LOG.csv` remain unchanged because they describe
  paths that were correct when those records were created. They are historical
  provenance, not stale operational navigation.
- No `.git` metadata was present. Moves therefore used ordinary filesystem
  operations and were verified with SHA-256 rather than `git mv`.

## Final high-level tree

```text
soil_simulator/
├── .github/
├── .gitignore
├── .pre-commit-config.yaml
├── AGENTS.md
├── README.md
├── pyproject.toml
├── uv.lock
├── src/
├── tests/
├── config/
├── data/
├── scripts/
├── outputs/
├── manuscript/
│   ├── current/
│   │   └── figures/
│   └── archive/
├── docs/
│   ├── specifications/
│   ├── provenance/
│   ├── prompts/
│   ├── maintenance/
│   └── audits/
├── audits/
│   └── incoming/
└── artifacts/
    └── builds/
        └── dist_snapshot/
```
