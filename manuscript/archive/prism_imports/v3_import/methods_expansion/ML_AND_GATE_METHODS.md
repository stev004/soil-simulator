# Machine-learning and gate evidence extraction

## Final benchmark models and preprocessing

The final Phase 9.6 benchmark imports, fits and evaluates only `RidgeModel` and `PolicyMeanModel`. No forest, boosted tree or other candidate is called by `prediction_benchmark`; older Phase 8.6 candidate lists are not evidence of final evaluation. Source: `src/soil_simulator/phase96/effect_ml.py:16,211-305`.

Headline rows exclude phosphorus and contain four policies in equal field-wise composition: conventional tillage, reduced tillage, cover crop and FYM. Source: `src/soil_simulator/phase96/effect_ml.py:23-29,83-120,213-215` (`POLICY_IDS`, `build_effect_rows`, `headline_eligible`).

Eleven numeric observable features are standardized by training-row population mean and population SD; zero-variance scales become 1. Five policy one-hot columns are appended. Means/scales are fit separately for each target-horizon using training rows only and reused unchanged for validation, test and OOD. Source: `src/soil_simulator/phase96/effect_ml.py:30-42,136-159,221-240` (`OBSERVABLE_FEATURES`, `_matrix_fit`, `_matrix_transform`).

Ridge alphas are evaluated in order `(0.1,1.0,10.0)`. Selection minimizes validation RMSE. Because replacement occurs only when `score < best_score`, exact ties retain the first value, i.e. the smallest alpha in this grid. Source: `src/soil_simulator/phase96/effect_ml.py:241-257` (`prediction_benchmark`).

## Exact final-benchmark split composition

Per primary target-horizon, train/validation/test/OOD contain 236/84/104/24 rows, 59/21/26/6 descendant fields, and 31/10/11/4 empirical locations. Each contains exactly one row per field for each of four policies (field counts per policy: 59/21/26/6). Across all seven primary target-horizons this is 1652/588/728/168 model rows. Source artifact: `outputs/phase96_v0.9.6/effect_only_dataset.csv`; filter and target loop: `src/soil_simulator/phase96/effect_ml.py:211-230`. Exact location assignments: `DATA_SPLIT_REGISTER.csv`.

The raw effect dataset also contains phosphorus rows, so unfiltered totals are 2065/735/910/210. Those phosphorus rows are not in the final benchmark. Source: `outputs/phase96_v0.9.6/effect_only_dataset.csv` (`headline_eligible`).

The target-level OOD pool is exactly all rows whose `population_split == weather_ood` for that target/horizon after headline filtering. It pools six descendants from four location groups across the four policies (24 rows). No archetype-OOD split is created because `archetype_ood_archetypes: []`; no cross-OOD concatenation occurs in the final code. Sources: `src/soil_simulator/phase96/effect_ml.py:227-274`; `config/populations/phase96_population.yaml:10-11`.

## Prediction, OOD and interval construction

For target (t), test pass is (RMSE_{ridge,t,test}<RMSE_{policymean,t,test}). The prediction gate is the conjunction over all seven primary target-horizons. Equality fails. Source: `src/soil_simulator/phase96/effect_ml.py:275-295,309-313`.

OOD pass is (RMSE_{ridge,t,OOD}\le1.10\,RMSE_{policymean,t,OOD}); the OOD gate is the conjunction over all targets. Equality passes. Source: `src/soil_simulator/phase96/effect_ml.py:277-296`.

For validation absolute residuals sorted (r_{(1)}\le\cdots\le r_{(n)}), half-width is (q=r_{(k)}), (k=\max[1,\min(n,\lceil0.90n\rceil)]). The same symmetric interval ŷ±q is applied to test and OOD. This is the implemented empirical quantile, not the finite-sample split-conformal `(n+1)` rank. Source: `src/soil_simulator/phase96/effect_ml.py:178-181,258-274` (`_quantile`).

## Binomial/Wilson coverage and abstention

For reported coverage (c) and (n) rows, successes are (s=clip(round(cn),0,n)). With (p_0=0.90),

\[
F(k;n,p_0)=\sum_{j=0}^{k}{n\choose j}p_0^j(1-p_0)^{n-j},\quad
L=\min\{k:F(k;n,p_0)\ge0.025\},\quad
U=\min\{k:F(k;n,p_0)\ge0.975\}.
\]

The count passes when (L\le s\le U). Source: `src/soil_simulator/phase97/gates.py:288-307,346-350` (`_binomial_acceptance_counts`).

With \hat p=s/n and (z=1.959963984540054), Wilson limits are

\[
\frac{\hat p+z^2/(2n)}{1+z^2/n}\ \pm\
\frac{z\sqrt{\hat p(1-\hat p)/n+z^2/(4n^2)}{1+z^2/n}.
\]

Source: `src/soil_simulator/phase97/gates.py:271-285` (`_wilson_interval`).

A supported target/regime passes when its success count lies within both central bounds and full interval width/RMSE (≤5). Severe undercoverage and excessive overcoverage are the lower/upper count failures. A regime with fewer than 20 rows or fewer than four empirical groups returns `abstain_insufficient_calibration_evidence`; that abstention is locally marked passed and does not fail the target coverage gate. Source: `src/soil_simulator/phase97/gates.py:310-397` (`uncertainty_coverage_evidence`).

## Leakage, independent validation and downstream conjunction

Leakage pass requires all five computable checks: no location crosses splits; descendants/fields remain isolated; preprocessing fit groups are train only; validation groups do not enter test/weather-OOD/archetype-OOD; and no exact or standardized-Euclidean-distance ≤1e-6 cross-split duplicate fields exist. Missing evidence fails closed. Source: `src/soil_simulator/phase97/gates.py:38-188` (`empirical_location_leakage_evidence`).

Independent empirical effect validation requires complete metadata, records with treatment/target/horizon/effect, only the four supported treatments, exact coverage of all seven primary target-horizons, independence from calibration/development, and at least 30 records. No dataset exists, so it is non-computable and false. Source: `src/soil_simulator/phase97/gates.py:191-268` (`independent_effect_validation_evidence`); artifact: `outputs/phase97_v0.9.7/gate_evidence.json`.

Downstream eligibility is

\[
G=G_{prediction}\land G_{OOD}\land G_{target\ coverage}\land G_{leakage}\land G_{independent\ validation}.
\]

Only if all five are true is selection/regret execution allowed; absent or false values fail closed. Source: `src/soil_simulator/phase97/gates.py:405-432` (`downstream_gate_evidence`).
