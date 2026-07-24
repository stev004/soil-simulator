# Phase 9.7 Sobol and convergence correction

## Design

SciPy `scipy.stats.qmc.Sobol` generates one scrambled `2D` unit-cube sequence.
Its first and second `D` columns form the A and B matrices. A_B(i) hybrids use
the B value for factor `i` and A values elsewhere. First-order indices use the
Saltelli 2010 covariance estimator; total-order indices use the Jansen 1999
squared-difference estimator. Deterministic bootstrap intervals quantify
finite-sample estimator noise. Negative estimates are reported and never
clipped.

The five Phase 9.6 Morris-screened factors retain their exact configured
distributions and bounds: empirical location, intact weather-year resample,
schedule interval, tillage decomposition multiplier and FYM phosphorus
content. The analysis covers the primary paired effects at supported horizons:
24-month yield and 60/120-month total-SOC, protected-SOC-proxy and respiration
effects for the four headline non-phosphorus policies. These are simulator
effects, not empirical causal effects.

## Convergence rule

The nested base sizes are 128, 256, 512 and 1,024. The largest adjacent pair
passes only when maximum S1/ST change is at most 0.10, both rank correlations
are at least 0.90, mean 95% interval width is at most 0.20 and at most 10% of
estimates are unstable. The artifacts additionally report negative-estimate
fraction, evaluation count, runtime evidence and policy-ranking stability.

## Result

Convergence was **not reached**, so the Phase 9.7 indices remain diagnostic and
must not be labelled final. Between 512 and 1,024 base samples, maximum absolute
S1 and ST changes were 0.122 and 0.112, above the 0.10 threshold. S1/ST rank
correlations were 0.935/0.997; mean confidence-interval width was 0.110;
unstable and negative-estimate fractions were both 0.0179. Thus the rank,
interval-width and unstable-fraction criteria passed, but the index-change
criterion failed.

The frozen one-worker reference runtime was 211.176, 424.182, 854.173 and
1,447.559 seconds at base sizes 128, 256, 512 and 1,024. Runtime is measured
evidence and does not enter the convergence decision or deterministic artifact
hash. Numerical estimator noise (confidence intervals, negative estimates and
convergence deltas) remains distinct from biological/scenario uncertainty (the
declared input distributions and their provenance classifications).
