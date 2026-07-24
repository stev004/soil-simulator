"""Frozen non-biological contracts for Phase 8.6 repeated experiments."""

from __future__ import annotations

import hashlib
import json
import math
from typing import Annotated, Literal, Self

from pydantic import Field, model_validator

from soil_simulator.domain.enums import ParameterSource
from soil_simulator.domain.models import ContractModel, NonNegativeInt

PHASE86_VERSION = "0.8.6"
PHASE86_PRIMARY_TASKS = (
    "delta_crop_yield_t_dm_ha@24",
    "delta_final_total_soc_t_c_ha@60",
    "delta_final_total_soc_t_c_ha@120",
    "delta_final_protected_soc_proxy_t_c_ha@60",
    "delta_final_protected_soc_proxy_t_c_ha@120",
)
PHASE86_MODEL_COMPLEXITY = (
    "policy_mean",
    "pooled_ridge",
    "per_policy_ridge",
    "pooled_forest",
    "per_policy_forest",
)
PHASE86_WEATHER_REGIMES = ("temperate", "dry", "hot", "wet", "cool", "hot_dry")


class Phase86BenchmarkConfig(ContractModel):
    """Predeclared repeated-experiment, selection, calibration, and gate settings."""

    name: Annotated[str, Field(min_length=1)]
    version: Literal["0.8.6"]
    random_seed: NonNegativeInt
    foundation_group_count: Annotated[int, Field(ge=75)]
    development_population_size: Annotated[int, Field(ge=75)]
    final_population_size: Annotated[int, Field(ge=75)]
    development_foundation_seeds: Annotated[tuple[int, ...], Field(min_length=10)]
    population_seeds: Annotated[tuple[int, ...], Field(min_length=10)]
    weather_resampling_seeds: Annotated[tuple[int, ...], Field(min_length=2)]
    biological_parameter_seeds: Annotated[tuple[int, ...], Field(min_length=2)]
    final_foundation_seed: NonNegativeInt
    final_population_seed: NonNegativeInt
    final_weather_resampling_seed: NonNegativeInt
    final_biological_parameter_seed: NonNegativeInt
    simulation_horizons_months: Annotated[tuple[int, ...], Field(min_length=3, max_length=3)]
    ridge_alphas: Annotated[tuple[float, ...], Field(min_length=1)]
    forest_tree_counts: Annotated[tuple[int, ...], Field(min_length=1)]
    forest_max_depths: Annotated[tuple[int, ...], Field(min_length=1)]
    forest_min_leaf: Annotated[int, Field(ge=2)]
    forest_feature_fraction: Annotated[float, Field(gt=0.0, le=1.0, allow_inf_nan=False)]
    model_selection_relative_tolerance: Annotated[
        float, Field(ge=0.0, le=0.25, allow_inf_nan=False)
    ]
    conformal_alpha: Annotated[float, Field(gt=0.0, lt=1.0, allow_inf_nan=False)]
    minimum_calibration_groups: Annotated[int, Field(ge=3)]
    coverage_tolerance: Annotated[float, Field(gt=0.0, lt=0.5, allow_inf_nan=False)]
    supported_regime_max_median_mae_sd: Annotated[float, Field(gt=0.0, allow_inf_nan=False)]
    maximum_repeat_failure_frequency: Annotated[float, Field(ge=0.0, lt=1.0, allow_inf_nan=False)]
    maximum_repeat_iqr_mae_sd: Annotated[float, Field(gt=0.0, allow_inf_nan=False)]
    maximum_final_mae_sd: Annotated[float, Field(gt=0.0, allow_inf_nan=False)]
    minimum_supported_climate_regimes: Annotated[int, Field(ge=1, le=5)]
    near_duplicate_distance: Annotated[float, Field(gt=0.0, allow_inf_nan=False)]
    classification: Literal[ParameterSource.SCENARIO_ASSUMPTION]
    provenance: Annotated[str, Field(min_length=1)]

    @model_validator(mode="after")
    def validate_protocol(self) -> Self:
        """Reject seed overlap, incomplete repeats, or invalid model grids."""
        repeat_count = len(self.population_seeds)
        if len(self.development_foundation_seeds) != repeat_count:
            raise ValueError("each population seed requires one independent foundation seed")
        if len(set(self.population_seeds)) != repeat_count:
            raise ValueError("population seeds must be distinct")
        if len(set(self.development_foundation_seeds)) != repeat_count:
            raise ValueError("development foundation seeds must be distinct")
        development_seeds = (
            set(self.population_seeds)
            | set(self.weather_resampling_seeds)
            | set(self.biological_parameter_seeds)
            | set(self.development_foundation_seeds)
        )
        final_seeds = {
            self.final_foundation_seed,
            self.final_population_seed,
            self.final_weather_resampling_seed,
            self.final_biological_parameter_seed,
        }
        if development_seeds & final_seeds or len(final_seeds) != 4:
            raise ValueError("all frozen-final seeds must be distinct from development seeds")
        if any(not math.isfinite(value) or value <= 0.0 for value in self.ridge_alphas):
            raise ValueError("ridge alphas must be positive and finite")
        if any(value < 1 for value in self.forest_tree_counts + self.forest_max_depths):
            raise ValueError("forest grids must contain positive integers")
        if self.simulation_horizons_months != (24, 60, 120):
            raise ValueError("Phase 8.6 requires exactly 24, 60, and 120 month horizons")
        return self

    @property
    def repeat_count(self) -> int:
        """Return the number of independently seeded development experiments."""
        return len(self.population_seeds)

    def stable_hash(self) -> str:
        """Return the deterministic semantic SHA-256 of the frozen protocol."""
        payload = json.dumps(
            self.model_dump(mode="json"),
            allow_nan=False,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )
        return hashlib.sha256(payload.encode()).hexdigest()


def predeclared_model_choice(
    validation_scores: dict[str, float], relative_tolerance: float
) -> tuple[str, dict[str, object]]:
    """Choose the least complex candidate within tolerance of the best score."""
    if set(validation_scores) != set(PHASE86_MODEL_COMPLEXITY):
        raise ValueError("model selection requires exactly the five predeclared candidates")
    if not validation_scores or any(
        not math.isfinite(value) or value < 0.0 for value in validation_scores.values()
    ):
        raise ValueError("validation scores must be finite and non-negative")
    best = min(validation_scores.values())
    threshold = best * (1.0 + relative_tolerance)
    eligible = tuple(
        name for name in PHASE86_MODEL_COMPLEXITY if validation_scores[name] <= threshold
    )
    selected = eligible[0]
    return selected, {
        "criterion": "lowest median validation normalised RMSE",
        "relative_tolerance": relative_tolerance,
        "best_score": best,
        "eligibility_threshold": threshold,
        "eligible_models_in_complexity_order": eligible,
        "selected_for_simplicity": selected,
        "r_squared_used_for_selection": False,
    }
