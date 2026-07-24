# Phase 9.7 targeted audit closure

## Scope and outcome

Phase 9.7 addresses only defects identified by the independent Phase 9.6
clean-slate re-audit. It changes no verified Phase 3--6 biological equation,
adds no intervention recommendation, and creates no API or dashboard.

The current `docs/AUDIT_soil_simulator_v0.9.0.md` bytes are preserved. The
historical Phase 9.6 manifest is also preserved. A separate correction manifest
rehashes every path against current bytes, records each old and new digest and
explains that the audit document was restored or updated after the Phase 9.6
freeze. Historical v0.9.0 and Phase 9.6 output directories are not overwritten.

The corrected sensitivity design, computed scientific gates, target-specific
coverage rule and FYM boundary profile are new Phase 9.7 evidence. Selection,
oracle and regret analysis remain prohibited unless every computed prerequisite
gate genuinely passes.

## Closure artifacts

- `outputs/phase97_v0.9.7/audit_closure_matrix.csv` and `.json`
- `corrected_phase96_artifact_hashes.json`
- `source_manifest.json`, `pipeline_manifest.json` and `artifact_hashes.json`
- Phase 9.6 versus Phase 9.7 comparison CSV/JSON

The clean-slate defects are implementation-closed when the focused re-audit can
replay these artifacts. A gate may remain scientifically failed after its
hardcoded implementation defect is closed; such a failure is retained rather
than tuned away.

The corrected run found non-converged sensitivity estimates, failed all-target
prediction/OOD readiness, no independent empirical effect dataset, and a
boundary-constrained FYM calibration with weak held-out cessation performance.
These are remaining scientific limitations, not unclosed implementation defects.
