# Sensitivity methods evidence extraction

## Policies and outputs

The corrected Phase 9.7 artifact retains exactly four policies: `conventional_tillage`, `reduced_tillage`, `cover_crop`, and `farmyard_manure`. Source: `src/soil_simulator/phase97/pipeline.py:37-39` (`HEADLINE_POLICIES`); confirmed by `outputs/phase97_v0.9.7/sensitivity_first_total.csv` (`policy_id`).

The general Phase 9.6 evaluator stores effects for five interventions (the four above plus phosphorus): yield at 24 months; NPP, residue C, respiration, total SOC and protected-SOC proxy at 60 and 120 months. This is 11 target-horizon outputs per policy. Source: `src/soil_simulator/phase95/analysis.py:278-319` (`sensitivity_evaluator`); confirmed by `outputs/phase96_v0.9.6/sensitivity_results.csv`.

The corrected Phase 9.7 filter retains seven target-horizon outputs per four policies: yield at 24; total SOC, protected-SOC proxy and respiration at 60 and 120, for 28 output keys. NPP/residue and phosphorus policy outputs are not retained in the corrected artifact. Source: `src/soil_simulator/phase97/pipeline.py:40-49,117-123` (`HEADLINE_TARGETS`, `_retained_output`).

## Morris population-aware screen

Phase 9.6 Morris uses seed 960021, 6 trajectories and 6 levels. The unit-space step is Δ=1/(levels-1)=0.2. Each trajectory begins independently on levels 0 through 4, randomly permutes factor order, increments each factor by Δ, and calculates elementary effect ([Y(x+Δe_i)-Y(x)]/Δ). Reported summaries are μ, μ* (mean absolute effect), and population SD σ. Sources: `config/phase96/sensitivity.yaml:1-6`; `src/soil_simulator/phase95/sensitivity.py:132-181` (`morris_screen`).

All 15 factors and transforms are: empirical location index discrete 0-55; weather-resample index discrete 0-9; spin-up pool blend uniform 0-1; allocation scaled Beta(2,8) 0.02-0.20; CUE triangular 0.30-0.65 mode 0.45; turnover log-uniform 0.1-6; necromass stabilisation scaled Beta(2,5) 0.02-0.50; P Vmax triangular 0.2-3 mode 1; P half-saturation log-uniform 2-40; tillage AMF mortality triangular 0-0.60 mode 0.25; tillage decomposition uniform 1-2; cover NPP uniform 0-0.50; cover root fraction uniform 0.30-0.80; FYM P content uniform 0-30; schedule interval discrete 12-36. Source: `config/phase96/sensitivity.yaml:7-22`.

Uniform is `min+q(max-min)`; discrete is `round(min+q(max-min))`; log-uniform is `exp(log(min)+q log(max/min))`; triangular uses the analytic inverse CDF; scaled integer-parameter beta uses a 60-iteration bisection inverse CDF. Source: `src/soil_simulator/phase95/sensitivity.py:31-81` (`SensitivityParameter.transform`, `_inverse_integer_beta`).

The round-based discrete transform gives endpoints half the unit-interval width of interior integers. The repository audit labels this low severity but gives no rationale for choosing it. Classification: `NOT_DOCUMENTED`. Source: `docs/audits/phase97_sobol_findings.md:41-48`; implementation: `src/soil_simulator/phase95/sensitivity.py:36-38`.

## Corrected Sobol design and estimators

The selected five factors are empirical location 0-55, weather index 0-9, schedule interval 12-36, tillage decomposition multiplier 1-2, and FYM P content 0-30. Source: `config/phase97/sensitivity.yaml:3-10`; full transform metadata: `outputs/phase97_v0.9.7/sobol_sampling_manifest.json` (`parameter_order`, `transforms`).

One scrambled `scipy.stats.qmc.Sobol` design of dimension 10 (=2D) with seed 970021 is generated at N=1024 and split column-wise into A and B. Nested prefixes N=128,256,512,1024 are used. For D=5, each size evaluates A, B and five A_B(i) hybrids: N(D+2)=7N = 896,1792,3584,7168 evaluations. Source: `src/soil_simulator/phase97/sensitivity.py:117-128,406-483`; `config/phase97/sensitivity.yaml:1-13`; `outputs/phase97_v0.9.7/sobol_sampling_manifest.json`.

With (V=Var([Y_A,Y_B])) using population variance,

\[
S_i=\frac{mean[Y_B(Y_{AB_i}-Y_A)]}{V},\qquad
S_{Ti}=\frac{mean[(Y_A-Y_{AB_i})^2]}{2V}.
\]

Negative finite-sample estimates are retained. Source: `src/soil_simulator/phase97/sensitivity.py:143-155,164-233` (`_variance`, `_one_estimate`, `estimate_indices`).

For each N, 200 bootstrap index vectors (I_b=(i_{b1},\ldots,i_{bN})) are drawn with replacement from ({0,\ldots,N-1}) using NumPy RNG seed `970021+N`; A, B and every corresponding hybrid are indexed by the same (I_b). The two formulas above are recomputed on each indexed sample to obtain (S_i^{(b)},S_{Ti}^{(b)}). The reported central 95% interval is ([Q_{0.025}({S^{(b)}),Q_{0.975}({S^{(b)})]), using NumPy's linear quantile interpolation. Sources: `config/phase97/sensitivity.yaml:10-12`; `src/soil_simulator/phase97/sensitivity.py:158-209,475-483`.

The convergence decision compares each nested size with its predecessor; the final decision uses 512 versus 1024 and requires maximum absolute S1/ST change ≤0.10, both Spearman rank correlations ≥0.90, mean CI width ≤0.20, and unstable estimate fraction ≤0.10. Source: `src/soil_simulator/phase97/sensitivity.py:246-349`; `config/phase97/sensitivity.yaml:14-18`.
