# Audit archive

This directory is the stable audit index for the research archive. Audit work
assessed evidence; it did not change scientific results. Implementation
remediation means that code, accounting, sampling, gate or reporting defects
were corrected and replayable. Scientific validation instead requires
independent observations and appropriate external tests. The former never
implies the latter.

## Audit sequence

| Audit | Repository phase assessed | Findings closed by later work | Limitations retained |
|---|---|---|---|
| `AUDIT_v0.9.0_INDEPENDENT.md` | Frozen v0.9.0 simulator, ML and selector benchmark | Effect-only targets; recurring accounting; duplicate policy removal; empirical pilot; long-term SOC exercise; sensitivity workflow | Pilot representativeness, biological calibration, AMF/protected-SOC validation, real-field causal validity |
| `AUDIT_PHASE96_CLEAN_SLATE.md` | Phase 9.6 evidence | Confirmed C2, M2 and M3 closed; C1/M5 substantially addressed; exposed manifest drift, invalid Sobol labelling, decorative gates, weak coverage and under-disclosed calibration boundary for Phase 9.7 correction | Agricultural prediction unsupported; empirical pilot thin; P loop/calibration/sensitivity limitations retained |
| `AUDIT_PHASE97_FOCUSED.md` | Corrected Phase 9.7 evidence | Six of nine Phase 9.6 defects closed; three substantially addressed with implementation defects fixed and residual scientific limitations disclosed; no unresolved or replacement defect | Sensitivity not converged; OOD coverage low-power at small n; FYM cessation weak; no independent empirical effect dataset; agricultural prediction unsupported |

All three reports identify the audit as independent and read-only. The Phase
9.6 and Phase 9.7 reports, closure matrices, recomputed metrics, discrepancy
records and focused Sobol/convergence findings were validated against
`AUDIT_EXPORT_MANIFEST.json` and copied here without changing their bytes.
Internal project closure artifacts remain preserved under `outputs/` and are
still labelled internal.

## Scientific limitations that remain

- The 56 paired soil–climate locations are a limited empirical pilot, not a
  nationally representative sample.
- Generated descendants retain synthetic perturbations and latent AMF/P priors.
- Hoosfield source correction improved aggregate uncalibrated fit, but FYM
  cessation performance remains weak.
- The FYM reconstruction factor is boundary-constrained at 1.10.
- Phase 9.7 sensitivity indices did not meet the convergence rule.
- Effect-prediction and OOD gates fail, and no independent empirical
  intervention-effect dataset is available.
- `protected_soc` is a model proxy, not measured MAOC.
- No real-farm causal or recommendation claim is supported.

The focused re-audit concludes that bounded methodological, software/simulator
or portfolio drafting is defensible. It does not support an agricultural
prediction or recommendation paper.

`audit_manifest.json` hashes every archived file, records 10/10 source-export
validation and reports no missing independent deliverable. No report was
reconstructed, reformatted or reinterpreted.
