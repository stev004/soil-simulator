"""Immutable contracts for reproducible Phase 7 synthetic field populations.

The population layer constructs inputs for the verified Phase 6 simulator. It
does not change mechanistic equations. Carbon stocks use ``t C ha-1`` and
available phosphorus uses ``kg P ha-1``. ``protected_soc_c`` remains a model
proxy and is not measured MAOC.
"""

from __future__ import annotations

import hashlib
import json
import math
from typing import Annotated, Literal, Self

from pydantic import Field, model_validator

from soil_simulator.domain.enums import ParameterSource, PopulationSplit
from soil_simulator.domain.models import (
    ContractModel,
    FieldProperties,
    FieldState,
    ModelParameter,
    NonNegativeFloat,
    NonNegativeInt,
    VersionedInput,
    WeatherMonth,
)


class EmpiricalSeedRecord(ContractModel):
    """One jointly coherent 0--23 cm soil record from a versioned adapter."""

    seed_id: Annotated[str, Field(min_length=1)]
    region_id: Annotated[str, Field(min_length=1)]
    archetype: Annotated[str, Field(min_length=1)]
    latitude_deg: Annotated[float, Field(ge=-90.0, le=90.0, allow_inf_nan=False)]
    longitude_deg: Annotated[float, Field(ge=-180.0, le=180.0, allow_inf_nan=False)]
    clay_percent: Annotated[float, Field(gt=0.0, lt=100.0, allow_inf_nan=False)]
    silt_percent: Annotated[float, Field(gt=0.0, lt=100.0, allow_inf_nan=False)]
    sand_percent: Annotated[float, Field(gt=0.0, lt=100.0, allow_inf_nan=False)]
    ph: Annotated[float, Field(ge=3.0, le=10.0, allow_inf_nan=False)]
    soc_t_c_ha: Annotated[float, Field(gt=0.0, allow_inf_nan=False)]
    bulk_density_g_cm3: Annotated[float, Field(gt=0.0, allow_inf_nan=False)]
    available_p_kg_ha: Annotated[float, Field(gt=0.0, allow_inf_nan=False)]
    cation_exchange_capacity_cmolc_kg: NonNegativeFloat
    total_nitrogen_percent: NonNegativeFloat
    amf_live_c_t_ha: NonNegativeFloat
    amf_necromass_c_t_ha: NonNegativeFloat
    drainage_class: Annotated[str, Field(min_length=1)]
    management_history: Annotated[str, Field(min_length=1)]
    eligible_interventions: Annotated[tuple[str, ...], Field(min_length=1)]
    provenance: Annotated[str, Field(min_length=1)]

    @model_validator(mode="after")
    def validate_texture(self) -> Self:
        """Require empirical texture percentages to be compositional."""
        if not math.isclose(
            self.clay_percent + self.silt_percent + self.sand_percent,
            100.0,
            rel_tol=0.0,
            abs_tol=0.01,
        ):
            raise ValueError("empirical texture percentages must sum to 100")
        return self


class WeatherYearRecord(ContractModel):
    """One complete coherent weather year kept intact during resampling."""

    weather_year_id: Annotated[str, Field(min_length=1)]
    region_id: Annotated[str, Field(min_length=1)]
    source_year: Annotated[int, Field(ge=1800, le=2200)]
    temperature_c: Annotated[tuple[float, ...], Field(min_length=12, max_length=12)]
    rainfall_mm: Annotated[tuple[NonNegativeFloat, ...], Field(min_length=12, max_length=12)]
    evapotranspiration_mm: Annotated[
        tuple[NonNegativeFloat, ...], Field(min_length=12, max_length=12)
    ]
    provenance: Annotated[str, Field(min_length=1)]

    @model_validator(mode="after")
    def validate_finite_temperatures(self) -> Self:
        """Reject non-finite temperature values not caught by a bare tuple type."""
        if any(not math.isfinite(value) for value in self.temperature_c):
            raise ValueError("weather temperatures must be finite")
        return self


class EmpiricalDataset(ContractModel):
    """Adapter-neutral versioned collection of seed rows and weather years."""

    dataset_name: Annotated[str, Field(min_length=1)]
    dataset_version: Annotated[str, Field(min_length=1)]
    adapter_name: Annotated[str, Field(min_length=1)]
    adapter_version: Annotated[str, Field(min_length=1)]
    source_datasets: Annotated[tuple[VersionedInput, ...], Field(min_length=1)]
    seeds: Annotated[tuple[EmpiricalSeedRecord, ...], Field(min_length=1)]
    weather_years: Annotated[tuple[WeatherYearRecord, ...], Field(min_length=1)]
    provenance: Annotated[str, Field(min_length=1)]

    @model_validator(mode="after")
    def validate_identifiers_and_regions(self) -> Self:
        """Require unique IDs and at least one complete weather year per seed region."""
        seed_ids = [seed.seed_id for seed in self.seeds]
        weather_ids = [year.weather_year_id for year in self.weather_years]
        if len(seed_ids) != len(set(seed_ids)):
            raise ValueError("empirical seed identifiers must be unique")
        if len(weather_ids) != len(set(weather_ids)):
            raise ValueError("weather-year identifiers must be unique")
        weather_regions = {year.region_id for year in self.weather_years}
        missing = {seed.region_id for seed in self.seeds} - weather_regions
        if missing:
            raise ValueError(f"seed regions lack complete weather years: {sorted(missing)}")
        return self


class PopulationGenerationConfig(ContractModel):
    """Validated Phase 7 generation, perturbation, spin-up and QC settings."""

    name: Annotated[str, Field(min_length=1)]
    version: Annotated[str, Field(min_length=1)]
    default_population_size: Annotated[int, Field(ge=1)]
    generation_seed: NonNegativeInt
    weather_years_per_field: Annotated[int, Field(ge=1, le=100)]
    max_generation_attempt_multiplier: Annotated[int, Field(ge=1, le=100)]
    split_train_fraction: Annotated[float, Field(gt=0.0, lt=1.0, allow_inf_nan=False)]
    split_validation_fraction: Annotated[float, Field(gt=0.0, lt=1.0, allow_inf_nan=False)]
    split_test_fraction: Annotated[float, Field(gt=0.0, lt=1.0, allow_inf_nan=False)]
    archetype_ood_archetypes: tuple[str, ...] = ()
    weather_ood_regions: tuple[str, ...] = ()
    texture_logratio_sd: ModelParameter
    soil_shared_factor_sd: ModelParameter
    soc_independent_log_sd: ModelParameter | None = None
    bulk_density_independent_sd: ModelParameter | None = None
    bulk_density_shared_factor_coefficient: ModelParameter | None = None
    ph_absolute_sd: ModelParameter
    phosphorus_log_sd: ModelParameter
    amf_log_sd: ModelParameter
    soc_relative_limit: ModelParameter
    weather_pet_to_open_pan_divisor: ModelParameter
    spinup_max_years: ModelParameter
    spinup_relative_tolerance: ModelParameter
    spinup_reference_annual_input_t_c_ha: ModelParameter
    minimum_soc_t_c_ha: ModelParameter
    maximum_soc_t_c_ha: ModelParameter
    minimum_bulk_density_g_cm3: ModelParameter
    maximum_bulk_density_g_cm3: ModelParameter
    minimum_ph: ModelParameter
    maximum_ph: ModelParameter
    minimum_available_p_kg_ha: ModelParameter
    maximum_available_p_kg_ha: ModelParameter
    classification: Literal[ParameterSource.SCENARIO_ASSUMPTION]
    provenance: Annotated[str, Field(min_length=1)]

    @model_validator(mode="after")
    def validate_config(self) -> Self:
        """Require conservative split, range and integer-spin-up settings."""
        split_total = (
            self.split_train_fraction + self.split_validation_fraction + self.split_test_fraction
        )
        if not math.isclose(split_total, 1.0, rel_tol=0.0, abs_tol=1.0e-12):
            raise ValueError("population split fractions must sum to 1")
        if set(self.archetype_ood_archetypes) & set(self.weather_ood_regions):
            raise ValueError("OOD archetype names and weather region IDs must be distinct")
        for lower, upper, label in (
            (self.minimum_soc_t_c_ha, self.maximum_soc_t_c_ha, "SOC"),
            (
                self.minimum_bulk_density_g_cm3,
                self.maximum_bulk_density_g_cm3,
                "bulk density",
            ),
            (self.minimum_ph, self.maximum_ph, "pH"),
            (
                self.minimum_available_p_kg_ha,
                self.maximum_available_p_kg_ha,
                "available P",
            ),
        ):
            if lower.default >= upper.default:
                raise ValueError(f"minimum {label} must be less than maximum {label}")
        if not self.spinup_max_years.default.is_integer():
            raise ValueError("spinup_max_years must be a whole number")
        return self

    def stable_hash(self) -> str:
        """Return the deterministic semantic SHA-256 configuration hash."""
        canonical = json.dumps(
            self.model_dump(mode="json"),
            allow_nan=False,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )
        return hashlib.sha256(canonical.encode()).hexdigest()


class UncertaintyDraw(ContractModel):
    """One explicit provisional latent biological parameter draw."""

    name: Annotated[str, Field(min_length=1)]
    value: Annotated[float, Field(allow_inf_nan=False)]
    unit: Annotated[str, Field(min_length=1)]
    distribution: Annotated[str, Field(min_length=1)]
    distribution_parameters: Annotated[str, Field(min_length=1)]
    classification: ParameterSource
    random_seed: NonNegativeInt
    provenance: Annotated[str, Field(min_length=1)]


class SpinUpDiagnostic(ContractModel):
    """Traceable RothC-compatible pool spin-up result."""

    years_run: Annotated[int, Field(ge=1)]
    converged: bool
    relative_cycle_change: NonNegativeFloat
    target_soc_t_c_ha: NonNegativeFloat
    achieved_soc_t_c_ha: NonNegativeFloat
    equilibrium_annual_input_t_c_ha: NonNegativeFloat
    method: Literal["scaled_periodic_rothc_spinup"] = "scaled_periodic_rothc_spinup"
    classification: Literal[ParameterSource.SCENARIO_ASSUMPTION]
    provenance: Annotated[str, Field(min_length=1)]


class SyntheticField(ContractModel):
    """One accepted virtual field and every input needed for deterministic replay."""

    field: FieldProperties
    empirical_seed_id: Annotated[str, Field(min_length=1)]
    region_id: Annotated[str, Field(min_length=1)]
    archetype: Annotated[str, Field(min_length=1)]
    population_split: PopulationSplit
    management_history: Annotated[str, Field(min_length=1)]
    intervention_eligibility: Annotated[tuple[str, ...], Field(min_length=1)]
    initial_state: FieldState
    weather: Annotated[tuple[WeatherMonth, ...], Field(min_length=12)]
    weather_year_ids: Annotated[tuple[str, ...], Field(min_length=1)]
    uncertainty_draws: Annotated[tuple[UncertaintyDraw, ...], Field(min_length=1)]
    spinup: SpinUpDiagnostic
    generation_seed: NonNegativeInt
    weather_seed: NonNegativeInt
    biological_parameter_seed: NonNegativeInt
    qc_passed: bool
    provenance: Annotated[str, Field(min_length=1)]

    @model_validator(mode="after")
    def validate_weather_blocks_and_carbon(self) -> Self:
        """Require complete weather years and coherent starting carbon totals."""
        if len(self.weather) != 12 * len(self.weather_year_ids):
            raise ValueError("weather must contain complete years matching weather_year_ids")
        for offset in range(0, len(self.weather), 12):
            if [month.month for month in self.weather[offset : offset + 12]] != list(range(1, 13)):
                raise ValueError("each sampled weather block must contain months 1--12")
        state_c = math.fsum(
            (
                self.initial_state.amf_live_c,
                self.initial_state.amf_necromass_c,
                self.initial_state.dpm_c,
                self.initial_state.rpm_c,
                self.initial_state.microbial_c,
                self.initial_state.protected_soc_c,
                self.initial_state.iom_c,
            )
        )
        if not math.isclose(
            state_c,
            self.field.baseline_soc_t_c_ha,
            rel_tol=0.0,
            abs_tol=1.0e-7,
        ):
            raise ValueError("initial carbon stocks must equal baseline SOC")
        return self

    def uncertainty_value(self, name: str) -> float:
        """Return one named draw or fail loudly if the manifest is incomplete."""
        for draw in self.uncertainty_draws:
            if draw.name == name:
                return draw.value
        raise KeyError(name)


class RejectionRecord(ContractModel):
    """A rejected candidate and all deterministic quality-control reasons."""

    candidate_id: Annotated[str, Field(min_length=1)]
    empirical_seed_id: Annotated[str, Field(min_length=1)]
    reasons: Annotated[tuple[str, ...], Field(min_length=1)]


class FieldManifestEntry(ContractModel):
    """Compact field-level provenance retained in the population manifest."""

    field_id: Annotated[str, Field(min_length=1)]
    empirical_seed_id: Annotated[str, Field(min_length=1)]
    region_id: Annotated[str, Field(min_length=1)]
    archetype: Annotated[str, Field(min_length=1)]
    population_split: PopulationSplit
    weather_year_ids: Annotated[tuple[str, ...], Field(min_length=1)]
    uncertainty_draws: Annotated[tuple[UncertaintyDraw, ...], Field(min_length=1)]


class PopulationManifest(ContractModel):
    """Versioned deterministic population manifest with data and rejection provenance."""

    manifest_version: Literal["0.7.0"] = "0.7.0"
    model_version: Annotated[str, Field(min_length=1)]
    generation_seed: NonNegativeInt
    weather_resampling_seed: NonNegativeInt | None = None
    biological_parameter_seed: NonNegativeInt | None = None
    configuration_hash: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
    model_configuration_hash: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
    dataset_name: Annotated[str, Field(min_length=1)]
    dataset_version: Annotated[str, Field(min_length=1)]
    adapter_name: Annotated[str, Field(min_length=1)]
    adapter_version: Annotated[str, Field(min_length=1)]
    source_datasets: Annotated[tuple[VersionedInput, ...], Field(min_length=1)]
    fields: tuple[FieldManifestEntry, ...]
    rejections: tuple[RejectionRecord, ...]
    accepted_count: NonNegativeInt
    rejected_count: NonNegativeInt
    population_hash: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
    uncertainty_status: Literal["phase_7_provisional_population_not_field_validation"] = (
        "phase_7_provisional_population_not_field_validation"
    )
    provenance: Annotated[str, Field(min_length=1)]


class SyntheticPopulation(ContractModel):
    """Accepted virtual fields plus a complete generation manifest."""

    fields: tuple[SyntheticField, ...]
    manifest: PopulationManifest


class PopulationQcResult(ContractModel):
    """Strict deterministic quality-control decision for one candidate field."""

    passed: bool
    reasons: tuple[str, ...]


class PopulationBatchFieldResult(ContractModel):
    """Compact Phase 6 outcome for one synthetic field and eligible policy."""

    field_id: Annotated[str, Field(min_length=1)]
    policy_id: Annotated[str, Field(min_length=1)]
    simulation_horizon_months: Annotated[int, Field(ge=1)]
    population_split: PopulationSplit
    archetype: Annotated[str, Field(min_length=1)]
    yield_t_dm_ha: NonNegativeFloat
    final_total_soc_t_c_ha: NonNegativeFloat
    final_protected_soc_proxy_t_c_ha: NonNegativeFloat
    cumulative_respiration_t_c_ha: NonNegativeFloat
    final_available_phosphorus_kg_p_ha: NonNegativeFloat
    final_amf_live_c_t_ha: NonNegativeFloat
    cost_gbp_ha: NonNegativeFloat
    emissions_proxy_kg_co2e_ha: NonNegativeFloat
    maximum_carbon_residual_t_c_ha: NonNegativeFloat
    maximum_phosphorus_residual_kg_p_ha: NonNegativeFloat


class PopulationBatchFailure(ContractModel):
    """One simulator failure retained instead of being silently discarded."""

    field_id: Annotated[str, Field(min_length=1)]
    policy_id: Annotated[str, Field(min_length=1)]
    reason: Annotated[str, Field(min_length=1)]


class PopulationBatchResult(ContractModel):
    """Phase 6 baseline/intervention outcomes across a synthetic population."""

    population_hash: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
    scenario_version: Annotated[str, Field(min_length=1)]
    results: tuple[PopulationBatchFieldResult, ...]
    failures: tuple[PopulationBatchFailure, ...]
    maximum_carbon_residual_t_c_ha: NonNegativeFloat
    maximum_phosphorus_residual_kg_p_ha: NonNegativeFloat
    uncertainty_status: Literal["phase_7_synthetic_outcomes_not_field_validation"] = (
        "phase_7_synthetic_outcomes_not_field_validation"
    )
