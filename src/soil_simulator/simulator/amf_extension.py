"""Deterministic Phase 5 plant--AMF--phosphorus--RothC orchestration."""

from __future__ import annotations

import math
from collections.abc import Iterable
from typing import Final

from soil_simulator.domain.amf import (
    AmfPhosphorusMassBalanceDiagnostic,
    AmfPlantOutcome,
    AmfSimulationResult,
    AmfStepResult,
)
from soil_simulator.domain.carbon import CarbonCoreMonth, CarbonInput
from soil_simulator.domain.enums import (
    AmfCarbonPool,
    CarbonBoundary,
    CarbonPool,
    PhosphorusPool,
)
from soil_simulator.domain.models import (
    FieldState,
    FluxRecord,
    ModelParameters,
    NumericalParameters,
)
from soil_simulator.domain.plant import PhosphorusFluxRecord, PlantMonth, PlantStressDiagnostic
from soil_simulator.processes.amf import (
    acquire_amf_phosphorus,
    allocate_plant_carbon_to_amf,
    decay_and_route_necromass,
    fungal_growth_and_respiration,
    fungal_turnover_t_c_ha,
)
from soil_simulator.processes.phosphorus import (
    direct_phosphorus_uptake_kg_p_ha,
    phosphorus_demand_kg_p_ha,
    phosphorus_stress_modifier,
)
from soil_simulator.processes.plant import (
    allocate_npp,
    combine_stress_modifiers,
    harvest_plant,
    partition_residue_dpm_rpm,
    plant_moisture_modifier,
    plant_temperature_modifier,
    prescribed_potential_npp,
)
from soil_simulator.processes.rothc import moisture_modifier, temperature_modifier
from soil_simulator.simulator.carbon_core import step_carbon_core
from soil_simulator.simulator.errors import MassBalanceError, NumericalSafetyError
from soil_simulator.simulator.plant_baseline import (
    _carbon_balance,
    _carbon_flux,
    _phosphorus_flux,
    _tolerance,
    _validate_state,
    ecosystem_carbon_total,
)

AMF_PROVENANCE: Final = (
    "soil_simulator Phase 5 deterministic AMF extension v0.5.0; provisional relationships "
    "documented in docs/AMF_EXTENSION.md"
)


def _phosphorus_balance(
    *,
    month_index: int,
    initial: float,
    final: float,
    external: float,
    direct_plant_uptake: float,
    amf_acquisition: float,
    numerics: NumericalParameters,
) -> AmfPhosphorusMassBalanceDiagnostic:
    left = initial + external
    right = final + direct_plant_uptake + amf_acquisition
    residual = left - right
    scale, tolerance = _tolerance(left, right, numerics)
    diagnostic = AmfPhosphorusMassBalanceDiagnostic(
        month_index=month_index,
        initial_available_p_kg_ha=initial,
        external_inputs_kg_p_ha=external,
        direct_plant_uptake_kg_p_ha=direct_plant_uptake,
        amf_acquisition_kg_p_ha=amf_acquisition,
        final_available_p_kg_ha=final,
        residual_kg_p_ha=residual,
        relative_residual=abs(residual) / scale if scale > 0.0 else 0.0,
        tolerance_kg_p_ha=tolerance,
        within_tolerance=abs(residual) <= tolerance,
    )
    if not diagnostic.within_tolerance:
        raise MassBalanceError(
            f"month {month_index}: Phase 5 available-P residual {residual:.17g} kg P ha-1 "
            f"exceeds tolerance {tolerance:.17g}"
        )
    return diagnostic


def _outcome(effect: float, numerics: NumericalParameters) -> AmfPlantOutcome:
    if abs(effect) <= numerics.absolute_mass_balance_tolerance:
        return "neutral"
    return "beneficial" if effect > 0.0 else "harmful"


def _step_amf_extension(
    state: FieldState,
    month: PlantMonth,
    parameters: ModelParameters,
    *,
    amf_enabled: bool,
) -> AmfStepResult:
    """Advance the integrated Phase 5 model by one deterministic month."""
    month_index = state.month_index
    forcing = month.forcing
    potential_npp = prescribed_potential_npp(month.calendar_month, parameters.plant)
    temperature_stress = plant_temperature_modifier(
        forcing.mean_air_temperature_c, parameters.plant
    )
    rothc_moisture = moisture_modifier(
        previous_accumulated_tsmd_mm=state.topsoil_moisture_deficit_mm,
        precipitation_mm=forcing.precipitation_mm,
        open_pan_evaporation_mm=forcing.open_pan_evaporation_mm,
        is_covered=forcing.is_covered,
        clay_percent=forcing.clay_percent,
        soil_depth_cm=forcing.soil_depth_cm,
        parameters=parameters.rothc,
    )
    moisture_stress = plant_moisture_modifier(rothc_moisture.modifier, parameters.rothc)
    growth_before_p = potential_npp * temperature_stress * moisture_stress
    p_demand = phosphorus_demand_kg_p_ha(
        growth_before_p,
        parameters.plant.carbon_fraction_of_dry_matter.default,
        parameters.plant.phosphorus_concentration_kg_p_per_kg_dm.default,
    )
    available_after_input = state.available_p_kg_ha + month.external_available_p_kg_ha

    host_activity = 1.0 if amf_enabled and growth_before_p > 0.0 else 0.0
    amf_p = acquire_amf_phosphorus(
        live_biomass_t_c_ha=state.amf_live_c,
        available_p_kg_ha=available_after_input,
        vmax_kg_p_per_t_amf_c_month=parameters.amf.p_uptake_vmax.default,
        half_saturation_kg_p_ha=parameters.amf.p_uptake_km.default,
        temperature_modifier=temperature_stress * host_activity,
        moisture_modifier=moisture_stress,
        transfer_to_plant_fraction=parameters.amf.p_transfer_to_plant_fraction.default,
    )
    available_after_amf = available_after_input - amf_p.acquired_kg_p_ha
    unmet_after_amf_transfer = max(0.0, p_demand - amf_p.transferred_to_plant_kg_p_ha)
    direct_p_uptake = direct_phosphorus_uptake_kg_p_ha(
        available_after_amf,
        unmet_after_amf_transfer,
        parameters.plant.direct_p_uptake_half_saturation.default,
    )
    final_available_p = available_after_amf - direct_p_uptake
    if final_available_p < 0.0:
        if abs(final_available_p) <= parameters.numerics.absolute_mass_balance_tolerance:
            final_available_p = 0.0
        else:
            raise NumericalSafetyError(
                f"month {month_index}: available P became negative ({final_available_p})"
            )

    total_plant_p = direct_p_uptake + amf_p.transferred_to_plant_kg_p_ha
    phosphorus_stress = phosphorus_stress_modifier(total_plant_p, p_demand)
    combined_stress = combine_stress_modifiers(
        temperature_stress, moisture_stress, phosphorus_stress
    )
    gross_realised = potential_npp * combined_stress

    no_amf_direct_p = direct_phosphorus_uptake_kg_p_ha(
        available_after_input,
        p_demand,
        parameters.plant.direct_p_uptake_half_saturation.default,
    )
    no_amf_p_stress = phosphorus_stress_modifier(no_amf_direct_p, p_demand)
    no_amf_combined = combine_stress_modifiers(temperature_stress, moisture_stress, no_amf_p_stress)
    no_amf_realised = potential_npp * no_amf_combined

    carbon_allocation = allocate_plant_carbon_to_amf(
        realised_plant_carbon_t_c_ha=gross_realised,
        base_fraction=parameters.amf.photosynthate_allocation_fraction.default,
        available_p_kg_ha=available_after_input,
        p_feedback_minimum=parameters.amf.allocation_p_feedback_minimum.default,
        p_feedback_half_saturation_kg_p_ha=(parameters.amf.allocation_p_half_saturation.default),
        environmental_modifier=temperature_stress * moisture_stress,
        maximum_fraction=parameters.amf.photosynthate_allocation_fraction.maximum,
        host_active=amf_enabled and growth_before_p > 0.0,
    )
    turnover = (
        fungal_turnover_t_c_ha(state.amf_live_c, parameters.amf.turnover_per_month.default)
        if amf_enabled
        else 0.0
    )
    fungal_carbon = fungal_growth_and_respiration(
        allocated_carbon_t_c_ha=carbon_allocation.allocated_t_c_ha,
        carbon_use_efficiency=parameters.amf.carbon_use_efficiency.default,
        turnover_t_c_ha=turnover,
    )
    rothc_temperature = temperature_modifier(forcing.mean_air_temperature_c, parameters.rothc)
    necromass = decay_and_route_necromass(
        necromass_t_c_ha=state.amf_necromass_c,
        decay_rate_year=parameters.amf.necromass_decay_year.default,
        temperature_modifier=rothc_temperature,
        moisture_modifier=rothc_moisture.modifier,
        to_dpm_fraction=parameters.amf.necromass_to_dpm_fraction.default,
        to_rpm_fraction=parameters.amf.necromass_to_rpm_fraction.default,
        to_protected_fraction=parameters.amf.necromass_stabilisation_fraction.default,
    )
    plant_allocation = allocate_npp(
        carbon_allocation.net_plant_t_c_ha,
        parameters.plant.root_allocation_fraction.default,
    )
    no_amf_allocation = allocate_npp(
        no_amf_realised,
        parameters.plant.root_allocation_fraction.default,
    )

    live_after_turnover = state.amf_live_c + fungal_carbon.biomass_growth_t_c_ha - turnover
    if live_after_turnover < 0.0 and abs(live_after_turnover) <= (
        parameters.numerics.absolute_mass_balance_tolerance
    ):
        live_after_turnover = 0.0
    pre_core_values = state.model_dump(mode="python")
    pre_core_values.update(
        {
            "plant_c": state.plant_c + plant_allocation.shoot_t_c_ha,
            "root_c": state.root_c + plant_allocation.root_t_c_ha,
            "amf_live_c": live_after_turnover,
            "amf_necromass_c": necromass.remaining_t_c_ha + turnover,
            "available_p_kg_ha": final_available_p,
            "crop_development": min(
                1.0,
                state.crop_development
                + parameters.plant.monthly_npp_profile[month.calendar_month - 1],
            ),
        }
    )
    pre_core = FieldState.model_validate(pre_core_values)
    core_result = step_carbon_core(
        pre_core,
        CarbonCoreMonth(
            external_input=CarbonInput(
                classification="scenario_assumption",
                provenance="Phase 5 internal AMF and residue transfers are post-decomposition",
            ),
            forcing=forcing,
        ),
        parameters,
    )
    routed_values = core_result.final_state.model_dump(mode="python")
    routed_values.update(
        {
            "dpm_c": core_result.final_state.dpm_c + necromass.to_dpm_t_c_ha,
            "rpm_c": core_result.final_state.rpm_c + necromass.to_rpm_t_c_ha,
            "protected_soc_c": (
                core_result.final_state.protected_soc_c + necromass.to_protected_t_c_ha
            ),
        }
    )
    final_state = FieldState.model_validate(routed_values)

    carbon_fluxes: list[FluxRecord] = []
    if gross_realised > 0.0:
        carbon_fluxes.append(
            _carbon_flux(
                state=state,
                source=CarbonBoundary.EXTERNAL_INPUTS,
                destination=AmfCarbonPool.REALISED_PLANT,
                amount=gross_realised,
                process="plant_realised_carbon_assimilation",
                parameters=parameters,
                provenance=AMF_PROVENANCE,
            )
        )
    carbon_routes = (
        (
            AmfCarbonPool.REALISED_PLANT.value,
            "plant_c",
            plant_allocation.shoot_t_c_ha,
            "net_plant_carbon_to_shoot",
        ),
        (
            AmfCarbonPool.REALISED_PLANT.value,
            "root_c",
            plant_allocation.root_t_c_ha,
            "net_plant_carbon_to_root",
        ),
        (
            AmfCarbonPool.REALISED_PLANT.value,
            AmfCarbonPool.SUBSTRATE.value,
            carbon_allocation.allocated_t_c_ha,
            "plant_carbon_allocation_to_amf",
        ),
        (
            AmfCarbonPool.SUBSTRATE.value,
            AmfCarbonPool.LIVE.value,
            fungal_carbon.biomass_growth_t_c_ha,
            "amf_biomass_growth",
        ),
        (
            AmfCarbonPool.SUBSTRATE.value,
            CarbonBoundary.ATMOSPHERE.value,
            fungal_carbon.maintenance_respiration_t_c_ha,
            "amf_maintenance_respiration",
        ),
        (
            AmfCarbonPool.SUBSTRATE.value,
            CarbonBoundary.ATMOSPHERE.value,
            fungal_carbon.growth_respiration_t_c_ha,
            "amf_growth_respiration",
        ),
        (
            AmfCarbonPool.LIVE.value,
            AmfCarbonPool.NECROMASS.value,
            turnover,
            "amf_biomass_turnover",
        ),
        (
            AmfCarbonPool.NECROMASS.value,
            CarbonPool.DPM.value,
            necromass.to_dpm_t_c_ha,
            "amf_necromass_to_dpm",
        ),
        (
            AmfCarbonPool.NECROMASS.value,
            CarbonPool.RPM.value,
            necromass.to_rpm_t_c_ha,
            "amf_necromass_to_rpm",
        ),
        (
            AmfCarbonPool.NECROMASS.value,
            CarbonPool.PROTECTED_SOC.value,
            necromass.to_protected_t_c_ha,
            "amf_necromass_to_protected_proxy",
        ),
    )
    for source, destination, amount, process in carbon_routes:
        if amount > 0.0:
            carbon_fluxes.append(
                _carbon_flux(
                    state=state,
                    source=source,
                    destination=destination,
                    amount=amount,
                    process=process,
                    parameters=parameters,
                    provenance=AMF_PROVENANCE,
                )
            )

    phosphorus_fluxes: list[PhosphorusFluxRecord] = []
    p_routes = (
        (
            PhosphorusPool.EXTERNAL_INPUTS.value,
            PhosphorusPool.AVAILABLE.value,
            month.external_available_p_kg_ha,
            "external_available_phosphorus_input",
            month.provenance,
        ),
        (
            PhosphorusPool.AVAILABLE.value,
            PhosphorusPool.AMF.value,
            amf_p.acquired_kg_p_ha,
            "amf_phosphorus_acquisition",
            AMF_PROVENANCE,
        ),
        (
            PhosphorusPool.AMF.value,
            PhosphorusPool.PLANT.value,
            amf_p.transferred_to_plant_kg_p_ha,
            "amf_phosphorus_transfer_to_plant",
            AMF_PROVENANCE,
        ),
        (
            PhosphorusPool.AMF.value,
            PhosphorusPool.AMF_RETAINED.value,
            amf_p.retained_by_amf_kg_p_ha,
            "amf_phosphorus_retention",
            AMF_PROVENANCE,
        ),
        (
            PhosphorusPool.AVAILABLE.value,
            PhosphorusPool.PLANT.value,
            direct_p_uptake,
            "direct_plant_phosphorus_uptake",
            AMF_PROVENANCE,
        ),
    )
    for source, destination, amount, process, provenance in p_routes:
        if amount > 0.0:
            phosphorus_fluxes.append(
                _phosphorus_flux(
                    state=state,
                    source=source,
                    destination=destination,
                    amount=amount,
                    process=process,
                    parameters=parameters,
                    provenance=provenance,
                )
            )

    grain_c = 0.0
    grain_yield = 0.0
    no_amf_yield = 0.0
    harvested_c = 0.0
    above_residue = 0.0
    root_residue = 0.0
    residue_dpm = 0.0
    residue_rpm = 0.0
    root_export = 0.0
    if month.harvest:
        harvest = harvest_plant(
            shoot_c_t_ha=final_state.plant_c,
            root_c_t_ha=final_state.root_c,
            harvest_index=parameters.plant.harvest_index.default,
            aboveground_retained_fraction=(
                parameters.plant.aboveground_residue_retained_fraction.default
            ),
            root_residue_fraction=parameters.plant.root_residue_fraction.default,
            carbon_fraction_of_dry_matter=(parameters.plant.carbon_fraction_of_dry_matter.default),
        )
        no_amf_harvest = harvest_plant(
            shoot_c_t_ha=state.plant_c + no_amf_allocation.shoot_t_c_ha,
            root_c_t_ha=state.root_c + no_amf_allocation.root_t_c_ha,
            harvest_index=parameters.plant.harvest_index.default,
            aboveground_retained_fraction=(
                parameters.plant.aboveground_residue_retained_fraction.default
            ),
            root_residue_fraction=parameters.plant.root_residue_fraction.default,
            carbon_fraction_of_dry_matter=(parameters.plant.carbon_fraction_of_dry_matter.default),
        )
        grain_c = harvest.grain_carbon_t_c_ha
        grain_yield = harvest.grain_yield_t_dm_ha
        no_amf_yield = no_amf_harvest.grain_yield_t_dm_ha
        harvested_c = harvest.harvested_biomass_carbon_t_c_ha
        above_residue = harvest.retained_aboveground_residue_t_c_ha
        root_residue = harvest.root_residue_t_c_ha
        root_export = harvest.root_export_t_c_ha
        shoot_dpm, shoot_rpm = partition_residue_dpm_rpm(
            above_residue, parameters.rothc.crop_dpm_rpm_ratio
        )
        root_dpm, root_rpm = partition_residue_dpm_rpm(
            root_residue, parameters.rothc.crop_dpm_rpm_ratio
        )
        residue_dpm = shoot_dpm + root_dpm
        residue_rpm = shoot_rpm + root_rpm
        harvest_routes = (
            ("plant_c", CarbonBoundary.HARVEST_EXPORT.value, grain_c, "grain_harvest"),
            (
                "plant_c",
                CarbonBoundary.HARVEST_EXPORT.value,
                harvest.aboveground_export_t_c_ha,
                "unretained_aboveground_biomass_removal",
            ),
            (
                "root_c",
                CarbonBoundary.RESIDUE_EXPORT.value,
                root_export,
                "unretained_root_export",
            ),
            ("plant_c", CarbonPool.DPM.value, shoot_dpm, "shoot_residue_to_dpm"),
            ("plant_c", CarbonPool.RPM.value, shoot_rpm, "shoot_residue_to_rpm"),
            ("root_c", CarbonPool.DPM.value, root_dpm, "root_residue_to_dpm"),
            ("root_c", CarbonPool.RPM.value, root_rpm, "root_residue_to_rpm"),
        )
        for source, destination, amount, process in harvest_routes:
            if amount > 0.0:
                carbon_fluxes.append(
                    _carbon_flux(
                        state=state,
                        source=source,
                        destination=destination,
                        amount=amount,
                        process=process,
                        parameters=parameters,
                        provenance=AMF_PROVENANCE,
                    )
                )
        final_values = final_state.model_dump(mode="python")
        final_values.update(
            {
                "plant_c": 0.0,
                "root_c": 0.0,
                "dpm_c": final_state.dpm_c + residue_dpm,
                "rpm_c": final_state.rpm_c + residue_rpm,
                "crop_development": 0.0,
                "cumulative_yield_t_dm_ha": final_state.cumulative_yield_t_dm_ha + grain_yield,
            }
        )
        final_state = FieldState.model_validate(final_values)

    carbon_fluxes.extend(core_result.fluxes)
    _validate_state(final_state)
    carbon_balance = _carbon_balance(
        month_index=month_index,
        initial=ecosystem_carbon_total(state),
        final=ecosystem_carbon_total(final_state),
        npp=gross_realised,
        other_inputs=0.0,
        respiration=core_result.respiration_t_c_ha + fungal_carbon.total_respiration_t_c_ha,
        harvest_exports=harvested_c,
        residue_exports=root_export,
        numerics=parameters.numerics,
    )
    p_balance = _phosphorus_balance(
        month_index=month_index,
        initial=state.available_p_kg_ha,
        final=final_state.available_p_kg_ha,
        external=month.external_available_p_kg_ha,
        direct_plant_uptake=direct_p_uptake,
        amf_acquisition=amf_p.acquired_kg_p_ha,
        numerics=parameters.numerics,
    )
    net_effect = carbon_allocation.net_plant_t_c_ha - no_amf_realised
    return AmfStepResult(
        initial_state=state,
        final_state=final_state,
        potential_npp_t_c_ha=potential_npp,
        gross_realised_plant_carbon_t_c_ha=gross_realised,
        no_amf_counterfactual_plant_carbon_t_c_ha=no_amf_realised,
        plant_to_amf_carbon_t_c_ha=carbon_allocation.allocated_t_c_ha,
        effective_amf_allocation_fraction=carbon_allocation.effective_fraction,
        net_plant_carbon_t_c_ha=carbon_allocation.net_plant_t_c_ha,
        net_plant_carbon_effect_t_c_ha=net_effect,
        plant_outcome=_outcome(net_effect, parameters.numerics),
        stress=PlantStressDiagnostic(
            temperature=temperature_stress,
            moisture=moisture_stress,
            phosphorus=phosphorus_stress,
            combined=combined_stress,
        ),
        shoot_growth_t_c_ha=plant_allocation.shoot_t_c_ha,
        root_growth_t_c_ha=plant_allocation.root_t_c_ha,
        fungal_biomass_growth_t_c_ha=fungal_carbon.biomass_growth_t_c_ha,
        fungal_maintenance_respiration_t_c_ha=(fungal_carbon.maintenance_respiration_t_c_ha),
        fungal_growth_respiration_t_c_ha=fungal_carbon.growth_respiration_t_c_ha,
        fungal_respiration_t_c_ha=fungal_carbon.total_respiration_t_c_ha,
        fungal_turnover_t_c_ha=turnover,
        necromass_decomposition_t_c_ha=necromass.decomposed_t_c_ha,
        necromass_to_dpm_t_c_ha=necromass.to_dpm_t_c_ha,
        necromass_to_rpm_t_c_ha=necromass.to_rpm_t_c_ha,
        necromass_to_protected_t_c_ha=necromass.to_protected_t_c_ha,
        phosphorus_demand_kg_p_ha=p_demand,
        direct_plant_phosphorus_uptake_kg_p_ha=direct_p_uptake,
        amf_phosphorus_acquired_kg_p_ha=amf_p.acquired_kg_p_ha,
        amf_phosphorus_transferred_kg_p_ha=amf_p.transferred_to_plant_kg_p_ha,
        amf_phosphorus_retained_kg_p_ha=amf_p.retained_by_amf_kg_p_ha,
        total_plant_phosphorus_received_kg_p_ha=total_plant_p,
        grain_carbon_t_c_ha=grain_c,
        grain_yield_t_dm_ha=grain_yield,
        no_amf_counterfactual_grain_yield_t_dm_ha=no_amf_yield,
        net_yield_effect_t_dm_ha=grain_yield - no_amf_yield,
        harvested_biomass_carbon_t_c_ha=harvested_c,
        aboveground_residue_carbon_t_c_ha=above_residue,
        root_residue_carbon_t_c_ha=root_residue,
        residue_to_dpm_t_c_ha=residue_dpm,
        residue_to_rpm_t_c_ha=residue_rpm,
        carbon_fluxes=tuple(carbon_fluxes),
        phosphorus_fluxes=tuple(phosphorus_fluxes),
        carbon_core=core_result,
        carbon_mass_balance=carbon_balance,
        phosphorus_mass_balance=p_balance,
        provenance=AMF_PROVENANCE,
    )


def step_amf_extension(
    state: FieldState,
    month: PlantMonth,
    parameters: ModelParameters,
) -> AmfStepResult:
    """Advance one Phase 5 month with the explicit AMF module enabled."""
    return _step_amf_extension(state, month, parameters, amf_enabled=True)


def run_amf_extension(
    initial_state: FieldState,
    monthly_steps: Iterable[PlantMonth],
    parameters: ModelParameters,
    *,
    seed: int | None = None,
) -> AmfSimulationResult:
    """Run a deterministic multi-month Phase 5 AMF trajectory."""
    resolved_seed = parameters.numerics.default_seed if seed is None else seed
    if resolved_seed < 0:
        raise ValueError("seed must be non-negative")
    months = tuple(monthly_steps)
    steps: list[AmfStepResult] = []
    counterfactual_steps: list[AmfStepResult] = []
    state = initial_state
    counterfactual_state = initial_state.model_copy(
        update={"amf_live_c": 0.0, "amf_necromass_c": 0.0}
    )
    for month in months:
        result = _step_amf_extension(state, month, parameters, amf_enabled=True)
        counterfactual = _step_amf_extension(
            counterfactual_state,
            month,
            parameters,
            amf_enabled=False,
        )
        path_effect = result.net_plant_carbon_t_c_ha - counterfactual.net_plant_carbon_t_c_ha
        result = result.model_copy(
            update={
                "no_amf_counterfactual_plant_carbon_t_c_ha": (
                    counterfactual.net_plant_carbon_t_c_ha
                ),
                "net_plant_carbon_effect_t_c_ha": path_effect,
                "plant_outcome": _outcome(path_effect, parameters.numerics),
                "no_amf_counterfactual_grain_yield_t_dm_ha": (counterfactual.grain_yield_t_dm_ha),
                "net_yield_effect_t_dm_ha": (
                    result.grain_yield_t_dm_ha - counterfactual.grain_yield_t_dm_ha
                ),
            }
        )
        steps.append(result)
        counterfactual_steps.append(counterfactual)
        state = result.final_state
        counterfactual_state = counterfactual.final_state

    gross_npp = math.fsum(step.gross_realised_plant_carbon_t_c_ha for step in steps)
    respiration = math.fsum(
        step.carbon_core.respiration_t_c_ha + step.fungal_respiration_t_c_ha for step in steps
    )
    harvest_exports = math.fsum(step.harvested_biomass_carbon_t_c_ha for step in steps)
    residue_exports = math.fsum(
        record.amount_t_c_ha
        for step in steps
        for record in step.carbon_fluxes
        if record.destination_pool == CarbonBoundary.RESIDUE_EXPORT
    )
    cumulative_carbon_balance = _carbon_balance(
        month_index=state.month_index,
        initial=ecosystem_carbon_total(initial_state),
        final=ecosystem_carbon_total(state),
        npp=gross_npp,
        other_inputs=0.0,
        respiration=respiration,
        harvest_exports=harvest_exports,
        residue_exports=residue_exports,
        numerics=parameters.numerics,
    )
    p_external = math.fsum(month.external_available_p_kg_ha for month in months)
    direct_p = math.fsum(step.direct_plant_phosphorus_uptake_kg_p_ha for step in steps)
    amf_p = math.fsum(step.amf_phosphorus_acquired_kg_p_ha for step in steps)
    cumulative_p_balance = _phosphorus_balance(
        month_index=state.month_index,
        initial=initial_state.available_p_kg_ha,
        final=state.available_p_kg_ha,
        external=p_external,
        direct_plant_uptake=direct_p,
        amf_acquisition=amf_p,
        numerics=parameters.numerics,
    )
    return AmfSimulationResult(
        seed=resolved_seed,
        configuration_hash=parameters.stable_hash(),
        initial_state=initial_state,
        final_state=state,
        steps=tuple(steps),
        carbon_fluxes=tuple(record for step in steps for record in step.carbon_fluxes),
        phosphorus_fluxes=tuple(record for step in steps for record in step.phosphorus_fluxes),
        cumulative_potential_npp_t_c_ha=math.fsum(step.potential_npp_t_c_ha for step in steps),
        cumulative_gross_realised_plant_carbon_t_c_ha=gross_npp,
        cumulative_no_amf_counterfactual_plant_carbon_t_c_ha=math.fsum(
            step.net_plant_carbon_t_c_ha for step in counterfactual_steps
        ),
        cumulative_plant_to_amf_carbon_t_c_ha=math.fsum(
            step.plant_to_amf_carbon_t_c_ha for step in steps
        ),
        cumulative_net_plant_carbon_t_c_ha=math.fsum(
            step.net_plant_carbon_t_c_ha for step in steps
        ),
        cumulative_net_plant_carbon_effect_t_c_ha=(
            math.fsum(step.net_plant_carbon_t_c_ha for step in steps)
            - math.fsum(step.net_plant_carbon_t_c_ha for step in counterfactual_steps)
        ),
        cumulative_fungal_respiration_t_c_ha=math.fsum(
            step.fungal_respiration_t_c_ha for step in steps
        ),
        cumulative_fungal_turnover_t_c_ha=math.fsum(step.fungal_turnover_t_c_ha for step in steps),
        cumulative_necromass_to_dpm_t_c_ha=math.fsum(
            step.necromass_to_dpm_t_c_ha for step in steps
        ),
        cumulative_necromass_to_rpm_t_c_ha=math.fsum(
            step.necromass_to_rpm_t_c_ha for step in steps
        ),
        cumulative_necromass_to_protected_t_c_ha=math.fsum(
            step.necromass_to_protected_t_c_ha for step in steps
        ),
        cumulative_amf_phosphorus_acquired_kg_p_ha=amf_p,
        cumulative_amf_phosphorus_transferred_kg_p_ha=math.fsum(
            step.amf_phosphorus_transferred_kg_p_ha for step in steps
        ),
        cumulative_direct_plant_phosphorus_uptake_kg_p_ha=direct_p,
        cumulative_grain_yield_t_dm_ha=math.fsum(step.grain_yield_t_dm_ha for step in steps),
        cumulative_no_amf_counterfactual_grain_yield_t_dm_ha=math.fsum(
            step.grain_yield_t_dm_ha for step in counterfactual_steps
        ),
        cumulative_net_yield_effect_t_dm_ha=(
            math.fsum(step.grain_yield_t_dm_ha for step in steps)
            - math.fsum(step.grain_yield_t_dm_ha for step in counterfactual_steps)
        ),
        cumulative_residue_to_dpm_t_c_ha=math.fsum(step.residue_to_dpm_t_c_ha for step in steps),
        cumulative_residue_to_rpm_t_c_ha=math.fsum(step.residue_to_rpm_t_c_ha for step in steps),
        cumulative_carbon_mass_balance=cumulative_carbon_balance,
        cumulative_phosphorus_mass_balance=cumulative_p_balance,
        provenance=AMF_PROVENANCE,
    )
