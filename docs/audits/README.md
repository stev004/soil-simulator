# Audit archive

## IMPORTANT SCOPE NOTICE

These audits were AI-executed computational implementation reviews conducted in separate clean-context sessions. They were not human peer review, institutional review, or independent biological validation. They assessed implementation, reproducibility, artifact integrity, and claim alignment only.

This directory provides living navigation for the canonical historical audit
documents and their preserved supporting records. Audit work assessed evidence;
it did not change scientific results. Implementation remediation means that
code, accounting, sampling, gate or reporting defects were corrected and
replayable. Biological validation requires suitable external observations and
tests; implementation review does not provide it.

`docs/audits/` contains the canonical repository copies, the living navigation
in this file, and the dedicated
[`AUDIT_SCOPE_NOTICE.md`](AUDIT_SCOPE_NOTICE.md). `audits/incoming/` contains
the immutable incoming source deliverables and supplied export manifest. The
incoming files are preserved for provenance and are not the navigation layer.

## Historical audit navigation

| Historical document | Repository phase assessed | Scope and status |
|---|---|---|---|
| [`AUDIT_v0.9.0_INDEPENDENT.md`](AUDIT_v0.9.0_INDEPENDENT.md) | Frozen v0.9.0 simulator, ML and selector benchmark | AI-executed clean-context computational audit. The historical `INDEPENDENT` filename does not mean independent human review or independent biological validation. |
| [`AUDIT_PHASE96_CLEAN_SLATE.md`](AUDIT_PHASE96_CLEAN_SLATE.md) | Phase 9.6 evidence | AI-executed clean-context computational re-audit; immutable historical payload. |
| [`AUDIT_PHASE97_FOCUSED.md`](AUDIT_PHASE97_FOCUSED.md) | Corrected Phase 9.7 evidence | AI-executed focused computational re-audit; immutable historical payload. |

Supporting historical records:

- [`phase96_finding_closure.csv`](phase96_finding_closure.csv),
  [`phase96_recomputed_metrics.json`](phase96_recomputed_metrics.json), and
  [`phase96_discrepancies.md`](phase96_discrepancies.md)
- [`phase97_finding_closure.csv`](phase97_finding_closure.csv),
  [`phase97_recomputed_metrics.json`](phase97_recomputed_metrics.json), and
  [`phase97_discrepancies.md`](phase97_discrepancies.md)
- [`phase97_sobol_findings.md`](phase97_sobol_findings.md) and
  [`phase97_convergence_findings.md`](phase97_convergence_findings.md)
- [`AUDIT_EXPORT_MANIFEST.json`](AUDIT_EXPORT_MANIFEST.json) and
  [`audit_manifest.json`](audit_manifest.json)

The historical conclusions and scientific limitations remain in those
documents unchanged. Frozen reports and supporting payloads must not be edited
or renamed.
