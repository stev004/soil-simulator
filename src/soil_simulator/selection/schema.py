"""Strict, versioned non-biological contracts for the Phase 9 benchmark."""

from __future__ import annotations

import hashlib
import json
import math
from typing import Annotated, Literal, Self

from pydantic import Field, model_validator

from soil_simulator.domain.enums import ParameterSource
from soil_simulator.domain.models import ContractModel, NonNegativeInt

PHASE9_VERSION = "0.9.0"
PHASE9_POLICIES = (
    "baseline",
    "conventional_tillage",
    "reduced_tillage",
    "no_till",
    "cover_crop",
    "phosphorus",
    "farmyard_manure",
)
PHASE9_METHODS = (
    "status_quo",
    "random_eligible",
    "best_global",
    "rule_based",
    "policy_mean",
    "observable_ml",
    "uncertainty_lcb",
    "uncertainty_overlap_abstain",
    "uncertainty_baseline_abstain",
    "simulator_oracle",
)


class ObjectiveWeights(ContractModel):
    """Visible unitless preferences applied after training-only normalisation."""

    yield_effect: Annotated[float, Field(ge=0.0, le=1.0, allow_inf_nan=False)]
    total_soc_effect: Annotated[float, Field(ge=0.0, le=1.0, allow_inf_nan=False)]
    protected_soc_proxy_effect: Annotated[float, Field(ge=0.0, le=1.0, allow_inf_nan=False)]
    intervention_cost: Annotated[float, Field(ge=0.0, le=1.0, allow_inf_nan=False)]
    emissions_proxy: Annotated[float, Field(ge=0.0, le=1.0, allow_inf_nan=False)]

    @model_validator(mode="after")
    def validate_sum(self) -> Self:
        """Require an explicit convex preference mixture."""
        if not math.isclose(sum(self.model_dump().values()), 1.0, rel_tol=0.0, abs_tol=1.0e-9):
            raise ValueError("utility weights must sum to one")
        return self


class HardConstraints(ContractModel):
    """Scenario thresholds with physical units; none is agronomic advice."""

    maximum_yield_loss_t_dm_ha: Annotated[float, Field(ge=0.0, allow_inf_nan=False)]
    maximum_cost_gbp_ha: Annotated[float, Field(ge=0.0, allow_inf_nan=False)]
    maximum_emissions_proxy_kg_co2e_ha: Annotated[float, Field(ge=0.0, allow_inf_nan=False)]
    minimum_total_soc_benefit_t_c_ha: Annotated[float, Field(allow_inf_nan=False)]
    maximum_actual_violation_rate: Annotated[float, Field(ge=0.0, le=1.0, allow_inf_nan=False)]


class UtilityProfile(ContractModel):
    """One predeclared synthetic decision scenario."""

    profile_id: Annotated[str, Field(min_length=1)]
    description: Annotated[str, Field(min_length=1)]
    weights: ObjectiveWeights
    constraints: HardConstraints
    carbon_horizon_weights: Annotated[
        tuple[float, float], Field(description="Weights for 5-year and 10-year carbon effects")
    ]
    classification: Literal[ParameterSource.SCENARIO_ASSUMPTION]
    provenance: Annotated[str, Field(min_length=1)]

    @model_validator(mode="after")
    def validate_horizons(self) -> Self:
        """Use both frozen carbon horizons and keep their mixture visible."""
        if any(not math.isfinite(value) or value < 0.0 for value in self.carbon_horizon_weights):
            raise ValueError("carbon horizon weights must be finite and non-negative")
        if not math.isclose(sum(self.carbon_horizon_weights), 1.0, abs_tol=1.0e-9):
            raise ValueError("carbon horizon weights must sum to one")
        if 0.0 in self.carbon_horizon_weights:
            raise ValueError("Phase 9 profiles must exercise both frozen carbon horizons")
        return self


class FrozenArtifactExpectations(ContractModel):
    """Expected semantic identities for every consumed Phase 8.6 artifact."""

    phase86_version: Literal["0.8.6"]
    protocol_hash: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
    frozen_decision_hash: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
    preprocessing_hash: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
    model_hashes: dict[str, Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]]
    maximum_absolute_standardised_feature: Annotated[float, Field(gt=0.0, allow_inf_nan=False)]


class Phase9BenchmarkConfig(ContractModel):
    """Frozen experiment, selector, utility, constraint and gate definitions."""

    name: Annotated[str, Field(min_length=1)]
    version: Literal["0.9.0"]
    random_seed: NonNegativeInt
    foundation_group_count: Annotated[int, Field(ge=75)]
    population_size: Annotated[int, Field(ge=75)]
    final_population_size: Annotated[int, Field(ge=75)]
    foundation_seeds: Annotated[tuple[int, ...], Field(min_length=10)]
    population_seeds: Annotated[tuple[int, ...], Field(min_length=10)]
    weather_resampling_seeds: Annotated[tuple[int, ...], Field(min_length=2)]
    biological_parameter_seeds: Annotated[tuple[int, ...], Field(min_length=2)]
    final_foundation_seed: NonNegativeInt
    final_population_seed: NonNegativeInt
    final_weather_resampling_seed: NonNegativeInt
    final_biological_parameter_seed: NonNegativeInt
    simulation_horizons_months: tuple[Literal[24], Literal[60], Literal[120]]
    utility_profiles: Annotated[tuple[UtilityProfile, ...], Field(min_length=4)]
    frozen_artifacts: FrozenArtifactExpectations
    ranking_overlap_tolerance_utility: Annotated[float, Field(ge=0.0, allow_inf_nan=False)]
    confidence_improvement_margin_utility: Annotated[float, Field(ge=0.0, allow_inf_nan=False)]
    catastrophic_normalised_regret_threshold: Annotated[
        float, Field(gt=0.0, le=1.0, allow_inf_nan=False)
    ]
    stability_perturbation_fraction_of_training_scale: Annotated[
        float, Field(gt=0.0, le=0.25, allow_inf_nan=False)
    ]
    near_duplicate_distance: Annotated[float, Field(gt=0.0, allow_inf_nan=False)]
    reasonable_seed_median_regret_iqr: Annotated[float, Field(ge=0.0, allow_inf_nan=False)]
    classification: Literal[ParameterSource.SCENARIO_ASSUMPTION]
    provenance: Annotated[str, Field(min_length=1)]

    @model_validator(mode="after")
    def validate_freeze(self) -> Self:
        """Reject seed reuse, missing profiles or unrecognised frozen targets."""
        count = len(self.population_seeds)
        if len(self.foundation_seeds) != count:
            raise ValueError("each population seed requires an independent foundation seed")
        if len(set(self.foundation_seeds)) != count or len(set(self.population_seeds)) != count:
            raise ValueError(
                "development/evaluation foundation and population seeds must be unique"
            )
        development = (
            set(self.foundation_seeds)
            | set(self.population_seeds)
            | set(self.weather_resampling_seeds)
            | set(self.biological_parameter_seeds)
        )
        final = {
            self.final_foundation_seed,
            self.final_population_seed,
            self.final_weather_resampling_seed,
            self.final_biological_parameter_seed,
        }
        if development & final or len(final) != 4:
            raise ValueError("frozen-final seeds must be unique and unused during development")
        profile_ids = tuple(profile.profile_id for profile in self.utility_profiles)
        required = {
            "yield_priority",
            "carbon_priority",
            "balanced",
            "cost_emissions_constrained",
        }
        if not required.issubset(profile_ids) or len(set(profile_ids)) != len(profile_ids):
            raise ValueError("four unique required utility profiles must be predeclared")
        from soil_simulator.ml.phase86_schema import PHASE86_PRIMARY_TASKS

        if set(self.frozen_artifacts.model_hashes) != set(PHASE86_PRIMARY_TASKS):
            raise ValueError("frozen model hashes must cover exactly the five Phase 8.6 tasks")
        return self

    def stable_hash(self) -> str:
        """Return the semantic SHA-256 of every predeclared Phase 9 choice."""
        payload = json.dumps(
            self.model_dump(mode="json"),
            allow_nan=False,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )
        return hashlib.sha256(payload.encode()).hexdigest()
