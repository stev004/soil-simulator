"""Immutable contracts for the deterministic Phase 5 AMF extension."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field

from soil_simulator.domain.carbon import CarbonCoreStepResult
from soil_simulator.domain.models import (
    ContractModel,
    FieldState,
    FluxRecord,
    Fraction,
    NonNegativeFloat,
    NonNegativeInt,
)
from soil_simulator.domain.plant import (
    PhosphorusFluxRecord,
    PlantCarbonMassBalanceDiagnostic,
    PlantStressDiagnostic,
)

AmfPlantOutcome = Literal["beneficial", "neutral", "harmful"]


class AmfPhosphorusMassBalanceDiagnostic(ContractModel):
    """Available-P conservation with direct and fungal withdrawals [kg P ha-1]."""

    month_index: NonNegativeInt
    initial_available_p_kg_ha: NonNegativeFloat
    external_inputs_kg_p_ha: NonNegativeFloat
    direct_plant_uptake_kg_p_ha: NonNegativeFloat
    amf_acquisition_kg_p_ha: NonNegativeFloat
    final_available_p_kg_ha: NonNegativeFloat
    residual_kg_p_ha: float = Field(allow_inf_nan=False)
    relative_residual: NonNegativeFloat
    tolerance_kg_p_ha: NonNegativeFloat
    within_tolerance: bool


class AmfStepResult(ContractModel):
    """Immutable result of one integrated plant--AMF--P--RothC month."""

    initial_state: FieldState
    final_state: FieldState
    potential_npp_t_c_ha: NonNegativeFloat
    gross_realised_plant_carbon_t_c_ha: NonNegativeFloat
    no_amf_counterfactual_plant_carbon_t_c_ha: NonNegativeFloat
    plant_to_amf_carbon_t_c_ha: NonNegativeFloat
    effective_amf_allocation_fraction: Fraction
    net_plant_carbon_t_c_ha: NonNegativeFloat
    net_plant_carbon_effect_t_c_ha: float = Field(allow_inf_nan=False)
    plant_outcome: AmfPlantOutcome
    stress: PlantStressDiagnostic
    shoot_growth_t_c_ha: NonNegativeFloat
    root_growth_t_c_ha: NonNegativeFloat
    fungal_biomass_growth_t_c_ha: NonNegativeFloat
    fungal_maintenance_respiration_t_c_ha: NonNegativeFloat
    fungal_growth_respiration_t_c_ha: NonNegativeFloat
    fungal_respiration_t_c_ha: NonNegativeFloat
    fungal_turnover_t_c_ha: NonNegativeFloat
    necromass_decomposition_t_c_ha: NonNegativeFloat
    necromass_to_dpm_t_c_ha: NonNegativeFloat
    necromass_to_rpm_t_c_ha: NonNegativeFloat
    necromass_to_protected_t_c_ha: NonNegativeFloat
    phosphorus_demand_kg_p_ha: NonNegativeFloat
    direct_plant_phosphorus_uptake_kg_p_ha: NonNegativeFloat
    amf_phosphorus_acquired_kg_p_ha: NonNegativeFloat
    amf_phosphorus_transferred_kg_p_ha: NonNegativeFloat
    amf_phosphorus_retained_kg_p_ha: NonNegativeFloat
    total_plant_phosphorus_received_kg_p_ha: NonNegativeFloat
    grain_carbon_t_c_ha: NonNegativeFloat
    grain_yield_t_dm_ha: NonNegativeFloat
    no_amf_counterfactual_grain_yield_t_dm_ha: NonNegativeFloat
    net_yield_effect_t_dm_ha: float = Field(allow_inf_nan=False)
    harvested_biomass_carbon_t_c_ha: NonNegativeFloat
    aboveground_residue_carbon_t_c_ha: NonNegativeFloat
    root_residue_carbon_t_c_ha: NonNegativeFloat
    residue_to_dpm_t_c_ha: NonNegativeFloat
    residue_to_rpm_t_c_ha: NonNegativeFloat
    carbon_fluxes: tuple[FluxRecord, ...]
    phosphorus_fluxes: tuple[PhosphorusFluxRecord, ...]
    carbon_core: CarbonCoreStepResult
    carbon_mass_balance: PlantCarbonMassBalanceDiagnostic
    phosphorus_mass_balance: AmfPhosphorusMassBalanceDiagnostic
    carbon_unit: Literal["t_C_ha"] = "t_C_ha"
    phosphorus_unit: Literal["kg_P_ha"] = "kg_P_ha"
    uncertainty_status: Literal["provisional_phase_5_not_quantified"] = (
        "provisional_phase_5_not_quantified"
    )
    provenance: Annotated[str, Field(min_length=1)]


class AmfSimulationResult(ContractModel):
    """Immutable deterministic multi-month Phase 5 AMF trajectory."""

    seed: NonNegativeInt
    configuration_hash: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
    initial_state: FieldState
    final_state: FieldState
    steps: tuple[AmfStepResult, ...]
    carbon_fluxes: tuple[FluxRecord, ...]
    phosphorus_fluxes: tuple[PhosphorusFluxRecord, ...]
    cumulative_potential_npp_t_c_ha: NonNegativeFloat
    cumulative_gross_realised_plant_carbon_t_c_ha: NonNegativeFloat
    cumulative_no_amf_counterfactual_plant_carbon_t_c_ha: NonNegativeFloat
    cumulative_plant_to_amf_carbon_t_c_ha: NonNegativeFloat
    cumulative_net_plant_carbon_t_c_ha: NonNegativeFloat
    cumulative_net_plant_carbon_effect_t_c_ha: float = Field(allow_inf_nan=False)
    cumulative_fungal_respiration_t_c_ha: NonNegativeFloat
    cumulative_fungal_turnover_t_c_ha: NonNegativeFloat
    cumulative_necromass_to_dpm_t_c_ha: NonNegativeFloat
    cumulative_necromass_to_rpm_t_c_ha: NonNegativeFloat
    cumulative_necromass_to_protected_t_c_ha: NonNegativeFloat
    cumulative_amf_phosphorus_acquired_kg_p_ha: NonNegativeFloat
    cumulative_amf_phosphorus_transferred_kg_p_ha: NonNegativeFloat
    cumulative_direct_plant_phosphorus_uptake_kg_p_ha: NonNegativeFloat
    cumulative_grain_yield_t_dm_ha: NonNegativeFloat
    cumulative_no_amf_counterfactual_grain_yield_t_dm_ha: NonNegativeFloat
    cumulative_net_yield_effect_t_dm_ha: float = Field(allow_inf_nan=False)
    cumulative_residue_to_dpm_t_c_ha: NonNegativeFloat
    cumulative_residue_to_rpm_t_c_ha: NonNegativeFloat
    cumulative_carbon_mass_balance: PlantCarbonMassBalanceDiagnostic
    cumulative_phosphorus_mass_balance: AmfPhosphorusMassBalanceDiagnostic
    carbon_unit: Literal["t_C_ha"] = "t_C_ha"
    phosphorus_unit: Literal["kg_P_ha"] = "kg_P_ha"
    uncertainty_status: Literal["provisional_phase_5_not_quantified"] = (
        "provisional_phase_5_not_quantified"
    )
    provenance: Annotated[str, Field(min_length=1)]
