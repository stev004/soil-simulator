"""Transparent analysis of the Phase 9.6 FYM calibration boundary solution."""

from __future__ import annotations

import math
from collections import defaultdict
from collections.abc import Mapping

from soil_simulator.phase96.values import as_float


def calibration_boundary_profile(diagnosis: Mapping[str, object]) -> dict[str, object]:
    """Profile the bounded objective without widening or refitting the parameter range."""
    calibration = diagnosis.get("optional_calibration")
    if not isinstance(calibration, Mapping):
        return {"computable": False, "boundary_constrained": False, "reason": "missing data"}
    parameters = calibration.get("predeclared_parameters")
    best = calibration.get("best_parameters")
    candidates = calibration.get("candidate_summary")
    if (
        not isinstance(parameters, Mapping)
        or not isinstance(best, Mapping)
        or not isinstance(candidates, list)
    ):
        return {
            "computable": False,
            "boundary_constrained": False,
            "reason": "calibration artifact is schema-incomplete",
        }
    fym_spec = parameters.get("fym_carbon_factor")
    if not isinstance(fym_spec, Mapping):
        return {
            "computable": False,
            "boundary_constrained": False,
            "reason": "FYM parameter specification is missing",
        }
    bounds_raw = fym_spec.get("bounds")
    if not isinstance(bounds_raw, list) or len(bounds_raw) != 2:
        return {
            "computable": False,
            "boundary_constrained": False,
            "reason": "FYM bounds are missing",
        }
    lower, upper = (as_float(value) for value in bounds_raw)
    estimate = as_float(best["fym_carbon_factor"])
    by_fym: dict[float, list[float]] = defaultdict(list)
    for raw in candidates:
        if not isinstance(raw, Mapping):
            continue
        by_fym[as_float(raw["fym_carbon_factor"])].append(
            as_float(raw["calibration_objective_mean_treatment_rmse_t_c_ha"])
        )
    profile = [
        {
            "fym_carbon_factor": value,
            "profile_objective_mean_treatment_rmse_t_c_ha": min(objectives),
            "profiled_over": "plant_residue_factor within its predeclared bounds",
        }
        for value, objectives in sorted(by_fym.items())
    ]
    boundary = math.isclose(estimate, lower) or math.isclose(estimate, upper)
    likely_improves_beyond = False
    edge_slope: float | None = None
    if len(profile) >= 2 and math.isclose(estimate, upper):
        left = profile[-2]
        right = profile[-1]
        edge_slope = (
            as_float(right["profile_objective_mean_treatment_rmse_t_c_ha"])
            - as_float(left["profile_objective_mean_treatment_rmse_t_c_ha"])
        ) / (as_float(right["fym_carbon_factor"]) - as_float(left["fym_carbon_factor"]))
        likely_improves_beyond = edge_slope < 0.0
    held_out = calibration.get("held_out_treatment_metrics")
    identifiability = calibration.get("identifiability")
    return {
        "computable": True,
        "parameter": "fym_carbon_factor",
        "estimate": estimate,
        "permitted_range": [lower, upper],
        "classification": fym_spec.get("classification"),
        "boundary_constrained": boundary,
        "boundary": "upper" if math.isclose(estimate, upper) else "lower" if boundary else None,
        "profile": profile,
        "edge_objective_slope": edge_slope,
        "objective_likely_improves_beyond_bound": likely_improves_beyond,
        "beyond_bound_evaluation_performed": False,
        "bound_widened": False,
        "identifiability": identifiability,
        "held_out_cessation_performance": held_out,
        "general_calibration_success": False,
        "general_calibration_reason": (
            "the optimum is boundary-constrained, the profile is still improving at the upper "
            "bound, and held-out FYM-cessation error remains material"
        ),
    }
