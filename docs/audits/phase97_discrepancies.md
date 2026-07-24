# Phase 9.7 — Discrepancies between independent recomputation and reported values

**Audit:** soil_simulator Phase 9.7 focused independent re-audit — 2026-07-22
**Scope:** every reported Phase 9.7 metric was independently recomputed from source, configuration and machine-readable outputs.

## Headline

**No material scientific discrepancies were found.** Every headline Phase 9.7 metric — artifact hashes and set digests, the Sobol design/result hashes, all convergence numbers, all effect-ML gate values, all 14 uncertainty-coverage cells, and the FYM calibration profile — reproduces the reported value exactly. The two items below are procedural/observational, not disagreements with the reported science.

## Procedural / observational items

| # | Severity | Item | Reported | Independent | Note |
|---|---|---|---|---|---|
| 1 | INFO | Pipeline worker count in scratch double-run | committed `evaluation_workers=4` | audit ran `=1` | On this ~0.1 GB-free machine the 4-worker fork was OOM-killed; single-worker was used for the reproduction. It changes only the two `evaluation_workers_requested/actual` bookkeeping fields (which cascade into 4 manifest files); the Sobol **design hash** (`86e4502a…`) and **result hash** (`96e14659…`) and all estimates/convergence/policy-ranking are byte-identical to committed. Worker count has zero effect on the deterministic science. |
| 2 | LOW (disclosed limitation, not a discrepancy) | OOD uncertainty-coverage band at small n | "all 7 targets pass" | reproduced exactly (14/14 cells) | At n=24 the exact central-95% Binomial(n,0.90) count range is [18,24] → acceptance band [0.75,1.00]; the upper edge is 100%, so **overcoverage cannot fail** and the acceptance region is wide. This is a genuine and honestly-disclosed statistical-power limitation of small-n OOD, not an arithmetic discrepancy. The gate is nonetheless structurally sound and materially stronger than the Phase 9.6 flat 0.80–1.00 band. |

## Exact-match ledger (independent recomputation == reported)

| Quantity | Value | Match |
|---|---|---|
| Phase 9.7 artifact hashes | 35/35 files | ✓ |
| Phase 9.7 artifact-set digest | `cf0915f2…` (recorded table AND current bytes) | ✓ |
| corrected_phase96 manifest | 48/48 rehash to current bytes | ✓ |
| historical Phase 9.6 manifest | UNCHANGED (set `ed1ff1ae…`, AUDIT entry `c5494d1f…`) | ✓ |
| historical v0.9.0 / phase96 outputs | not overwritten | ✓ |
| Phase 9.7 double-run | byte-identical (18/18 outputs) | ✓ |
| Phase 9.6 double-run | byte-identical (19/19 outputs) | ✓ |
| population hash (input) | `9bb2f8fec9…` | ✓ |
| Sobol design hash (seed 970021, d=10, N=1024) | `86e4502a…` bit-for-bit | ✓ |
| Sobol result hash (estimates only) | `96e14659…` (runtime excluded) | ✓ |
| Ishigami estimator validation | S1 [0.314,0.443,0.0002] / ST [0.558,0.443,0.244] vs textbook | ✓ (3–4 dp) |
| Convergence 128→256 | S1chg 0.2224, STchg 0.1885, rankS1 0.912, rankST 0.992, CIw 0.216, unst 0.075, neg 0.046 | ✓ |
| Convergence 256→512 | S1chg 0.1412, STchg 0.1338, rankS1 0.913, rankST 0.988, CIw 0.157, unst 0.025, neg 0.043 | ✓ |
| Convergence 512→1024 (deciding) | S1chg 0.1220, STchg 0.1123, rankS1 0.935, rankST 0.997, CIw 0.110, unst 0.0179, neg 0.0179 | ✓ |
| convergence_reached | False (index-change criterion fails) | ✓ |
| FYM winner (all 7 target·horizon, all base sizes 128→1024) | farmyard_manure, stable | ✓ |
| Full pytest | 227 passed | ✓ (reported count confirmed) |
| Leakage checks (5) | 56 loc, 31 train/25 excluded, 0 overlaps, min cross-group dist 0.814 | ✓ |
| Leakage injection test | fails closed + names crossover (4 scenarios + missing + empty) | ✓ |
| Downstream eligibility | False; blocked by effect_prediction, ood_performance, independent-validation | ✓ |
| selection_regret_executed | False | ✓ |
| Coverage cells | 14/14, 0 arithmetic mismatches | ✓ |
| Binomial range n=104 / n=24 | [87,99] / [18,24] | ✓ |
| FYM calibration estimate | 1.10 (upper bound of [0.90,1.10]) | ✓ |
| FYM edge slope | −7.865 (fit improving at bound) | ✓ |
| Held-out FYM cessation | MAE 7.214 / RMSE 7.577 / bias −7.214 | ✓ |
| RothC constants / FYM bound | unchanged | ✓ |

## Interpretation

Phase 9.7 is a faithful, reproducible, honestly-documented remediation. The Phase 9.6 audit's own reported numbers were confirmed there and Phase 9.7's are confirmed here; the repository does not overstate any result and it retains its own negative findings (non-convergence, failed prediction/OOD gates, boundary calibration) rather than tuning them away.
