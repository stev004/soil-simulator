# Visual QA report for manuscript v3

## Scope

- Compiled `manuscript_v3.tex` only; manuscript v2 was neither repaired nor compiled as the final manuscript.
- Final PDF: 20 pages.
- Final PDF SHA-256 after the consistency patch: `f374e93b43e27f63892a82c54c05f243d45957252feb4322851c5760de3a8b3d`.
- Every page was rendered to PNG under `/tmp/prism-pdf-previews/v3` and inspected in five four-page contact sheets. Pages 19–20 were re-rendered and reinspected after correcting stale Supplementary Table S5 wording.
- For the final consistency patch, all 20 pages were rendered again under `/tmp/prism-pdf-previews/v3-consistency`. Directly affected pages 7, 11, and 18 were reinspected, together with regenerated-asset pages 3, 8, 9, 10, and 17.

## Page-by-page inspection

| Pages | Content checked | Outcome |
|---|---|---|
| 1–2 | Title, abstract, introduction, start of Methods | Clear; placeholders visible; no clipping |
| 3–4 | Architecture figure/table, equations, empirical-pilot methods | Figure legible; equations and citations render; no overflow |
| 5–6 | Sensitivity, ML, gate, and audit methods | Equations and thresholds legible; both retained limitations visible |
| 7–8 | Results, corrected descendant wording, Hoosfield figure and table | Results 3.2 wording is complete and legible; figure/table and negative calibration result preserved |
| 9–10 | Sensitivity and readiness figures/tables | Non-convergence and blocked readiness are visually explicit |
| 11–12 | Discussion, conclusions, availability statements | Revised “suggested” wording is legible; claim boundaries and submission placeholders remain visible |
| 13–15 | Verified references | Entries render without collision or truncation |
| 16 | Main legends | Complete and legible |
| 17 | Supplementary flow and audit figures | Both v3-local converted assets render clearly |
| 18 | Supplementary data/software/audit tables | Updated RothC archive and e-RA licence/boundary wording is legible; long-table continuation is clean |
| 19–20 | Claim boundaries, sensitivity methods, gate definitions | Corrected policy names/citations and endpoint-weighting disclosure render without overflow |

## Compile-log checks

- No missing figure assets.
- No undefined citations.
- No undefined cross-references.
- No overfull boxes in the final log.
- Two benign underfull/longtable box diagnostics remain; visual inspection confirms no clipping, overlap, or unreadable layout.
- LaTeX and Markdown contain the same 27 verified citation keys; every key exists in `references_v3.bib`.
- Markdown declares `references_v3.bib` as its bibliography and contains no historical v2 bibliography or unresolved-v2 citation instruction.

## Asset provenance

The six PDFs in `figures/` are fresh v3-local typesetting conversions from the bundled authoritative SVGs. They are not recovered historical v2 conversions. Conversion hashes are recorded in `asset_conversion_manifest_v3.txt`.

## Final visual-QA result

Pass. The compiled v3 PDF is complete, readable, internally referenced, and free of visible clipping or missing content. The consistency patch changed wording and reference representation only; no scientific result, analysis, equation, threshold, claim boundary, figure, or interpretation changed. Remaining blockers are author/journal metadata rather than typesetting defects.