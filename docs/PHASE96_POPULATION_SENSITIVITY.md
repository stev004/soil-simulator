# Phase 9.6 population sensitivity (historical, superseded)

The Phase 9.6 result used ordinary pseudorandom A/B draws and a base sample of
32. It was incorrectly labelled Sobol and its nested rank agreement is not
evidence of convergence. Do not treat these sensitivity estimates as final.
Phase 9.7 preserves the parameter distributions and bounds while replacing the
design with SciPy's scrambled Sobol engine, Saltelli/Jansen estimators,
confidence intervals and a 128/256/512/1,024 convergence sequence. See
`PHASE97_SENSITIVITY_CORRECTION.md`.
