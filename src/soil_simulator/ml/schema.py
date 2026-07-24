"""Typed Phase 8.5 dataset, configuration, and provenance contracts."""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from typing import Annotated, Literal, Self

from pydantic import Field, model_validator

from soil_simulator.domain.enums import ParameterSource, PopulationSplit
from soil_simulator.domain.models import ContractModel, NonNegativeInt

DATASET_VERSION = "0.8.5"
CLAIM_BOUNDARY = (
    "All performance is measured on synthetic simulator outcomes; it is non-causal, "
    "is not real-field validation, and must not be used as an intervention recommendation."
)

BASE_TARGETS = (
    "final_total_soc_t_c_ha",
    "final_protected_soc_proxy_t_c_ha",
    "crop_yield_t_dm_ha",
    "cumulative_respiration_t_c_ha",
    "final_available_phosphorus_kg_p_ha",
    "intervention_cost_gbp_ha",
    "emissions_proxy_kg_co2e_ha",
)
TARGETS = BASE_TARGETS + tuple(f"delta_{name}" for name in BASE_TARGETS)
TARGET_UNITS = {
    "final_total_soc_t_c_ha": "t C ha-1",
    "final_protected_soc_proxy_t_c_ha": "t C ha-1 (model proxy; not measured MAOC)",
    "crop_yield_t_dm_ha": "t dry matter ha-1",
    "cumulative_respiration_t_c_ha": "t C ha-1",
    "final_available_phosphorus_kg_p_ha": "kg P ha-1",
    "intervention_cost_gbp_ha": "GBP ha-1",
    "emissions_proxy_kg_co2e_ha": "kg CO2e ha-1 (non-mechanistic proxy)",
    "delta_final_total_soc_t_c_ha": "t C ha-1 versus paired baseline",
    "delta_final_protected_soc_proxy_t_c_ha": "t C ha-1 versus paired baseline proxy",
    "delta_crop_yield_t_dm_ha": "t dry matter ha-1 versus paired baseline",
    "delta_cumulative_respiration_t_c_ha": "t C ha-1 versus paired baseline",
    "delta_final_available_phosphorus_kg_p_ha": "kg P ha-1 versus paired baseline",
    "delta_intervention_cost_gbp_ha": "GBP ha-1 versus paired baseline",
    "delta_emissions_proxy_kg_co2e_ha": "kg CO2e ha-1 versus paired baseline",
}

OBSERVABLE_NUMERIC_FEATURES = (
    "soil_depth_cm",
    "clay_percent",
    "silt_percent",
    "sand_percent",
    "bulk_density_g_cm3",
    "ph",
    "cation_exchange_capacity_cmolc_kg",
    "baseline_total_nitrogen_percent",
    "baseline_soc_t_c_ha",
    "baseline_soc_concentration_g_kg",
    "weather_mean_temperature_c",
    "weather_temperature_sd_c",
    "weather_annual_rainfall_mm",
    "weather_annual_pet_mm",
    "growing_season_mean_temperature_c",
    "growing_season_rainfall_mm_per_year",
    "growing_season_pet_mm_per_year",
    "winter_rainfall_mm_per_year",
    "climate_aridity_index",
    "dry_month_fraction",
    "management_history_tillage_intensity",
    "management_history_cover_crop_indicator",
    "management_history_high_input_indicator",
    "simulation_horizon_months",
)
OBSERVABLE_CATEGORICAL_FEATURES = (
    "drainage_class",
    "management_history",
    "policy_id",
    "initial_phosphorus_status",
)
FULL_STATE_EXTRA_NUMERIC_FEATURES = (
    "initial_available_phosphorus_kg_p_ha",
    "initial_plant_c_t_ha",
    "initial_root_c_t_ha",
    "initial_amf_live_c_t_ha",
    "initial_amf_necromass_c_t_ha",
    "initial_dpm_c_t_ha",
    "initial_rpm_c_t_ha",
    "initial_microbial_c_t_ha",
    "initial_protected_soc_proxy_t_c_ha",
    "initial_iom_c_t_ha",
    "initial_topsoil_moisture_deficit_mm",
    "spinup_equilibrium_annual_input_t_c_ha",
    "latent_photosynthate_allocation_fraction",
    "latent_carbon_use_efficiency",
    "latent_turnover_per_month",
    "latent_necromass_stabilisation_fraction",
    "latent_p_uptake_vmax",
    "latent_conventional_amf_pulse_mortality",
    "latent_cover_crop_establishment_success",
)


@dataclass(frozen=True)
class FeatureSet:
    """Explicit deployable or diagnostic feature registry."""

    name: str
    numeric: tuple[str, ...]
    categorical: tuple[str, ...]
    deployable: bool
    description: str

    @property
    def names(self) -> tuple[str, ...]:
        """Return features in deterministic preprocessing order."""
        return self.numeric + self.categorical


FEATURE_SETS = {
    "observable_features": FeatureSet(
        name="observable_features",
        numeric=OBSERVABLE_NUMERIC_FEATURES,
        categorical=OBSERVABLE_CATEGORICAL_FEATURES,
        deployable=True,
        description=(
            "Soil-test-like measurements, coherent weather summaries, management history, "
            "field metadata, policy identity, and horizon only."
        ),
    ),
    "full_simulator_state": FeatureSet(
        name="full_simulator_state",
        numeric=OBSERVABLE_NUMERIC_FEATURES + FULL_STATE_EXTRA_NUMERIC_FEATURES,
        categorical=OBSERVABLE_CATEGORICAL_FEATURES,
        deployable=False,
        description=(
            "Observable features plus initial mechanistic pools, spin-up state, and latent "
            "biological parameter draws for diagnostic experiments only."
        ),
    ),
}


@dataclass(frozen=True)
class MlRow:
    """One field-policy-horizon row with flat features and explicit targets."""

    field_id: str
    empirical_seed_id: str
    archetype: str
    weather_regime: str
    phosphorus_status: str
    population_split: PopulationSplit
    policy_id: str
    simulation_horizon_months: int
    features: dict[str, float | str]
    targets: dict[str, float]

    @property
    def row_id(self) -> str:
        """Return the stable composite row key."""
        return f"{self.field_id}|{self.policy_id}|{self.simulation_horizon_months}"


class Phase8BenchmarkConfig(ContractModel):
    """Validated non-biological settings for deterministic Phase 8.5 benchmarking."""

    name: Annotated[str, Field(min_length=1)]
    version: Literal["0.8.5"]
    random_seed: NonNegativeInt
    foundation_group_count: Annotated[int, Field(ge=50)]
    foundation_seed: NonNegativeInt
    simulation_horizons_months: Annotated[tuple[int, ...], Field(min_length=3)]
    ridge_alphas: Annotated[tuple[float, ...], Field(min_length=1)]
    forest_tree_counts: Annotated[tuple[int, ...], Field(min_length=1)]
    forest_max_depths: Annotated[tuple[int, ...], Field(min_length=1)]
    forest_min_leaf: Annotated[int, Field(ge=2)]
    forest_feature_fraction: Annotated[float, Field(gt=0.0, le=1.0, allow_inf_nan=False)]
    conformal_alpha: Annotated[float, Field(gt=0.0, lt=1.0, allow_inf_nan=False)]
    minimum_calibration_groups: Annotated[int, Field(ge=3)]
    minimum_subgroup_interval_rows: Annotated[int, Field(ge=2)]
    coverage_tolerance: Annotated[float, Field(gt=0.0, lt=0.5, allow_inf_nan=False)]
    acceptable_ood_mae_sd_ratio: Annotated[float, Field(gt=0.0, allow_inf_nan=False)]
    near_duplicate_distance: Annotated[float, Field(gt=0.0, allow_inf_nan=False)]
    boundary_fraction: Annotated[float, Field(gt=0.0, lt=0.5, allow_inf_nan=False)]
    classification: Literal[ParameterSource.SCENARIO_ASSUMPTION]
    provenance: Annotated[str, Field(min_length=1)]

    @model_validator(mode="after")
    def validate_grids(self) -> Self:
        """Reject invalid deterministic hyperparameter grids."""
        if any(not math.isfinite(value) or value <= 0.0 for value in self.ridge_alphas):
            raise ValueError("ridge_alphas must be positive finite values")
        if any(value < 1 for value in self.forest_tree_counts):
            raise ValueError("forest_tree_counts must be positive")
        if any(value < 1 for value in self.forest_max_depths):
            raise ValueError("forest_max_depths must be positive")
        if tuple(sorted(self.simulation_horizons_months)) != self.simulation_horizons_months:
            raise ValueError("simulation_horizons_months must be unique and sorted")
        if self.simulation_horizons_months != (24, 60, 120):
            raise ValueError("Phase 8.5 requires exactly the 24, 60, and 120 month horizons")
        return self

    def stable_hash(self) -> str:
        """Return a deterministic semantic SHA-256."""
        payload = json.dumps(
            self.model_dump(mode="json"),
            allow_nan=False,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )
        return hashlib.sha256(payload.encode()).hexdigest()


class MlDatasetManifest(ContractModel):
    """Versioned provenance and leakage audit for a Phase 8.5 tabular dataset."""

    dataset_version: Literal["0.8.5", "0.8.6", "0.9.0"] = "0.8.5"
    dataset_hash: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
    population_hash: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
    population_configuration_hash: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
    model_configuration_hash: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
    source_dataset_name: Annotated[str, Field(min_length=1)]
    source_dataset_version: Annotated[str, Field(min_length=1)]
    source_batch_scenario_version: Annotated[str, Field(min_length=1)]
    row_count: NonNegativeInt
    field_count: NonNegativeInt
    empirical_seed_group_count: NonNegativeInt
    split_counts: dict[str, int]
    split_empirical_seed_group_counts: dict[str, int]
    observable_features: tuple[str, ...]
    full_simulator_state: tuple[str, ...]
    targets: tuple[str, ...]
    target_units: dict[str, str]
    horizon_target_applicability: dict[str, tuple[int, ...]]
    observable_feature_measurement_rationale: dict[str, str]
    revised_covariance_assumptions: tuple[str, ...]
    exact_duplicate_field_pairs: tuple[tuple[str, str], ...]
    near_duplicate_field_pairs: tuple[tuple[str, str, float], ...]
    claim_boundary: Literal[
        "All performance is measured on synthetic simulator outcomes; it is non-causal, "
        "is not real-field validation, and must not be used as an intervention recommendation."
    ] = (
        "All performance is measured on synthetic simulator outcomes; it is non-causal, "
        "is not real-field validation, and must not be used as an intervention recommendation."
    )
    provenance: Annotated[str, Field(min_length=1)]


def validate_feature_sets() -> None:
    """Fail if identifiers, targets, or latent state silently enter the primary set."""
    forbidden = set(TARGETS) | {
        "field_id",
        "empirical_seed_id",
        "population_split",
        "archetype",
    }
    observable = set(FEATURE_SETS["observable_features"].names)
    if observable & forbidden:
        raise ValueError(f"forbidden observable features: {sorted(observable & forbidden)}")
    latent = set(FULL_STATE_EXTRA_NUMERIC_FEATURES)
    if observable & latent:
        raise ValueError("latent simulator features entered observable_features")


validate_feature_sets()


HORIZON_TARGET_APPLICABILITY = {
    target: (
        (24,)
        if target in {"crop_yield_t_dm_ha", "delta_crop_yield_t_dm_ha"}
        else (60, 120)
        if target
        in {
            "final_total_soc_t_c_ha",
            "final_protected_soc_proxy_t_c_ha",
            "cumulative_respiration_t_c_ha",
            "delta_final_total_soc_t_c_ha",
            "delta_final_protected_soc_proxy_t_c_ha",
            "delta_cumulative_respiration_t_c_ha",
        }
        else (24, 60, 120)
    )
    for target in TARGETS
}

OBSERVABLE_FEATURE_RATIONALE = {
    "soil_depth_cm": "Field sampling depth is recorded with a soil test.",
    "clay_percent": "Particle-size analysis is an established soil laboratory measurement.",
    "silt_percent": "Particle-size analysis is an established soil laboratory measurement.",
    "sand_percent": "Particle-size analysis is an established soil laboratory measurement.",
    "bulk_density_g_cm3": "Core sampling can measure topsoil bulk density.",
    "ph": "Routine soil testing measures pH.",
    "cation_exchange_capacity_cmolc_kg": "CEC is available from laboratory soil analysis.",
    "baseline_total_nitrogen_percent": "Total nitrogen is available from laboratory analysis.",
    "baseline_soc_t_c_ha": (
        "Baseline SOC stock combines measured concentration, depth, and density."
    ),
    "baseline_soc_concentration_g_kg": "Derived only from baseline SOC, depth, and bulk density.",
    "weather_mean_temperature_c": "Pre-intervention monthly weather records provide this summary.",
    "weather_temperature_sd_c": "Pre-intervention monthly weather records provide this summary.",
    "weather_annual_rainfall_mm": "Pre-intervention monthly weather records provide this summary.",
    "weather_annual_pet_mm": "Pre-intervention weather products provide this summary.",
    "growing_season_mean_temperature_c": "March--September weather records provide this index.",
    "growing_season_rainfall_mm_per_year": "March--September rainfall records provide this index.",
    "growing_season_pet_mm_per_year": "March--September PET records provide this index.",
    "winter_rainfall_mm_per_year": "October--February rainfall records provide this index.",
    "climate_aridity_index": "Annual rainfall divided by PET is calculated from weather records.",
    "dry_month_fraction": (
        "The fraction of months with rainfall below PET is observable weather history."
    ),
    "management_history_tillage_intensity": "Farm records can classify recent tillage intensity.",
    "management_history_cover_crop_indicator": "Farm records can show recent cover-crop use.",
    "management_history_high_input_indicator": (
        "Farm input records can classify high-input history."
    ),
    "simulation_horizon_months": "The requested prediction horizon is known at prediction time.",
    "drainage_class": "Mapped or field-recorded topsoil drainage class is field metadata.",
    "management_history": "A coarse pre-intervention management-history category is recordable.",
    "policy_id": "The intervention scenario whose outcome is predicted is known.",
    "initial_phosphorus_status": (
        "A coarse low/moderate/high status can be supplied by a soil test; the raw simulator "
        "available-P stock is intentionally excluded from observable features."
    ),
}
