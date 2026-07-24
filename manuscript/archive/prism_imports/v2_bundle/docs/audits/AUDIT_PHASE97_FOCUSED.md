# AUDIT_PHASE97_FOCUSED.md — Focused independent re-audit of soil_simulator Phase 9.7

**Auditor:** independent (clean-context) re-audit
**Date:** 2026-07-22
**Repository:** `/Users/stevenmatson/Documents/soil_simulator`, version 0.9.7
**Constraint honoured:** no repository files were modified. All reproduction ran against read-only reads or `/tmp` scratch copies.
**Predecessor:** this audit re-verifies the fixes made in response to the Phase 9.6 clean-slate audit (`AUDIT_PHASE96_CLEAN_SLATE.md`, in the artifact store).

---

## Headline judgement

**Phase 9.7 is a faithful, reproducible and honestly-documented remediation of the Phase 9.6 defects.** Of the nine defects, **six are closed** and **three are substantially addressed** (their implementation defect is fixed; the residual is a scientific limitation that Phase 9.7 discloses rather than an unclosed defect). **No defect is unresolved and none was replaced by a new issue.** Every headline metric I independently recomputed matches the reported value; the reported `227 passed` is confirmed; the pipeline is byte-for-byte deterministic; and history was preserved (no historical manifest or output was overwritten).

**Publication verdict (unchanged in direction from Phase 9.6, now with cleared implementation blockers):** a **validated agricultural-prediction paper remains NOT supported**. A **methodological paper** and a **software/simulator paper** are now **defensible** subject to the bounded-claim conditions below. A **portfolio/case-study** is **supported now**. Prism manuscript drafting may begin **only** for the methodological, software, or portfolio framings, with the prohibited claims listed in §11 explicitly excluded.

---

## 1. Artifact integrity and reproducibility — CLEAN

- **Phase 9.7 artifact hashes: 35/35 verify.** The artifact-set digest `cf0915f2…` matches both the recorded table and a recompute over current bytes.
- **Corrected Phase 9.6 manifest** (`corrected_phase96_artifact_hashes.json`): all **48/48** paths rehash to current bytes; the set digest matches; each drifted file carries an explicit old→new change record with reason. The `docs/AUDIT_soil_simulator_v0.9.0.md` entry now records the current on-disk bytes (`f2654c04…`).
- **History preserved.** The historical Phase 9.6 manifest is **unchanged** (set digest still `ed1ff1ae…`, AUDIT-doc entry still the pre-edit `c5494d1f…`); `historical_manifest_modified=False` and `historical_v0_9_0_artifacts_modified=False` are both truthful. The Phase 9.6 manifest-drift defect is thus closed the correct way — a *separate* correction manifest layered on top of an untouched historical record.
- **Determinism.** Two full Phase 9.7 runs in isolated scratch dirs are **byte-identical across all 18 outputs**. Two Phase 9.6 runs are byte-identical across all 19 outputs; the population hash `9bb2f8fec9…` reproduces. The scrambled Sobol **design hash** (`86e4502a…`) reproduces bit-for-bit from an independent `scipy.stats.qmc.Sobol` draw, and the **result hash** (`96e14659…`) recomputed from estimates only equals the stored value — confirming runtime is correctly excluded from the deterministic digest.
- **Only non-identity vs committed:** my scratch runs used `evaluation_workers=1` (the 4-worker fork was OOM-killed on this ~0.1 GB-free machine). That changes only the `evaluation_workers_requested/actual` bookkeeping fields; all estimates, convergence, policy rankings and hashes are identical. Worker count has no effect on the deterministic science.

## 2. Engineering verification — ALL GREEN

`ruff format --check` (114 files) and `ruff check` pass; `mypy --strict` clean (113 source files). **Full pytest: 227 passed** — the reported count is confirmed, and the Phase 9.6 hash-drift failure (`test_source_and_artifact_hash_manifests_replay_offline`) is now resolved. RothC parity (1), carbon/phosphorus balance (22), deterministic replay (20), scenario-direction (15) and phase97 (13) suites all pass. The 0.9.7 wheel and sdist build via hatchling; a fresh-venv install imports all `phase97` submodules, resolves scipy/numpy as declared dependencies, and runs the CLI.

## 3. Sobol correction — CLOSED

The Phase 9.6 plain-PRNG sampler is gone. Phase 9.7 uses a genuine **scrambled `scipy.stats.qmc.Sobol(d=2·5, scramble=True, seed=970021)`** drawn with `random_base2` (proper power-of-two sizes), split column-wise into A and B, with A_B(i) hybrids. First-order indices use the **Saltelli 2010 covariance estimator** `mean(B·(A_B−A))/var`; total-order uses the **Jansen 1999 estimator** `mean((A−A_B)²)/(2·var)`. Negative estimates are retained, never clipped. I validated the estimator on the **Ishigami function** (S1 `[0.314, 0.443, 0.0002]`, ST `[0.558, 0.443, 0.244]` — textbook to 3–4 dp), confirmed the discrete parameter transforms map correctly (location 0–55, weather 0–9, schedule 12–36), and confirmed the bootstrap CIs are bit-identical across repeated runs.

## 4. Convergence — SUBSTANTIALLY ADDRESSED (correctly declared non-converged)

Phase 9.7 replaces the Phase 9.6 self-consistency number with a **predeclared nested-size convergence rule** over base sizes 128/256/512/1024 (max |ΔS1|,|ΔST| ≤ 0.10; both rank correlations ≥ 0.90; mean 95% CI width ≤ 0.20; unstable fraction ≤ 0.10). The deciding 512→1024 pair gives max ΔS1 = 0.122 and ΔST = 0.112, both above 0.10 — so **convergence is not reached**, the rank/width/stability criteria notwithstanding. The repository correctly labels the indices *diagnostic, not final*. I reproduced all convergence numbers exactly. The change magnitudes decay slowly (0.222 → 0.141 → 0.122), so reaching the 0.10 threshold would require substantially more than 1024 base samples. **No headline scientific conclusion depends on the non-converged indices**: the one policy conclusion (farmyard manure is the top policy for all seven target·horizon pairs) comes from `policy_ranking_stability`, which ranks by the mean A-matrix output effect — a first-moment statistic entirely separate from the S1/ST variance decomposition — and is stable at every base size.

## 5. Leakage gate + injection test — CLOSED

The Phase 9.6 hardcoded `empirical_location_leakage_check = True` literal is gone. The gate now computes all five isolation checks from `effect_only_dataset.csv` (56 locations, 31 exclusively-train / 25 excluded, 0 field overlaps, minimum cross-group standardised distance 0.814) and **fails closed** on missing columns or empty evidence. A deliberate **injection test** — introducing synthetic crossovers in a scratch copy — makes the gate **fail and name the crossover** under four distinct leakage scenarios plus missing-column and empty-input cases.

## 6. Independent effect-validation + downstream gates — CLOSED

The Phase 9.6 hardcoded `independent_effect_validation = False` literal is replaced by a genuine **evidence contract**: the gate passes only for an identified empirical intervention-effect dataset with ≥30 observations, compatible treatments, coverage of every primary target·horizon pair, independent collection, and no use in calibration. No such dataset exists, so the gate is **correctly False** and records dataset identity, source, sample size, compatibility, independence and reason — and it fails closed on malformed metadata while genuinely being able to pass with valid evidence (verified, so it is not forced-false). Downstream eligibility is a **true 5-way conjunction** of the prediction, OOD, uncertainty, leakage and independent-validation gates — forcing the inputs True flips eligibility True, proving it is not structurally forced. It is currently blocked by three gates (effect prediction, OOD performance, independent validation); `selection_regret_executed = False` is confirmed. **Stopping downstream selection/oracle/regret was required and correctly enforced.**

## 7. Uncertainty coverage — SUBSTANTIALLY ADDRESSED

The Phase 9.6 flat 0.80–1.00 acceptance band is replaced by a **per-target and per-regime** (test + OOD) nominal-90% rule using the exact central-95% Binomial(n, 0.90) count range, Wilson confidence intervals and an excessive-width diagnostic; regimes with fewer than 20 rows or fewer than four independent groups explicitly abstain, and no target can hide another's undercoverage. All 14 coverage cells reproduce exactly (0 arithmetic mismatches) and every target passes. **Residual (disclosed limitation, not a defect):** at n = 24 the OOD acceptance band is [0.75, 1.00] with an upper edge of 100%, so overcoverage cannot fail and the acceptance region is wide at small n. The rule is structurally sound and materially stronger than Phase 9.6, but small-n OOD coverage remains low-power.

## 8. FYM calibration boundary — CLOSED (as disclosure)

Phase 9.7 explicitly profiles the boundary solution rather than hiding it. The FYM carbon-reconstruction factor estimate sits exactly on its [0.90, 1.10] upper bound; the objective decreases monotonically across the profile (4.862 → 3.129 for factor 0.90 → 1.10) with an edge slope of −7.865 (fit still improving at the bound); identifiability in the FYM direction collapses to [1.10, 1.10]; held-out FYM-cessation performance is weak (MAE 7.214, RMSE 7.577, bias −7.214 t C ha⁻¹). The manifest records `boundary_constrained = True`, `objective_likely_improves_beyond_bound = True`, `general_calibration_success = False`. The bound was **not** widened, out-of-bound values were **not** evaluated, and RothC constants are unchanged. The documentation does not overstate: it states plainly that this is not a successful general calibration and validates neither AMF dynamics nor `protected_soc` as measured MAOC.

## 9. Documentation and claims — ACCURATE

All nine required limitations are stated explicitly: non-converged/diagnostic-only sensitivity; a 56-location pilot that is not nationally representative; generated fields with synthetic perturbations and latent AMF/P priors; `protected_soc` as a model proxy, not measured MAOC; absent independent empirical effect validation; failed effect-prediction/OOD gates; blocked downstream selection; boundary-constrained FYM calibration with weak cessation; and unsupported agricultural-prediction claims. The docs disambiguate simulator effects from empirical causal effects. Every quantitative claim I checked matches the machine-readable outputs. **No claim overstates the evidence** — the repository is unusually candid, retaining its own negative findings rather than tuning them away.

## 10. Finding-by-finding closure of the 9 Phase 9.6 defects

| # | Defect (Phase 9.6) | Phase 9.7 classification |
|---|---|---|
| D1 | Manifest drift / RED offline-replay test | **CLOSED** |
| D2 | PRNG Sobol sampler, negative/over-unity indices | **CLOSED** |
| D3 | "Convergence" was self-consistency; underpowered | **SUBSTANTIALLY ADDRESSED** (rule now genuine; convergence still not reached — disclosed) |
| D4 | Hardcoded leakage gate (fail-open) | **CLOSED** |
| D5 | Hardcoded independent-validation gate | **CLOSED** |
| D6 | Structurally forced downstream result | **CLOSED** |
| D7 | Weak 0.80–1.00 uncertainty band; OOD ungated | **SUBSTANTIALLY ADDRESSED** (per-target/regime exact-binomial; permissive at small n — disclosed) |
| D8 | FYM boundary solution insufficiently disclosed | **CLOSED** (now fully profiled/disclosed; calibration limitation remains, honestly reported) |
| D9 | Overstated documentation / contradictions | **SUBSTANTIALLY ADDRESSED** (Phase 9.7 docs accurate; Phase 9.6 population-label wording is outside 9.7 scope) |

Detail and evidence per defect are in `phase97_finding_closure.csv`.

## 11. Publication readiness by paper type

**(a) Validated agricultural-prediction paper — NOT SUPPORTED.**
Blockers are scientific, not implementation: no independent empirical effect-validation dataset; failed effect-prediction and OOD gates on the sole yield target; a 56-location pilot that is not representative; `protected_soc` is a proxy, not measured MAOC; the FYM calibration is boundary-constrained with weak held-out cessation. None of these can be argued away with the current evidence.

**(b) Methodological paper — DEFENSIBLE (bounded).**
The corrected Sobol/convergence machinery, the fail-closed gate architecture with a passing injection test, the per-target/regime coverage rule, and the boundary-calibration diagnosis are a genuine, reproducible methodological contribution. Permitted claims: "here is a determinism- and leakage-audited effect-only sensitivity/gating pipeline, and here is why its own gates *block* a predictive claim." **Prohibited:** presenting the Sobol indices as converged/final, or the FYM calibration as successful. Recommended (not required) strengthening: push the convergence sweep past 1024 to demonstrate the index-change criterion can be met, and add at least one larger-n OOD regime so the coverage gate has power against overcoverage.

**(c) Software/simulator paper — DEFENSIBLE (bounded).**
The software is strong: strict typing, deterministic byte-identical pipelines, a full green test suite, clean build and installed-wheel smoke, and history-preserving artifact manifests. A software/simulator paper describing the architecture and reproducibility guarantees is supportable. **Prohibited:** any claim that simulator effects are empirically validated agricultural outcomes.

**(d) Portfolio / case study — SUPPORTED NOW.**
With the synthetic/non-causal boundaries already stated in the repo, this is publishable as-is.

## 12. Remaining analyses required before each publication form

- **Agricultural-prediction paper:** acquire and register an independent empirical intervention-effect dataset (≥30 obs, all target·horizon pairs, unused in calibration); pass the effect-prediction and OOD gates on real held-out effects; replace or empirically ground the `protected_soc` proxy against measured MAOC; resolve or widen-and-justify the FYM calibration bound with a defensible cessation result; expand the pilot toward a representative population. Until then this paper type stays blocked.
- **Methodological paper:** none required to publish the method honestly; optionally extend the Sobol sweep beyond 1024 and add a larger-n OOD regime.
- **Software/simulator paper:** none required beyond the current green suite and builds.
- **Portfolio/case study:** none.

---

## Final verdict

The Phase 9.7 remediation did what it claimed. Every implementation defect the Phase 9.6 clean-slate audit identified is genuinely fixed — verified independently at source, in the machine-readable outputs, by a leakage injection test, by an Ishigami estimator check, and by byte-identical double-runs — with no historical artifact overwritten and no negative finding tuned away. The three "substantially addressed" items are honestly-disclosed scientific limitations (non-converged indices, small-n OOD coverage power, and Phase-9.6-scope documentation wording), not unclosed defects.

**Manuscript drafting may begin for a bounded methodological paper, a software/simulator paper, or a portfolio case study** — with the §11 prohibited claims explicitly excluded. **A validated agricultural-prediction manuscript must not be drafted:** its blockers are scientific and unresolved, and the repository's own gates correctly refuse to authorise the downstream claims such a paper would require.
