# Phase 9.8 compact Prism export

## Outcome

`prism_manuscript_bundle.zip` packages the completed Phase 9.8 manuscript
archive as one compact Prism project. It contains one wrapper directory,
`prism_manuscript_bundle/`, with a generated entry document and manifest plus
byte-exact copies of the requested curated repository files.

## Included material

- complete `manuscript/` directory: 71 files;
- complete `docs/audits/` directory: 14 files;
- `docs/PHASE98_MANUSCRIPT_ARCHIVE.md`;
- `docs/provenance/RESEARCH_ARCHIVE.md`;
- `README.md`;
- generated `START_HERE.md`;
- generated `BUNDLE_MANIFEST.json`.

The ZIP contains 90 files under the single top-level
`prism_manuscript_bundle/` directory. Of these, 88 are byte-exact repository
copies and two are packaging documents generated for this export.

## Excluded material

The export excludes `.git/`, virtual environments, caches, `src/`, `tests/`,
raw or uncurated outputs outside `manuscript/`, build artifacts, temporary
files, editor metadata, `audits/incoming/` and duplicate large evidence already
represented by manuscript indexes. ZIP inspection found no hidden files,
source code, caches, raw output directories or other forbidden entries.

## Size and digests

- File count: 90.
- Uncompressed size: 522,566 bytes (approximately 510 KiB).
- ZIP size: 188,423 bytes (approximately 184 KiB).
- ZIP SHA-256:
  `e85dcd8476ce3aef93690ebc63eefd3b4ead6f8e4ed8f82f11683efd787ebd3e`.
- `BUNDLE_MANIFEST.json` SHA-256:
  `962bb3690f5d9a10bd23dd93b40a08d750d70ff65418a5b0d9e2d85f6991b411`.
- Preserved Phase 9.8 manuscript-bundle set digest:
  `98aa6e6366ac4f3c4708883817cb987850c8d2858b20cdbfbe9dde11525099a5`.
- Package version: 0.9.7.

Largest included files:

| Bytes | Path |
|---:|---|
| 34,217 | `BUNDLE_MANIFEST.json` |
| 25,322 | `manuscript/manifests/manuscript_bundle_manifest.json` |
| 22,783 | `docs/audits/AUDIT_PHASE96_CLEAN_SLATE.md` |
| 21,705 | `manuscript/supplementary/ASSUMPTIONS_REGISTER.csv` |
| 19,563 | `manuscript/supplementary/source_manifests/phase97_source_manifest.json` |
| 17,470 | `docs/audits/phase97_recomputed_metrics.json` |

No individual file is likely to exceed normal Prism import limits. The archive
is already compact, so no required evidence was removed or split.

## Validation

- Required source existence: pass.
- `manuscript/PRISM_HANDOFF.md`: present.
- Ten independent Phase 9.6/9.7 audit deliverables: present.
- Copied-source SHA-256 and byte equality: pass for all 88 copied files.
- Internal Markdown links resolvable within the compact bundle: pass, zero
  unresolved or out-of-bundle Markdown links.
- JSON validation: pass for 25 files.
- CSV parsing and consistent row width: pass for 17 files.
- ZIP duplicate-entry inspection: pass, zero duplicates.
- ZIP hidden/forbidden-entry inspection: pass, zero unwanted entries.
- Temporary extraction replay: pass; all 90 extracted files match their
  pre-ZIP bytes.
- Extracted payload-manifest replay: pass, zero hash or size mismatches.

`BUNDLE_MANIFEST.json` records every payload file. The manifest itself is
necessarily self-excluded from its entry array because a file cannot contain
its own final SHA-256; its external SHA-256 is recorded above.

## Repository integrity

Packaging did not modify frozen Phase 9.5–9.7 artifacts, scientific outputs,
audit evidence, model configuration, readiness gates, manuscript evidence or
claim boundaries. The existing Phase 9.8 manuscript-bundle digest remains
unchanged at
`98aa6e6366ac4f3c4708883817cb987850c8d2858b20cdbfbe9dde11525099a5`.

Only the requested packaging directory, ZIP and this report were added.

## Prism import instructions

1. Import `/Users/stevenmatson/Documents/soil_simulator/prism_manuscript_bundle.zip`
   into Prism as a single project/archive.
2. Open `prism_manuscript_bundle/START_HERE.md`.
3. Continue with `prism_manuscript_bundle/manuscript/PRISM_HANDOFF.md` and its
   prescribed reading order.
4. Draft only the bounded methodological/software framing.
5. Do not infer missing results, citations, validation or implementation
   details from intentionally absent source-code files.
6. Do not make agricultural-prediction, causal intervention or field-
   recommendation claims.

READY TO IMPORT INTO PRISM
