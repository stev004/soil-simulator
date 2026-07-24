# Phase 9.8 manuscript-ready research archive

## Outcome

Phase 9.8 now contains the complete independent-audit evidence required for a
bounded Prism handoff. The ten supplied Phase 9.6/9.7 audit deliverables were
validated against `incoming_audits/AUDIT_EXPORT_MANIFEST.json`, copied to their
canonical `docs/audits/` names without changing bytes, indexed and reconciled
with the manuscript bundle. No audit was reconstructed or reformatted.

The focused independent re-audit states that bounded methodological,
software/simulator or portfolio drafting is defensible. It continues to reject
a validated agricultural-prediction paper. Phase 9.8 did not draft manuscript
prose and did not rerun or reinterpret scientific analyses.

## Files added, copied and regenerated

The restoration added byte-exact canonical copies of:

- `AUDIT_PHASE96_CLEAN_SLATE.md`;
- `phase96_finding_closure.csv`;
- `phase96_recomputed_metrics.json`;
- `phase96_discrepancies.md`;
- `AUDIT_PHASE97_FOCUSED.md`;
- `phase97_finding_closure.csv`;
- `phase97_recomputed_metrics.json`;
- `phase97_discrepancies.md`;
- `phase97_sobol_findings.md`;
- `phase97_convergence_findings.md`.

The supplied `AUDIT_EXPORT_MANIFEST.json` was also copied unchanged into the
audit archive as transfer provenance. `docs/audits/audit_manifest.json` now
contains 13 entries: the audit README, the v0.9.0 report, the ten restored
deliverables and the export manifest. Its missing-deliverables list is empty.

The following Phase 9.8 evidence was regenerated from existing sources:

- the audit archive README and manifest;
- all nine canonical CSV tables and their Markdown previews;
- all eleven figures and `FIGURE_INDEX.md` source/status reconciliation;
- the independent-audit supplementary index;
- data, table, figure, supplementary and complete-bundle manifests;
- the audit trail, methods/results/limitations evidence indexes, scope records,
  Prism handoff and research-archive navigation;
- `docs/PHASE98_RESTRUCTURING_LOG.csv`.

Large frozen scientific outputs remain indexed rather than duplicated. The
generated `manuscript/supplementary/INDEPENDENT_AUDIT_INDEX.json` points to the
canonical audit copies; internal Phase 9.6/9.7 closure matrices remain clearly
labelled internal.

No file was moved or deleted.

## Audit validation and closure

All ten incoming filenames exactly match the export manifest set. Every source
matched its declared byte size, SHA-256 and `retrieved_unchanged: true`
attestation. Every canonical destination was then compared byte-for-byte with
its source. Result: **10/10 pass, zero discrepancies**.

The Phase 9.6 clean-slate audit confirmed the conservative stop decision and
identified implementation defects for Phase 9.7 correction. The focused Phase
9.7 re-audit independently classified six defects closed and three
substantially addressed; the latter retain disclosed scientific limitations,
not open implementation defects. It found no unresolved or replacement defect
and explicitly permits bounded methodological, software/simulator or portfolio
drafting.

## Tables and figures

Nine manuscript-ready CSV tables and adjacent previews cover model components,
data sources, verification tests, Hoosfield evaluation, sensitivity
convergence, ML gates, independent audit closure, claim boundaries and the
assumptions summary. Table 07 now uses the independent Phase 9.6 and Phase 9.7
closure matrices rather than treating internal closure evidence as a substitute.

Eleven reproducible or byte-preserved SVG figures cover architecture, C/P
accounting, empirical coverage/distributions, Hoosfield trajectories/residuals,
the FYM profile, sensitivity convergence/representative ST estimates, ML gates
and the audit chronology. Sensitivity figures remain visibly marked **NOT
CONVERGED**. No figure implies an agricultural recommendation.

## Claim boundary

Permitted claims include deterministic replay under frozen configurations,
enforced carbon/phosphorus accounting, documented RothC parity, use of the
56-location paired empirical pilot, improved aggregate uncalibrated Hoosfield
fit after source correction, failed prediction/OOD gates, the blocked selector
decision, and independently verified implementation remediation.

Qualification remains mandatory for non-converged sensitivity, limited pilot
coverage, the protected-SOC proxy, residual interval coverage, weak FYM
cessation performance and the boundary-constrained FYM factor.

Prohibited claims include real-farm prediction, causal effects, field or
national recommendations, national representativeness, measured MAOC,
validated carbon credits, real-soil sequestration quantities, generalisable ML
selection, final-stock R² publication claims and sensitivity convergence.

## Reproducibility verification

- Ruff formatting: pass, 118 files.
- Ruff lint: pass.
- Strict mypy: pass, 116 source files.
- Complete pytest suite: **234 passed**.
- Manuscript-table validation: pass.
- Figure/XML/source validation: pass.
- Internal-link validation: pass.
- Audit-export and canonical-copy replay: pass, 10/10.
- Audit/archive manifest replay: pass.
- Manuscript-bundle set-digest replay: pass.
- Wheel and source-distribution builds: pass.
- Installed-wheel import: pass from the fresh wheel, package version 0.9.7.
- Installed-wheel CLI smoke: `show-model-info` and `validate-config` pass using
  the locked project environment as the offline dependency source.

Fresh distribution hashes:

- wheel: `b86bd12cd8c7ebf919280d92b96a4059d82041a003c3a8562866deb72bc072b4`
  (240,664 bytes);
- sdist: `38c79e775203aabd7b78fae3357f31e9f604fb3c5f536fdec29cc0029dbb9f44`
  (11,492,890 bytes).

The package version is 0.9.7 and Python is 3.14.6. The supplied checkout has
no usable Git metadata, so commit/tag identity remains unavailable. This is a
software-provenance limitation, not missing scientific evidence.

## Unchanged scientific state

No Phase 9.5, 9.6 or 9.7 output file was renamed, edited, overwritten or
relocated. The recorded 62-file frozen-output inventory digest remains
`273f3af883e5cfe8f63b4cde054cd08d8b84e0134ede577f10fc1d5c86fa0af7`.
The Phase 9.7 scientific artifact-set digest remains
`cf0915f2f4c0f38f493840b47be0fcfc367c234bdeab90fffd4ea6db18e8b910`.

Scientific equations, parameters, configurations, datasets, experimental
results, readiness gates and the blocked downstream decision are unchanged.
The historical manifests remain untouched. The existing transparent Phase 9.8
README-only current-byte correction remains the sole allowed Phase 9.7-manifest
path change and is explicitly non-scientific.

## Manifests and digest

- Audit manifest SHA-256:
  `e86f7276d5c5c46d4d00d74c4a3867207191c3445bc8990091f4e78d4540b185`.
- Complete manuscript bundle: 69 indexed files.
- Final manuscript-bundle set SHA-256:
  `98aa6e6366ac4f3c4708883817cb987850c8d2858b20cdbfbe9dde11525099a5`.

The canonical entry lists, byte sizes, SHA-256 values, categories, sources,
actions and scientific-freeze flags are in `docs/audits/audit_manifest.json`
and `manuscript/manifests/`.

## Missing items

There are no missing Phase 9.8 audit deliverables. The remaining limitations
are scientific claim boundaries documented in `manuscript/LIMITATIONS_EVIDENCE.md`;
they block agricultural prediction/recommendation claims but do not block the
bounded paper types authorised by the independent focused re-audit.

## Exact Prism start instructions

1. Open `manuscript/PRISM_HANDOFF.md` as the single starting document.
2. Draft only a bounded methodological/software paper, narrower
   software/simulator paper or portfolio case study.
3. Cite numerical claims only through `manuscript/RESULTS_EVIDENCE.md` and its
   exact machine-readable source paths.
4. Preserve every negative result and fail-closed gate decision.
5. Treat all Phase 9.7 sensitivity indices as non-converged and diagnostic.
6. Do not invent results, citations, validation or causal interpretations.
7. Do not describe the framework as a field recommendation system or draft an
   agricultural-prediction manuscript.

READY FOR BOUNDED PRISM DRAFTING
