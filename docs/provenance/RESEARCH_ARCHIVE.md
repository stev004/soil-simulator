# Research archive index

This index navigates the verified v0.9.7 scientific state and the Phase 9.8
manuscript evidence packaging. Historical output directories remain in place
and are not renamed, edited or overwritten.

## Starting points

- Current audited boundary: `docs/PHASE97_PUBLICATION_READINESS.md`
- Formal audits: `docs/audits/README.md`
- Manuscript evidence status: `manuscript/README.md`
- Prism handoff and blocker: `manuscript/PRISM_HANDOFF.md`
- Phase 9.8 archive report: `docs/PHASE98_MANUSCRIPT_ARCHIVE.md`
- Restructuring log: `docs/PHASE98_RESTRUCTURING_LOG.csv`

## Software and configurations

- Package source: `src/soil_simulator/`
- Package/version/dependencies: `pyproject.toml`, `uv.lock`
- Model defaults: `config/model_defaults.yaml`
- Scenario schedules: `config/scenarios/`
- Population configurations: `config/populations/`
- Phase 9.5–9.7 analysis configurations: `config/phase95/`,
  `config/phase96/`, `config/phase97/`

## Data

- Raw cached source data: `data/raw/`
- Processed paired soil/climate pilot: `data/processed/phase96_empirical_*`
- Source/licence/hash manifest:
  `outputs/phase96_v0.9.6/EMPIRICAL_SOURCE_MANIFEST.json`
- Archive data index: `manuscript/data/DATA_INDEX.csv`
- Availability statement: `manuscript/DATA_AVAILABILITY.md`

## Experiments and frozen outputs

- Phase 9.5 remediation: `outputs/phase95_v0.9.5/`
- Phase 9.6 empirical grounding: `outputs/phase96_v0.9.6/`
- Phase 9.7 focused correction: `outputs/phase97_v0.9.7/`
- Historical frozen selector evidence: `outputs/phase9_v0.9.0/`

The Phase 9.7 canonical artifact-set SHA-256 is
`cf0915f2f4c0f38f493840b47be0fcfc367c234bdeab90fffd4ea6db18e8b910`.
Use the manifest itself as canonical evidence.

## Audits

- v0.9.0 independent audit: `docs/audits/AUDIT_v0.9.0_INDEPENDENT.md`
- Audit manifest: `docs/audits/audit_manifest.json`
- Internal Phase 9.6/9.7 closure matrices: indexed under
  `manuscript/supplementary/`

The independent Phase 9.6 clean-slate and Phase 9.7 focused re-audit
deliverables are archived byte-for-byte and validated against the supplied
export manifest; see `docs/audits/README.md`. Internal closure artifacts remain
separately labelled and are not relabelled as independent reports.

## Manuscript evidence bundle

- Scope and claim limits: `manuscript/MANUSCRIPT_SCOPE.md`,
  `manuscript/CLAIM_BOUNDARIES.md`
- Methods/results/limitations indexes: `manuscript/*_EVIDENCE.md`
- Canonical CSV tables and previews: `manuscript/tables/`
- Reproducible/copy-preserved SVG figures: `manuscript/figures/`
- Supplementary copies and large-file indexes: `manuscript/supplementary/`
- Bundle manifests and set digest: `manuscript/manifests/`

## Tests and reproducibility

- Tests: `tests/unit/`, `tests/properties/`, `tests/parity/`,
  `tests/scenarios/`, `tests/integration/`
- Validation plan: `docs/VALIDATION_PLAN.md`
- Reproduction commands: `manuscript/REPRODUCIBILITY.md`
- Software availability: `manuscript/SOFTWARE_AVAILABILITY.md`

The archive distinguishes verification, validation and policy evaluation. A
passing software suite does not establish field validity, and a copied/indexed
artifact does not acquire stronger scientific status through packaging.
