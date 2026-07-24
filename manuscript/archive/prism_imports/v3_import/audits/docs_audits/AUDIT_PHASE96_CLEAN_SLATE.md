# Independent Clean-Slate Re-Audit — `soil_simulator` Phase 9.6

**Scope.** Soil–plant–AMF synthetic-field simulator and its Phase 9.6 remediation of the
v0.9.0 audit findings. Independent, adversarial, verify-nothing-on-trust re-audit.

**Constraints honoured.** No repository files were modified (all pipeline re-runs, quality
gates and metric recomputations were executed against read-only reads or `/tmp` scratch
copies). No negative finding is softened. Manuscript drafting is recommended only for a
paper type the evidence actually supports.

**Method.** Independent SHA-256 recomputation of every manifest; two full pipeline re-runs
from scratch; the complete quality-gate stack (ruff format, ruff check, mypy --strict,
pytest, RothC parity, C/P balance, build, installed-wheel smoke); independent
re-implementation of the Hoosfield validation (both by running repo code and by recomputing
from `validation_trajectories.csv`), the Morris/Sobol convergence numbers, and the entire
effect-only ML benchmark (ridge normal-equations + alpha selection + policy-mean baseline +
conformal intervals) from `effect_only_dataset.csv`; and direct source reading of the
sensitivity, population, empirical and gating code.

---

## Headline judgement

**Phase 9.6 is a genuine, well-disciplined remediation. Every headline scientific metric it
reports reproduces exactly, and its own top-line conclusion — _stop; do not draft a
manuscript_ — is correct and independently confirmed.** The v0.9.0 findings have been
materially worked down: two of the two criticals and all three "closed-class" majors are
resolved or nearly so.

That verdict comes with three hard qualifications, none of which the repository hides but
each of which a reader must carry:

1. **The empirical grounding is real but thin.** The population is now anchored to 56
   genuinely paired real soil–climate records (not the 10 authored seeds of v0.9.0), but it
   is a small, GB-wide, non-representative pilot; "112 fields" is 56 effective locations × ~2
   synthetic clones.
2. **The failed prediction/OOD gates are genuine, and stopping downstream was required.**
   But two of the five gates are cosmetic (hardcoded literals), and the uncertainty gate is
   weak — the pipeline reaches the right conservative answer through a mix of sound and
   decorative checks.
3. **The new global-sensitivity and calibration analyses exist but are not yet adequate.**
   Sobol is underpowered and mislabelled; the FYM calibration is a boundary solution; the
   Hoosfield FYM/cessation treatment still fails.

**One live integrity failure was found:** the repository's own offline-replay test is
currently **red** because `docs/AUDIT_soil_simulator_v0.9.0.md` was edited after its hash was
frozen.

---

## 1. Integrity — SHA-256 verification

| Manifest | Result |
|---|---|
| `EMPIRICAL_SOURCE_MANIFEST.json` — 68 raw + 2 processed files | **all match** |
| RothC v2.1.1 validation zip (`728ef132…`) | **match** |
| `artifact_hashes.json` — 48 files | **47/48 match** |
| `artifact_set_sha256` digest | internally consistent with its own recorded table; does **not** match the current file tree |
| `config/phase95/frozen_v090_sha256.json` — frozen baseline | **18/18 match** |

**The one mismatch is real and consequential.** `docs/AUDIT_soil_simulator_v0.9.0.md` on disk
hashes to `f2654c04…`; the manifest recorded `c5494d1f…`. File mtimes show the doc was edited
at **20:14** while `artifact_hashes.json` was frozen at **19:47** — the audit document drifted
after the provenance was sealed. The `artifact_set` digest is computed over the *recorded*
per-file table (`json.dumps(files, sort_keys, separators=(",",":"))`, pipeline.py L487–490),
so it remains internally consistent but no longer certifies the on-disk tree.

*Note:* the v0.9.0 audit `.md` itself contains **no** SHA-256 literals; the machine-readable
v0.9.0 integrity record is the frozen-baseline manifest (18/18 verified), not the prose
document.

## 2. Determinism & reproducibility

Two independent full pipeline runs (`python -m soil_simulator.phase96.pipeline`, ~9m20s each)
into separate scratch roots are **byte-identical across all 19 outputs**. The population hash
`9bb2f8fec93b17296051265745766503d5284bc774b1ff50aa022d76712c4124` reproduces exactly. The
only difference versus the committed `outputs/phase96_v0.9.6/` is `artifact_hashes.json`, and
the only differing entry within it is the drifted AUDIT-doc hash of §1. **The pipeline is
fully deterministic; the observed delta is post-hoc file drift, not a reproducibility
failure.**

## 3. Quality gates

| Gate | Result |
|---|---|
| `ruff format --check` | **pass** (107 files) |
| `ruff check` | **pass** (all checks) |
| `mypy --strict` | **pass** (106 source files, no issues) |
| **`pytest` (full suite)** | **FAIL — 1 failed / 213 passed** |
| RothC parity (`tests/parity/test_rothc_worked_example.py`) | **pass** |
| Carbon & phosphorus balance tests | **pass** (~15 `*_balances` tests green) |
| `python -m build` | **pass** (0.9.6 wheel + sdist via hatchling) |
| Installed-wheel smoke test | **pass** (imports, `phase96.pipeline` loads, CLI = 11 subcommands) |

The single failing test is
`tests/unit/test_phase96.py::test_source_and_artifact_hash_manifests_replay_offline` — it
asserts every file matches its recorded hash and trips on exactly the AUDIT-doc drift of §1.
**This is a currently-failing repository integrity gate, not a benign warning.** It is trivial
to fix (re-freeze the hash or revert the doc edit), but as the checkout stands, the suite is
red.

---

## 4. Reassessment of the original v0.9.0 findings

Full evidence and file/line citations are in `audit_closure_matrix_independent.csv`.

| ID | Finding (v0.9.0) | Independent status |
|---|---|---|
| **C1** | Population is bounded perturbation of hand-authored seeds; not empirically grounded | **Substantially addressed** |
| **C2** | Stock "predictability" is persistence of an observable initial condition (circularity) | **Closed** |
| **M1** | Phosphorus is top carbon "intervention" (structural loop); emissions blind to induced carbon | **Partially addressed** |
| **M2** | Cost/emissions horizon-invariant lump sums & policy-identity lookups | **Closed** |
| **M3** | `no_till` byte-identical to `baseline`; "7-policy" benchmark is really 6 | **Closed** |
| **M4** | No global sensitivity, no calibration, no external multi-decade validation | **Partially addressed** |
| **M5** | Synthetic generator covariance is designed, not estimated | **Substantially addressed** |

- **C2 (closed).** Headline ML targets are now paired intervention-minus-baseline effects
  (`delta_*`, spanning zero), with stocks, deterministic cost and emissions explicitly
  excluded. The circularity mechanism is removed from the reported skill claim.
- **M2 (closed).** Cost/emissions now scale with horizon via recurring events
  (conventional_tillage 140/350/700 GBP at 24/60/120 m; event_count 2/5/10) and separate
  operational from partial-lifecycle emissions; the deterministic targets are excluded from ML.
- **M3 (closed).** `no_till` was detected as a biological duplicate of `baseline`
  (shared digest `3dd8ddfa…`) and removed; the benchmark uses 6 distinct policies.
- **C1 (substantially addressed).** Real 56-location paired grounding replaces the 10 seeds,
  and the authored covariance factor is disabled — but it is a small, non-representative,
  GB-wide pilot (no arable land-use filter; Wales/Scotland uplands included), and 112 fields =
  56 effective locations.
- **M5 (substantially addressed).** The authored shared Gaussian soil factor is genuinely
  disabled (`soil_shared_factor_sd = 0`, generator shared = 0), so covariance is inherited
  from real anchors — but residual clay/SOC couplings remain hand-imposed, no covariance
  matrix is explicitly estimated-and-sampled, the "empirically_estimated" flag is a hardcoded
  label, and two shipped docs contradict each other on this point.
- **M1 (partially addressed).** Phosphorus is excluded from every headline ranking and given a
  partial-lifecycle emissions proxy, but the underlying uncalibrated P→NPP→residue→SOC loop is
  unchanged — managed by exclusion, not resolved.
- **M4 (partially addressed).** Global sensitivity, calibration and multi-decade validation
  now all exist, but each is quality-limited (see §§5–7).

**No original finding is *unresolved-as-stated*, and none is *replaced by a new issue* of
equal severity.** The remediation moved every finding in the right direction. The residue is
concentrated in M1/M4 and in a set of new, lower-severity issues surfaced below.

---

## 5. Empirical pilot

- **Paired real records — confirmed.** All 56 accepted locations have both a real SoilGrids
  soil record and a real NASA POWER climate record (240 monthly rows each); the soil and
  climate location sets are identical.
- **Rejections — genuine.** 8 of the pre-declared 64 (gb009/014/017/022/035/046/047/057) are
  rejected; each has null SoilGrids Q0.5 at every depth × property. The rejection is real
  missing-data handling, correctly coded (`empirical.py::_depth_values` raises, caught and
  recorded).
- **Harmonisation — byte-exact.** Depth thickness-weighting to 0–23 cm and unit conversion
  reproduce with 0.0 max abs error across all 56 × 9 harmonised columns.
- **Caveats.** (i) SoilGrids texture has a large closure gap before renormalisation (clay+silt+
  sand mean 90.7%, max gap 28.5 pp, 21/56 > 10 pp) — a genuine soil-input data-quality caveat.
  (ii) NASA POWER/MERRA-2 substitutes for the intended ERA5-Land without a plain disclosure;
  PET is a Thornthwaite temperature-only surrogate (A080). (iii) Provenance labels "v10" /
  "SoilGrids 2.0" rest on request URLs, not returned metadata.
- **Population support — insufficient as independent evidence.** 112 fields = 56 locations ×
  ~2 clones; test = 11 locations/26 fields, OOD = 4 locations/6 fields. Grouping is clean
  (0/56 leakage), but this cannot carry a population-level empirical claim.

## 6. Hoosfield reproduction

**Every reported number reproduces exactly**, both by running the repo's validation code and
by independent recomputation from the trajectories CSV:

| Metric | Reported = Recomputed |
|---|---|
| Phase 9.5 aggregate MAE / RMSE / bias | 8.518 / 10.154 / −8.360 |
| Source-corrected aggregate MAE / RMSE / bias | 3.657 / 4.340 / −0.528 |
| Calibration best factors | plant_residue 0.85, fym_carbon 1.10 |
| Held-out temporal MAE / RMSE / bias | 1.5158 / 1.8848 / 0.4975 |
| Held-out cessation MAE / RMSE / bias | 7.2142 / 7.5771 / −7.2142 |

- **The forcing "correction" is a valid source correction, not tuning.** The replacement
  `OFFICIAL_*` forcing vectors are byte-identical to the Rothamsted-bundled `RothC_input.dat`
  in the verified v2.1.1 zip, applied uniformly to all treatments and splits, with RothC
  constants untouched. This alone takes aggregate RMSE 10.154 → 4.340 and bias −8.360 → −0.528.
- **No calibration leakage.** The grid fit uses only unfertilised + annual-FYM points at
  year ≤ 1965; post-1965 and the entire cessation treatment are genuinely held out. Verified
  in code and in the CSV role assignments.
- **Boundary solution (red flag, honestly surfaced).** `fym_carbon_factor = 1.10` sits exactly
  on its `[0.90, 1.10]` upper bound, and the whole within-10% near-optimal band is pinned at
  the ceiling. The FYM factor is set by the imposed cap, not the data — the fit is not
  identified in the FYM direction. The repo flags this via `boundary_solution: True`.
- **Cessation genuinely fails** (MAE 7.21, one-sided bias −7.21) and is honestly retained as a
  failure. The uncalibrated model does not reproduce observed FYM-treatment stock accumulation.

## 7. Sensitivity analysis

- **Morris — correct.** Textbook elementary-effects screening: proper trajectories, random
  order, Δ = 1/(levels−1), unit-hypercube normalisation, correct μ/μ*/σ.
- **Sobol — correct estimators, wrong sampler, underpowered.** The Saltelli/Jansen estimator
  forms are right, but the design matrices are drawn with a plain PRNG (`random.random`), not a
  low-discrepancy Sobol sequence, at N = 32 (224 evaluations). Consequence: **25% of
  first-order indices are impossibly negative** (min −0.425), first-order max 1.40 and
  total-order max 2.10 both exceed 1. The large "interaction" fractions are estimator noise,
  not real interactions.
- **"Convergence" 0.840 / 0.760 is mislabelled.** These are nested-subsample self-consistency
  scores — the "half sample" is byte-identically the first half of the full sample (same seed).
  This measures internal stability, not independent-replication convergence, and shared bias
  inflates the agreement. **0.760 does not support any quantitative Sobol variance partition or
  a "stable Sobol ranking" claim.**
- **What the analysis *does* support.** The one robust result is the Morris-level intervention
  ranking: **farmyard manure is the stable policy winner (94–100% of draws)** across every
  headline target and horizon. That claim is independently reproduced and defensible; the
  quantitative Sobol partition is not.
- The Phase 9.5→9.6 drop (0.982 → 0.760) is expected and honest — moving from one field / 12
  parameters to a 56-location population with location and weather as dominant global factors
  is a harder problem at the same tiny N.

## 8. Revised population

- **M5 fix is real.** Authored shared factor disabled in config and code; covariance inherited
  from 56 real anchors. AMF and phosphorus latent priors confirmed **separate** (sampled from
  fixed priors, absent from ML features). Split isolation clean (0/56 locations in >1 split).
- **But "estimated covariance" is overstated.** It is anchor-inheritance plus hand-imposed
  clay_shift/SOC couplings; correlations are systematically attenuated vs empirical (mean
  |Δ| 0.044, max 0.156); the "empirically_estimated" flag is a hardcoded label; and
  `SYNTHETIC_POPULATIONS.md` ("designed, not estimated") directly contradicts
  `PHASE96_EMPIRICAL_GROUNDING.md` ("estimated only from paired empirical records"). The docs
  should be reconciled.
- **Extrapolation limits.** Confined to temperate GB arable, 56 effective locations. The repo's
  own provenance is honest that "synthetic success is not field validation."

## 9. Effect-only ML & the stop decision

The entire benchmark was re-implemented from `effect_only_dataset.csv` and **every gate number
reproduces to 4 decimals**.

- **Construction is sound.** Targets are paired effects (not stocks); features are
  observable-only (latent priors excluded); preprocessing is train-isolated; alpha selected on
  validation; intervals from validation quantiles.
- **The failed gates are genuine.** `all_effect_targets_beat_policy_mean = False` and
  `all_effect_targets_have_acceptable_ood = False` are both driven by a single target,
  `delta_yield_t_dm_ha|24`: ridge test RMSE 0.0555 vs policy-mean 0.0550 (loses by 0.9%), and
  OOD RMSE 0.0697 > 1.10 × 0.0619 tolerance (12.6% worse). The SOC/respiration effect targets
  *do* beat the policy mean (by 4–10%). Note the **policy-mean baseline is itself very strong**
  (R² ≈ 0.94–0.99 on the SOC targets) — the effect signal is largely a low-variance function of
  policy identity, so "beating the policy mean" is a demanding but narrow bar.
- **Stopping downstream selection was required and is justified.** At least one predeclared
  gate genuinely fails on the data, `downstream_selection_executed = False`, no selector/oracle/
  regret benchmark was run, and publication is correctly refused (fail-closed). This is the
  right call.
- **Three gates are defective (mechanism, not outcome).**
  1. `empirical_location_leakage_check` is a **hardcoded literal `True`** (effect_ml.py L314),
     never computed — fail-open. Data is coincidentally leak-free (independently verified), so
     the value is correct today, but a real leak would still report `True`.
  2. `independent_empirical_effect_validation` is a **hardcoded literal `False`** (L306) that
     makes `all_gates` structurally unpassable regardless of model quality — an intentional
     fail-closed constant, but a constant, not a validation.
  3. `all_effect_targets_have_calibrated_uncertainty = True` is a **weak check**: a permissive
     0.80–1.00 acceptance band on a 90% interval, under which **6 of 7 targets under-cover the
     nominal** (test coverage 0.865–0.885; only `protected_soc|60` = 0.913 meets 0.90), and OOD
     coverage is computed but never gated. Passing it is not evidence of nominal calibration.

  Net: the pipeline reaches the correct conservative conclusion through a mix of sound and
  decorative gates. The conclusion is safe; the gate *machinery* should not be cited as
  evidence of rigour without these caveats.

---

## 10. Publication readiness by paper type

The repository's own verdict — **not publication ready, do not start manuscript drafting** — is
correct. Assessed per intended paper type:

### (a) Validated agricultural prediction paper — **NOT SUPPORTED**
This is the strongest claim and the least supported. There is **no field validation of
intervention effects**; the effect ML is trained and tested entirely on simulator output; the
only real-world SOC comparison (Hoosfield) *fails* on the FYM/cessation treatments and relies
on a boundary-solution calibration. The empirical pilot grounds *inputs* (soil/climate
distributions), not *effects*. **Critical blockers:** independent empirical effect validation
against real paired trials; a Hoosfield FYM treatment that does not fail; a representative,
land-use-filtered arable sample. Do not attempt.

### (b) Synthetic / methodological paper — **CLOSEST TO SUPPORTABLE, with fixes**
A paper whose claim is *"a disciplined, fail-closed methodology for building a leakage-controlled
synthetic soil-carbon benchmark and honestly refusing to over-claim"* is defensible in outline:
determinism is exact, leakage controls are genuine, the effect/stock distinction is correctly
enforced, and the stop decision is principled. **Major blockers before submission:** (i) replace
the underpowered PRNG-sampled Sobol with a proper low-discrepancy design at adequate N, or drop
the Sobol variance partition and report Morris screening only; (ii) relabel "convergence" as
nested-subsample stability; (iii) replace the two hardcoded gate literals with real computed
checks and strengthen the uncertainty gate to a true nominal-coverage test; (iv) reconcile the
contradictory covariance docs and soften "estimated covariance" to "anchor-inherited +
partly imposed." These are correctness-of-method issues a methods reviewer will catch.

### (c) Simulator / software paper — **SUPPORTABLE, with minor fixes**
The mechanistic core is strong: RothC parity reproduced exactly, carbon and phosphorus mass
balance enforced (residuals ~1e-14), clean typing/lint, deterministic offline pipeline,
machine-readable provenance and hashes. A software/tools paper describing the simulator and its
reproducibility infrastructure is close to ready. **Blockers (all minor/mechanical):** fix the
red integrity test (re-freeze the AUDIT-doc hash), fix the three defective gates so the
software's own quality claims are honest, reconcile the docs. No scientific blocker.

### (d) Portfolio / case-study write-up — **SUPPORTED NOW**
As an honest case study of *finding and remediating* audit findings — with the negative results
(FYM failure, failed prediction gates, refusal to publish) as the point — the material is
already sufficient and unusually candid. This is the one form that can be written today, and it
should foreground the negatives, not bury them.

---

## 11. Remaining critical / major analyses before publication

**Critical (block the agricultural-prediction paper entirely):**
1. Independent empirical validation of *intervention effects* against real paired field trials
   (the current pilot validates inputs, not effects).
2. Resolve the Hoosfield FYM/cessation failure without a boundary-solution calibration.

**Major (block the methodological and software papers):**
3. Re-run Sobol with a genuine low-discrepancy sampler at adequate N, or remove the Sobol
   partition; relabel "convergence."
4. Replace the two hardcoded gate literals (`empirical_location_leakage_check`,
   `independent_empirical_effect_validation`) with real computed checks; strengthen the
   uncertainty gate to a nominal-coverage test that also gates OOD coverage.
5. Fix the red offline-replay integrity test (re-freeze the AUDIT-doc hash or revert the edit).
6. Reconcile the contradictory covariance documentation; restate "estimated covariance" as
   "anchor-inherited plus partly hand-imposed."

**Minor (disclosure hygiene):** state the ERA5-Land→NASA POWER substitution plainly; document
the SoilGrids texture-closure renormalisation as a data-quality caveat; correct the "v10" /
"SoilGrids 2.0" provenance labels to what the raw files actually assert; state "112 fields = 56
effective locations."

---

## Final verdict

**Phase 9.6 is a scientifically honest, reproducible, and correctly self-limiting piece of
work. Its central conclusion — that the evidence does not yet support a predictive
agricultural claim, and that manuscript drafting should not begin — is independently confirmed
and should be upheld.** Every headline metric reproduces exactly; the v0.9.0 criticals are
closed (C2) or substantially addressed (C1); the majors are closed (M2, M3) or moved
materially forward (M1, M4, M5).

It is **not** publication-ready as a validated prediction paper and must not be presented as
one: there is no empirical validation of effects, the one real-world SOC test fails on FYM, and
that failure is only masked by a boundary-solution calibration. It is **closest to ready as a
software/simulator paper** and **plausibly ready as a methodological paper** once the
underpowered Sobol, the three defective gates, and the contradictory documentation are fixed —
and it is **already sufficient as an honest remediation case study**. One live defect must be
fixed regardless of paper type: the repository's own offline-replay integrity test is currently
failing because the v0.9.0 audit document was edited after its hash was frozen.

**Recommendation:** do **not** begin drafting a predictive agricultural manuscript. A
simulator/software paper or a methodological paper is a defensible target *conditional on* the
§11 major fixes; the remediation case study can be written now. Under no framing should the
synthetic effect-prediction results be reported as evidence about real fields.
