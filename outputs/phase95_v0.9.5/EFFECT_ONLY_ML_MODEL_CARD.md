# Phase 9.5 effect-only ML model card

## Status

Target contract implemented; model training **not rerun** because the required
empirical population pilot and covariance revision were not completed.

## Primary targets

- paired yield effect at 24 months;
- paired total-SOC effect at 60 and 120 months;
- paired protected-SOC-proxy effect at 60 and 120 months;
- paired cumulative-respiration effect at 60 and 120 months.

Every target is intervention minus the matched same-field, same-horizon
baseline. These are synthetic simulator effects, not causal field effects.

## Diagnostic-only targets

Final total-SOC stock and final protected-SOC-proxy stock are persistence-
dominated diagnostics. `protected_soc` is not measured MAOC. Cost and emissions
are deterministic policy/schedule identities computed directly from events;
they are prohibited from ML training and scoring.

## Circularity result

Across archived 5/10-year data, final-stock correlation with initial SOC is
0.9933. An initial-SOC-only baseline attains R² 0.9868 for final total SOC and
0.9939 for the final protected proxy. Adding clay increases protected-proxy R²
by only 0.00188, although the residual clay correlation is 0.544. These results
show why stock-level skill is not meaningful intervention-effect evidence.

## Leakage and evaluation contract

Future training must preserve complete location/region groups across train,
validation and test; fit preprocessing and calibration only on permitted
groups; compare against zero-effect, policy-mean and regularized baselines; and
report incremental effect skill. No Phase 9.5 scores are available because no
revised empirical population or effect dataset was generated.

## Intended and prohibited use

Intended only for offline scientific benchmarking after the blockers are
resolved. Prohibited for farm advice, deployment, causal claims, carbon-credit
accounting or product recommendations.
