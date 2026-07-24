# Methods expansion report

## Scope and evidence rule

This expansion is evidence extraction only. No model, configuration, dataset, scientific output, gate, test, audit or historical artifact was changed or regenerated. The three requested `manuscript/v2/...` inputs do not exist in this archive; the exact v2 files are `manuscript/manifests/unresolved_methods_v2.md`, `manuscript/manifests/manuscript_v2.md`, and `manuscript/manifests/drafting_evidence_map_v2.csv`. Source: repository file inventory; mapping confirmed by `manuscript/manifests/README.md`.

Executable code/configuration was treated as authoritative for implemented equations/settings; immutable outputs for assignments/counts/objective values; and documentation/audits for provenance, rationale and claim boundaries. No missing scientific rationale was inferred. Governing boundaries: `AGENTS.md:5-51`; `docs/MODEL_SPEC.md`; `docs/VALIDATION_PLAN.md`; `docs/ARCHITECTURE.md`.

## Gap disposition

| ID | requested gap | classification | verified result |
|---|---|---|---|
| MEP-01 | Complete RothC modifier and monthly-transition equations | `RESOLVED_FROM_CODE` | All modifiers, pool decay, retained-carbon routing, input timing and state updates are explicit. |
| MEP-02 | Complete crop, residue, P and AMF equations/defaults | `RESOLVED_FROM_CODE` | Equations and executable defaults are extracted in EQUATIONS_AND_PROCESSES.md and the parameter register. |
| MEP-03 | Full parameter table with units, defaults, provenance and status | `RESOLVED_FROM_CONFIG` | All in-scope executable model, pilot, sensitivity, calibration and ML settings are registered. |
| MEP-04 | Assumptions register is not a complete executable specification | `RESOLVED_FROM_CONFIG` | Executable configuration supplies values/ranges; the assumptions register supplies status and qualifications. |
| EMP-01 | Exact rule and source used to choose the 64 coordinates | `PARTIALLY_RESOLVED` | The fixed list and downstream replay are documented; original frame construction is retained as an irrecoverable historical provenance limitation. |
| EMP-02 | Processed soil columns and conversion/weighting formulas | `RESOLVED_FROM_CODE` | All 16 processed columns, unit-divisor conversion, 0-23 cm weighting, SOC stock and texture closure are explicit. |
| EMP-03 | Bounds/distributions for descendant perturbations | `RESOLVED_FROM_CODE` | Every random draw, deterministic coefficient, clamp and QC bound is extracted. |
| EMP-04 | Latent P, AMF, drainage, history and pool-allocation priors | `RESOLVED_FROM_CODE` | Fixed anchor priors, stochastic perturbations and periodic spin-up are explicit. |
| EMP-05 | Allocation of all 56 groups and exact split counts | `RESOLVED_FROM_ARTIFACT` | DATA_SPLIT_REGISTER.csv contains every accepted location, split, descendants and benchmark row contribution. |
| EMP-06 | Weather-OOD versus archetype-OOD construction | `RESOLVED_FROM_CONFIG` | Weather OOD is four listed location regions; archetype OOD is empty in the final pilot. |
| HOO-01 | Plant-residue bounds and calibration grid | `RESOLVED_FROM_CODE` | Plant factor 0.80-1.20 by 0.05 and FYM factor 0.90-1.10 by 0.05 form 45 candidates. |
| HOO-02 | How both calibration factors enter reconstructed inputs | `RESOLVED_FROM_CODE` | Annual/monthly reconstruction and 1.44 plus 49/49/2 routing equations are explicit. |
| HOO-03 | Complete two-dimensional calibration objective surface | `RESOLVED_FROM_ARTIFACT` | All 45 objective values already exist and are reproduced in HOOSFIELD_METHODS.md. |
| SEN-01 | Exact four corrected sensitivity policies | `RESOLVED_FROM_CODE` | conventional_tillage, reduced_tillage, cover_crop and farmyard_manure. |
| SEN-02 | Complete Morris settings and factor bounds | `RESOLVED_FROM_CONFIG` | Six trajectories, six levels, seed 960021 and all 15 screened factor transforms are explicit. |
| SEN-03 | Every stored sensitivity output | `RESOLVED_FROM_CODE` | The Phase 9.6 screen stores six output families; the corrected Phase 9.7 artifact retains 28 policy-target-horizon outputs. |
| SEN-04 | Rationale for endpoint half-weighting | `PARTIALLY_RESOLVED` | The mapping, unequal endpoint probabilities and low-severity limitation are disclosed; no scientific rationale is supplied. |
| MLG-01 | Candidate models actually evaluated in final benchmark | `RESOLVED_FROM_CODE` | Only RidgeModel and PolicyMeanModel are fit/evaluated. |
| MLG-02 | Alpha grid and tie-breaking rule | `RESOLVED_FROM_CODE` | Grid is (0.1,1.0,10.0); strict score improvement retains the first/smallest alpha on an exact tie. |
| MLG-03 | Train/validation/test/OOD rows and policy composition | `RESOLVED_FROM_ARTIFACT` | Per primary target: 236/84/104/24 rows from 59/21/26/6 fields and 31/10/11/4 locations, with four policies in equal field-wise composition. |
| MLG-04 | Exact target-level OOD pooling rule | `RESOLVED_FROM_CODE` | All weather_ood rows for a target/horizon and four headline policies are pooled; no archetype-OOD rows exist. |
| MLG-05 | Complete prediction and OOD gate formulas | `RESOLVED_FROM_CODE` | Prediction is a conjunction of strict ridge<policy-mean test RMSE; OOD is a conjunction of ridge<=1.10*policy-mean OOD RMSE. |
| MLG-06 | Interval quantile, Binomial and Wilson formulas | `RESOLVED_FROM_CODE` | All quantile ranks, count acceptance, Wilson intervals, width, abstention and conjunction logic are explicit. |

## Documentation-addendum closure

`METHODS_LIMITATIONS_ADDENDUM.md` supplies manuscript-ready Methods, Limitations and Reproducibility wording for the coordinate-frame provenance boundary, and Sensitivity Methods, Limitations and Future Work wording for the discrete-transform boundary. This closes the manuscript-disclosure gaps without claiming recovery of the missing coordinate-frame history or inventing a scientific rationale for unequal endpoint probability. Sources: `METHODS_LIMITATIONS_ADDENDUM.md`; `src/soil_simulator/phase96/empirical.py:32-110`; `src/soil_simulator/phase95/sensitivity.py:31-38`; `docs/audits/phase97_sobol_findings.md:41-48`; `outputs/phase97_v0.9.7/sensitivity_convergence_manifest.json`.

Final method status:

- Missing executable-method details: **0**.
- Disclosed irrecoverable historical provenance limitations: **1** (coordinate-frame construction).
- Disclosed discrete-sampling design limitations: **1** (round-based endpoint half-weighting).
- Requirements for new analysis: **0**.
- Requirements to modify the simulator: **0**.

Addendum verification boundary:

- Created: `manuscript/methods_expansion/METHODS_LIMITATIONS_ADDENDUM.md`.
- Updated: `manuscript/methods_expansion/METHODS_EXPANSION_REPORT.md`, `manuscript/methods_expansion/unresolved_after_expansion.md`, `manuscript/methods_expansion/methods_evidence_map.csv`, and `manuscript/methods_expansion/manifest.json`.
- No file outside `manuscript/methods_expansion/` changed; the deterministic aggregate SHA-256 over the pre-existing external file set remained `0680ffda3cf10d8a0bb5fb15582942e520b98d528ee4f532984398c1724c6e81`.
- Frozen files under `data/` and `outputs/` remained byte-identical; their deterministic aggregate SHA-256 remained `2fbf1bed14f4ea8a137a07e2d52a7e00f8d5b9dc99e222a75dcb50adf20d8378`.
- No analysis, simulation, test gate or audit was rerun. No assumption, equation, parameter, dataset, gate or scientific result changed.

## Validation performed

- Executable configuration loaded successfully through `load_model_parameters` and `load_population_config`; semantic hashes were `d9864cf8f17956ee313abbec6937f508d3de98c24fb25931e74759a975c65efb` and `c8e86664667ceb965990d6cf45d0a76aa40e5e336562f4976d3c6aeef7b8ff4e`. Loader sources: `src/soil_simulator/io/configuration.py:18-28`; `src/soil_simulator/io/population_configuration.py:12-19`; population validation: `src/soil_simulator/domain/population.py:117-194`.
- Every registered `config/model_defaults.yaml` default/range was extracted directly from the validated YAML; equations were cross-checked against pure process functions and simulator integration call sites. Sources: `COMPLETE_PARAMETER_REGISTER.csv`; `src/soil_simulator/processes/`; `src/soil_simulator/simulator/carbon_core.py`; `src/soil_simulator/simulator/amf_extension.py`.
- All 56 accepted location assignments were read from the frozen population artifact. Location split sets are disjoint; the Phase 9.7 leakage artifact independently reports 56 groups, zero overlaps and all five checks passed. Sources: `DATA_SPLIT_REGISTER.csv`; `outputs/phase97_v0.9.7/leakage_check_evidence.json`.
- Final sensitivity policy names and output keys match the corrected artifact: four policies, seven target-horizon combinations and five factors. Sources: `src/soil_simulator/phase97/pipeline.py:37-50`; `outputs/phase97_v0.9.7/sensitivity_first_total.csv`.
- Hoosfield objective values were copied from the existing 45-candidate artifact; no simulation or calibration was rerun. Source: `outputs/phase96_v0.9.6/long_term_diagnosis.json` (`optional_calibration.candidate_summary`).
- Before/after SHA-256 comparison excludes this new directory and verifies no pre-existing repository file changed. Manifest entries hash every non-manifest generated file; the final manifest hash is reported at handoff because a file cannot contain its own byte hash without circularity. Source: `manifest.json`.

## Required ending counts after the documentation addendum

- Method gaps fully resolved: **21**.
- Method gaps partially resolved as disclosed limitations: **2**.
- Missing executable-method details: **0**.
- Undisclosed methods limitations: **0**.
- Method gaps requiring new scientific justification: **0**.
- Method gaps requiring new analysis: **0**.
- Is the package sufficient for a bounded methodological/software manuscript without modifying the simulator? **Yes**, provided the two limitations in `METHODS_LIMITATIONS_ADDENDUM.md` remain disclosed. This sufficiency does not make the coordinate frame representative and does not make the non-converged sensitivity results final.

## Scientific uncertainties retained

The paired pilot is non-representative; descendant perturbations and unobserved P/AMF/history/drainage remain scenario priors; Hoosfield validates total SOC only and its FYM fit is boundary-constrained; sensitivity did not converge at the final threshold; and no independent empirical intervention-effect validation exists. `protected_soc` remains a model proxy, not measured MAOC. Sources: `docs/PHASE97_PUBLICATION_READINESS.md`; `outputs/phase97_v0.9.7/calibration_profile.json`; `outputs/phase97_v0.9.7/sensitivity_convergence_manifest.json`; `outputs/phase97_v0.9.7/gate_evidence.json`; `manuscript/CLAIM_BOUNDARIES.md`.

## Output-change statement

Scientific outputs did not change. The methods addendum and package-index updates are documentation only; they transcribe, qualify and index existing evidence.
