# Phase 9.7 FYM calibration-boundary analysis

The Phase 9.6 optional calibration estimated the FYM carbon reconstruction
factor at **1.10**, exactly the permitted **0.90--1.10** range's upper bound.
The estimate is boundary-constrained. Profiling the objective over FYM factor
while minimising over the permitted plant-residue factor shows a decreasing
objective at the upper edge, so fit would likely improve beyond the bound.
Phase 9.7 does not evaluate or adopt an out-of-bound calibration and does not
widen the range.

The near-optimal surface leaves input-reconstruction identifiability limited.
The held-out FYM-cessation metrics remain MAE 7.214, RMSE 7.577 and bias -7.214
t C ha-1. Source correction substantially improved the uncalibrated aggregate
trajectory, but this boundary solution and weak cessation result do not
constitute successful general calibration. RothC constants are unchanged and
the exercise validates neither AMF dynamics nor `protected_soc` as measured
MAOC.

Machine-readable profile points, edge slope, permitted range, identifiability
summary and held-out metrics are in `outputs/phase97_v0.9.7/calibration_profile.*`.
