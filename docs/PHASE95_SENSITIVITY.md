# Phase 9.5 global sensitivity specification and results

## Method

The framework uses deterministic Morris screening over all 12 declared
mechanistic and scheduling parameters, followed by Saltelli/Sobol first-order
and total-order estimates for the four highest aggregate Morris scores. Morris
effects use unit-hypercube distance, so rankings reflect movement across each
parameter's full registered range rather than its physical unit. No range was
narrowed.

Results are separated by the five intervention policies, paired target and
24/60/120-month horizon. The target set includes yield at 24 months and NPP,
residue carbon, respiration, total-SOC effect and protected-SOC-proxy effect at
5 and 10 years. Seeds are frozen in `seed_manifest.json`.

## Results

The four screened parameters passed to Sobol were:

1. intervention schedule interval;
2. FYM phosphorus content;
3. cover-crop potential NPP;
4. conventional-tillage decomposition multiplier.

Across outputs, the Morris half-versus-full exact rank agreement averaged
0.853. Sobol half-versus-full rank agreement averaged 0.982. In 24 ranking
draws on the archived diagnostic field, FYM ranked first for the carbon-priority
proxy both with and without phosphorus. This differs from the audited Phase 9
selector's phosphorus concentration, but the two exercises have different
populations, schedules and objectives and are not directly comparable.

## Limitations and gate status

This is a global mechanistic/schedule analysis on one archived synthetic field.
It does not propagate observable soil/climate covariance assumptions because
the required real pilot was unavailable. Therefore the global-sensitivity
publication gate fails despite the completed Morris/Sobol computation. Ranking
stability cannot be generalized to a field population.

Machine-readable results are in `outputs/phase95_v0.9.5/sensitivity_results.json`
and the long table is in `sensitivity_results.csv`.
