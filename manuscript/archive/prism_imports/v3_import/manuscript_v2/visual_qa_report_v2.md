# Visual QA report for manuscript version 2

## Procedure

- Compiled `manuscript_v2.tex` with pdfLaTeX/BibTeX and repeated pdfLaTeX passes.
- Rendered all 18 PDF pages to PNG under `/tmp/prism-pdf-previews-v2` at 100–110 dpi.
- Inspected every rendered page for clipping, missing assets, figure legibility, table collisions, overfull content, broken references, and unintended placeholder boxes.
- Re-rendered pages affected by final figure clipping and supplementary renumbering.
- Checked the final LaTeX log for overfull boxes, missing references, undefined citations, missing assets, and fatal errors.

## Page-by-page inspection

| Page | Content | QA result |
|---:|---|---|
| 1 | Title, 225-word abstract, keywords, Introduction opening | Pass; title and abstract fit, no clipping |
| 2 | Introduction conclusion; Methods architecture opening | Pass; readable with intentional lower whitespace before figure float |
| 3 | Main Figure 1, main Table 1, process-method opening | Pass after clipping phase-only footer; table columns do not overlap |
| 4 | Model processes, management, empirical pilot | Pass; no overflow or broken lines |
| 5 | Hoosfield and sensitivity methods; ML methods | Pass; mathematical symbols and units render correctly |
| 6 | Gate/reproducibility methods; Results sections 3.1–3.3 | Pass; cross-references resolved |
| 7 | Hoosfield results, main Figure 2, main Table 2 | Pass; real figure embedded; table roles and units readable |
| 8 | Main Figure 3, main Table 3, leakage/coverage, prediction results | Pass; non-convergence label visible; no table collision |
| 9 | Blocked selection, main Figure 4, main Table 4 | Pass after clipping internal phase title; real gate figure embedded; table readable |
| 10 | Computational-audit summary and Discussion 4.1–4.4 | Pass; audit wording does not imply human peer review |
| 11 | Limitations, future work, conclusions, availability, reproducibility | Pass; qualification language visible and unambiguous |
| 12 | AI disclosure, author/funding placeholders, completed references, figure legends | Pass; placeholders visible; bibliography not clipped |
| 13 | Main table legends | Pass; sparse page is a deliberate section break before supplementary material |
| 14 | Supplementary Figures S1 and S2 | Pass after clipping overlapping low-priority timeline annotation row; both real assets embedded and captions visible |
| 15 | Supplementary Tables S1–S3 opening | Pass; supplementary numbering correct; no overlap |
| 16 | Supplementary Tables S3–S4 | Pass; longtable continuation and boundaries readable |
| 17 | Supplementary Tables S5–S6 opening | Pass; factors, bounds, thresholds, and unresolved policy names readable |
| 18 | Supplementary Table S6 continuation and index | Pass; repeated table header and final rows render correctly |

## Corrections made during QA

- Rebuilt all tables with `tabularx` or `longtable` and reduced fixed column totals until the compile log contained no overfull boxes.
- Converted the six curated SVG assets to v2-local PDFs without modifying the imported SVG evidence files.
- Applied LaTeX clipping to the architecture and readiness figures to remove phase-only internal labels from main scientific displays.
- Applied LaTeX clipping to the supplementary audit timeline to omit an overlapping annotation row while retaining the real timeline, provenance nodes, and phase identifiers.
- Reset supplementary figure/table counters to S1–S2 and S1–S6.

## Final status

- Pages inspected: **18/18**.
- Missing figures: **0**.
- Placeholder figure boxes: **0**.
- Table collisions: **0**.
- Overfull boxes in final log: **0**.
- Undefined citations/references: **0**.
- Visual QA: **PASS**.
