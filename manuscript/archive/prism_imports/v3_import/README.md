# Prism v3 clean-import bundle

## Purpose

This bundle consolidates the manuscript v2 baseline, final methods expansion, verified references, figures, audits, compact canonical evidence, and manifests needed for a clean Prism project that produces manuscript version 3. It contains instructions and unchanged source evidence only; it does not draft manuscript v3 or change scientific results.

> Read `START_HERE_V3.md` first and follow its source order before drafting or editing anything.

## Source directories

- `manuscript/manifests/`: actual repository location of the authoritative v2 Markdown, LaTeX, evidence map, historical bibliography/inventories, revision log, visual-QA report, and v2 README.
- `manuscript/methods_expansion/`: final methods-expansion package and manifest.
- `reference_update/`: verified reference-update package and verification manifest.
- `manuscript/figures/`: all 11 available SVG figures and the original figure index.
- `manuscript/`, `manuscript/tables/`, `manuscript/supplementary/`, and `manuscript/data/`: claim boundaries, manuscript evidence, curated tables, gate/uncertainty evidence, model card, and large-artifact indexes.
- `docs/audits/`, `docs/AUDIT_soil_simulator_v0.9.0.md`, and `manuscript/AUDIT_TRAIL.md`: audit chronology, canonical reports, recomputations, discrepancies, and closure records.
- Selected small frozen files from `outputs/phase96_v0.9.6/` and `outputs/phase97_v0.9.7/`: Hoosfield, calibration, leakage, uncertainty, gate, readiness, and convergence evidence.

## Organization

- `manuscript_v2/`: unchanged meaningful files from the repository's actual v2 package location. The pending bibliography and unresolved inventories are historical context only.
- `methods_expansion/`: byte-identical complete current directory.
- `reference_update/`: byte-identical complete verified reference package.
- `figures/`: byte-identical SVG sources plus `ASSET_INDEX.md`.
- `audits/`: canonical computational-audit reports and closure evidence.
- `evidence/`: claim boundaries, curated tables, model/gate/uncertainty records, Hoosfield evidence, and large-file indexes.
- `manifests/`: source, artifact, figure, table, supplementary, data-index, and archive manifests.
- `PACKAGE_MANIFEST.json`: relative path, SHA-256, byte size, category, and role for every other bundled file. Because a file cannot contain its own final byte hash without circular self-reference, the package manifest's own hash is verified externally during ZIP validation.

## Authority and limitations

Follow `AUTHORITATIVE_SOURCE_ORDER.md`. Methods expansion supersedes the old unresolved-methods inventory except for the two disclosed limitations. Verified references supersede the pending v2 bibliography and earlier citation metadata. Nothing in this bundle may change or broaden frozen scientific results.

The two retained methods limitations are:

1. The archived coordinate list and analysed pilot are reproducible, but the original 64-coordinate frame-construction procedure is unavailable. No representativeness claim is permitted.
2. Deterministic rounding for discrete Sobol factors gives unequal endpoint probabilities, has no preserved scientific rationale, and the affected sensitivity results remain non-converged and non-final.

## Missing historical supporting files

Repository-wide inspection, including `prism_manuscript_bundle.zip`, found no `manuscript_v2.pdf` and no six v2-local converted PDF figures referenced by `manuscript_v2/manuscript_v2.tex`. They were not recreated because missing historical artifacts must not be manufactured. All corresponding SVG sources are included, and `figures/ASSET_INDEX.md` documents the exact mapping and compile-path implication. No local `.sty` or `.cls` file is referenced; the LaTeX source uses standard packages.

## Excluded large artifacts

Large generated populations, effect-only datasets, raw caches, and full sensitivity tables were not duplicated. Their paths, byte sizes, and hashes are indexed by `evidence/supplementary/LARGE_FILE_INDEX.json`, `evidence/data/DATA_INDEX.csv`, and the source/artifact manifests under `manifests/`. The bundle includes compact targeted evidence sufficient to trace manuscript claims without importing complete source-code trees or unnecessary generated datasets.

The superseded `manuscript/REFERENCES_SOURCE_LIST.md` inventory was also excluded because it presented the unrelated DOI `10.5281/zenodo.10724802` as a provisional RothC URL. The verified reference package replaces that inventory. Two immutable historical source manifests retain the obsolete URL solely as frozen provenance; `manifests/README.md` identifies the exact fields and forbids their citation use.

## Validation performed

- All 11 files listed by the methods manifest match SHA-256 and byte size; `manifest.json` is the twelfth current methods-package file.
- All eight payload files listed by the reference verification manifest match SHA-256 and byte size; the verification manifest is the ninth package file and is hashed by `PACKAGE_MANIFEST.json`.
- Methods classification confirmed: 21 gaps fully resolved, two partially resolved as disclosed limitations, zero missing executable-method details, zero requirements for new analysis, and zero requirements to modify the simulator.
- Required v2 Markdown, LaTeX, evidence map, historical bibliography/inventories, revision log, visual-QA report, and README are present. The historical PDF and six converted figure PDFs are absent as disclosed above.
- Every copied scientific/evidence source was byte-compared to its repository source, and protected repository files were rehashed after packaging.
- The final ZIP is extracted to a temporary directory and every payload byte and package-manifest entry is reverified before handoff.

## Start a clean Prism project

1. Upload the single top-level directory from `soil_simulator_prism_v3_bundle.zip` as a new Prism project.
2. Read `START_HERE_V3.md` first and follow its source order before drafting or editing anything.
3. Create v3 work only in a new output directory and leave all imported sources unchanged.
4. Use `figures/ASSET_INDEX.md` when preparing v3 LaTeX assets, and disclose remaining submission blockers in the required v3 outputs.
