# Authoritative source order for manuscript v3

Use the following precedence whenever sources differ:

1. Frozen scientific artifacts and canonical computational-audit evidence in `evidence/`, `audits/`, and `manifests/`.
2. Final methods-expansion files in `methods_expansion/` and their latest `manifest.json`.
3. Verified reference files in `reference_update/` and `REFERENCE_VERIFICATION_MANIFEST.json`.
4. Manuscript v2 in `manuscript_v2/` and `drafting_evidence_map_v2.csv`.
5. Earlier drafts, pending bibliographies, and unresolved inventories.

## Supersession rules

- Methods-expansion evidence supersedes `manuscript_v2/unresolved_methods_v2.md`, except for the two retained disclosed limitations: the irrecoverable coordinate-frame construction history and the unequal endpoint probabilities in the deterministic rounding transform for discrete Sobol factors.
- Verified references supersede `manuscript_v2/references_pending_v2.bib`, `manuscript_v2/unresolved_citations_v2.md`, and all earlier reference metadata.
- No documentation or citation may alter frozen scientific results.
- No citation may imply a stronger biological or agricultural claim than the project evidence supports.
- Incorrect earlier RothC and SoilGrids metadata must not be reused. SoilGrids 2.0 is led by Poggio, not de Sousa. DOI `10.5281/zenodo.10724802` is unrelated to RothC and is never a valid RothC citation. Use RothC v2.1.1 version DOI `10.5281/zenodo.17454357`, concept DOI `10.5281/zenodo.10707406`, RothC Python v1.0.0 DOI `10.5281/zenodo.10732265`, and Hoosfield SOC dataset DOI `10.23637/KeyRefOAHBsoc` only as directed by the verified reference package.

When a lower-precedence file records historical wording that conflicts with a higher-precedence source, retain the lower-precedence file only as provenance and follow the higher-precedence source in manuscript v3.
