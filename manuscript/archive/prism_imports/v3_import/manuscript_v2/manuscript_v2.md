# Audit-driven development of a reproducible soil–plant–mycorrhizal simulation framework with fail-closed machine-learning evaluation

**Authors:** [AUTHOR NAME(S) AND ORCID(S) TO BE SUPPLIED]  
**Affiliations:** [AFFILIATION(S) TO BE SUPPLIED]  
**Corresponding author:** [NAME AND EMAIL TO BE SUPPLIED]

## Abstract

Soil-system simulators increasingly combine mechanistic process models with machine learning, but reproducible execution and internal predictive performance do not by themselves establish empirical validity or readiness for intervention selection. We developed a modular soil–plant–arbuscular-mycorrhizal-fungal simulation framework that integrates a RothC-based soil-carbon core, crop and residue processes, phosphorus limitation, fungal allocation and turnover, scheduled management, explicit carbon and phosphorus accounting, deterministic artifact generation, long-term evaluation, global sensitivity analysis, and fail-closed machine-learning gates. Artifacts and decision evidence were preserved for deterministic replay and inspection. A limited empirical pilot paired soil and climate records for 56 accepted locations and generated two synthetic descendants per location. Correcting the Hoosfield forcing source improved aggregate uncalibrated total-SOC RMSE from 10.154 to 4.340 t C ha⁻¹. An optional bounded farmyard-manure reconstruction did not generalize adequately: its factor reached the 1.10 upper bound and held-out cessation RMSE was 7.577 t C ha⁻¹. Corrected Sobol estimates remained non-converged at the largest base sample size and were retained as diagnostic evidence only. Leakage-isolation and target-specific residual-coverage checks passed, whereas effect-prediction, out-of-distribution, and independent empirical effect-validation gates failed. The conjunctive readiness rule therefore blocked selector, oracle, and regret analyses. Separate, clean-context, read-only computational audits identified and tested remediation of implementation defects while preserving negative scientific findings. The contribution is a methodological and software framework for auditable simulation and evidence-gated stopping, not validated agricultural prediction or recommendation.

## Keywords

soil carbon; RothC; arbuscular mycorrhizal fungi; reproducible simulation; scientific software; sensitivity analysis; distribution shift; fail-closed evaluation; computational audit

## 1. Introduction

Transparent soil-system simulation requires more than a collection of process equations. Carbon turnover, crop production, nutrient availability, microbial allocation, and management events interact across state variables and timescales, so assumptions, interfaces, numerical balances, and provenance must remain inspectable. RothC provides an established conceptual representation of soil-carbon turnover [Rothamsted Research, 2024; Coleman et al., 2024], but extensions for crop, phosphorus, and arbuscular mycorrhizal fungal (AMF) processes introduce provisional relationships whose implementation and empirical credibility must be assessed separately.

The distinction becomes sharper when simulator outputs are used to train machine-learning models. Predictive skill can be inflated by persistence of observable starting stocks, deterministic policy identities, related records crossing data splits, or evaluation within the generator’s own distribution. Paired targets can reduce stock-level circularity, and location-grouped splitting can reduce direct leakage, but neither converts simulated contrasts into causal field evidence. Distribution shift remains consequential because an intervention selector must work beyond the data configurations used for model fitting and calibration.

Three evidential levels must therefore be distinguished. Software verification asks whether represented calculations, contracts, balances, and pipelines execute as specified. Model evaluation asks how defined simulated quantities compare with relevant observations. Deployment readiness asks whether evidence is sufficient for a consequential downstream use. Passing software tests or reproducing an aggregate stock trajectory cannot establish the validity of provisional biology, causal intervention effects, or field recommendations.

Fail-closed scientific evaluation makes these distinctions operational. Under this design, each prerequisite is calculated from explicit evidence, absent or malformed evidence fails rather than passes, and downstream analysis is permitted only when every required condition is satisfied. Separate, clean-context, read-only computational audits can further test artifact integrity, recompute metrics, inject failures, and challenge whether gates are genuine. In this study those audits were AI-executed implementation reviews. They were not human peer review and did not provide independent biological validation.

The objectives were to: (1) describe a modular, typed, mass-balanced soil–plant–AMF simulator and its reproducibility controls; (2) evaluate its bounded empirical grounding and long-term total-SOC behavior; (3) implement corrected global sensitivity and effect-only machine-learning evaluation with leakage, uncertainty, out-of-distribution (OOD), and independent-effect-validation gates; and (4) determine whether the resulting evidence justified downstream intervention selection. The intended contribution is methodological and software-focused, not proof that an agricultural intervention works.

## 2. Materials and methods

### 2.1 Final software architecture

The final `soil-simulator` package (version 0.9.7) separates configuration, typed domain contracts, process modules, simulator orchestration, population construction, experimental pipelines, machine-learning evaluation, readiness gates, and evidence manifests (Figure 1; Table 1). Carbon pools, management events, configuration records, and outputs are represented through explicit contracts. Deterministic pipelines produce machine-readable artifacts and file-level hashes. This modular boundary supports process-level tests while preventing a passing software check from being interpreted as biological validation.

**[Figure 1 near here]**

**Table 1. Final model and evidence-pipeline components.**

| Component | Represented state/output | Verified implementation boundary | Scientific boundary |
|---|---|---|---|
| RothC core | DPM, RPM, BIO, HUM/protected proxy, IOM, respiration | Worked-case parity; carbon properties | Parity is not full forcing or field validation |
| Crop/residue | NPP, shoot/root carbon, yield, residues | Unit and integration tests | Monthly response and partitioning remain provisional |
| Phosphorus | Available P, plant/AMF uptake, P balance | Property and balance tests | Kinetics and effect magnitudes lack field calibration |
| AMF | Biomass, allocation, respiration, P contribution, turnover, necromass | Unit, integration, accounting, and direction tests | No independent empirical AMF or protected-SOC validation |
| Management/accounting | Scheduled events; recurring cost/emissions proxies | Contract and horizon-aware accounting tests | Partial accounting proxy, not full LCA |
| Population/spin-up | Empirical anchors, descendants, initialized pools | Population, grouping, and manifest checks | Limited pilot; descendants and latent priors remain synthetic |
| Sensitivity | Morris screening; S1/ST estimates and convergence | Corrected sampler, estimators, bootstrap, diagnostics | Sobol estimates remained non-converged |
| Effect-only ML/gates | Paired effects, ridge prediction, residual intervals, readiness evidence | Artifact-derived computed gates | Simulated effects are not empirical causal effects |

### 2.2 Carbon, crop, phosphorus, and AMF processes

The carbon core represents decomposable plant material (DPM), resistant plant material (RPM), microbial biomass (BIO), humified organic matter (HUM), inert organic matter (IOM), and carbon dioxide loss using the documented RothC structure. Environmental modifiers and pool updates are configuration controlled. A documented monthly Hoosfield decay case was used for arithmetic parity. The compact bundle does not contain a complete equation-level model specification suitable for reprinting all governing equations; the indexed model specification and assumptions register remain the required supplementary sources.

Monthly crop modules represent net primary production, allocation to shoot and root carbon, yield, and residue return. Phosphorus processes represent an available-P stock, plant and AMF acquisition, whole-plant demand limitation, and explicit phosphorus accounting. Direct-root and AMF pathways use separate aggregate uptake kinetics while drawing from the same available-P stock. AMF processes represent plant carbon allocation, carbon-use efficiency, fungal respiration, biomass turnover, necromass, phosphorus contribution, and necromass routing into represented carbon pools. Many crop, AMF, and phosphorus magnitudes are literature-informed priors or provisional scenario assumptions rather than calibrated field relationships.

Carbon and phosphorus sources, transfers, exports, and losses are explicitly accounted. The variable `protected_soc` is always interpreted as a humified/protected model proxy, never as measured mineral-associated organic carbon (MAOC).

### 2.3 Scheduled management and recurring accounting

Management actions are scheduled events with deterministic same-month ordering and event identifiers. Costs and greenhouse-gas-emissions proxies are additive metadata and do not alter mechanistic carbon or phosphorus stocks. Repeating events are accumulated across the simulated horizon, distinguishing operational from partial lifecycle proxies. These quantities are not a complete life-cycle assessment or regional budget and were excluded from headline machine-learning targets. Historical defects involving a duplicate policy and horizon-invariant accounting are summarized in the computational-audit subsection and Supplementary Table S3.

### 2.4 Empirical soil–climate pilot and generated fields

The empirical pilot used a predeclared 64-location temperate Great Britain arable frame. Coordinates were rounded to 0.1° and did not identify farms or fields. SoilGrids 2.0 median predictions were requested for 0–5, 5–15, and 15–30 cm layers; the upper 8 cm of the third layer was used to harmonize values to 0–23 cm. SOC stock was derived from concentration, bulk density, and layer thickness, and independently predicted texture fractions were renormalized with corrections retained. Extracted soil variables available to the final ML workflow were clay, silt, sand, bulk density, pH, cation-exchange capacity, baseline total nitrogen, and baseline SOC.

Monthly NASA POWER v10/MERRA-2 records for 2001–2020 supplied mean, minimum, and maximum 2-m air temperature and corrected precipitation. Monthly potential evapotranspiration was derived from monthly mean temperature, latitude, and daylength using the documented Thornthwaite assumption. Eight locations were rejected because SoilGrids median values were null across the required depth–property combinations; 56 paired locations remained, each with a soil record and 240 monthly climate records. This is a limited empirical pilot, not representative coverage. The audit also recorded a pre-renormalization texture-closure caveat and uncertainty arising from mapped soil predictions, reanalysis climate, and derived PET.

Two descendants were generated per accepted location, giving 112 synthetic fields. Observed between-location soil–climate covariance was inherited from the empirical anchors. Bounded within-location perturbations and latent available-P, AMF, drainage, and management-history priors remained synthetic. Periodic-equilibrium spin-up initialized pools; the allocation of total carbon among pools was a structural assumption rather than an observation.

Empirical location was the grouping unit for ML isolation. The final leakage evidence recorded 56 groups, with 31 training groups and 25 groups excluded from preprocessing fitting. Validation groups used for interval calibration were excluded from test, weather-OOD, and archetype-OOD evaluation. Exact and near-duplicate fields were also checked across groups.

### 2.5 Hoosfield total-SOC evaluation

Long-term evaluation used total-SOC observations for three Hoosfield treatments: unfertilized, annual FYM, and FYM applied from 1852 to 1871 followed by cessation. Observations were available for 1852, 1882, 1913, 1946, 1965, 1975, 1982, and 1998. The 1852 value initialized each trajectory; post-initialization values were evaluated with mean absolute error (MAE), root-mean-square error (RMSE), and mean signed bias.

The analysis compared the originally authored forcing with the official monthly normal bundled in the verified RothC/Hoosfield v2.1.1 archive. The corrected forcing was applied uniformly without changing RothC turnover constants or treatment schedules. Optional calibration varied plant-residue and FYM input-reconstruction factors within predeclared bounds. The documented grid fit used unfertilized and annual-FYM observations through 1965; later observations and the complete FYM-cessation treatment were held out. The FYM factor was constrained to 0.90–1.10. The profile objective was mean treatment RMSE in t C ha⁻¹, profiled over the plant-residue factor within its bounds. Calibrated factors were diagnostic and were not retained as general simulator parameters.

### 2.6 Global sensitivity analysis

The final workflow retained Morris elementary-effects screening and corrected variance-based sensitivity analysis. The Sobol design used one scrambled, seeded 10-column sequence split into two five-factor matrices, with hybrid matrices formed by replacing one A-matrix factor with its B-matrix value. First-order estimates used the Saltelli covariance form and total-order estimates used the Jansen squared-difference form; negative finite-sample estimates were retained. Two hundred deterministic bootstrap resamples per base size produced percentile 95% intervals, with bootstrap seed equal to the analysis seed plus base size.

The five factors and bounds were: empirical-location index, uniform discrete 0–55; weather-resample index, uniform discrete 0–9; schedule interval, uniform discrete 12–36 months; tillage decomposition multiplier, uniform 1–2; and FYM phosphorus content, uniform 0–30 in the configured units. Outputs comprised protected-SOC-proxy, respiration, and total-SOC effects at 60 and 120 months, plus yield effect at 24 months. The indexed result covered four policies, but their exact names are absent from the compact methods evidence and are therefore not inferred. Base sizes were 128, 256, 512, and 1,024, corresponding to 7N evaluations for five factors.

Convergence was decided from the largest nested comparison and required maximum adjacent changes in S1 and ST ≤0.10, both rank correlations ≥0.90, mean 95% interval width ≤0.20, and unstable fraction ≤0.10. Failure of any component prevented final sensitivity claims. Supplementary Table S5 contains the reproducible design summary; unresolved details are listed in `unresolved_methods_v2.md`.

### 2.7 Effect-only machine-learning evaluation

Targets were paired intervention-minus-baseline simulator effects. The seven target–horizon combinations were protected-SOC-proxy, respiration, and total-SOC effects at 60 and 120 months, and yield effect at 24 months. Final stocks, deterministic cost, deterministic emissions, and phosphorus were excluded from headline targets.

The evidence bundle documents a regularized linear ridge model fit by normal equations, with regularization strength selected on validation data, and a policy-mean comparator. The retained model card reports selected alpha 0.1 for every target. Observable inputs were clay, silt, sand, bulk density, pH, cation-exchange capacity, baseline total nitrogen, baseline SOC, mean temperature, annual precipitation, and annual PET. Latent AMF allocation, carbon-use efficiency, turnover, necromass stabilization, hidden initial pools, and spin-up diagnostics were excluded.

Performance was evaluated using MAE, RMSE, bias, and R² on test and OOD regimes. The prediction gate required every target-specific ridge model to beat its policy-mean comparator on test RMSE. OOD acceptability required model RMSE no greater than 1.10 times the policy-mean OOD RMSE. Exact train/validation/test row allocation and the complete definitions of weather-OOD and archetype-OOD construction are not present in the compact bundle and are recorded as unresolved methods.

### 2.8 Residual coverage and readiness gates

Absolute validation residuals defined target-specific predictive intervals. Coverage was evaluated separately for test and OOD regimes against nominal 0.90 coverage. A target–regime cell passed only if its count fell within the exact central 95% Binomial(n, 0.90) range, without severe undercoverage, excessive overcoverage, or interval width exceeding five times RMSE. Regimes with fewer than 20 rows or fewer than four independent groups abstained. These checks concern predictive residual coverage within synthetic evaluation regimes, not structural, causal, or real-field uncertainty.

Five gates formed a conjunctive readiness rule: effect prediction, empirical-location leakage isolation, independent empirical intervention-effect validation, OOD performance, and target-specific uncertainty. Independent validation required an identified independent dataset with at least 30 observations, compatible treatments, coverage of all primary target–horizon combinations, and no use in calibration or model development. Every gate was evidence-derived and missing evidence failed closed. Supplementary Table S6 defines the inputs, thresholds, and failure behavior.

### 2.9 Reproducibility and computational audits

The final system recorded dependency declarations, package version, source and artifact hashes, pipeline commands, and deterministic manifests. Software verification included formatting, linting, strict typing, tests, builds, installed-wheel import, command-line smoke tests, and replay of artifact manifests. Frozen scientific artifacts were not overwritten.

The development record includes an initial computational audit, empirical-grounding remediation, a clean-context audit of the revised evidence, corrected sensitivity and readiness implementation, a focused computational re-audit, and final archive verification. The audits were performed in separate, clean-context AI sessions using read-only repository access or temporary scratch copies. They reviewed implementation and claims; they did not supply new observations or independently validate the biology. Audit findings covered stock-target circularity, limited population grounding, phosphorus interpretation, recurring accounting, a duplicate policy, sensitivity construction and convergence, hardcoded gates, forced downstream logic, uncertainty criteria, calibration-boundary disclosure, artifact history, and documentation.

## 3. Results

### 3.1 Software verification and deterministic replay

Final archive verification passed formatting, linting, strict typing, package-build, installed-wheel, command-line, link, table, figure, and manifest checks. The complete final replay passed 234 tests. The focused computational re-audit reproduced headline metrics and verified all 35 paths in the final sensitivity/readiness artifact set. Repeated corrected pipelines were byte-identical under the audited conditions. These findings verify implementation and reproducibility under frozen configurations; they do not constitute biological or field validation. Full provenance identifiers and digests are retained in the supplementary manifests rather than the main results.

### 3.2 Empirical pilot and generated fields

Fifty-six of the 64 planned Great Britain locations had complete paired soil and climate records; eight were rejected for missing SoilGrids median values. Depth and unit harmonization reproduced exactly across 56 locations and nine harmonized columns. Two descendants per accepted location produced 112 synthetic fields. Location grouping remained isolated, but the modest geographic frame, mapped/reanalysis inputs, synthetic descendants, and latent priors preclude representative population claims.

### 3.3 RothC parity and mass balance

The documented January 1852 decay case reproduced DPM 0.1139, RPM 4.4454, BIO 0.6651, HUM 25.8551, and CO₂-C 0.0836 t C ha⁻¹, with agreement better than 10⁻⁴. Audited residuals were 5.68×10⁻¹⁴ t C ha⁻¹ for carbon and 1.42×10⁻¹⁴ kg P ha⁻¹ for phosphorus. The result supports arithmetic parity and enforced accounting, not biological accuracy.

### 3.4 Hoosfield performance and FYM calibration failure

Original-forcing aggregate post-initialization total-SOC performance had RMSE 10.154 t C ha⁻¹. Source-corrected uncalibrated forcing reduced aggregate RMSE to 4.340 t C ha⁻¹, with MAE 3.657 and bias −0.528 t C ha⁻¹ (Figure 2; Table 2). This was a source correction using the official forcing, not parameter tuning.

The optional calibrated run did not improve the aggregate result and did not generalize to cessation. The FYM reconstruction factor reached the 1.10 upper bound, the objective continued to decrease toward that boundary, and general calibration success was false. Held-out cessation RMSE was 7.577 t C ha⁻¹, with MAE and bias magnitudes both 7.214 t C ha⁻¹. This is an explicit calibration failure. Hoosfield evaluated total SOC only and did not validate AMF dynamics or the protected-SOC proxy.

**[Figure 2 near here]**

**Table 2. Hoosfield total-SOC evaluation.**

| Run | Evaluation role | MAE | RMSE | Bias | Units |
|---|---|---:|---:|---:|---|
| Original forcing | All post-initialization observations | 8.518 | 10.154 | −8.360 | t C ha⁻¹ |
| Source-corrected, uncalibrated | All post-initialization observations | 3.657 | 4.340 | −0.528 | t C ha⁻¹ |
| Optional bounded calibration | All post-initialization observations | 3.817 | 4.948 | −2.354 | t C ha⁻¹ |
| Optional bounded calibration | Complete held-out FYM cessation treatment | 7.214 | 7.577 | −7.214 | t C ha⁻¹ |

### 3.5 Corrected sensitivity analysis and non-convergence

The corrected workflow used the declared scrambled Sobol design, standard first- and total-order estimators, retained negative estimates, and deterministic bootstrap intervals. Across the nested base sizes, maximum adjacent index changes declined but did not meet the predeclared threshold (Figure 3; Table 3). At 512→1,024, maximum changes were 0.122 for S1 and 0.112 for ST. Rank correlations, mean interval width, and unstable fraction passed their thresholds, but the two index-change criteria failed. Sensitivity estimates were therefore non-converged and remain diagnostic rather than final.

**[Figure 3 near here]**

**Table 3. Nested sensitivity convergence. All comparisons failed the conjunctive rule.**

| Base-size comparison | Max |ΔS1| | Max |ΔST| | S1 rank correlation | ST rank correlation | Mean CI width | Converged |
|---|---:|---:|---:|---:|---:|---|
| 128→256 | 0.222 | 0.188 | 0.912 | 0.992 | 0.216 | No |
| 256→512 | 0.141 | 0.134 | 0.913 | 0.988 | 0.157 | No |
| 512→1,024 | 0.122 | 0.112 | 0.935 | 0.997 | 0.110 | No |

### 3.6 Leakage and residual-coverage checks

All five leakage-isolation checks passed. Evidence covered empirical-location grouping, descendant isolation by empirical seed, preprocessing fitted on training groups only, exclusion of calibration groups from final evaluation, and absence of exact or near-duplicate fields across groups. Injection tests in the focused computational re-audit caused the gate to fail when crossovers or missing evidence were introduced.

All 14 target-by-regime residual-coverage cells passed the final rules. Test cells contained 104 rows from 11 empirical locations, and OOD cells contained 24 rows from four locations. The small OOD sample made the binomial acceptance range broad and the check low-powered against overcoverage. Passing coverage therefore does not quantify structural, causal, mechanistic, or real-field uncertainty.

### 3.7 Prediction, OOD, and independent-validation failures

The all-target prediction gate failed because the 24-month yield-effect ridge model did not beat the policy-mean comparator on test RMSE (0.0555 versus 0.0550 t dry matter ha⁻¹). The OOD gate also failed for that target: ridge RMSE was 0.0697 compared with policy-mean RMSE 0.0619, exceeding the 1.10 tolerance. Other indexed targets passed these target-specific comparisons, but the all-target conjunction remained false.

No eligible independent empirical intervention-effect dataset was supplied. The validation contract therefore recorded sample size zero, non-computability, and failure. The focused computational re-audit verified that the gate could pass with structurally valid evidence and failed on malformed or absent evidence.

### 3.8 Blocked downstream selection

Three of the five required gates—prediction, OOD performance, and independent empirical effect validation—failed (Figure 4; Table 4). Leakage and target-specific residual coverage passed. Because eligibility was a genuine conjunction, downstream selector, oracle, and regret analyses remained unexecuted. The stop decision was the intended fail-closed outcome, not evidence for any intervention.

**[Figure 4 near here]**

**Table 4. Readiness-gate outcomes.**

| Gate | Outcome | Consequence |
|---|---|---|
| Effect prediction | Fail | Required prerequisite not met |
| Empirical-location leakage | Pass | Isolation evidence met the encoded checks |
| Independent empirical effect validation | Fail | No eligible dataset; sample size zero |
| OOD performance | Fail | Required prerequisite not met |
| Target-specific residual coverage | Pass | Synthetic residual-coverage rule met |
| Downstream execution | Blocked | Selector, oracle, and regret not run |

### 3.9 Computational-audit remediation summary

The initial computational audit identified stock-target circularity, weak empirical grounding, an uncalibrated phosphorus loop, horizon-invariant accounting, a duplicate policy, and missing long-term and sensitivity evidence. Subsequent remediation introduced paired effect targets, recurring accounting, policy deduplication, bounded phosphorus interpretation, the empirical pilot, and Hoosfield evaluation. A later clean-context audit identified manifest drift, an invalid sensitivity sampler and convergence label, hardcoded gate values, a structurally forced stop, permissive uncertainty logic, and insufficient calibration-boundary disclosure. The corrected implementation replaced those mechanisms with computed evidence and explicit failure behavior. A focused, separate, clean-context, read-only computational re-audit classified six implementation defects as closed and three as substantially addressed, with the remaining issues retained as scientific limitations. Supplementary Figure S2 and Table S3 give the provenance chronology.

## 4. Discussion

### 4.1 What was verified and what was evaluated

The framework achieved strong bounded software evidence: typed modular architecture, deterministic replay, artifact hashing, a green quality suite, documented RothC parity, and enforced carbon and phosphorus accounting. Empirical evaluation was narrower. The soil–climate data provided 56 paired location anchors, and Hoosfield supplied multi-decadal total-SOC observations for three treatments. These data improved the evidence base but did not validate the complete biological system.

The distinction matters because mass balance constrains represented flows without establishing correct flux magnitudes. Total-SOC trajectory fit does not independently test crop response, phosphorus limitation, fungal allocation, necromass routing, or the protected-SOC proxy. Likewise, software and computational-audit success cannot establish causal agricultural effects.

### 4.2 Paired effects reduced circularity but did not establish causality

Replacing final stock targets with intervention-minus-baseline effects reduced dependence on persistent initial stocks. Excluding deterministic accounting fields and hidden biological variables further reduced direct shortcuts. Grouping descendants by empirical location addressed a clear leakage risk. These are meaningful methodological improvements.

The resulting targets nevertheless remain simulator contrasts. Their variation inherits simulator structure, policy definitions, provisional priors, and synthetic descendants. A strong policy-mean comparator also showed that much of the effect signal was organized by policy identity. Paired effects therefore improved target validity within the simulator but did not create empirical causal evidence.

### 4.3 The fail-closed stop was scientifically appropriate

The readiness rule prevented favorable subsets of evidence from authorizing selection. Leakage and residual-coverage checks passed, but the yield target failed both test and OOD requirements, and external intervention-effect validation was absent. Because every prerequisite was required, no selector was run.

This is the central methodological result. A workflow optimized for positive presentation could have emphasized better-performing SOC or respiration targets and continued to intervention ranking. The fail-closed workflow instead treated target heterogeneity, distribution shift, and absent external evidence as decisive. It converted insufficient evidence into an auditable stop rather than a recommendation.

### 4.4 Contribution of computational auditing

Separate, clean-context, read-only computational audits added adversarial implementation review beyond the project’s own tests. They recomputed metrics, inspected source-to-artifact contracts, reproduced sensitivity construction, injected leakage failures, tested whether gates could change state, checked history-preserving manifests, and challenged documentation. Audit findings materially improved the evidence pipeline by replacing literal or structurally forced outcomes with computed contracts.

These audits were AI-executed and must not be represented as independent human or institutional peer review. They reviewed implementation and claim alignment, not biological truth. Their strongest contribution was to expose where software assurance ended and unresolved scientific limitations began.

### 4.5 Remaining limitations

The empirical frame was limited to 56 accepted Great Britain locations and used mapped soil predictions, reanalysis climate, derived PET, and synthetic descendants. Soil texture required renormalization, and observation uncertainty was not propagated. Crop, AMF, phosphorus, and management-response parameters remain provisional or broadly prior informed. Spin-up pool allocation was not observed. `protected_soc` is a model proxy, not measured MAOC.

Hoosfield evaluated total SOC at one long-term experiment. Although source correction improved aggregate fit, the optional FYM factor was boundary constrained and cessation performance remained weak. Sensitivity estimates were non-converged. Predictive intervals described residual coverage in synthetic regimes only. The yield-effect model failed prediction and OOD gates, and no independent empirical intervention-effect dataset was available. These limitations block real-farm prediction, causal intervention claims, carbon-credit quantities, generalisable selection, field recommendations, and agricultural deployment readiness.

### 4.6 Future work

Future work should extend the predeclared sensitivity sequence and reassess convergence without relaxing thresholds; broaden soil–climate sampling with explicit coverage analysis; calibrate and evaluate total-SOC behavior across independent long-term experiments; obtain empirical AMF, phosphorus, and carbon-fraction observations; assemble independent treatment-compatible intervention-effect datasets; and evaluate machine-learning models on externally collected effects and larger OOD regimes. These are required strengthening steps, not completed analyses.

## 5. Conclusions

The final framework combines reproducible soil–plant–AMF simulation, explicit carbon and phosphorus accounting, bounded empirical evaluation, corrected sensitivity methods, effect-only machine learning, and computed readiness gates. Arithmetic, accounting, deterministic replay, and implementation remediation were verified. Source correction improved aggregate Hoosfield total-SOC performance, but FYM calibration remained boundary constrained and failed on cessation. Sensitivity remained non-converged. Prediction, OOD, and independent empirical validation gates failed, so downstream selection was not executed.

The contribution is a methodological and software demonstration of evidence-gated stopping. It does not support agricultural prediction or recommendation.

## 6. Data availability

The imported archive indexes raw external responses, processed pilot records, generated fields, simulated outputs, and their manifests. Redistribution remains subject to upstream terms, including current Rothamsted e-RA conditions. [PUBLIC DATA REPOSITORY AND DOI TO BE SUPPLIED.]

## 7. Software availability

The indexed software is `soil-simulator` version 0.9.7. The supplied checkout lacks Git metadata, so commit identity is unavailable. Package metadata records a proprietary licence. [SOFTWARE REPOSITORY, RELEASE DOI, AND FINAL LICENCE/ACCESS CONDITIONS TO BE SUPPLIED.]

## 8. Reproducibility statement

The preferred environment uses the frozen `uv.lock`; final archive verification used the existing locked Python 3.14.6 environment because `uv` was absent. Provenance identifiers remain attached to the archived v0.9.5, v0.9.6, and v0.9.7 artifacts and to the final archive manifests. Historical scientific outputs must not be overwritten during replay.

## 9. AI-assisted development and computational-audit disclosure

The human author directed the research question, scientific scope, architecture, validation priorities, and interpretation. AI coding assistants supported implementation, testing, evidence organization, and documentation. Separate, clean-context AI sessions conducted read-only computational audits; findings led to remediation, and negative results and failed gates were preserved. These computational audits do not replace human peer review or independent empirical validation. The human author retains responsibility for the work and interpretation. AI systems are not authors. [AUTHOR TO SUPPLY SUPPORTED PRODUCT/MODEL NAMES, VERSIONS, DATES, AND JOURNAL-REQUIRED WORDING.]

## 10. Author contributions

[AUTHOR NAME(S), ORCID(S), AND CRediT ROLES TO BE SUPPLIED.]

## 11. Funding

[FUNDING SOURCE, GRANT NUMBER, AND FUNDER ROLE TO BE SUPPLIED, OR CONFIRM NO SPECIFIC FUNDING.]

## 12. Competing interests

[COMPETING-INTEREST DECLARATION TO BE SUPPLIED.]

## 13. Acknowledgements

[ACKNOWLEDGEMENTS TO BE SUPPLIED.]

## 14. References

Coleman, K., Milne, A. E., and Prout, J. M. (2024). *Python version of RothC Official Rothamsted Research Release, v1.0.0*. Zenodo. doi:10.5281/zenodo.10732265.

Rothamsted Research. (2024). *RothC—A model for the turnover of carbon in soil: Model Description*. Rothamsted Research.

References with incomplete metadata are not presented as completed citations; see `unresolved_citations_v2.md`.

## 15. Main figure legends

**Figure 1. Final simulator and evidence-pipeline architecture.** Configuration, typed contracts, process modules, simulation, population construction, evaluation, readiness gates, and evidence manifests are separated. Source: curated `figure_01_model_architecture.svg`. Architecture does not imply biological validation.

**Figure 2. Hoosfield observed and simulated total-SOC trajectories.** Observations are distinguished from original-forcing, source-corrected uncalibrated, and optional bounded-calibration trajectories for the three treatments. Source: curated `figure_05_hoosfield_trajectories.svg`. The evaluation concerns total SOC only.

**Figure 3. Sensitivity convergence diagnostics.** Adjacent S1 and ST changes are compared across nested base sizes. Source: curated `figure_08_sensitivity_convergence.svg`. Results are explicitly non-converged and diagnostic.

**Figure 4. Fail-closed readiness gates.** Prediction, empirical-location leakage, independent validation, OOD performance, and residual coverage feed the conjunctive downstream decision. Source: curated `figure_10_ml_gate_summary.svg`. The blocked result is not an intervention recommendation.

## 16. Main table legends

**Table 1. Final model and evidence-pipeline components.** Verification and scientific boundaries are separated.

**Table 2. Hoosfield total-SOC evaluation.** Original, corrected, calibrated, and held-out roles are distinguished.

**Table 3. Nested sensitivity convergence.** All comparisons failed the conjunctive rule.

**Table 4. Readiness-gate outcomes.** Three failed prerequisites blocked downstream execution.

## 17. Supplementary figures and tables

**Supplementary Figure S1. Represented carbon and phosphorus flows.** Source: curated `figure_02_carbon_phosphorus_flow.svg`. The protected-SOC state is a model proxy, not measured MAOC.

**Supplementary Figure S2. Computational-audit and remediation chronology.** Source: curated `figure_11_audit_remediation_timeline.svg`. Phase/version identifiers are retained in the source chronology for provenance. Computational audit is implementation review, not human peer review or biological validation.

**Supplementary Table S1. Data-source and empirical-pilot record.** Includes source classes, frame, depth harmonization, variables, access date, and limitations.

**Supplementary Table S2. Software-verification record.** Includes the final replay, parity, balance, deterministic replay, package, and manifest checks.

**Supplementary Table S3. Computational-audit finding and remediation summary.** Historical identifiers are retained only for provenance.

**Supplementary Table S4. Claim-boundary register.** Lists permitted, qualified, and prohibited interpretations.

**Supplementary Table S5. Reproducible sensitivity-methods summary.** Lists factors, distributions, bounds, outputs, base sizes, bootstrap, estimators, and convergence rule; absent policy names are explicitly marked unresolved.

**Supplementary Table S6. Readiness-gate definitions.** Lists evidence inputs, thresholds, and fail-closed behavior for all five gates.

### Supplementary Table S1. Data-source and empirical-pilot record

| Source | Coverage/use | Processing | Boundary |
|---|---|---|---|
| SoilGrids 2.0 | 64 requested; 56 accepted; 0–23 cm covariates | Thickness weighting, unit conversion, texture renormalization | Mapped medians; eight missing-data rejections; texture-closure caveat |
| NASA POWER v10/MERRA-2 | Monthly 2001–2020; 240 records per accepted location | Temperature and precipitation; Thornthwaite PET | Reanalysis; PET derived; source uncertainty unpropagated |
| RothC/Hoosfield v2.1.1 | Official monthly normal and treatment reconstruction | Source-corrected forcing | Total SOC only; citation metadata pending |
| Rothamsted e-RA Hoosfield | Three treatments; 1852–1998 observations | Normalized total-SOC fixture | Redistribution and citation metadata pending |

### Supplementary Table S2. Software-verification record

| Check | Result | Interpretation |
|---|---|---|
| Complete final replay | 234 tests passed | Software verification, not scientific validation |
| RothC parity | Documented case passed | Arithmetic fidelity of one decay step |
| Carbon/P properties | Passed within suite | Enforced accounting, not biological accuracy |
| Corrected pipeline replay | Byte-identical under audited conditions | Determinism under frozen configurations |
| Final artifact paths | 35/35 verified in focused re-audit | File identity, not Git identity |
| Build/wheel/CLI | Passed | Package integrity and basic execution |

### Supplementary Table S3. Computational-audit finding and remediation summary

| Provenance stage | Finding/remediation | Residual scientific boundary |
|---|---|---|
| v0.9.0 initial audit | Stock circularity, authored population, P loop, accounting, duplicate policy, missing evaluation | Field/causal/AMF/protected-SOC validation absent |
| v0.9.5 remediation | Effect-only targets, recurring accounting, deduplication, bounded P interpretation, initial evaluation | Empirical population and corrected sensitivity unresolved |
| v0.9.6 empirical grounding and clean-context audit | 56-location pilot and Hoosfield correction; audit exposed manifest, sensitivity, gate, uncertainty, and calibration-disclosure defects | Pilot thin; cessation weak; agricultural prediction unsupported |
| v0.9.7 corrected implementation and focused re-audit | Computed gates, genuine Sobol design, convergence and coverage rules, boundary profile, history-preserving manifests | Sensitivity non-converged; small-n OOD; no empirical effects |
| Final archive verification | Ten audit deliverables restored and complete bundle replayed | Scientific limitations unchanged |

### Supplementary Table S4. Claim-boundary register

| Class | Examples |
|---|---|
| Permitted | Deterministic replay; enforced carbon/P balance; documented parity; 56-location pilot; improved aggregate uncalibrated Hoosfield fit; failed prediction/OOD gates; blocked selection |
| Qualified | Pilot is limited; sensitivity non-converged; `protected_soc` proxy; residual coverage is not field uncertainty; FYM boundary/cessation failure |
| Prohibited | Real-farm prediction; causal effects; recommendations; national representativeness; measured MAOC; carbon-credit quantities; generalisable selection; agricultural deployment readiness |

### Supplementary Table S5. Reproducible sensitivity-methods summary

| Item | Specification | Range/setting | Evidence boundary |
|---|---|---|---|
| Factor 1 | Empirical-location index | Uniform discrete 0–55 | Accepted pilot anchors |
| Factor 2 | Weather-resample index | Uniform discrete 0–9 | Complete-year resampling |
| Factor 3 | Schedule interval | Uniform discrete 12–36 months | Scenario assumption |
| Factor 4 | Tillage decomposition multiplier | Uniform 1–2 | Scenario assumption |
| Factor 5 | FYM phosphorus content | Uniform 0–30 | Configured units; scenario assumption |
| Outputs | Seven target–horizon pairs | Protected proxy, respiration, total SOC at 60/120; yield at 24 | Proxy is not measured MAOC |
| Policies | Four indexed policies | Exact names absent | Not inferred in manuscript |
| Base sizes | Nested Sobol | 128, 256, 512, 1,024 | 7N evaluations |
| Bootstrap | Deterministic percentile intervals | 200 resamples; 95%; seed plus N | Negative estimates retained |
| Estimators | Saltelli S1; Jansen ST | Standard forms in audit evidence | Citation metadata pending |
| Convergence | Conjunctive rule | Δ≤0.10; ranks ≥0.90; width ≤0.20; unstable ≤0.10 | Failure means diagnostic only |

### Supplementary Table S6. Readiness-gate definitions

| Gate | Evidence input | Threshold/criterion | Fail-closed behavior |
|---|---|---|---|
| Effect prediction | Target-specific ridge and policy-mean test RMSE | Every target ridge beats policy mean | Missing/failed target fails gate |
| Location leakage | Location, descendant, preprocessing, calibration, duplicate evidence | All five checks computable and pass | Missing columns or evidence fail |
| Independent effect validation | Dataset identity, sample, treatment and target coverage, independence | At least 30 observations; all target–horizon pairs; unused in development | Absent or malformed evidence fails |
| OOD performance | Target-specific ridge and policy-mean OOD RMSE | Every target ridge ≤1.10× comparator | Missing/failed target fails |
| Residual coverage | Per target/regime counts, Wilson intervals, width | Central 95% Binomial rule; width ≤5× RMSE; minimum 20 rows/4 groups | Undersized regime abstains; failed cell fails |
| Downstream eligibility | Five gate booleans | Logical conjunction of all five | Any failure blocks execution |

## 18. Supplementary-material index

- Effect-only model card.
- Leakage evidence.
- Target- and regime-specific uncertainty evidence.
- Sensitivity sampling and convergence manifests.
- Calibration profile and validation residuals.
- Assumptions register.
- Source and artifact manifests.
- Canonical computational-audit reports and closure records.
- Large-file index for frozen generated, sensitivity, and ML artifacts.