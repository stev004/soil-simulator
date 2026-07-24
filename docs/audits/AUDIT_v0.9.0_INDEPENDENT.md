# Independent Audit — `soil_simulator` v0.9.0

**Scope:** soil–plant–AMF synthetic-field simulator and ML/selection benchmark.
**Constraint honoured:** no files modified; findings not softened.
**Method:** direct reading of source, config, docs and outputs; independent
re-computation of the RothC parity, the Phase 9 regret/abstention aggregation,
and the circularity/target-structure claims; full test-suite execution.

All 194 tests pass (`pytest -q` → `194 passed, 62 warnings in 43.75s`; warnings
are benign — Hypothesis in-memory DB fallback and a `.pytest_cache` write
blocked by the read-only mount).

---

## Headline judgement

This is an unusually disciplined and self-critical codebase. Three things I
independently reproduced **exactly**:

1. **RothC core** matches the official executable release (Coleman, Milne &
   Prout 2024; RothC_Py v1.0.0). My from-scratch Hoosfield Jan-1852 recompute:
   DPM 0.1139371278, RPM 4.4454477169, BIO 0.6651053396, HUM 25.8551050324,
   CO₂-C 0.0836047833 — matches the documented parity table to <1e-4.
2. **Phase 9 regret/abstention** — reproducing the code's nested aggregation
   (per run×profile×method, then median across profile groups, on *unnormalised*
   `utility_regret`) gives the frozen-report numbers to the digit: final
   `observable_ml` worst-decile 0.1792 / catastrophic 0.04 / exact-match 0.84 /
   abstain 0.1267; uncertainty variants strictly worse (worst-decile 0.6452 /
   1.6921 / 1.7466). The gate
   `uncertainty_aware_reduces_worst_decile_or_catastrophic_regret = False` and
   the overall `passed = False` are genuine and correctly computed.
3. **Mass balance** — max monthly residuals 5.68e-14 t C/ha and 1.42e-14 kg
   P/ha; per-step and cumulative C and P balances are enforced with
   `MassBalanceError` on exceedance.

The negative Phase 9 conclusion ("do not continue recommendation-system
development") is well-supported by the artifacts and is not overstated.

The findings below are therefore **not** "the results are wrong." They are:
(a) a small number of **structural circularities and accounting asymmetries**
that inflate apparent ML performance and shape the intervention ranking, most
of which the repo discloses but does not fully neutralise; and (b) the
**missing analyses** a defensible paper would require.

---

## CRITICAL

### C1 — The "population" is bounded perturbation of 10 hand-authored seeds and 20 fabricated weather-years; it is not empirically grounded
- **Evidence:** `data/processed/phase7_empirical_seed_fixture_v1.yaml` contains
  exactly 10 seed records (`east-01/02`, `midlands-01/02`, `north-01/02`,
  `southeast-01/02`, `west-01/02`) and 20 complete weather-years (2 per region ×
  5 regions, `source_year` 2018/2019). `provenance:` states outright: "values
  are traceable test/demo records, not a national survey or field validation
  dataset" and "no network access or silent download". `src/soil_simulator/
  population/generator.py` builds all 250 fields by additive-log-ratio texture
  perturbation + a shared Gaussian soil factor + bounded residuals around those
  10 seeds.
- **Why critical:** every downstream result — the ML benchmark, the Phase 9
  regret distribution, the "population variation" plots — is a property of a
  synthetic generator seeded by 10 authored rows, not of UK arable soils. The
  `SYNTHETIC_POPULATIONS.md` §2 references (SoilGrids, ERA5-Land, the 2026 AMF
  mycelial dataset, Rothamsted e-RA) are **intended production sources**, not
  what is wired in.
- **Disclosure status:** disclosed (assumption A039; `SYNTHETIC_POPULATIONS.md`
  §"Remaining scientific limitations"). The finding is that the disclosure is
  easy to lose against the volume of "250-field population" framing elsewhere.
- **Files:** `data/processed/phase7_empirical_seed_fixture_v1.yaml`;
  `src/soil_simulator/population/generator.py`;
  `docs/SYNTHETIC_POPULATIONS.md`; `docs/ASSUMPTIONS_REGISTER.csv` (A039).

### C2 — Stock-level "predictability" is largely persistence of an observable initial condition (circularity)
- **Evidence (independently computed on `outputs/phase85_v0.8.5/
  training_dataset_v0.8.5.csv`, 5,250 rows):**
  - Initial protected-SOC proxy is essentially a deterministic function of two
    **observable** features: regressing `initial_protected_soc_proxy` on
    `1 + baseline_soc + clay` gives **R² = 0.99902**; the proxy is ~0.748 ×
    baseline SOC (sd 0.014) by construction of the linear RothC spin-up
    (`src/soil_simulator/population/spinup.py` scales the converged periodic
    state to target SOC).
  - Final total SOC at 120 months correlates **0.998** with `baseline_soc`
    (`final ≈ 0.835 × baseline`, sd 0.020).
- **Why critical:** any model given `baseline_soc` (which is in the 28-feature
  observable set) will show very high R² on *stock* targets
  (`final_total_soc`, `initial/final protected_soc_proxy`) with no biological
  learning — the target is ~85% the input. If stock-target R² is ever cited as
  evidence of surrogate quality, it is misleading.
- **Mitigation already in place:** the Phase 9 selection benchmark evaluates
  **paired intervention effects and oracle regret**, not stock levels, and the
  docs state "good final SOC stock prediction does not imply good
  intervention-effect prediction." So the *headline* Phase 9 conclusion is not
  contaminated by this. The residual risk is presentational and applies to any
  stock-level R² reporting (Phase 8/8.5 tables).
- **Files:** `src/soil_simulator/population/spinup.py`;
  `src/soil_simulator/ml/dataset.py` (observable registry);
  `outputs/phase85_v0.8.5/training_dataset_v0.8.5.csv`.

---

## MAJOR

### M1 — Phosphorus fertiliser is the top carbon-sequestration "intervention," a structural loop artifact, and its emissions proxy ignores the induced carbon
- **Evidence:** mean `delta_final_total_soc` @120m by policy (independently
  computed): phosphorus **+0.782**, farmyard_manure +0.443, cover_crop +0.159,
  reduced_tillage −0.008, conventional_tillage −0.120, no_till/baseline 0.000.
  The phosphorus policy is a bare +20 kg P/ha stock addition
  (`config/scenarios/management_scenarios.yaml` L212–224) with
  `emissions_proxy_kg_co2e_ha: 20`. That +0.78 t C/ha ≈ **+2.86 t CO₂e/ha** of
  modelled soil-carbon gain, driven purely by the P-stress → NPP → residue →
  DPM/RPM → SOC loop, is credited against a flat 20 kg CO₂e emissions proxy that
  does not represent P manufacture, N₂O, or the induced-carbon accounting.
- **Why major:** P as the best carbon practice is a model implication of an
  uncalibrated stress→growth coupling, not an agronomic finding; the
  cost/emissions ledger cannot see it, so any utility profile weighting
  emissions will still rank P highly. Direction may be defensible; the
  **magnitude and ranking are artifacts.**
- **Files:** `config/scenarios/management_scenarios.yaml`;
  `src/soil_simulator/processes/plant.py`, `phosphorus.py`;
  `outputs/phase85_v0.8.5/training_dataset_v0.8.5.csv`.

### M2 — Cost and emissions are horizon-invariant lump sums and pure functions of policy identity
- **Evidence:** `intervention_cost_gbp_ha` is **identical across the 24/60/120-
  month horizons** for every policy (e.g. conventional_tillage = 140 at all
  three horizons; phosphorus = 30; FYM = 80). Cost and emissions each take
  exactly **one value per policy** across all 5,250 rows.
- **Two consequences:**
  1. A 10-year SOC/yield benefit is weighed against the **same** fixed cost as
     a 2-year benefit — benefits accrue with horizon, costs do not. This
     asymmetry flatters long-horizon cost-effectiveness.
  2. 2 of the 7 base objective targets (`intervention_cost`,
     `emissions_proxy`) are **trivial policy-identity lookups** — an ML model
     "predicting" them is doing a dictionary read, which inflates aggregate
     multi-target skill statistics if those two are pooled with the genuine
     targets.
- **Files:** `config/scenarios/management_scenarios.yaml` (per-event
  `cost_gbp_ha`/`emissions_proxy_kg_co2e_ha`);
  `outputs/phase85_v0.8.5/training_dataset_v0.8.5.csv`.

### M3 — `no_till` is byte-identical to `baseline`; the "7-policy" benchmark is effectively 6 interventions
- **Evidence:** across all 250 fields, `no_till` vs `baseline` max abs
  difference is **0.0** for both `final_total_soc` and `crop_yield`. The
  no_till effect parameters are all null-defaults (pulse mortality 0.0, turnover
  mult 1.0, decomp mult 1.0; `config/model_defaults.yaml`;
  `management_scenarios.yaml` L171–184 "A009 explicit no-effect defaults").
- **Why major:** no_till contributes no test signal, yet it counts as a
  distinct policy in eligibility, selection and regret. It inflates apparent
  policy diversity and the oracle's choice set with a duplicate of baseline.
- **Files:** `config/model_defaults.yaml`;
  `config/scenarios/management_scenarios.yaml`.

### M4 — No global sensitivity analysis, no calibration, no external validation (missing analyses for a defensible paper)
- **Evidence:** `docs/MODEL_SPEC.md` explicitly calls for parameters (e.g. AMF
  turnover) to be "run through global sensitivity analysis"; none exists in
  `outputs/` or `tests/`. The repo itself lists as open: "latent biological
  priors can dominate simulated intervention effects" (`SYNTHETIC_POPULATIONS.md`),
  and 7 critical-priority provisional assumptions remain uncalibrated (A007,
  A009, A016, A021, A035, A045, A060). There is no comparison of simulated SOC
  trajectories against the Rothamsted long-term experiments beyond the single
  one-step RothC parity.
- **What a paper needs:** (i) global (Sobol/Morris) sensitivity of the effect
  targets to the latent priors, to show the ranking is not an artifact of A009/
  A016/A021/A045; (ii) at least one multi-decade SOC trajectory validated
  against Hoosfield/Broadbalk; (iii) a calibration or explicit "no-calibration"
  ablation quantifying how much of the effect signal is prior-driven.
- **Files:** `docs/MODEL_SPEC.md`; `docs/ASSUMPTIONS_REGISTER.csv`;
  `docs/VALIDATION_PLAN.md`.

### M5 — The synthetic generator's joint covariance is *designed*, not estimated — any ML skill partly reflects learning the generator
- **Evidence:** `SYNTHETIC_POPULATIONS.md` ("Perturbation covariance is
  designed, not estimated from residual data"; A045) and `generator.py` (a
  hand-set shared Gaussian soil factor inducing SOC–CEC–N and SOC–bulk-density
  couplings). The ML models see feature relationships that were authored, not
  observed.
- **Why major:** out-of-sample skill on this population is partly a measure of
  how well the model recovers the generator's own design, which does not
  transfer to real fields. This compounds C1.
- **Files:** `src/soil_simulator/population/generator.py`;
  `docs/ASSUMPTIONS_REGISTER.csv` (A045).

---

## MINOR

### m1 — RothC parity is partially self-referential
The Hoosfield parity test inverts the temperature modifier to recover a
combined rate modifier (a≈0.3561) and assumes fully wet, bare forcing (b=c=1)
because the source does not report January 1852 weather components (self-flagged
in `CARBON_CORE.md`). The <1e-4 agreement is real but demonstrates *arithmetic
fidelity of the decay step*, not that the environmental modifiers are correct
for that month. **File:** `tests/` RothC parity test; `docs/CARBON_CORE.md`.

### m2 — AMF necromass DPM/RPM routing borrows the crop 1.44 ratio
`necromass_to_dpm` 0.5016 / `necromass_to_rpm` 0.3484 come from applying the
established RothC crop DPM:RPM ratio to the non-protected 0.85 share (A021). The
code and `AMF_EXTENSION.md` state plainly this "is not an observed
fungal-necromass partition"; See et al. (2021) supports fast/slow fractions but
not these values. **File:** `config/model_defaults.yaml`;
`src/soil_simulator/processes/amf.py`.

### m3 — Several provisional biological constants carry wide, uncalibrated ranges
AMF CUE 0.45 (range 0.30–0.65; the cited synthesis "supports a CUE formulation
but not this universal value"), turnover 1.0/month (0.1–6.0),
necromass_stabilisation 0.15 (0.02–0.50), FYM P content 5.0 kg P/t C (A026),
allocation 0.062 (0.02–0.20). All are honestly classified, but the effect
targets inherit their uncertainty and no sensitivity run bounds it (see M4).
**File:** `config/model_defaults.yaml`; `docs/ASSUMPTIONS_REGISTER.csv`.

### m4 — The uncertainty machinery never met nominal coverage, and Phase 9 confirms it hurts
Historical Phase 8 conformal coverage was ~56% against a 90% nominal target;
Phase 9 shows all three uncertainty-aware variants **worsen** worst-decile and
catastrophic regret (catastrophic 12.83% / 35.33% / 46.0% vs 5.5% for plain
observable_ml). This is correctly reported and is the basis of the gate failure
— noted here only so a reader does not mistake "uncertainty-aware" for "safer."
**File:** `outputs/phase9_v0.9.0/frozen_final_evaluation_report.json`;
`docs/ML_BENCHMARKING.md`.

### m5 — Spin-up assumes periodic climate and equilibrium historical input
`spinup.py` scales a converged unit-input periodic state to target SOC (A035),
assuming the field sits at RothC equilibrium under a repeating 2-year weather
block. Real fields are rarely at equilibrium; this bakes a smooth,
texture-determined initial pool structure into every field (feeds C2). **File:**
`src/soil_simulator/population/spinup.py`.

---

## Dimension-by-dimension verdict

| # | Dimension | Verdict |
|---|-----------|---------|
| 1 | Equations vs cited sources | **Faithful.** RothC parity reproduced exactly; AMF/P/plant equations match `AMF_EXTENSION.md` and cited M-M / CUE forms. |
| 2 | Unsupported parameters/relationships | **Honestly flagged, not hidden.** All non-RothC constants are provisional priors with citations + ranges. Residual risk: no sensitivity bounding (M4); P→carbon coupling drives an implausible ranking (M1). |
| 3 | Carbon & phosphorus accounting | **Mechanistically sound** (residuals ~1e-14, balances enforced). **But** cost/emissions ledger is horizon-invariant and blind to induced carbon (M1, M2). |
| 4 | Synthetic-population realism | **Weakest link.** 10 authored seeds + 20 fabricated weather-years; designed (not estimated) covariance (C1, M5). |
| 5 | Leakage & circularity | **Leakage controls are genuine and enforced** (group isolation, train-only preprocessing, mandatory abstention preserved, 0 unsupported non-abstaining selections). **Circularity is the real issue** — protected/stock targets are near-deterministic in observables (C2). |
| 6 | ML benchmark validity | **Valid for effect targets; inflated for stock/cost/emissions targets.** Ridge legitimately wins; no gate requires nonlinear to beat it. Trivial targets (M2) and stock persistence (C2) should be excluded from any skill headline. |
| 7 | Phase 9 regret & abstention | **Reproduced exactly; conclusions correct and not overstated.** Uncertainty-aware variants genuinely worsen tail regret; gate fail is real. |
| 8 | Claim-boundary justification | **Strong and consistent.** "No field validation," "model proxy not MAOC," "verification ≠ validation" repeated accurately throughout. The one gap: derived rankings (M1) and the stock-vs-effect distinction (C2) can still mislead a casual reader. |
| 9 | Missing analyses | **Global sensitivity analysis, calibration, and external multi-decade validation are absent** and required before publication (M4). |

---

## Recommended actions before this is a defensible paper
1. Global sensitivity analysis of the **effect** targets against the latent
   priors (A007, A009, A016, A021, A045); show the intervention ranking is
   stable (addresses M1, M4, M5).
2. Validate at least one multi-decade SOC trajectory against Hoosfield/
   Broadbalk, not just the single-step parity (M4).
3. Replace or supplement the 10-seed fixture with a documented real extraction,
   or restate every population-level result as "generator behaviour" (C1).
4. Report ML skill **only on paired effect targets**; drop `intervention_cost`/
   `emissions_proxy` (lookups) and stock levels (persistence) from any headline
   skill metric (C2, M2).
5. Make cost/emissions horizon-dependent and give the P intervention an
   induced-carbon-aware emissions treatment (M1, M2).
6. Either parameterise `no_till` distinctly or drop it (M3).
