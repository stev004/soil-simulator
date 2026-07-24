# Audit trail

## v0.9.0 independent audit

- **Major findings:** authored synthetic population; stock-target circularity;
  uncalibrated phosphorus loop; horizon-invariant accounting; duplicate
  `no_till`; missing global sensitivity/calibration/long-term validation.
- **Evidence:** `docs/audits/AUDIT_v0.9.0_INDEPENDENT.md`.
- **Status:** independent report preserved byte-for-byte in the audit archive.
- **Unresolved:** real-field, causal, AMF and protected-SOC validation.

## Phase 9.5 remediation

- **Corrective action:** effect-only headline targets, deterministic identities
  excluded from ML, duplicate policy removed, recurring accounting added,
  phosphorus bounded/excluded, sensitivity framework and uncalibrated
  Hoosfield evaluation added.
- **Evidence:** `docs/PHASE95_*.md` and `outputs/phase95_v0.9.5/`.
- **Status:** implementation changes retained; empirical population and
  population-aware sensitivity blockers remained.

## Phase 9.6 empirical grounding and clean-slate audit

- **Corrective action:** paired 56-location soil–climate pilot, source-corrected
  Hoosfield diagnosis, optional bounded calibration, population-aware
  sensitivity and effect-only ML gates.
- **Evidence:** `docs/PHASE96_*.md`; `outputs/phase96_v0.9.6/`;
  `docs/audits/AUDIT_PHASE96_CLEAN_SLATE.md` and associated independent
  closure/recomputation/discrepancy files.
- **Status:** historical Phase 9.6 outputs remain unchanged. The independent
  clean-slate audit confirmed the stop decision and found implementation
  defects requiring Phase 9.7 correction.
- **Unresolved:** Phase 9.6 sensitivity was incorrectly labelled Sobol; literal
  gates and overly broad coverage logic required correction; scientific
  prediction/calibration limitations remained.

## Phase 9.7 correction

- **Corrective action:** scrambled SciPy Sobol sequence, Saltelli/Jansen
  estimators, nested convergence, computed leakage/validation/coverage gates,
  target/regime coverage, transparent hash correction and FYM boundary profile.
- **Evidence:** `docs/PHASE97_*.md`; `outputs/phase97_v0.9.7/`.
- **Status:** internal closure matrix reports implementation defects addressed.
  Sensitivity did not converge; prediction/OOD and independent-effect gates
  failed; selection stayed blocked.

## Focused Phase 9.7 re-audit

- **Review:** deterministic replay, Sobol construction and estimators,
  gate recomputation, calibration profile, claims, builds and wheel smoke tests.
- **Evidence:** `docs/audits/AUDIT_PHASE97_FOCUSED.md` and its closure,
  recomputation, discrepancy, Sobol and convergence deliverables.
- **Status:** independent review confirmed six defects closed and three
  substantially addressed; no defect unresolved or replaced by a new issue.
  It reproduced every headline metric, 35/35 artifact hashes, 227 tests and
  byte-identical pipeline replay at the audited Phase 9.7 state.
- **Consequence:** implementation blockers for bounded methodological/software
  drafting are cleared. Residual items remain scientific limitations.

## Final allowed manuscript scope

Bounded methodological/software framing or a portfolio case study is
independently supported. An agricultural prediction/recommendation paper is
not supported.
Negative findings were preserved rather than tuned away: cessation error,
boundary calibration, non-convergence, failed effect/OOD gates and absent
independent effect validation remain explicit.
