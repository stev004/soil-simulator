# Phase 9.5 pre-publication scientific remediation

## Decision

Phase 9.5 is **not publication ready**. The exact next task is **remaining
scientific remediation**, not manuscript drafting. An independent re-audit is
appropriate only after the empirical population and covariance/sensitivity
blockers are resolved.

The requested `docs/AUDIT_soil_simulator_v0.9.0.md` is absent from this
checkout. The issue list in the Phase 9.5 implementation request therefore
governs this pass; this report does not claim line-by-line closure against an
unavailable audit document.

## Frozen baseline and output boundary

`outputs/phase9_v0.9.0/` is the frozen audited baseline. Its 18 files are
declared in `config/phase95/frozen_v090_sha256.json` and pass byte-level
verification. No historical Phase 3--9 result or report was overwritten.
All new results are under `outputs/phase95_v0.9.5/`.

## Migration notes

| Change | v0.9.0 | Phase 9.5 | Scientific/accounting reason |
|---|---|---|---|
| Headline targets | Included persistence-dominated stocks and deterministic policy identities | Paired effects only; stocks are circularity diagnostics; cost/emissions are direct calculations | Prevent inflated or circular ML-skill claims |
| Policies | Seven, including a biologically null `no_till` duplicate | Six; `no_till` removed | Duplicate policies inflated apparent diversity and could inflate exact matches |
| Intervention timing | Legacy finite schedules and horizon-invariant outcome lookups | Recurring biological and accounting events at explicit months | Correct the number of intervention events at 24, 60 and 120 months |
| Emissions | One aggregate proxy | Operational and partial lifecycle proxies separated | Expose unsupported lifecycle boundaries |
| Phosphorus | Provisional response entered selector conclusions | Current, bounded-dose and alternative-response ablations; excluded from headline carbon conclusions | The structural P→NPP→residue→SOC loop is uncalibrated |
| Sensitivity | Local/stress diagnostics | Morris plus Sobol on registered full ranges by policy/target/horizon | Quantify global mechanistic and scheduling uncertainty |
| SOC validation | One-step RothC parity only | Separate uncalibrated 1852--1998 Hoosfield exercise | One-step parity is verification, not long-term validation |
| Population | Synthetic expanded fixtures | Still explicitly synthetic; real 50-location pilot blocked | No empirical relabelling without a reproducible extraction |
| Selection/regret | Frozen Phase 9 benchmark | Not rerun | Predictor/population prerequisites are not satisfied |

No biological equation was silently recalibrated. `protected_soc` remains a
model proxy, not measured MAOC.

## Findings addressed

- Stock circularity is quantified and removed from headline ML framing.
- Deterministic cost/emissions identity targets are excluded from ML.
- The baseline/`no_till` duplicate is detected and removed.
- Horizon-aware recurring event accounting is implemented outside C/P balance.
- The phosphorus structural loop is reported through six requested views.
- A reproducible Morris/Sobol framework, convergence diagnostics and ranking
  stability analysis are available.
- Uncalibrated multi-decade Hoosfield total-SOC trajectories, errors and a plot
  are reported separately from the one-step parity test.
- Baseline preservation, provenance, hashes and fail-closed readiness gates are
  machine tested.

## Unresolved findings

- No reliable version-pinned paired soil/climate extraction with 50 real
  locations was available. No revised empirical population was generated.
- Observable population covariance was therefore not re-estimated or included
  in the global sensitivity result.
- The Morris/Sobol result uses one archived synthetic field and is a framework
  and mechanistic screening result, not population-level sensitivity evidence.
- Phosphorus response magnitudes lack defensible field calibration.
- The Hoosfield run substantially underpredicts FYM treatments and does not
  validate AMF dynamics or the protected-SOC proxy.
- Effect-only ML, applicability, oracle and regret benchmarks were not rerun
  because their empirical population prerequisite failed.

## Reproduction

```bash
.venv/bin/python -m soil_simulator.phase95.pipeline
.venv/bin/ruff format --check .
.venv/bin/ruff check .
.venv/bin/mypy --strict
.venv/bin/pytest
.venv/bin/python -m build
```

The artifact runner is offline and deterministic. See the artifact hashes and
seed manifest in `outputs/phase95_v0.9.5/`.
