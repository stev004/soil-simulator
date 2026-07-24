# soil_simulator reference update

Verified bibliography and citation-context package for the bounded methodological/software manuscript
*"Audit-driven development of a reproducible soil–plant–mycorrhizal simulation framework with fail-closed
machine-learning evaluation."*

This is a **citation verification and literature-context** deliverable. It does **not** alter the simulator,
scientific results, evidence artifacts, manuscript claims, or claim boundaries. No bibliographic metadata was
invented; every completed entry was verified against an authoritative record.

## Contents

| File | Purpose |
|---|---|
| `VERIFIED_REFERENCES.bib` | Valid BibTeX, 38 entries, stable keys, DOI/URL and versions; no placeholders. |
| `VERIFIED_REFERENCES.md` | Human-readable list: citation, source type, verification source, manuscript role, confidence. |
| `CLAIM_TO_CITATION_MAP.csv` | 31 rows mapping manuscript claims → recommended sources, with direct-support, qualification, target section, and soften flags. |
| `DATASET_CITATION_AND_LICENCE.md` | Citation, licence, redistribution posture, attribution wording, and access-date requirements for 5 data/software sources. |
| `LITERATURE_REVIEW_NOTES.md` | 25 Crossref-verified scholarly-context references across four subtopics, with role and qualification notes. |
| `AI_DISCLOSURE_SOURCES.md` | 12 authoritative AI-disclosure policy sources for Section 9 (no journal-specific wording selected). |
| `UNRESOLVED_REFERENCES.md` | Items not fully verifiable or requiring author input; plus previously-unresolved items now resolved, and inventory corrections. |
| `REFERENCE_VERIFICATION_MANIFEST.json` | SHA-256 of every file, verification method per reference, and DOI-resolution record. |
| `README.md` | This file. |

## Verification method

- **Journal articles / proceedings:** Crossref REST API (`api.crossref.org`) — title, full author list, year, venue, volume/issue/pages.
- **Zenodo software & dataset DOIs:** DataCite REST API (`api.datacite.org`) — creators, title, version, licence (`rightsList`).
- **Dataset licences:** official product/licence pages (ISRIC SoilGrids, NASA POWER Referencing Guide, Rothamsted e-RA dataset page).
- Every DOI in the `.bib` was re-resolved and confirmed to point at the intended work.

## Boundary discipline

The manuscript is a bounded methodological/software paper. Citations here support **methodological framing and
process existence only**. No source is used to support real-farm prediction, causal intervention effects, field
recommendations, national representativeness, measured MAOC, carbon-credit quantities, or generalisable ML
selection. Publication citations are grouped separately from dataset/software citations throughout.

## Key corrections found

1. **SoilGrids 2.0** lead author is **Poggio, L.** (the imported inventory recorded *de Sousa, L. M.*).
2. **RothC v2.1.1** inventory DOI `10.5281/zenodo.10724802` was **incorrect** (resolved to an unrelated study);
   the correct DOI is `10.5281/zenodo.17454357` (concept `10.5281/zenodo.10707406`).
3. **Rothamsted e-RA Hoosfield SOC** dataset fully resolved: DOI `10.23637/KeyRefOAHBsoc`, CC BY 4.0, with a
   mandatory citation string.

## Reproducibility

All API-verified metadata was captured on the generation date recorded in `REFERENCE_VERIFICATION_MANIFEST.json`.
Re-running verification against Crossref/DataCite reproduces the same records.
