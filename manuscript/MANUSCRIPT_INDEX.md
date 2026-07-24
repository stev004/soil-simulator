# Manuscript workspace index

## Authoritative manuscript

`current/` is the authoritative latest manuscript package: **manuscript version 3**, titled *Audit-driven development of a reproducible soil–plant–mycorrhizal simulation framework with fail-closed machine-learning evaluation*.

Use `current/manuscript_v3.md` and `current/manuscript_v3.tex` as the manuscript
sources. `current/references_v3.bib` is the local v3 bibliography. The canonical
locally available PDF is `current/manuscript_v3.pdf`, SHA-256
`c2db01f4130865570a924262dbdf120d6dcfcebcdfac66d3425b0882b5797d10`.
Historical drafts, Prism packages, and ZIPs are not authoritative outputs.

## Evidence and archives

- Final methods evidence: `methods_expansion/`.
- Verified citation and licence evidence: `reference_update/`.
- Version 1 archive: `archive/v1/`. No standalone v1 manuscript files were present during cleanup; the v1-to-v2 revision log is retained with v2.
- Version 2 manuscript and manifests: `archive/v2/`.
- Version 2 drafting evidence, tables, supplementary records, and data indexes: `archive/v2/evidence_bundle/`.
- Available historical SVG assets: `archive/v2/figures/`.
- Historical extracted Prism material: `archive/prism_imports/`.
- Historical manuscript package ZIPs: `archive/package_zips/`.
- File-move audit trail: `CLEANUP_MANIFEST.json`.

## Directory tree

```text
manuscript/
├── current/                         # authoritative manuscript v3
│   ├── manuscript_v3.pdf            # canonical local 20-page PDF
│   ├── LOCAL_PDF_BUILD_RECORD.md    # local-build provenance and hashes
│   └── figures/                     # six v3-local PDF typesetting assets
├── methods_expansion/               # final methods evidence
├── reference_update/                # verified references and licences
├── archive/
│   ├── v1/                          # no standalone v1 files found
│   ├── v2/
│   │   ├── evidence_bundle/
│   │   └── figures/
│   ├── prism_imports/
│   │   ├── v2_bundle/
│   │   └── v3_import/
│   └── package_zips/
├── MANUSCRIPT_INDEX.md
└── CLEANUP_MANIFEST.json
```

## Current-package status and submission blockers

The v3 Markdown, LaTeX, bibliography, drafting evidence map, unresolved-input records, revision log, visual-QA report, README, and asset-conversion manifest were moved byte-for-byte into `current/`.

The canonical 20-page PDF is now present at `current/manuscript_v3.pdf`. Its
SHA-256 is
`c2db01f4130865570a924262dbdf120d6dcfcebcdfac66d3425b0882b5797d10`.
The earlier Prism-rendered PDF hash
`f374e93b43e27f63892a82c54c05f243d45957252feb4322851c5760de3a8b3d`
is retained as historical provenance only; the two builds are not
byte-identical because they used different typesetting and figure-conversion
toolchains.

All six LaTeX-referenced PDF figures are present under `current/figures/`.
Their authoritative SVG source hashes match the historical conversion
manifest. The locally restored PDF conversions have current hashes recorded in
`current/asset_conversion_manifest_v3.txt` and
`current/LOCAL_PDF_BUILD_RECORD.md`. Every `\includegraphics` path and the
`\bibliography{references_v3}` path resolves locally.

Other submission blockers retained in the v3 unresolved-input records are:

- author names, ORCIDs, affiliations, and corresponding-author email;
- repository URL, archival DOI, and release/commit identifier;
- funding, competing-interest, acknowledgement, and author-contribution statements;
- target journal and manuscript style;
- exact AI product/model names, versions, use dates, and compliant disclosure wording;
- final NASA POWER service/product citation and acknowledgement details.

## Immutability rule

Everything under `archive/` is historical. Do not edit, normalize, deduplicate, replace, or silently correct archived files. Preserve their bytes and use `CLEANUP_MANIFEST.json`, embedded package manifests, and verified-reference precedence to interpret them. Future manuscript work belongs in `current/` or a new explicitly versioned successor directory.
