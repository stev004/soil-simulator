# Phase 9.7 convergence analysis — independent audit findings

Scope: `convergence_diagnostics` / `policy_ranking_stability` in
`src/soil_simulator/phase97/sensitivity.py`; `sensitivity_convergence_manifest.json`,
`sensitivity_first_total.json`, `sobol_sampling_manifest.json`;
`docs/PHASE97_SENSITIVITY_CORRECTION.md`. Verdict: **convergence analysis and the
"not converged" conclusion are correct; no scientific conclusion depends on the
non-converged indices.**

## B1 — Decision arithmetic reproduced exactly
Recomputed `convergence_diagnostics` on the committed per-size estimates with the
predeclared rule (max index change ≤0.10, min rank corr ≥0.90, mean CI width ≤0.20,
max unstable fraction ≤0.10). Every field matches the manifest to <1e-12:

| pair | maxΔS1 | maxΔST | rankS1 | rankST | CIwidth | unstable | negative | passed |
|------|--------|--------|--------|--------|---------|----------|----------|--------|
|128→256 |0.222408|0.188464|0.9120|0.9918|0.2156|0.0750|0.0464|False|
|256→512 |0.141186|0.133827|0.9130|0.9882|0.1565|0.0250|0.0429|False|
|512→1024|0.121989|0.112311|0.9351|0.9974|0.1101|0.0179|0.0179|False|

Deciding pair 512→1024: maxΔS1 0.122 > 0.10 AND maxΔST 0.112 > 0.10 → index-change
criterion FAILS; rank (0.935/0.997 ≥ 0.90), CI width (0.110 ≤ 0.20) and unstable
fraction (0.0179 ≤ 0.10) all PASS. Overall `passed=False`,
`convergence_reached=False`, `status="not_converged_results_not_final"`. Correct.

## B2 — Doc numbers match manifest
PHASE97_SENSITIVITY_CORRECTION.md states 512→1024: S1 0.122, ST 0.112, rank 0.935/0.997,
CI width 0.110, unstable/neg both 0.0179. All match the manifest (and my recompute)
exactly. Doc correctly says index-change criterion failed while the other three passed.

## B3 — Runtime excluded from decision and from hash
Runtime (211.176/424.182/854.173/1447.559 s) lives only in
`sampling_manifest.runtime_reference`; `convergence_diagnostics` never reads it.
Recomputing `result_sha256` over the estimates dict alone reproduces the stored
`96e14659…` exactly, and no "runtime" key appears anywhere under `estimates` ⇒ runtime is
NOT in the deterministic hash. Manifest explicitly flags runtime as measured evidence
excluded from convergence decisions and hashes. Confirmed.

## B4 — No scientific conclusion relies on the non-converged indices
The headline conclusion (FYM is the winning policy) comes from
`policy_ranking_stability`, which ranks policies by the MEAN A-matrix output effect
(a first-moment statistic over the QMC A samples) — completely independent of the
S1/ST variance decomposition. Verified from the committed output:
farmyard_manure is the winner for ALL 7 target|horizon combinations
(protected_soc_proxy 60/120, respiration 60/120, total_soc 60/120, yield 24) and
`winner_stable_with_largest_design` is True at every base size 128/256/512/1024.
Thus the FYM-winner conclusion is fully separable from — and does not depend on — the
non-converged S1/ST indices. The doc correctly labels the indices "diagnostic … must not
be labelled final." No headline claim rides on them.

## B5 — Sample size / approach needed for stable rankings
Observed maxΔS1 trajectory across doublings: 0.222 → 0.141 → 0.122. This is far slower
than the ~1/√N Monte-Carlo rate (which predicts ×0.707 per doubling, i.e. 0.222→0.157→0.111;
the actual 0.141→0.122 ratio ≈0.864 is worse). Extrapolating at that empirical ratio,
reaching the 0.10 threshold needs n = ln(0.10/0.122)/ln(0.864) ≈ 1.36 doublings, i.e. at
most 2 further doublings: 0.122·0.864 ≈ 0.105 (still >0.10 at N≈2048), 0.122·0.864² ≈ 0.091
(<0.10 at N≈4096). So order N ≈ 2k–4k base samples (~1.4e4–2.9e4 model evaluations at
7 evals/base-row), reached in roughly 2–4× the largest run already performed (N=1024) — not the days–
weeks scale a naive read might assume. (An earlier draft overstated this as 5–7 doublings /
32k–128k samples; that was an extrapolation error — corrected here.) Even so, the observed
decay is slower than 1/√N and the ratio may not stay constant, so treat 2k–4k as a lower
bound and verify empirically. More effective remedies, in order of
expected payoff: (a) the fym_phosphorus_content factor is identically 0 for the
non-phosphorus policy outputs — dropping inert factors / restricting the decomposition to
the genuinely active factors reduces dimensionality and variance; (b) a lower-variance
total-order estimator is already in use (Jansen), so the gain is mainly from N and
dimension; (c) if only rankings (not index magnitudes) are needed, note rank correlations
are already ≥0.91 and the FYM winner is stable — ranking stability does not require index
convergence. Treat S1/ST magnitudes as non-final until N is raised to ~2k–4k base samples
(verified empirically) or the factor set is reduced.
