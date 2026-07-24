# Discrepancies — independent recomputation vs repository-reported values

Phase 9.6 clean-slate re-audit. Every headline scientific metric reproduced **exactly**; 
the discrepancies below are integrity drift, provenance-label gaps, and interpretation/adequacy issues — not arithmetic errors.


## Severity legend

HIGH = affects a claim's validity; MEDIUM = a real caveat that should be disclosed/fixed; LOW = labelling/precision only.


| # | Severity | Item | Repository-reported | Independent recomputation | Note |
|---|----------|------|---------------------|---------------------------|------|
| 1 | HIGH | pytest suite status | reported/expected: green (194 passed in v0.9.0 audit) | independent: **1 FAILED / 213 passed** — test_source_and_artifact_hash_manifests_replay_offline | The repo's own offline-replay integrity test is currently RED because docs/AUDIT_soil_simulator_v0.9.0.md was edited (mtime 20:14) after its hash was frozen in artifact_hashes.json (19:47). A live failing gate, not a benign warning. |
| 2 | HIGH | artifact_hashes.json / docs/AUDIT_soil_simulator_v0.9.0.md | recorded SHA-256 c5494d1f8f3b… | on-disk SHA-256 f2654c04f497… | Same root cause as above; the artifact_set digest is internally consistent with its own recorded table but no longer matches the current file tree. |
| 3 | HIGH | Sobol 'stable ranking' adequacy | reported: Sobol rank agreement 0.760 supports the analysis | independent: 0.760 + 25% impossible-negative first-order indices do NOT support any quantitative variance partition or 'stable Sobol ranking' | Correct Saltelli/Jansen estimator forms but plain-PRNG sampler (random.random), not a low-discrepancy Sobol sequence, at N=32. Interaction magnitudes are estimator noise. Morris screening and the FYM-winner result are sound; the Sobol partition is not. |
| 4 | HIGH | empirical_location_leakage_check gate | reported: True (a passed validation check) | independent: hardcoded literal True (effect_ml.py L314), never computed from data | Fail-open gate inside a fail-closed system. Data is coincidentally leak-free (independently verified 0/56 locations span >1 split), so the value is correct today, but a future leak would still report True. |
| 5 | MEDIUM | independent_empirical_effect_validation gate | reported: False | independent: hardcoded literal False (effect_ml.py L306) | Intentional fail-closed constant that makes all_gates structurally unpassable regardless of model quality. Correct conservative outcome, but it is a constant, not a validation. |
| 6 | MEDIUM | 'calibrated uncertainty = True' | reported: all_effect_targets_have_calibrated_uncertainty = True | independent: 6 of 7 targets UNDER-cover the 90% nominal (test coverage 0.865–0.885; only protected_soc\|60 = 0.913 meets 0.90); OOD coverage computed but NOT gated | Gate uses a permissive 0.80–1.00 acceptance band; passing it is not evidence of nominal 90% calibration. |
| 7 | MEDIUM | 'convergence' 0.840 / 0.760 | reported: mean Morris/Sobol rank agreements (convergence) | independent: nested-subsample self-consistency — the half-sample is byte-identical to the first half of the full sample (same seed) | Overstates reproducibility; shared bias inflates agreement. Should read 'nested-subsample stability', not convergence. |
| 8 | MEDIUM | observable covariance 'estimated from empirical records' | reported (PHASE96_EMPIRICAL_GROUNDING.md L5): estimated only from paired empirical records | independent: covariance is anchor-inheritance from 56 records PLUS hand-imposed clay_shift/SOC couplings; 'empirically_estimated' is a hardcoded label (pipeline.py L234); no covariance matrix is estimated & sampled | SYNTHETIC_POPULATIONS.md L278 says the opposite ('designed, not estimated'). Two shipped docs contradict each other. Correlations attenuated vs empirical (mean \|Δ\| 0.044, max 0.156). |
| 9 | MEDIUM | FYM calibration boundary | reported: best fym_carbon_factor = 1.1, boundary_solution = True | independent: reproduced exactly — 1.10 sits ON the [0.90,1.10] upper bound; the entire within-10% near-optimal band is pinned at the ceiling | Fit is not identified in the FYM direction; the factor is set by the imposed cap, not the data. The repo honestly surfaces this via the boundary_solution flag. |
| 10 | MEDIUM | ERA5-Land → NASA POWER substitution | reported: intended production climate source is ERA5-Land (REFERENCES.md L122; era5 adapter listed) | independent: the pilot actually uses NASA POWER / MERRA-2; the swap is never stated plainly, only inferable by cross-referencing docs | Defensible for a pilot, but should be disclosed explicitly. Consequence: PET is a Thornthwaite temperature-only surrogate (A080). |
| 11 | MEDIUM | SoilGrids texture closure | reported: predicted texture fractions renormalised, corrections retained (A077) | independent: pre-renormalisation clay+silt+sand mean 90.7% (min 71.5%, max 98.6%); closure gap mean 9.27pp, max 28.48pp; 21/56 locations >10pp | Renormalisation rescales but does not repair large raw texture inconsistency — a genuine data-quality caveat on the soil inputs. |
| 12 | MEDIUM | '112 generated fields' | reported: 112 generated fields grouped by empirical location | independent: 112 = 56 locations × ~2 synthetic clones with bounded perturbations; NOT 112 independent observations | Assumptions register (A052/A078) is honest that replication adds no empirical evidence; downstream support is a 56-location pilot (test = 11 loc/26 fields, OOD = 4 loc/6 fields). |
| 13 | LOW | NASA POWER version label | reported: 'v10' | independent: raw JSON header api.version = v2.9.7, sources = [MERRA2]; no 'v10' string anywhere in the raw file | MERRA-2 source and 2001–2020 window confirmed; only the 'v10' label is unverifiable. |
| 14 | LOW | SoilGrids '2.0' provenance | reported: SoilGrids 2.0 median predictions | independent: raw JSON body carries no version stamp; only the request URL rest.isric.org/soilgrids/v2.0 pins the version | Version rests on the download URL, not returned metadata. |
| 15 | LOW | package __version__ (auditor note) | n/a | independent: src __version__ = 0.9.6, matches pyproject; an earlier 0.8.5 reading was an auditor wheel-selection error, corrected | No defect — recorded for transparency. |

## Metrics that reproduced EXACTLY (no discrepancy)

- Hoosfield Phase 9.5 aggregate MAE/RMSE/bias 8.518 / 10.154 / −8.360 t C/ha
- Source-corrected aggregate MAE/RMSE/bias 3.657 / 4.340 / −0.528 t C/ha
- Calibration best factors {plant_residue 0.85, fym_carbon 1.10}, boundary_solution True
- Held-out temporal MAE/RMSE/bias 1.5158 / 1.8848 / 0.4975
- Held-out cessation MAE/RMSE/bias 7.2142 / 7.5771 / −7.2142
- Morris mean rank agreement 0.840; Sobol mean rank agreement 0.760; 224 Sobol evaluations
- Selected Sobol parameters (location, weather, schedule interval, tillage decomp, FYM-P)
- FYM policy-winner proportion 0.938–1.000 across all headline target/horizons
- All 7 effect-ML target test/OOD RMSE, alpha, coverage reproduced to 4 decimals from CSV
- Effect gates all_beat_policy_mean False, acceptable_ood False, downstream_selection_executed False
- Population hash 9bb2f8fec9…; two pipeline runs byte-identical across all 19 outputs
- 56 accepted / 8 rejected locations; harmonisation byte-exact (0.0 error, 56×9); all raw+processed+RothC-zip hashes match; frozen v0.9.0 baseline 18/18
