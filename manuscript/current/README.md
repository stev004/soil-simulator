# Manuscript v3 output

This directory contains the manuscript-v3 deliverables requested in `prism_v3_import/PRISM_V3_TASK.md`.

The canonical locally available PDF is `manuscript_v3.pdf`, SHA-256
`c2db01f4130865570a924262dbdf120d6dcfcebcdfac66d3425b0882b5797d10`.
It contains 20 pages and was compiled outside Prism from the authoritative v3
source package. The earlier Prism-rendered PDF SHA-256
`f374e93b43e27f63892a82c54c05f243d45957252feb4322851c5760de3a8b3d`
is historical provenance only, not the hash of the current local PDF. See
`LOCAL_PDF_BUILD_RECORD.md` for complete validation and toolchain provenance.

Compile from this directory with:

```sh
latexmk -pdf -interaction=nonstopmode -halt-on-error manuscript_v3.tex
```

The six PDFs under `figures/` are v3 typesetting assets derived from the
authoritative bundled SVGs now preserved under
`../archive/prism_imports/v3_import/figures/`. They are not recovered
historical v2 conversions. Historical conversion hashes and the current local
restoration hashes are recorded in `asset_conversion_manifest_v3.txt`.

`manuscript_v3.tex` and `manuscript_v3.md` are substantively equivalent. The Markdown declares `references_v3.bib` in its document metadata and uses the same 27 verified in-text citation keys as the LaTeX manuscript. `references_v3.bib` is copied from the verified reference package; no historical v2 bibliography is used. The v2 baseline remains immutable.

The final manuscript-v3 consistency patch synchronized Results 3.2, Discussion 4.2, Supplementary Table S1, Markdown citations, and bibliography representation without changing scientific results, equations, thresholds, claim boundaries, figures, or interpretation.
