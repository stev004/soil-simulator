# Start here: clean Prism manuscript v3 project

This bundle is a source package for producing manuscript version 3. It is not a draft of manuscript v3.

Read in this order before drafting or editing:

1. `AUTHORITATIVE_SOURCE_ORDER.md`.
2. `PRISM_V3_TASK.md`.
3. `manuscript_v2/manuscript_v2.md`, `manuscript_v2/manuscript_v2.tex`, and `manuscript_v2/drafting_evidence_map_v2.csv`.
4. `methods_expansion/METHODS_EXPANSION_REPORT.md`, `methods_expansion/METHODS_LIMITATIONS_ADDENDUM.md`, and `methods_expansion/methods_evidence_map.csv`.
5. `reference_update/CLAIM_TO_CITATION_MAP.csv`, `reference_update/VERIFIED_REFERENCES.bib`, and `reference_update/DATASET_CITATION_AND_LICENCE.md`.
6. Claim boundaries, audits, evidence, and manifests in `evidence/`, `audits/`, and `manifests/`.

Manuscript v2 is the drafting baseline. The expanded methods evidence should make v3 substantially more self-contained. Verified references must replace incomplete or incorrect v2 references. Perform no new scientific analysis and invent no missing information, provenance, result, citation, author detail, or rationale.

## Boundaries that must remain explicit

- The 56 locations form a limited empirical pilot.
- The original 64-coordinate frame-construction method is unavailable; no random, probability-based, nationally representative, optimally stratified, statistically representative, or other representativeness claim is permitted.
- The discrete Sobol endpoint weighting is a documented design limitation: deterministic rounding gives unequal endpoint probabilities and has no preserved scientific rationale.
- Sensitivity remains non-converged, diagnostic, and non-final.
- FYM calibration remains boundary constrained and fails on held-out cessation.
- Effect-prediction, out-of-distribution, and independent empirical-validation gates failed.
- Leakage and residual-coverage gates passed only within their encoded boundaries.
- Selector, oracle, and regret analyses were not executed.
- `protected_soc` is a model proxy, not measured MAOC.
- Computational auditing was AI-executed implementation review, not human peer review or independent biological validation.
- No agricultural prediction, recommendation, causal intervention, carbon-credit, national-representativeness, or deployment-readiness claim is permitted.

The historical compiled `manuscript_v2.pdf` and the six v2-local PDF conversions referenced by `manuscript_v2.tex` were not present in the repository. Do not invent or mislabel replacements. The unchanged SVG sources and exact mapping are in `figures/ASSET_INDEX.md`; format conversion for v3 typesetting may be performed without changing figure content.
