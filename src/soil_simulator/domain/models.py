"""Pydantic contracts for fields, configuration, weather, events, and provenance.

Carbon stocks and fluxes use ``t C ha-1``. Weather water quantities use
``mm month-1`` and temperatures use degrees Celsius. ``protected_soc_c`` is a
model proxy and must not be interpreted as measured MAOC.
"""

from __future__ import annotations

import hashlib
import json
import math
from datetime import date, datetime
from itertools import pairwise
from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from soil_simulator.domain.enums import ExternalInputTiming, ManagementEventType, ParameterSource

FiniteFloat = Annotated[float, Field(allow_inf_nan=False)]
NonNegativeFloat = Annotated[float, Field(ge=0.0, allow_inf_nan=False)]
PositiveFloat = Annotated[float, Field(gt=0.0, allow_inf_nan=False)]
Fraction = Annotated[float, Field(ge=0.0, le=1.0, allow_inf_nan=False)]
Percent = Annotated[float, Field(ge=0.0, le=100.0, allow_inf_nan=False)]
NonNegativeInt = Annotated[int, Field(ge=0)]

# The source specification says texture totals must be approximate but does not
# prescribe a tolerance. One hundredth of a percentage point accepts ordinary
# decimal rounding while rejecting materially inconsistent compositions.
TEXTURE_SUM_TOLERANCE_PERCENT = 0.01


class ContractModel(BaseModel):
    """Strict immutable base for scientific contracts."""

    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)


class FieldProperties(ContractModel):
    """Immutable topsoil properties, units, identity, and source provenance.

    Texture is expressed as percent by mass for the 0--23 cm mineral topsoil
    layer. Stocks are non-negative and SOC is in ``t C ha-1``.
    """

    field_id: Annotated[str, Field(min_length=1, description="Stable field identifier")]
    latitude_deg: Annotated[
        FiniteFloat | None,
        Field(default=None, ge=-90.0, le=90.0, description="Latitude [decimal degrees]"),
    ]
    longitude_deg: Annotated[
        FiniteFloat | None,
        Field(default=None, ge=-180.0, le=180.0, description="Longitude [decimal degrees]"),
    ]
    synthetic_archetype: Annotated[
        str | None,
        Field(default=None, min_length=1, description="Named synthetic field archetype"),
    ]
    soil_depth_cm: Annotated[PositiveFloat, Field(description="Modelled soil depth [cm]")]
    clay_percent: Annotated[Percent, Field(description="Clay content [% mass]")]
    silt_percent: Annotated[Percent, Field(description="Silt content [% mass]")]
    sand_percent: Annotated[Percent, Field(description="Sand content [% mass]")]
    bulk_density_g_cm3: Annotated[
        PositiveFloat, Field(description="Dry soil bulk density [g cm-3]")
    ]
    ph: Annotated[FiniteFloat, Field(ge=0.0, le=14.0, description="Soil pH [dimensionless]")]
    cation_exchange_capacity_cmolc_kg: Annotated[
        NonNegativeFloat, Field(description="Cation exchange capacity [cmol(c) kg-1]")
    ]
    baseline_total_nitrogen_percent: Annotated[
        NonNegativeFloat, Field(description="Baseline total nitrogen [% mass]")
    ]
    baseline_soc_t_c_ha: Annotated[
        NonNegativeFloat, Field(description="Baseline soil organic carbon stock [t C ha-1]")
    ]
    drainage_class: Annotated[str, Field(min_length=1, description="Documented drainage class")]
    climate_normal_id: Annotated[
        str, Field(min_length=1, description="Identifier for the climate normal source")
    ]
    provenance: Annotated[
        str, Field(min_length=1, description="Source or generation provenance for field properties")
    ]

    @model_validator(mode="after")
    def validate_texture_and_location(self) -> Self:
        """Require a valid texture composition and a coordinate pair or archetype."""
        texture_total = self.clay_percent + self.silt_percent + self.sand_percent
        if not math.isclose(
            texture_total,
            100.0,
            rel_tol=0.0,
            abs_tol=TEXTURE_SUM_TOLERANCE_PERCENT,
        ):
            raise ValueError(
                "clay_percent, silt_percent and sand_percent must sum to "
                f"100 +/- {TEXTURE_SUM_TOLERANCE_PERCENT} percentage points"
            )
        has_latitude = self.latitude_deg is not None
        has_longitude = self.longitude_deg is not None
        if has_latitude != has_longitude:
            raise ValueError("latitude_deg and longitude_deg must be supplied together")
        if not (has_latitude or self.synthetic_archetype):
            raise ValueError("supply a coordinate pair or synthetic_archetype")
        return self


class FieldState(ContractModel):
    """Immutable monthly state; carbon pools use ``t C ha-1``.

    ``protected_soc_c`` is the model's humified/protected SOC proxy, not a
    measurement of mineral-associated organic carbon.
    """

    month_index: Annotated[NonNegativeInt, Field(description="Zero-based simulation month")]
    plant_c: Annotated[NonNegativeFloat, Field(description="Plant carbon [t C ha-1]")]
    root_c: Annotated[NonNegativeFloat, Field(description="Root carbon [t C ha-1]")]
    amf_live_c: Annotated[NonNegativeFloat, Field(description="Live AMF carbon [t C ha-1]")]
    amf_necromass_c: Annotated[
        NonNegativeFloat, Field(description="AMF necromass carbon [t C ha-1]")
    ]
    dpm_c: Annotated[
        NonNegativeFloat, Field(description="Decomposable plant material carbon [t C ha-1]")
    ]
    rpm_c: Annotated[
        NonNegativeFloat, Field(description="Resistant plant material carbon [t C ha-1]")
    ]
    microbial_c: Annotated[
        NonNegativeFloat, Field(description="Non-AMF microbial carbon proxy [t C ha-1]")
    ]
    protected_soc_c: Annotated[
        NonNegativeFloat, Field(description="Humified/protected SOC model proxy [t C ha-1]")
    ]
    iom_c: Annotated[NonNegativeFloat, Field(description="Inert organic matter carbon [t C ha-1]")]
    available_p_kg_ha: Annotated[
        NonNegativeFloat, Field(description="Available phosphorus [kg P ha-1]")
    ]
    topsoil_moisture_deficit_mm: Annotated[
        FiniteFloat,
        Field(
            le=0.0,
            description=(
                "Accumulated RothC topsoil moisture deficit [mm]; 0 is field capacity "
                "and increasingly negative values are progressively drier"
            ),
        ),
    ]
    crop_development: Annotated[Fraction, Field(description="Crop development fraction [0--1]")]
    cumulative_yield_t_dm_ha: Annotated[
        NonNegativeFloat, Field(description="Cumulative harvested yield [t dry matter ha-1]")
    ]
    aggregate_protection_index: Annotated[
        Fraction | None,
        Field(default=None, description="Optional aggregate protection index [0--1]"),
    ]


class WeatherMonth(ContractModel):
    """One month of weather forcing with explicit units and provenance."""

    year: Annotated[int, Field(ge=1, description="Calendar year")]
    month: Annotated[int, Field(ge=1, le=12, description="Calendar month [1--12]")]
    mean_air_temperature_c: Annotated[
        FiniteFloat, Field(description="Monthly mean air temperature [deg C]")
    ]
    precipitation_mm: Annotated[
        NonNegativeFloat, Field(description="Monthly total precipitation [mm month-1]")
    ]
    potential_evapotranspiration_mm: Annotated[
        NonNegativeFloat,
        Field(description="Monthly potential evapotranspiration [mm month-1]"),
    ]
    source_id: Annotated[str, Field(min_length=1, description="Weather dataset/version identifier")]
    provenance: Annotated[str, Field(min_length=1, description="Weather record provenance")]


class EventParameter(ContractModel):
    """Typed scalar parameter attached to a management event."""

    name: Annotated[str, Field(min_length=1, description="Event parameter name")]
    value: FiniteFloat | str | bool
    unit: Annotated[str | None, Field(default=None, description="Physical unit, when applicable")]


class ManagementEvent(ContractModel):
    """One immutable scheduled intervention with explicit units and provenance.

    Exactly one of ``event_date`` and ``simulation_month`` identifies the
    monthly time step. ``amount`` uses the event-specific units validated
    below; costs and emissions proxies are accounting outputs and do not enter
    the carbon kernel.
    """

    event_id: Annotated[str, Field(min_length=1, description="Stable event identifier")]
    event_type: ManagementEventType
    event_date: Annotated[date | None, Field(default=None, description="Scheduled calendar date")]
    simulation_month: Annotated[
        NonNegativeInt | None,
        Field(default=None, description="Zero-based scheduled simulation month"),
    ]
    amount: Annotated[NonNegativeFloat, Field(description="Intervention amount")]
    units: Annotated[str, Field(min_length=1, description="Intervention amount units")]
    parameters: tuple[EventParameter, ...] = ()
    cost_gbp_ha: Annotated[NonNegativeFloat, Field(description="Management cost [GBP ha-1]")]
    emissions_proxy_kg_co2e_ha: Annotated[
        NonNegativeFloat, Field(description="Embodied emissions-proxy amount")
    ]
    parameter_provenance: Annotated[
        str, Field(min_length=1, description="Configuration/effect parameter provenance")
    ]
    source_classification: ParameterSource
    provenance: Annotated[str, Field(min_length=1, description="Event definition provenance")]

    @model_validator(mode="after")
    def validate_schedule_units_and_parameters(self) -> Self:
        """Require one timing form, event-specific units, and unique parameters."""
        if (self.event_date is None) == (self.simulation_month is None):
            raise ValueError("supply exactly one of event_date or simulation_month")
        expected_units = {
            ManagementEventType.TILLAGE: "operation_ha^-1",
            ManagementEventType.COVER_CROP_ESTABLISHMENT: "event",
            ManagementEventType.COVER_CROP_TERMINATION: "event",
            ManagementEventType.PHOSPHORUS_APPLICATION: "kg_P_ha^-1",
            ManagementEventType.FARMYARD_MANURE: "t_C_ha^-1",
        }
        if self.units != expected_units[self.event_type]:
            raise ValueError(
                f"{self.event_type.value} events require units '{expected_units[self.event_type]}'"
            )
        if self.event_type in {
            ManagementEventType.TILLAGE,
            ManagementEventType.COVER_CROP_ESTABLISHMENT,
            ManagementEventType.COVER_CROP_TERMINATION,
        } and not math.isclose(self.amount, 1.0, rel_tol=0.0, abs_tol=0.0):
            raise ValueError(f"{self.event_type.value} events require amount 1")
        names = [parameter.name for parameter in self.parameters]
        if len(names) != len(set(names)):
            raise ValueError("management event parameter names must be unique")
        tillage_levels = [p for p in self.parameters if p.name == "tillage_level"]
        if self.event_type is ManagementEventType.TILLAGE:
            if len(tillage_levels) != 1 or tillage_levels[0].value not in {
                "conventional",
                "reduced",
                "no_till",
            }:
                raise ValueError("tillage events require a valid tillage_level parameter")
        elif tillage_levels:
            raise ValueError("tillage_level is only valid for tillage events")
        return self


class ModelParameter(ContractModel):
    """A bounded, unit-aware scientific parameter and its source classification."""

    name: Annotated[str, Field(min_length=1, description="Stable parameter name")]
    default: Annotated[FiniteFloat, Field(description="Default parameter value")]
    minimum: Annotated[FiniteFloat, Field(alias="min", description="Allowed minimum")]
    maximum: Annotated[FiniteFloat, Field(alias="max", description="Allowed maximum")]
    unit: Annotated[str, Field(min_length=1, description="Physical unit or 'dimensionless'")]
    classification: ParameterSource
    distribution: Annotated[
        str | None, Field(default=None, min_length=1, description="Uncertainty distribution name")
    ]
    source_citation: Annotated[
        str | None, Field(default=None, min_length=1, description="Source citation identifier")
    ]
    notes: Annotated[
        str | None, Field(default=None, min_length=1, description="Scientific qualification")
    ]
    version_introduced: Annotated[
        str, Field(min_length=1, description="First model version containing this parameter")
    ]

    @model_validator(mode="after")
    def validate_bounds(self) -> Self:
        """Require ordered bounds, an in-range default, and valid fraction metadata."""
        if self.minimum > self.maximum:
            raise ValueError("min must be less than or equal to max")
        if not self.minimum <= self.default <= self.maximum:
            raise ValueError("default must lie within [min, max]")
        if self.unit == "fraction" and not (0.0 <= self.minimum <= self.maximum <= 1.0):
            raise ValueError("parameters with unit 'fraction' must have bounds within [0, 1]")
        return self


class ModelMetadata(ContractModel):
    """Identity and time/space boundary of the configured research model."""

    name: Annotated[str, Field(min_length=1, description="Model name")]
    version: Annotated[str, Field(min_length=1, description="Model configuration version")]
    timestep_months: Annotated[Literal[1], Field(description="Simulation time step [months]")]
    soil_depth_cm: Annotated[PositiveFloat, Field(description="Modelled topsoil depth [cm]")]
    horizon_years: Annotated[
        int, Field(ge=1, le=100, description="Configured simulation horizon [years]")
    ]
    carbon_unit: Literal["t_C_ha"]


class RothCParameters(ContractModel):
    """Established RothC reference constants from the source specification."""

    classification: Literal[ParameterSource.ESTABLISHED_MODEL]
    source_citation: Annotated[str, Field(min_length=1)]
    external_input_timing: ExternalInputTiming
    k_dpm_year: Annotated[NonNegativeFloat, Field(description="DPM decay rate [year-1]")]
    k_rpm_year: Annotated[NonNegativeFloat, Field(description="RPM decay rate [year-1]")]
    k_microbial_year: Annotated[
        NonNegativeFloat, Field(description="Microbial biomass decay rate [year-1]")
    ]
    k_protected_year: Annotated[
        NonNegativeFloat, Field(description="Protected/humified pool decay rate [year-1]")
    ]
    crop_dpm_rpm_ratio: Annotated[
        PositiveFloat, Field(description="Crop decomposable-to-resistant material ratio")
    ]
    retained_to_microbial_fraction: Fraction
    retained_to_protected_fraction: Fraction
    manure_dpm_fraction: Fraction
    manure_rpm_fraction: Fraction
    manure_protected_fraction: Fraction
    iom_coefficient: Annotated[PositiveFloat, Field(description="RothC IOM coefficient")]
    iom_exponent: Annotated[PositiveFloat, Field(description="RothC IOM exponent")]
    temperature_numerator: PositiveFloat
    temperature_exponent_numerator: PositiveFloat
    temperature_offset_c: PositiveFloat
    temperature_cutoff_c: FiniteFloat
    evapotranspiration_from_open_pan_fraction: Fraction
    maximum_tsmd_base_mm: PositiveFloat
    maximum_tsmd_clay_linear: PositiveFloat
    maximum_tsmd_clay_quadratic: PositiveFloat
    reference_soil_depth_cm: PositiveFloat
    moisture_threshold_fraction: Fraction
    bare_soil_maximum_tsmd_fraction: Fraction
    moisture_modifier_minimum: Fraction
    moisture_modifier_maximum: Fraction
    covered_soil_modifier: Fraction
    bare_soil_modifier: Fraction
    co2_retained_ratio_scale: PositiveFloat
    co2_retained_ratio_intercept: PositiveFloat
    co2_retained_ratio_clay_scale: PositiveFloat
    co2_retained_ratio_clay_exponent: PositiveFloat

    @model_validator(mode="after")
    def validate_partitions(self) -> Self:
        """Require each documented carbon partition to conserve its source amount."""
        retained_total = self.retained_to_microbial_fraction + self.retained_to_protected_fraction
        if not math.isclose(retained_total, 1.0, rel_tol=0.0, abs_tol=1.0e-12):
            raise ValueError("retained carbon fractions must sum to 1")
        manure_total = (
            self.manure_dpm_fraction + self.manure_rpm_fraction + self.manure_protected_fraction
        )
        if not math.isclose(manure_total, 1.0, rel_tol=0.0, abs_tol=1.0e-12):
            raise ValueError("manure carbon fractions must sum to 1")
        if self.moisture_modifier_minimum > self.moisture_modifier_maximum:
            raise ValueError("moisture modifier minimum cannot exceed maximum")
        return self


class PlantParameters(ContractModel):
    """Configuration for the provisional monthly spring-barley baseline."""

    crop: Literal["spring_barley"]
    monthly_npp_profile: tuple[Fraction, ...]
    monthly_npp_profile_classification: Literal[ParameterSource.SCENARIO_ASSUMPTION]
    monthly_npp_profile_source_citation: Annotated[str, Field(min_length=1)]
    annual_potential_npp_t_c_ha: ModelParameter
    temperature_response: tuple[TemperatureResponsePoint, ...]
    temperature_response_classification: Literal[ParameterSource.SCENARIO_ASSUMPTION]
    temperature_response_source_citation: Annotated[str, Field(min_length=1)]
    root_allocation_fraction: ModelParameter
    harvest_index: ModelParameter
    carbon_fraction_of_dry_matter: ModelParameter
    phosphorus_concentration_kg_p_per_kg_dm: ModelParameter
    direct_p_uptake_half_saturation: ModelParameter
    aboveground_residue_retained_fraction: ModelParameter
    root_residue_fraction: ModelParameter

    @model_validator(mode="after")
    def validate_monthly_profile(self) -> Self:
        """Require a normalised profile and an ordered temperature response."""
        if len(self.monthly_npp_profile) != 12:
            raise ValueError("monthly_npp_profile must contain exactly 12 values")
        if not math.isclose(sum(self.monthly_npp_profile), 1.0, rel_tol=0.0, abs_tol=1.0e-12):
            raise ValueError("monthly_npp_profile must sum to 1")
        temperatures = [point.temperature_c for point in self.temperature_response]
        if len(temperatures) < 2:
            raise ValueError("temperature_response must contain at least two points")
        if any(right <= left for left, right in pairwise(temperatures)):
            raise ValueError("temperature_response temperatures must be strictly increasing")
        return self


class TemperatureResponsePoint(ContractModel):
    """One point in a piecewise-linear plant-temperature response curve."""

    temperature_c: FiniteFloat
    modifier: Fraction


class AmfParameters(ContractModel):
    """Validated parameters for the provisional deterministic AMF extension."""

    photosynthate_allocation_fraction: ModelParameter
    allocation_p_feedback_minimum: ModelParameter
    allocation_p_half_saturation: ModelParameter
    carbon_use_efficiency: ModelParameter
    turnover_per_month: ModelParameter
    necromass_decay_year: ModelParameter
    necromass_to_dpm_fraction: ModelParameter
    necromass_to_rpm_fraction: ModelParameter
    necromass_stabilisation_fraction: ModelParameter
    p_uptake_vmax: ModelParameter
    p_uptake_km: ModelParameter
    p_transfer_to_plant_fraction: ModelParameter

    @model_validator(mode="after")
    def validate_necromass_partition(self) -> Self:
        """Require configured necromass destinations to conserve carbon."""
        total = (
            self.necromass_to_dpm_fraction.default
            + self.necromass_to_rpm_fraction.default
            + self.necromass_stabilisation_fraction.default
        )
        if not math.isclose(total, 1.0, rel_tol=0.0, abs_tol=1.0e-12):
            raise ValueError("AMF necromass routing fractions must sum to 1")
        return self


class TillageLevelParameters(ContractModel):
    """One provisional tillage scenario's bounded management assumptions."""

    amf_pulse_mortality: ModelParameter
    amf_turnover_multiplier: ModelParameter
    decomposition_multiplier: ModelParameter
    effect_duration_months: ModelParameter
    soil_cover_suppression_months: ModelParameter
    standing_biomass_incorporation_fraction: ModelParameter

    @model_validator(mode="after")
    def validate_duration_parameters(self) -> Self:
        """Require whole-month durations and non-decreasing rate multipliers."""
        for parameter in (self.effect_duration_months, self.soil_cover_suppression_months):
            if not parameter.default.is_integer():
                raise ValueError(f"{parameter.name} default must be a whole number of months")
        for parameter in (self.amf_turnover_multiplier, self.decomposition_multiplier):
            if parameter.minimum < 1.0:
                raise ValueError(f"{parameter.name} cannot have a minimum below 1")
        return self


class TillageParameters(ContractModel):
    """The three tillage levels included in the v0.1 scope."""

    conventional: TillageLevelParameters
    reduced: TillageLevelParameters
    no_till: TillageLevelParameters


class CoverCropParameters(ContractModel):
    """Provisional generic AM-compatible cover-crop assumptions."""

    monthly_potential_npp_t_c_ha: ModelParameter
    root_allocation_fraction: ModelParameter
    residue_return_fraction: ModelParameter
    phosphorus_return_fraction: ModelParameter
    water_use_open_pan_mm: ModelParameter


class PhosphorusManagementParameters(ContractModel):
    """Traceability metadata for direct available-P applications."""

    classification: Literal[ParameterSource.SCENARIO_ASSUMPTION]
    source_citation: Annotated[str, Field(min_length=1)]


class FarmyardManureParameters(ContractModel):
    """Configured P content for an explicit FYM carbon input."""

    phosphorus_content_kg_p_per_t_c: ModelParameter


class ManagementParameters(ContractModel):
    """Validated Phase 6 intervention-effect assumptions."""

    tillage: TillageParameters
    cover_crop: CoverCropParameters
    phosphorus: PhosphorusManagementParameters
    farmyard_manure: FarmyardManureParameters


class NumericalParameters(ContractModel):
    """Numerical safeguards and deterministic default seed."""

    absolute_mass_balance_tolerance: PositiveFloat
    relative_mass_balance_tolerance: PositiveFloat
    prohibit_negative_pools: Literal[True]
    fail_on_non_finite: Literal[True]
    default_seed: NonNegativeInt


class ModelParameters(ContractModel):
    """Complete validated representation of ``config/model_defaults.yaml``."""

    model: ModelMetadata
    rothc: RothCParameters
    plant: PlantParameters
    amf: AmfParameters
    management: ManagementParameters
    numerics: NumericalParameters

    def canonical_json(self) -> str:
        """Return deterministic semantic JSON, independent of YAML presentation."""
        return json.dumps(
            self.model_dump(mode="json"),
            allow_nan=False,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )

    def stable_hash(self) -> str:
        """Return a SHA-256 hash of validated canonical configuration values."""
        return hashlib.sha256(self.canonical_json().encode("utf-8")).hexdigest()


class VersionedInput(ContractModel):
    """Input dataset identity recorded for reproducibility."""

    name: Annotated[str, Field(min_length=1)]
    version: Annotated[str, Field(min_length=1)]
    provenance: Annotated[str, Field(min_length=1)]


class SimulationManifest(ContractModel):
    """Reproducibility manifest contract for a future simulation run."""

    run_id: Annotated[str, Field(min_length=1, description="Stable run identifier")]
    model_version: Annotated[str, Field(min_length=1)]
    configuration_hash: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
    git_commit: Annotated[str, Field(min_length=1)]
    environment_lockfile: Annotated[str, Field(min_length=1)]
    field_ids: Annotated[tuple[str, ...], Field(min_length=1)]
    policy_ids: Annotated[tuple[str, ...], Field(min_length=1)]
    random_seed: NonNegativeInt
    weather_seed: NonNegativeInt
    biological_parameter_seed: NonNegativeInt
    input_data_versions: tuple[VersionedInput, ...]
    started_at: Annotated[datetime, Field(description="Timezone-aware run start timestamp")]
    completed_at: Annotated[
        datetime | None, Field(default=None, description="Timezone-aware completion timestamp")
    ]
    test_gate_status: Annotated[str, Field(min_length=1)]

    @model_validator(mode="after")
    def validate_timestamps(self) -> Self:
        """Require timezone-aware, chronologically ordered manifest timestamps."""
        if self.started_at.tzinfo is None or self.started_at.utcoffset() is None:
            raise ValueError("started_at must be timezone-aware")
        if self.completed_at is not None:
            if self.completed_at.tzinfo is None or self.completed_at.utcoffset() is None:
                raise ValueError("completed_at must be timezone-aware")
            if self.completed_at < self.started_at:
                raise ValueError("completed_at cannot precede started_at")
        return self


class FluxRecord(ContractModel):
    """One traceable carbon transfer for a future append-only flux ledger."""

    month_index: Annotated[NonNegativeInt, Field(description="Zero-based simulation month")]
    source_pool: Annotated[str, Field(min_length=1)]
    destination_pool: Annotated[str, Field(min_length=1)]
    amount_t_c_ha: Annotated[NonNegativeFloat, Field(description="Carbon amount [t C ha-1]")]
    uncertainty_t_c_ha: Annotated[
        NonNegativeFloat | None,
        Field(default=None, description="Optional absolute uncertainty [t C ha-1]"),
    ]
    process: Annotated[str, Field(min_length=1)]
    parameter_version: Annotated[str, Field(min_length=1)]
    provenance: Annotated[str, Field(min_length=1)]
