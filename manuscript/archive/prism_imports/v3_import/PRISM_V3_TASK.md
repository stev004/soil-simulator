# Prism task: produce manuscript version 3

Use manuscript v2 as the drafting baseline and create manuscript version 3 in a new output directory. Follow `AUTHORITATIVE_SOURCE_ORDER.md` whenever sources differ. Do not edit any bundled source file.

## Required revision work

- Integrate the complete verified methods evidence into a self-contained, journal-style Methods section.
- Use equations, parameters, split details, model details, gate formulas, sensitivity settings, and Hoosfield procedures only where verified.
- Disclose both retained methods limitations accurately: unavailable original construction of the 64-coordinate frame, and unequal endpoint probability from the deterministic rounding transform for discrete Sobol factors with no preserved scientific rationale.
- Replace the old bibliography with `reference_update/VERIFIED_REFERENCES.bib` and apply citations according to `reference_update/CLAIM_TO_CITATION_MAP.csv`.
- Remove the incorrect earlier RothC DOI and SoilGrids authorship. Never cite `10.5281/zenodo.10724802` as RothC; use the verified RothC and Hoosfield identifiers in the reference package.
- Qualify process citations so they support biological concepts, not calibrated simulator magnitudes.
- Preserve every negative finding and the bounded methodological/software framing.
- Improve scholarly context without overstating support.
- Retain dataset licence and attribution requirements from `reference_update/DATASET_CITATION_AND_LICENCE.md`.
- Leave unresolved author, repository, DOI, funding, journal, and exact AI-product details as visible placeholders where still necessary.
- Preserve all boundaries listed in `START_HERE_V3.md` and `evidence/manuscript/CLAIM_BOUNDARIES.md`.

## Prohibited work

Do not modify scientific results; perform new modelling or statistical analysis; invent missing provenance, citations, rationales, results, or author information; describe computational audits as human peer review; or convert synthetic effects into causal, agricultural, carbon-credit, representative-sampling, or deployment claims.

## Required outputs

Create a new directory for v3 outputs containing:

```text
manuscript_v3.md
manuscript_v3.tex
manuscript_v3.pdf
references_v3.bib
drafting_evidence_map_v3.csv
unresolved_author_inputs_v3.md
unresolved_references_v3.md
revision_log_v2_to_v3.md
visual_qa_report_v3.md
README.md
```

The Markdown and LaTeX manuscripts must be substantively equivalent. Compile successfully with no missing assets, undefined citations or references, or overfull boxes. Inspect the PDF page by page. Update citation and scientific-claim evidence mapping. Report any methods detail that still cannot be incorporated and every remaining submission blocker.

The v2 LaTeX PDF conversions are absent from the source repository; use `figures/ASSET_INDEX.md` to convert the unchanged bundled SVGs as needed for v3 typesetting. Do not present newly converted files as recovered historical v2 artifacts.
