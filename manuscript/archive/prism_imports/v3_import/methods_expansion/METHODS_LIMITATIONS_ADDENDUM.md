# Methods limitations addendum

## Purpose and status

This addendum supplies manuscript-ready disclosure for two limitations identified by the methods-evidence expansion. It does not reconstruct missing history, supply a post hoc scientific rationale, alter an executable method, or change any result. The underlying evidence remains the archived coordinate tuple, empirical source manifest, implemented discrete transform, sensitivity audit and frozen convergence artifact. Sources: `src/soil_simulator/phase96/empirical.py:32-110` (`PILOT_LOCATIONS`); `outputs/phase96_v0.9.6/EMPIRICAL_SOURCE_MANIFEST.json`; `src/soil_simulator/phase95/sensitivity.py:31-38` (`SensitivityParameter.transform`); `docs/audits/phase97_sobol_findings.md:41-48`; `outputs/phase97_v0.9.7/sensitivity_convergence_manifest.json`.

## 1. Coordinate-frame provenance limitation

### Verified evidence boundary

The 64 Great Britain coordinates were fixed before the SoilGrids and NASA POWER extraction. The complete ordered tuple is archived in `src/soil_simulator/phase96/empirical.py:42-110` and transcribed in `EMPIRICAL_PILOT_METHODS.md`; the latter's byte hash is recorded in `manifest.json`. The raw and processed empirical files are separately byte-hashed in `outputs/phase96_v0.9.6/EMPIRICAL_SOURCE_MANIFEST.json`. Starting from the archived tuple, the extraction inputs, eight source-record rejections, 56 accepted locations and downstream group assignments are reproducible from repository evidence. Sources: `src/soil_simulator/phase96/empirical.py:42-110,248-342,406-413`; `outputs/phase96_v0.9.6/EMPIRICAL_SOURCE_MANIFEST.json`; `outputs/phase96_v0.9.6/generated_population_manifest.json`; `EMPIRICAL_PILOT_METHODS.md`; `DATA_SPLIT_REGISTER.csv`; `manifest.json`.

The archive does not preserve the procedure or external geographic frame used to construct the original 64-coordinate tuple. No selection algorithm, inclusion probabilities, sampling-frame definition or optimization criterion was found. This missing history must not be reconstructed by inference. Consequently, the frame cannot be described as random, probability based, nationally representative, optimally stratified or statistically representative. This limits reproducibility of the frame's original construction, not reproducibility of the analysed pilot dataset produced from the fixed archived list. The 56 accepted locations remain a limited empirical pilot. Sources searched and limitation basis: `src/soil_simulator/phase96/empirical.py:32-110`; `scripts/download_phase96_empirical.py`; `outputs/phase96_v0.9.6/EMPIRICAL_SOURCE_MANIFEST.json`; `docs/PHASE96_EMPIRICAL_GROUNDING.md`; `docs/audits/AUDIT_PHASE96_CLEAN_SLATE.md`.

### Manuscript-ready Methods wording

> Before empirical data extraction, the pilot used a fixed, predeclared list of 64 Great Britain coordinates rounded to 0.1 degrees. The complete ordered coordinate list is archived with the software and transcribed in the methods evidence package, where it is hash-verifiable. SoilGrids and NASA POWER extraction, source-record acceptance or rejection, and all downstream pilot analyses are reproducible from this fixed list. The historical procedure and external sampling frame used to construct the original list were not preserved; we therefore make no claim that the coordinate frame was random, probability based, nationally representative, optimally stratified or statistically representative.

Evidence for this wording: `src/soil_simulator/phase96/empirical.py:32-110,248-342`; `outputs/phase96_v0.9.6/EMPIRICAL_SOURCE_MANIFEST.json`; `EMPIRICAL_PILOT_METHODS.md`; `manifest.json`.

### Manuscript-ready Limitations wording

> The original construction of the 64-coordinate frame is an irrecoverable historical provenance limitation. Although the analysed pilot is reproducible from the archived coordinate list, the repository does not retain a higher-level rule from which that list can be regenerated. The frame must not be interpreted as a probability sample or as statistically representative of Great Britain. After documented source-record rejection, the 56 accepted locations constitute a limited empirical pilot and support only the bounded claims reported here.

Evidence for this wording: `outputs/phase96_v0.9.6/EMPIRICAL_SOURCE_MANIFEST.json` (`sampling_frame_locations`, `accepted_locations`, `rejected_locations`, `coordinate_policy`); `outputs/phase96_v0.9.6/generated_population_manifest.json` (`empirical_record_rejections`); `docs/PHASE96_EMPIRICAL_GROUNDING.md`.

### Manuscript-ready Reproducibility wording

> Reproducibility has two distinct boundaries. Construction of the original coordinate frame cannot be reproduced because its selection procedure was not preserved. In contrast, the analysed empirical pilot can be replayed from the archived 64-coordinate tuple and hash-verified raw and processed inputs: the same extraction scope, rejection rules, 56 accepted locations, generated descendants and train/validation/test/OOD assignments are recorded in the repository. This replayability does not confer representativeness on the frame.

Evidence for this wording: `src/soil_simulator/phase96/empirical.py:42-110,122-181,248-342`; `outputs/phase96_v0.9.6/EMPIRICAL_SOURCE_MANIFEST.json`; `outputs/phase96_v0.9.6/generated_population_manifest.json`; `DATA_SPLIT_REGISTER.csv`.

## 2. Discrete-transform endpoint-weighting limitation

### Verified implementation and consequence

For an integer-valued factor with integer endpoints \(a\) and \(b\), the implemented transform maps a unit-cube value \(q\in[0,1]\) as

\[
x(q)=\operatorname{round}\!\left(a+q(b-a)\right).
\]

Apart from deterministic handling of exact half-integer ties, each endpoint integer receives a unit-cube preimage of width \(1/[2(b-a)]\), while each interior integer receives width \(1/(b-a)\). Endpoint marginal probability is therefore half the interior marginal probability; the integer levels are not equiprobable. The behaviour is deterministic and reproducible. Source: `src/soil_simulator/phase95/sensitivity.py:31-38` (`SensitivityParameter.transform`); audit confirmation: `docs/audits/phase97_sobol_findings.md:41-48`.

No predeclared scientific rationale for unequal endpoint probability was found. The audit classified the behaviour as a low-severity limitation, and the corrected sensitivity analysis was already classified as non-converged. No final parameter ranking or agricultural conclusion relied on the affected sensitivity results. The present mapping must not be described as statistically neutral or optimal. Sources: `docs/audits/phase97_sobol_findings.md:41-48`; `outputs/phase97_v0.9.7/sensitivity_convergence_manifest.json` (`convergence_reached=false`, `status=not_converged_results_not_final`); claim boundary: `docs/PHASE97_PUBLICATION_READINESS.md`.

### Manuscript-ready Sensitivity Methods wording

> Integer-valued Sobol factors were generated by mapping continuous unit-cube values with \(x(q)=\operatorname{round}[a+q(b-a)]\), where \(a\) and \(b\) are the inclusive integer bounds. This deterministic mapping assigns each endpoint integer half the unit-cube interval width assigned to an interior integer, so the resulting discrete marginal probabilities are unequal. The mapping is reported as implemented; no predeclared scientific rationale for the unequal endpoint probability was found.

Evidence for this wording: `src/soil_simulator/phase95/sensitivity.py:31-38`; `config/phase96/sensitivity.yaml:7-22`; `config/phase97/sensitivity.yaml:3-10`; `outputs/phase97_v0.9.7/sobol_sampling_manifest.json`.

### Manuscript-ready Limitations wording

> The rounding-based integer transform is a low-severity sensitivity-design limitation because endpoint integers receive half the marginal probability of interior integers. The behaviour is deterministic and does not prevent computational replay, but it is neither equiprobable nor supported by a predeclared scientific rationale. Sensitivity estimates were independently classified as non-converged and were not used to establish a final parameter ranking or agricultural conclusion; the affected results remain non-final.

Evidence for this wording: `docs/audits/phase97_sobol_findings.md:41-48`; `outputs/phase97_v0.9.7/sensitivity_convergence_manifest.json`.

### Manuscript-ready Future Work wording

> Future sensitivity analyses should predeclare the intended marginal distribution for every integer-valued factor and implement it using an equal-probability discrete inverse-CDF, an equal-width floor-based mapping with explicit endpoint handling, or another transform justified before analysis. The transform and its probability mass function should be recorded in the sampling manifest and validated before parameter rankings are treated as final.

This is a prospective recommendation, not a description of the current implementation. Current implementation source: `src/soil_simulator/phase95/sensitivity.py:31-38`; current non-final status: `outputs/phase97_v0.9.7/sensitivity_convergence_manifest.json`.

## Final classification

| item | final classification | disclosure consequence |
|---|---|---|
| Coordinate-frame construction | `PARTIALLY_RESOLVED — DISCLOSED_IRRECOVERABLE_HISTORICAL_PROVENANCE_LIMITATION` | Analysed data are reproducible from the fixed list; original frame construction and representativeness are not recoverable. |
| Discrete integer transform | `PARTIALLY_RESOLVED — DISCLOSED_DISCRETE_SAMPLING_DESIGN_LIMITATION` | Mapping and probability consequence are documented; no scientific rationale is supplied, and affected non-converged results remain non-final. |

There are zero missing executable-method details, zero requirements for new analysis and zero requirements to modify the simulator. The package is sufficient for a bounded methodological/software manuscript only if both limitations remain explicit and no stronger sampling-representativeness or sensitivity-ranking claim is introduced.
