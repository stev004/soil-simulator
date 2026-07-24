# Manuscript v2 figure and LaTeX asset index

`manuscript_v2/manuscript_v2.tex` uses standard LaTeX packages and references six PDF files by basename from its compile working directory. The repository contains the corresponding unchanged SVG sources but not the historical v2-local PDF conversions.

| LaTeX reference | Bundled source | Role |
|---|---|---|
| `figure_01_model_architecture.pdf` | `figures/figure_01_model_architecture.svg` | Main architecture figure |
| `figure_05_hoosfield_trajectories.pdf` | `figures/figure_05_hoosfield_trajectories.svg` | Main Hoosfield trajectory figure |
| `figure_08_sensitivity_convergence.pdf` | `figures/figure_08_sensitivity_convergence.svg` | Main sensitivity-convergence figure |
| `figure_10_ml_gate_summary.pdf` | `figures/figure_10_ml_gate_summary.svg` | Main readiness-gate figure |
| `figure_02_carbon_phosphorus_flow.pdf` | `figures/figure_02_carbon_phosphorus_flow.svg` | Supplementary carbon/phosphorus-flow figure |
| `figure_11_audit_remediation_timeline.pdf` | `figures/figure_11_audit_remediation_timeline.svg` | Supplementary audit-timeline figure |

The other five SVGs are also included because they are indexed manuscript assets and support visual reproduction and future v3 figure allocation. `figures/FIGURE_INDEX.md` records all source-data and interpretation boundaries.

For v3 compilation, convert the SVG sources without altering their content or update v3 LaTeX to use a supported SVG workflow. Do not edit the historical v2 source and do not describe newly converted files as recovered historical v2 artifacts. The v2 bibliography path is `manuscript_v2/references_pending_v2.bib`, but that bibliography is historical only; v3 must use `reference_update/VERIFIED_REFERENCES.bib`.
