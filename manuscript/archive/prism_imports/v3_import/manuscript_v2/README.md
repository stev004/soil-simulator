# Version 2 manuscript package

This directory contains the revised bounded methodological/software manuscript. No file outside this directory was modified during version-2 drafting.

## Required outputs

- `manuscript_v2.md` — Markdown manuscript.
- `manuscript_v2.tex` — standalone LaTeX manuscript.
- `manuscript_v2.pdf` — compiled manuscript after validation.
- `references_pending_v2.bib` — completed imported references only, with unresolved records excluded.
- `drafting_evidence_map_v2.csv` — exact-source map for major and materially rewritten scientific claims.
- `unresolved_citations_v2.md` — incomplete bibliographic records.
- `unresolved_methods_v2.md` — methods details absent from the compact import.
- `unresolved_author_inputs_v2.md` — author and submission placeholders.
- `revision_log_v1_to_v2.md` — substantive changes from version 1.
- `visual_qa_report_v2.md` — page-by-page PDF inspection record.

## Display allocation

Main figures: architecture, Hoosfield trajectories, sensitivity convergence, and readiness gates. Supplementary figures: carbon/phosphorus flows and computational-audit chronology.

Main tables: components, Hoosfield evaluation, sensitivity convergence, and gate outcomes. Supplementary tables: data sources, verification, audit remediation, claim boundaries, sensitivity methods, and gate definitions.

## Build

Run from this directory:

```text
pdflatex manuscript_v2.tex
bibtex manuscript_v2
pdflatex manuscript_v2.tex
pdflatex manuscript_v2.tex
```
