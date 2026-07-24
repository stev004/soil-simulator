"""Immutable contracts for the deterministic Phase 4 plant/P baseline.

Carbon stocks and fluxes use ``t C ha-1``. Available-phosphorus stocks and
fluxes use ``kg P ha-1``. The plant relationships are provisional and are not
calibrated spring-barley agronomy.
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field

from soil_simulator.domain.carbon import CarbonCoreStepResult, RothCForcing
from soil_simulator.domain.enums import ParameterSource
from soil_simulator.domain.models import (
    ContractModel,
    FieldState,
    FluxRecord,
    Fraction,
    NonNegativeFloat,
    NonNegativeInt,
)


class PlantMonth(ContractModel):
    """One calendar month of forcing, available-P input and harvest scheduling."""

    calendar_month: Annotated[int, Field(ge=1, le=12)]
    forcing: RothCForcing
    external_available_p_kg_ha: Annotated[
        NonNegativeFloat, Field(description="External input to available P [kg P ha-1]")
    ] = 0.0
    harvest: bool = False
    classification: Literal[ParameterSource.SCENARIO_ASSUMPTION]
    provenance: Annotated[str, Field(min_length=1)]


class PlantStressDiagnostic(ContractModel):
    """Bounded monthly plant-growth modifiers, each dimensionless in [0, 1]."""

    temperature: Fraction
    moisture: Fraction
    phosphorus: Fraction
    combined: Fraction
    combination_equation: Literal["f_temperature * f_moisture * f_phosphorus"] = (
        "f_temperature * f_moisture * f_phosphorus"
    )


class PhosphorusFluxRecord(ContractModel):
    """One immutable available-phosphorus transfer [kg P ha-1]."""

    month_index: NonNegativeInt
    source_pool: Annotated[str, Field(min_length=1)]
    destination_pool: Annotated[str, Field(min_length=1)]
    amount_kg_p_ha: NonNegativeFloat
    process: Annotated[str, Field(min_length=1)]
    parameter_version: Annotated[str, Field(min_length=1)]
    provenance: Annotated[str, Field(min_length=1)]


class PlantCarbonMassBalanceDiagnostic(ContractModel):
    """Whole Phase 4 carbon-system conservation check [t C ha-1]."""

    month_index: NonNegativeInt
    initial_carbon_t_c_ha: NonNegativeFloat
    npp_inputs_t_c_ha: NonNegativeFloat
    other_external_inputs_t_c_ha: NonNegativeFloat
    respiration_losses_t_c_ha: NonNegativeFloat
    harvest_exports_t_c_ha: NonNegativeFloat
    residue_exports_t_c_ha: NonNegativeFloat
    final_carbon_t_c_ha: NonNegativeFloat
    residual_t_c_ha: float = Field(allow_inf_nan=False)
    relative_residual: NonNegativeFloat
    tolerance_t_c_ha: NonNegativeFloat
    within_tolerance: bool


class PhosphorusMassBalanceDiagnostic(ContractModel):
    """Available-P boundary conservation check [kg P ha-1]."""

    month_index: NonNegativeInt
    initial_available_p_kg_ha: NonNegativeFloat
    external_inputs_kg_p_ha: NonNegativeFloat
    plant_uptake_kg_p_ha: NonNegativeFloat
    final_available_p_kg_ha: NonNegativeFloat
    residual_kg_p_ha: float = Field(allow_inf_nan=False)
    relative_residual: NonNegativeFloat
    tolerance_kg_p_ha: NonNegativeFloat
    within_tolerance: bool


class PlantStepResult(ContractModel):
    """Immutable result of one integrated plant/P/RothC month."""

    initial_state: FieldState
    final_state: FieldState
    potential_npp_t_c_ha: NonNegativeFloat
    realised_npp_t_c_ha: NonNegativeFloat
    stress: PlantStressDiagnostic
    shoot_growth_t_c_ha: NonNegativeFloat
    root_growth_t_c_ha: NonNegativeFloat
    phosphorus_demand_kg_p_ha: NonNegativeFloat
    phosphorus_uptake_kg_p_ha: NonNegativeFloat
    grain_carbon_t_c_ha: NonNegativeFloat
    grain_yield_t_dm_ha: NonNegativeFloat
    harvested_biomass_carbon_t_c_ha: NonNegativeFloat
    aboveground_residue_carbon_t_c_ha: NonNegativeFloat
    root_residue_carbon_t_c_ha: NonNegativeFloat
    residue_to_dpm_t_c_ha: NonNegativeFloat
    residue_to_rpm_t_c_ha: NonNegativeFloat
    carbon_fluxes: tuple[FluxRecord, ...]
    phosphorus_fluxes: tuple[PhosphorusFluxRecord, ...]
    carbon_core: CarbonCoreStepResult
    carbon_mass_balance: PlantCarbonMassBalanceDiagnostic
    phosphorus_mass_balance: PhosphorusMassBalanceDiagnostic
    carbon_unit: Literal["t_C_ha"] = "t_C_ha"
    phosphorus_unit: Literal["kg_P_ha"] = "kg_P_ha"
    uncertainty_status: Literal["provisional_phase_4_not_quantified"] = (
        "provisional_phase_4_not_quantified"
    )
    provenance: Annotated[str, Field(min_length=1)]


class PlantSimulationResult(ContractModel):
    """Immutable deterministic multi-month Phase 4 trajectory."""

    seed: NonNegativeInt
    configuration_hash: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
    initial_state: FieldState
    final_state: FieldState
    steps: tuple[PlantStepResult, ...]
    carbon_fluxes: tuple[FluxRecord, ...]
    phosphorus_fluxes: tuple[PhosphorusFluxRecord, ...]
    cumulative_potential_npp_t_c_ha: NonNegativeFloat
    cumulative_realised_npp_t_c_ha: NonNegativeFloat
    cumulative_phosphorus_uptake_kg_p_ha: NonNegativeFloat
    cumulative_grain_yield_t_dm_ha: NonNegativeFloat
    cumulative_residue_to_dpm_t_c_ha: NonNegativeFloat
    cumulative_residue_to_rpm_t_c_ha: NonNegativeFloat
    cumulative_carbon_mass_balance: PlantCarbonMassBalanceDiagnostic
    cumulative_phosphorus_mass_balance: PhosphorusMassBalanceDiagnostic
    carbon_unit: Literal["t_C_ha"] = "t_C_ha"
    phosphorus_unit: Literal["kg_P_ha"] = "kg_P_ha"
    uncertainty_status: Literal["provisional_phase_4_not_quantified"] = (
        "provisional_phase_4_not_quantified"
    )
    provenance: Annotated[str, Field(min_length=1)]


class PlantScenario(ContractModel):
    """Versioned deterministic spring-barley baseline for the Phase 4 CLI."""

    name: Annotated[str, Field(min_length=1)]
    version: Annotated[str, Field(min_length=1)]
    seed: NonNegativeInt
    initial_state: FieldState
    monthly_steps: Annotated[tuple[PlantMonth, ...], Field(min_length=1)]
    classification: Literal[ParameterSource.SCENARIO_ASSUMPTION]
    provenance: Annotated[str, Field(min_length=1)]
