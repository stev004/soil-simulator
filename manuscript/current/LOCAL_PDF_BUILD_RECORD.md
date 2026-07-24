# Local PDF build record

## Canonical PDF

- Path: `manuscript/current/manuscript_v3.pdf`
- SHA-256: `c2db01f4130865570a924262dbdf120d6dcfcebcdfac66d3425b0882b5797d10`
- Byte size: 469,514
- Page count: 20
- Repository integration date: 2026-07-24
- Build provenance: compiled outside Prism from the authoritative manuscript-v3
  LaTeX source package, verified bibliography, and authoritative figures because
  Prism could not persist the binary PDF output.

## Structural and visual validation

- `file` identified a PDF 1.7 document.
- Poppler `pdfinfo` parsed the document successfully, reported 20 pages,
  letter-size pages (612 x 792 points), no encryption, no JavaScript, no forms,
  no suspect structural features, and a 469,514-byte file.
- All 20 pages were rendered locally to PNG at 90 dpi with `pdftoppm`. The
  rendered pages were inspected in four five-page contact sheets; no blank,
  missing, clipped, or visibly corrupted page was found.
- PDF metadata reports creator `LaTeX with hyperref`, producer
  `pdfTeX-1.40.26`, creation/modification time 2026-07-23 03:41:59 BST, and PDF
  version 1.7.

## Historical Prism provenance

The earlier Prism-rendered PDF SHA-256 is
`f374e93b43e27f63892a82c54c05f243d45957252feb4322851c5760de3a8b3d`.
That hash is historical provenance only. It is not the hash of the canonical
locally available PDF, and the two PDFs must not be described as
byte-identical. Differing binary hashes are expected because the files were
produced by different LaTeX and figure-conversion toolchains, which can change
PDF object layout and metadata without intentionally changing manuscript or
figure content. The existing Prism visual-QA report remains preserved at
`manuscript/current/visual_qa_report_v3.md`.

## Authoritative source hashes

- `manuscript/current/manuscript_v3.tex`:
  `ae47584698e1817bf73740206ece82483ccdc63d34044f470815a3ad992e0abc`
- `manuscript/current/references_v3.bib`:
  `5b173e9f7601b3dd620b5dfd74053c3af8c2a0659cae26a087a39cd32155b596`

## Current figure PDF hashes

The six current figure PDFs were restored during repository integration from
the authoritative, hash-matched v3 SVG sources using Inkscape 1.4.4 and cairo
1.18.2. Each is a structurally valid one-page PDF. Their binary hashes differ
from the retained historical 2026-07-22 conversion hashes because the local
conversion toolchain and PDF metadata differ.

- `manuscript/current/figures/figure_01_model_architecture.pdf`:
  `c3e02d410b761c4e9710f9ffd2679fb5e5ff0c876f0553633a82322ba384eb53`
- `manuscript/current/figures/figure_02_carbon_phosphorus_flow.pdf`:
  `e5a82f6fac555069b07d898d8d472d06843c713653daef9cb8bb67847c605bdd`
- `manuscript/current/figures/figure_05_hoosfield_trajectories.pdf`:
  `66a3d8faf44e955075014ccd8cd60403f8f8e5e144e0c1a856a05b9509150db4`
- `manuscript/current/figures/figure_08_sensitivity_convergence.pdf`:
  `69636c88f7801a8d6ba97ada602c6d519df228d9aab550f407d5bf21551f4a3d`
- `manuscript/current/figures/figure_10_ml_gate_summary.pdf`:
  `225f342a37700ce7f7a7c39a64b9c8d3f2ceffed2cef36351fa2a236c2e538a4`
- `manuscript/current/figures/figure_11_audit_remediation_timeline.pdf`:
  `a29ebe1b5c7d06b51d5a0d77ac4770a46e65607126b5572c5992b965bcc8aaf0`

No manuscript wording, citation, equation, scientific result, audit conclusion,
or figure content was intentionally changed during PDF and figure integration.
