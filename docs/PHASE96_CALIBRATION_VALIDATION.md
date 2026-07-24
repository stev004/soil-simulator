# Phase 9.6 calibration and held-out validation

The fully uncalibrated, source-corrected benchmark is retained. An optional grid calibration fits only plant-residue and FYM carbon reconstruction factors to unmanured/annual-FYM observations through 1965. Post-1965 points and the complete cessation treatment are held out. Best factors: {'plant_residue_factor': 0.8500000000000001, 'fym_carbon_factor': 1.1}. Boundary solution: True. Held-out temporal metrics: {'mae_t_c_ha': 1.5157887892167796, 'rmse_t_c_ha': 1.8847735853984364, 'bias_t_c_ha': 0.4975387778078299}. Held-out treatment metrics: {'mae_t_c_ha': 7.214238690963898, 'rmse_t_c_ha': 7.577073646005274, 'bias_t_c_ha': -7.214238690963898}.

The FYM estimate equals its permitted upper bound of 1.10 and is therefore
boundary-constrained. The bounded objective is still improving at that edge,
so the unconstrained optimum would likely be higher; the permitted bound is
not widened. The calibration is not retained as a general simulator parameter;
RothC constants are unchanged. The material held-out cessation error and
parameter identifiability limitations mean this is not successful general
calibration. Uncertainty bands are parameter-reconstruction bands, not
observational confidence intervals. See `PHASE97_CALIBRATION_BOUNDARY.md`.
