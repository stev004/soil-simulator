# Residual limitations after methods-evidence expansion and addendum

## Status ledger

- Missing executable-method details: **0**.
- Irrecoverable historical provenance limitations: **1**.
- Documented discrete-sampling design limitations: **1**.
- Requirements for new analysis: **0**.
- Requirements to modify the simulator: **0**.

## EMP-01 — coordinate-frame construction

Final classification: `PARTIALLY_RESOLVED — DISCLOSED_IRRECOVERABLE_HISTORICAL_PROVENANCE_LIMITATION`.

The 64 coordinates were fixed before empirical extraction. The complete ordered list is archived in `src/soil_simulator/phase96/empirical.py:42-110`, reproduced in `EMPIRICAL_PILOT_METHODS.md`, and hash-verifiable through `manifest.json`. Extraction, documented acceptance/rejection and downstream analysis are reproducible from that fixed list. The historical procedure and external frame used to construct the list were not preserved and cannot be recovered from repository evidence. The frame therefore cannot be described as random, probability based, nationally representative, optimally stratified or statistically representative. This is a limitation on reconstruction of the frame, not on replay of the analysed pilot; the 56 accepted locations remain a limited empirical pilot. Full disclosure wording: `METHODS_LIMITATIONS_ADDENDUM.md` section 1. Evidence: `outputs/phase96_v0.9.6/EMPIRICAL_SOURCE_MANIFEST.json`; `outputs/phase96_v0.9.6/generated_population_manifest.json`; `DATA_SPLIT_REGISTER.csv`.

## SEN-04 — round-based discrete transform

Final classification: `PARTIALLY_RESOLVED — DISCLOSED_DISCRETE_SAMPLING_DESIGN_LIMITATION`.

The implemented mapping `round(min + q*(max-min))` is fully documented and deterministic. Endpoint integers receive half-width unit-cube intervals relative to interior integers, so marginal probabilities are unequal. No predeclared scientific rationale for this weighting was found. The limitation is low severity, sensitivity results were already classified as non-converged, and no final parameter ranking or agricultural conclusion relied on them. Future analysis should predeclare and use an equal-probability discrete inverse-CDF, an equal-width floor mapping with explicit endpoint handling, or another justified transform. Full disclosure wording: `METHODS_LIMITATIONS_ADDENDUM.md` section 2. Evidence: `src/soil_simulator/phase95/sensitivity.py:31-38`; `docs/audits/phase97_sobol_findings.md:41-48`; `outputs/phase97_v0.9.7/sensitivity_convergence_manifest.json`.

## Completion consequence

No executable method remains undocumented. Neither limitation is scientifically resolved: the coordinate-frame construction remains historically irrecoverable, and no post hoc rationale is assigned to the unequal discrete probabilities. No new analysis or simulator modification is required. The methods package is sufficient for a bounded methodological/software manuscript if both disclosures are retained and the manuscript makes neither a representativeness claim for the pilot frame nor a final-ranking claim from the non-converged sensitivity results.
