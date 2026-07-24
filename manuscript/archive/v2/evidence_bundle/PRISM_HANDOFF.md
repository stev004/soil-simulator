# Prism handoff

## Readiness decision

**READY FOR BOUNDED PRISM DRAFTING.** The ten independent Phase 9.6/9.7
deliverables have been validated against their supplied export manifest,
archived without byte changes and reconciled with this bundle. The Phase 9.7
focused re-audit expressly permits methodological, software/simulator or
portfolio drafting. It expressly does not support a validated agricultural-
prediction paper.

**Validated agricultural-prediction paper: not supported.**

## Recommended paper type

A methodological/software paper on development, verification and independent auditing of the reproducible
soil–plant–AMF framework, including fail-closed ML intervention-effect
evaluation. A narrower software article is the second choice. A bounded
portfolio case study is also supported, but this handoff does not draft it.

## Working title options

1. *A reproducible and independently audited soil–plant–AMF simulation
   framework with fail-closed scientific-ML evaluation*
2. *Mechanistic accounting, deterministic replay and bounded machine-learning
   evaluation in a soil-carbon research simulator*
3. *Building and auditing a reproducible soil–plant–fungal simulation
   framework: verified accounting and preserved negative results*

Titles are options, not settled manuscript prose.

## Central research contribution

The contribution is the transparent engineering and verification of a modular
soil–plant–AMF simulator and its evidence pipeline: explicit carbon/phosphorus
accounting, deterministic artifacts, an empirical soil–climate pilot,
long-term SOC evaluation, corrected global-sensitivity workflow, effect-only ML
benchmarking, computed readiness gates and the auditable decision not to run or
deploy a selector when prerequisites failed.

## Claim controls

Use only claims listed as permitted in `CLAIM_BOUNDARIES.md`. Apply every
qualification in that register. Never claim:

- real-farm predictive validation or causal intervention effects;
- field, national or carbon-credit recommendations;
- measured MAOC prediction;
- generalisable ML selection;
- sensitivity convergence;
- successful general FYM calibration.

Treat all Phase 9.7 sensitivity indices and rankings as **non-converged,
diagnostic evidence**. Do not describe this model as a field recommendation
system.

## Suggested manuscript structure and evidence

| Planned section | Evidence starting points |
|---|---|
| Scope and contribution | `MANUSCRIPT_SCOPE.md`; `CLAIM_BOUNDARIES.md` |
| Architecture and mechanistic methods | `METHODS_EVIDENCE.md`; figures 01–02; tables 01, 03 |
| Data and population methods | `DATA_AVAILABILITY.md`; figure 03–04; table 02 |
| Long-term evaluation | `RESULTS_EVIDENCE.md`; figures 05–07; table 04 |
| Sensitivity methods/results | figures 08–09; table 05; Phase 9.7 manifests; always label non-converged |
| Effect-only ML and fail-closed gates | figure 10; table 06; model card/leakage/coverage supplementary files |
| Independent audit and remediation | `AUDIT_TRAIL.md`; figure 11; table 07; `docs/audits/AUDIT_PHASE96_CLEAN_SLATE.md`; `docs/audits/AUDIT_PHASE97_FOCUSED.md` |
| Limitations | `LIMITATIONS_EVIDENCE.md`; table 08–09 |
| Data/software/reproducibility | `DATA_AVAILABILITY.md`; `SOFTWARE_AVAILABILITY.md`; `REPRODUCIBILITY.md` |
| References | `REFERENCES_SOURCE_LIST.md` (inventory only; verify incomplete metadata) |

Priority figures: 01, 02, 05, 08, 10 and 11. Priority tables: 01, 03, 04, 05,
06, 07 and 08.

## Unresolved scientific limitations

- empirical pilot size/geographic coverage and synthetic descendants;
- uncalibrated biological/P relationships;
- protected-SOC proxy status;
- weak FYM cessation performance and boundary-constrained calibration;
- non-converged sensitivity estimates;
- failed effect-prediction/OOD gates;
- absent independent empirical intervention-effect validation;
- predictive residual coverage does not include structural/causal/field
  uncertainty.

## Required process language

Describe development as AI-assisted, with human-defined scientific scope,
explicit assumptions, deterministic tests and independent audit checkpoints.
Do not imply that AI authorship verified biology. State that independent audits
assessed artifacts without modifying scientific results, and distinguish
implementation remediation from scientific validation.

## Prism operating instructions

1. Do not invent results, citations, validation or causal
   interpretations.
2. Cite every numerical claim only from `RESULTS_EVIDENCE.md` and then from its
   exact indexed source artifact; do not use a Markdown preview as canonical.
3. Preserve negative findings and fail-closed decisions.
4. Treat Phase 9.6 sensitivity as superseded and Phase 9.7 sensitivity as
   non-converged.
5. Use `REFERENCES_SOURCE_LIST.md` only as an inventory; verify incomplete
   bibliographic metadata before citation.
6. Draft only the bounded framing authorised above. Do not describe the model
   as a field recommendation system or imply agricultural validation.
