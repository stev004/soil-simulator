# Phase 9.7 publication readiness

## Current boundary

Phase 9.7 is not a validated agricultural prediction system. The 56 real
soil--climate locations form an empirical pilot, not a nationally
representative population. Generated fields still contain synthetic
perturbations and latent AMF/P priors. `protected_soc` is a model proxy, not
measured MAOC. Hoosfield source correction improves uncalibrated total-SOC
performance, but held-out FYM cessation remains weak and the optional FYM
calibration is boundary-constrained.

Failed effect-prediction/OOD gates and the absence of independent empirical
effect validation block downstream selection. No Phase 9.7 selector, oracle or
regret result is authorised. The predeclared sensitivity convergence rule also
fails at 1,024 base samples, so those indices remain diagnostic rather than
final. Leakage and target-specific uncertainty coverage pass, but those
successes do not override another target or prerequisite gate.

Publication readiness by output type:

| Output | Readiness |
|---|---|
| Agricultural prediction paper | Not ready |
| Methodological paper | Potentially supportable after focused independent re-audit |
| Software/simulator paper | Potentially supportable after focused independent re-audit |
| Portfolio case study | Supported with the stated synthetic/non-causal boundaries |

Do not begin Prism manuscript drafting before the focused re-audit confirms
the corrected evidence.

## Focused independent re-audit

1. Verify the historical Phase 9.6 manifest is unchanged and replay
   `corrected_phase96_artifact_hashes.json` against exact current bytes.
2. Rerun the complete Phase 9.6 pipeline twice in isolated temporary copies;
   confirm byte-identical outputs without overwriting historical artifacts.
3. Run the Phase 9.7 pipeline twice to separate directories and compare all
   deterministic artifacts byte for byte.
4. Verify SciPy Sobol construction, parameter transforms, power-of-two sizes,
   Saltelli/Jansen estimators, confidence intervals, negative estimates and the
   predeclared convergence decision.
5. Independently recompute leakage, coverage, validation and downstream gates;
   confirm missing evidence fails closed and selection/regret was not run.
6. Review the FYM bounded profile, held-out cessation residuals, claim wording,
   complete quality suite, builds, installed-wheel import and CLI smoke tests.
