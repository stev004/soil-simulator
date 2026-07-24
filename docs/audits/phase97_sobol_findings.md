# Phase 9.7 Sobol implementation — independent audit findings

Scope: `src/soil_simulator/phase97/sensitivity.py`, `src/soil_simulator/phase95/sensitivity.py`
(transforms), `config/phase97/sensitivity.yaml`, committed outputs in
`outputs/phase97_v0.9.7/`. Repo code run read-only from a `sys.path` insert; no repo files
modified. Verdict: **implementation is mathematically correct.**

## A1 — Genuine scrambled Sobol, single 2D design split A/B
`sobol_unit_matrices` (sensitivity.py:130–141) builds
`qmc.Sobol(d=2*dimension, scramble=True, seed=seed)` then
`design = engine.random_base2(log2(N))`, `matrix_a = design[:, :d]`,
`matrix_b = design[:, d:]`. So ONE 10-column (2·5) scrambled Sobol sequence is drawn and
split column-wise into A (cols 0–4) and B (cols 5–9). `scramble=True` is hard-coded;
seed threaded from settings (`seed=970021`). This is real QMC, not a PRNG.
Independent reproduction of the largest design hash:
recomputed `86e4502a…76dc676a1` == manifest `largest_design_sha256_float64_le` (bit-for-bit).

## A2 — Hybrid A_B(i) construction
run_nested_sobol (sensitivity.py:~450 and ~470): `hybrid = row_a.copy(); hybrid[parameter_index] = row_b[parameter_index]`.
Correct Saltelli A_B(i): B value for factor i, A elsewhere. Verified in both the serial and
the parallel path (identical construction).

## A3 — Estimators (standard forms, written out)
`_one_estimate` (sensitivity.py:167–174), with V = population variance (ddof=0) of the
concatenated A and B evaluations (`_variance`, line 158):
  - First-order (Saltelli 2010 covariance):
      S1_i = mean( B * (AB_i − A) ) / V
  - Total-order (Jansen 1999 squared difference):
      ST_i = mean( (A − AB_i)^2 ) / (2 V)
These are the textbook Saltelli-2010 / Jansen-1999 forms.

**Ishigami validation** (a=7, b=0.1, N=8192, my own scrambled scipy Sobol design fed through
the repo's `estimate_indices`):
  S1 est [0.314, 0.443, 0.000] vs true [0.314, 0.442, 0.000]
  ST est [0.558, 0.443, 0.244] vs true [0.558, 0.442, 0.244]
Agreement to ~3 decimals ⇒ estimator is correct.

## A4 — Unit-cube → distribution transforms
`SensitivityParameter.transform` (phase95/sensitivity.py:31–58). Quantile clamped to [0,1].
- uniform: min + q·(max−min). fym q=0→0, 0.5→15, 1→30; tillage q=0→1, 1→2. Correct.
- uniform_discrete: round(min + q·(max−min)). Verified distinct integer support:
    empirical_location_index 0–55 → 56 distinct integers, min 0 max 55
    weather_resample_index   0–9  → 10 distinct integers
    schedule_interval_months 12–36→ 25 distinct integers (24-mo span +1)
  All values integral, endpoints correct.
- NOTE (low severity, not a defect): round()-based discretization half-weights the two
  endpoints (interior integers get width 1/n in q, endpoints 0.5/n). A minor,
  well-understood non-uniformity of round-based discrete sampling; does not affect
  estimator correctness or the audited conclusions.

## A5 — Deterministic bootstrap CIs
`estimate_indices` (sensitivity.py:187…): `rng = np.random.default_rng(bootstrap_seed)` then a
fixed `resamples` integer matrix (bootstrap_replicates=200) reused across every output/param;
`bootstrap_seed = settings.seed + size` (per size). Percentile interval at 95%.
Two independent runs with identical seed produced bit-identical CIs. Deterministic.

## A6 — Negatives never clipped
Grep of both modules: no `clip`, no `max(0,·)`, no `abs()` applied to S1/ST. The only `abs()`
uses are convergence change-magnitudes (|ΔS1|,|ΔST|) and Phase-95 Morris effect magnitudes;
the only `max(0.0,·)` is quantile clamping. `first_order`/`total_order` stored raw; negative
flags recorded (`first_order_negative`,`total_order_negative`); estimator dict literally states
`"negative_estimates": "retained without clipping"`. CSV shows negative CI bounds preserved.

## A7 — Independent recompute method used
(1) Ishigami analytic test function through the repo's own `estimate_indices` (A3) — passed.
(2) Bit-for-bit reproduction of the scrambled design hash (A1).
(3) Full convergence-diagnostic recomputation from the committed per-size estimates (see
convergence_findings.md) — reproduced exactly.
Did NOT re-run the full mechanistic evaluator (RAM-constrained, per instructions); this was
unnecessary because the design, estimator and diagnostics are all independently verified.
