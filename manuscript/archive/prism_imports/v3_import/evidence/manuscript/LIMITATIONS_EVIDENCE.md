# Limitations evidence index

Claim-block columns use: **A** agricultural prediction/recommendation, **M**
methodological, **S** software, **P** portfolio. “Blocks” means that the
limitation prevents an unqualified claim of that type, not that no bounded
discussion is possible.

| Area | Limitation and evidence | Consequence | Current mitigation | Claim blocks | Future work required |
|---|---|---|---|---|---|
| Empirical data | 56 accepted locations from a 64-location frame; `outputs/phase96_v0.9.6/EMPIRICAL_SOURCE_MANIFEST.json` | Limited geographic/numerical coverage; no population representativeness | Call it an empirical pilot; preserve rejection/source records | A; qualified M | Predeclared representative sampling, independent replication and coverage analysis. |
| Empirical data | SoilGrids are mapped median predictions and NASA POWER is reanalysis; PET is derived under A080 | Inputs carry mapping/reanalysis/derivation uncertainty not propagated as observation error | Source/version/hash records and explicit depth harmonisation | A; qualified M | Propagate source uncertainty and compare with measured field covariates. |
| Biological parameters | AMF allocation, CUE, turnover, necromass routing and P kinetics use broad priors (A003–A009, A021–A025) | Simulator effects may be prior-dominated | Assumptions register, global ranges, diagnostic sensitivity | A; qualified M | Calibrate against independent AMF, P and carbon-fraction observations. |
| Model structure | `protected_soc` is a humified/protected proxy and is not measured MAOC | MAOC claims are invalid | Persistent naming/claim boundary | A; qualified M/P | Fractionation-linked calibration and external validation. |
| Model structure | Crop, water and soil-P representations are simplified/provisional (`docs/MODEL_SPEC.md`) | Some management-response magnitudes and interactions may be structurally biased | Modular separation and explicit assumptions | A; qualified M | Compare alternative crop/water/P structures and validate each. |
| Calibration | FYM factor estimate 1.10 equals upper bound and objective improves at edge; `outputs/phase97_v0.9.7/calibration_profile.json` | Parameter is boundary-constrained and not identifiable as a general value | Bound not widened; general success reported false | A; qualified M | Independent input reconstruction, broader justified prior and prospective calibration design. |
| Validation | Held-out FYM-cessation RMSE 7.577073646005274 t C ha⁻¹ | Long-term treatment transfer remains weak | Negative result preserved and separated from aggregate improvement | A; qualified M | Diagnose cessation dynamics and validate against additional treatments/sites. |
| Validation | Hoosfield evaluates total SOC only | No validation of AMF dynamics or protected-SOC proxy | Narrow validation wording | A; qualified M | AMF and fractionation observations with independent holdout. |
| Sensitivity | Phase 9.7 rule fails at N=1,024: max S1/ST changes 0.122/0.112 | Indices and rankings are diagnostic, not final | Non-converged watermark, full CIs/negative estimates, fail-closed claim | Unqualified M; not S/P | Increase deterministic base sequence and reassess predeclared convergence without tuning thresholds. |
| Machine learning | Yield effect fails policy-mean and OOD gates; all-target prediction/OOD conjunction fails | Effect predictor is not ready for downstream selection | Effect-only targets; computed fail-closed gates | A; qualified M | Better empirical features/model design and untouched external effect data. |
| Machine learning | No eligible independent empirical intervention-effect dataset (sample size 0) | No external validation of simulated effects or selector | Downstream selector/oracle/regret execution blocked | A; qualified M | Obtain independent, treatment-compatible data covering every primary target/horizon. |
| Uncertainty | Passing coverage concerns residual intervals in synthetic test/OOD regimes | Does not quantify structural, mechanistic, causal or real-field uncertainty | Target/regime-specific rules and explicit wording | A; qualified M | Hierarchical uncertainty model with empirical observation and structural components. |
| Causal inference | Management effects are simulator contrasts, not randomized or quasi-experimental observations | No causal intervention statement is supported | Prohibited-claim register | A | Independent causal study design and validation. |
| Generalisability | Synthetic descendants retain within-location perturbations and latent AMF/P priors | Performance may reflect generator structure | Empirical-location group isolation and OOD diagnostics | A; qualified M | Multi-region measured populations and external prospective testing. |
| Software/reproducibility | Checkout lacks `.git` metadata and `uv` executable | Commit identity and canonical `uv` replay cannot be demonstrated locally | Package 0.9.7, Python 3.14.6, lockfile and file hashes recorded; `.venv` commands used | Qualified S/M | Restore VCS metadata and execute documented `uv --frozen` replay in a clean environment. |

None of these limitations is removed by passing software tests. Conversely,
retaining them does not invalidate the archive as a transparent software or
portfolio evidence record.
