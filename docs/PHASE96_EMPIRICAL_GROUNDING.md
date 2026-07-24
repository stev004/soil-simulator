# Phase 9.6 empirical grounding

The pilot contains **56 accepted paired locations** (8 rejected from the predeclared 64-location frame). SoilGrids 2.0 median predictions are thickness-harmonised to 0--23 cm; NASA POWER/MERRA-2 supplies complete monthly years for 2001--2020. Thornthwaite PET is derived from monthly mean temperature, latitude and daylength. Coordinates are rounded to 0.1 degrees.

Sample covariance is calculated only within this 56-location paired pilot. It
is not a national covariance estimate and does not establish population
representativeness. Latent AMF/P priors, within-location synthetic perturbations
and imposed simulator relationships remain separate. The generated population
contains 112 synthetic fields grouped by empirical location with frozen
train/validation/test/OOD assignments. See
`outputs/phase96_v0.9.6/EMPIRICAL_SOURCE_MANIFEST.json` and
`empirical_covariance_report.json`.
