"""Deterministic Phase 6 management orchestration around the verified Phase 5 step."""

from __future__ import annotations

import hashlib
import json
import math
from typing import Final

from soil_simulator.domain.enums import (
    AmfCarbonPool,
    CarbonBoundary,
    CarbonPool,
    ManagementEventType,
    PhosphorusPool,
    TillageLevel,
)
from soil_simulator.domain.management import (
    AppliedManagementEvent,
    ManagementCarbonBalance,
    ManagementComparisonResult,
    ManagementPhosphorusBalance,
    ManagementPolicy,
    ManagementRuntimeState,
    ManagementScenarioSet,
    ManagementSimulationResult,
    ManagementStepResult,
    event_simulation_month,
    ordered_events,
)
from soil_simulator.domain.models import (
    FieldState,
    FluxRecord,
    ManagementEvent,
    ModelParameters,
    TillageLevelParameters,
)
from soil_simulator.domain.plant import PhosphorusFluxRecord
from soil_simulator.processes.amf import (
    acquire_amf_phosphorus,
    allocate_plant_carbon_to_amf,
    fungal_growth_and_respiration,
)
from soil_simulator.processes.phosphorus import (
    direct_phosphorus_uptake_kg_p_ha,
    phosphorus_demand_kg_p_ha,
    phosphorus_stress_modifier,
)
from soil_simulator.processes.plant import (
    allocate_npp,
    partition_residue_dpm_rpm,
)
from soil_simulator.simulator.amf_extension import step_amf_extension
from soil_simulator.simulator.errors import MassBalanceError
from soil_simulator.simulator.plant_baseline import (
    _carbon_flux,
    _phosphorus_flux,
    _tolerance,
    ecosystem_carbon_total,
)

MANAGEMENT_PROVENANCE: Final = (
    "soil_simulator Phase 6 deterministic scheduled management v0.6.0; "
    "provisional effects documented in docs/MANAGEMENT_INTERVENTIONS.md"
)


def _event_parameter(event: ManagementEvent, name: str) -> float | str | bool:
    for parameter in event.parameters:
        if parameter.name == name:
            return parameter.value
    raise ValueError(f"management event is missing required parameter {name!r}")


def _tillage_parameters(parameters: ModelParameters, level: TillageLevel) -> TillageLevelParameters:
    if level is TillageLevel.CONVENTIONAL:
        return parameters.management.tillage.conventional
    if level is TillageLevel.REDUCED:
        return parameters.management.tillage.reduced
    return parameters.management.tillage.no_till


def _managed_carbon_total(state: FieldState, runtime: ManagementRuntimeState) -> float:
    return ecosystem_carbon_total(state) + runtime.cover_shoot_c_t_ha + runtime.cover_root_c_t_ha


def _policy_hash(policy: ManagementPolicy) -> str:
    canonical = json.dumps(
        policy.model_dump(mode="json"),
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _configuration_hash(parameters: ModelParameters, scenario_hash: str) -> str:
    return hashlib.sha256(f"{parameters.stable_hash()}:{scenario_hash}".encode()).hexdigest()


def _monthly_parameters(
    parameters: ModelParameters, runtime: ManagementRuntimeState
) -> ModelParameters:
    if runtime.tillage_effect_months_remaining == 0:
        return parameters
    values = parameters.model_dump(mode="python", by_alias=True)
    for name in ("k_dpm_year", "k_rpm_year", "k_microbial_year", "k_protected_year"):
        values["rothc"][name] *= runtime.decomposition_multiplier
    values["amf"]["turnover_per_month"]["default"] *= runtime.amf_turnover_multiplier
    return ModelParameters.model_validate(values)


def _balance_carbon(
    *,
    month_index: int,
    initial: float,
    final: float,
    crop_input: float,
    cover_input: float,
    manure_input: float,
    respiration: float,
    exports: float,
    parameters: ModelParameters,
) -> ManagementCarbonBalance:
    left = initial + crop_input + cover_input + manure_input
    right = final + respiration + exports
    residual = left - right
    _, tolerance = _tolerance(left, right, parameters.numerics)
    result = ManagementCarbonBalance(
        month_index=month_index,
        initial_carbon_t_c_ha=initial,
        crop_assimilation_t_c_ha=crop_input,
        cover_crop_assimilation_t_c_ha=cover_input,
        manure_input_t_c_ha=manure_input,
        respiration_t_c_ha=respiration,
        harvest_and_biomass_exports_t_c_ha=exports,
        final_carbon_t_c_ha=final,
        residual_t_c_ha=residual,
        tolerance_t_c_ha=tolerance,
        within_tolerance=abs(residual) <= tolerance,
    )
    if not result.within_tolerance:
        raise MassBalanceError(
            f"month {month_index}: Phase 6 carbon residual {residual:.17g} exceeds "
            f"tolerance {tolerance:.17g}"
        )
    return result


def _balance_phosphorus(
    *,
    month_index: int,
    initial: float,
    final: float,
    application: float,
    manure: float,
    crop_withdrawal: float,
    cover_amf_retention: float,
    cover_export: float,
    parameters: ModelParameters,
) -> ManagementPhosphorusBalance:
    left = initial + application + manure
    right = final + crop_withdrawal + cover_amf_retention + cover_export
    residual = left - right
    _, tolerance = _tolerance(left, right, parameters.numerics)
    result = ManagementPhosphorusBalance(
        month_index=month_index,
        initial_phosphorus_kg_p_ha=initial,
        phosphorus_application_kg_p_ha=application,
        manure_phosphorus_input_kg_p_ha=manure,
        crop_and_amf_withdrawal_kg_p_ha=crop_withdrawal,
        cover_amf_retention_kg_p_ha=cover_amf_retention,
        cover_phosphorus_export_kg_p_ha=cover_export,
        final_phosphorus_kg_p_ha=final,
        residual_kg_p_ha=residual,
        tolerance_kg_p_ha=tolerance,
        within_tolerance=abs(residual) <= tolerance,
    )
    if not result.within_tolerance:
        raise MassBalanceError(
            f"month {month_index}: Phase 6 phosphorus residual {residual:.17g} exceeds "
            f"tolerance {tolerance:.17g}"
        )
    return result


def run_management_policy(
    scenario: ManagementScenarioSet,
    policy: ManagementPolicy,
    parameters: ModelParameters,
) -> ManagementSimulationResult:
    """Run one validated management policy deterministically."""
    state = scenario.initial_state
    runtime = ManagementRuntimeState()
    steps: list[ManagementStepResult] = []
    all_applied: list[AppliedManagementEvent] = []
    schedule = ordered_events(policy.events, scenario.start_date)
    events_by_month: dict[int, list[ManagementEvent]] = {}
    for event in schedule:
        events_by_month.setdefault(event_simulation_month(event, scenario.start_date), []).append(
            event
        )

    for month_index, original_month in enumerate(scenario.monthly_steps):
        initial_state = state
        initial_runtime = runtime
        initial_carbon = _managed_carbon_total(state, runtime)
        initial_p = state.available_p_kg_ha + runtime.cover_plant_p_kg_ha
        carbon_fluxes: list[FluxRecord] = []
        p_fluxes: list[PhosphorusFluxRecord] = []
        event_p = 0.0
        manure_c = 0.0
        manure_p = 0.0
        incorporated_c = 0.0
        incorporated_shoot_c = 0.0
        incorporated_root_c = 0.0
        tillage_mortality = 0.0
        termination_return_c = 0.0
        termination_return_p = 0.0
        cover_export_c = 0.0
        cover_export_p = 0.0
        applied: list[AppliedManagementEvent] = []

        for order, event in enumerate(events_by_month.get(month_index, [])):
            applied_event = AppliedManagementEvent(
                event=event, simulation_month=month_index, order_in_month=order
            )
            applied.append(applied_event)
            all_applied.append(applied_event)
            if event.event_type is ManagementEventType.PHOSPHORUS_APPLICATION:
                event_p += event.amount
            elif event.event_type is ManagementEventType.TILLAGE:
                level = TillageLevel(str(_event_parameter(event, "tillage_level")))
                effects = _tillage_parameters(parameters, level)
                mortality = state.amf_live_c * effects.amf_pulse_mortality.default
                tillage_mortality += mortality
                fraction = effects.standing_biomass_incorporation_fraction.default
                shoot_incorporated = state.plant_c * fraction
                root_incorporated = state.root_c * fraction
                incorporated_shoot_c += shoot_incorporated
                incorporated_root_c += root_incorporated
                incorporated_c += shoot_incorporated + root_incorporated
                state = state.model_copy(
                    update={
                        "plant_c": state.plant_c - shoot_incorporated,
                        "root_c": state.root_c - root_incorporated,
                        "amf_live_c": state.amf_live_c - mortality,
                        "amf_necromass_c": state.amf_necromass_c + mortality,
                    }
                )
                runtime = runtime.model_copy(
                    update={
                        "tillage_effect_months_remaining": int(
                            effects.effect_duration_months.default
                        ),
                        "soil_cover_suppression_months_remaining": int(
                            effects.soil_cover_suppression_months.default
                        ),
                        "decomposition_multiplier": effects.decomposition_multiplier.default,
                        "amf_turnover_multiplier": effects.amf_turnover_multiplier.default,
                    }
                )
                if mortality > 0.0:
                    carbon_fluxes.append(
                        _carbon_flux(
                            state=initial_state,
                            source=AmfCarbonPool.LIVE,
                            destination=AmfCarbonPool.NECROMASS,
                            amount=mortality,
                            process="tillage_amf_pulse_mortality",
                            parameters=parameters,
                            provenance=event.parameter_provenance,
                        )
                    )
            elif event.event_type is ManagementEventType.COVER_CROP_TERMINATION:
                c_return_fraction = parameters.management.cover_crop.residue_return_fraction.default
                p_return_fraction = (
                    parameters.management.cover_crop.phosphorus_return_fraction.default
                )
                cover_total_c = runtime.cover_shoot_c_t_ha + runtime.cover_root_c_t_ha
                termination_return_c = cover_total_c * c_return_fraction
                cover_export_c = cover_total_c - termination_return_c
                termination_return_p = runtime.cover_plant_p_kg_ha * p_return_fraction
                cover_export_p = runtime.cover_plant_p_kg_ha - termination_return_p
                runtime = runtime.model_copy(
                    update={
                        "cover_crop_active": False,
                        "cover_shoot_c_t_ha": 0.0,
                        "cover_root_c_t_ha": 0.0,
                        "cover_plant_p_kg_ha": 0.0,
                    }
                )
            elif event.event_type is ManagementEventType.FARMYARD_MANURE:
                manure_c += event.amount
                manure_p += event.amount * (
                    parameters.management.farmyard_manure.phosphorus_content_kg_p_per_t_c.default
                )
            elif event.event_type is ManagementEventType.COVER_CROP_ESTABLISHMENT:
                runtime = runtime.model_copy(update={"cover_crop_active": True})

        monthly_parameters = _monthly_parameters(parameters, runtime)
        forcing = original_month.forcing
        if runtime.cover_crop_active:
            forcing = forcing.model_copy(
                update={
                    "is_covered": True,
                    "open_pan_evaporation_mm": forcing.open_pan_evaporation_mm
                    + parameters.management.cover_crop.water_use_open_pan_mm.default,
                }
            )
        if runtime.soil_cover_suppression_months_remaining > 0:
            forcing = forcing.model_copy(update={"is_covered": False})
        phase5_month = original_month.model_copy(
            update={
                "forcing": forcing,
                "external_available_p_kg_ha": original_month.external_available_p_kg_ha + event_p,
                "provenance": f"{original_month.provenance}; {MANAGEMENT_PROVENANCE}",
            }
        )
        amf_step = step_amf_extension(state, phase5_month, monthly_parameters)
        state = amf_step.final_state
        carbon_fluxes.extend(amf_step.carbon_fluxes)
        p_fluxes.extend(amf_step.phosphorus_fluxes)

        post_dpm = 0.0
        post_rpm = 0.0
        for carbon_source, amount, process in (
            ("plant_c", incorporated_shoot_c, "tillage_shoot_incorporation"),
            ("root_c", incorporated_root_c, "tillage_root_incorporation"),
            (
                "cover_crop_biomass_c",
                termination_return_c,
                "cover_crop_termination_residue_return",
            ),
        ):
            dpm, rpm = partition_residue_dpm_rpm(amount, parameters.rothc.crop_dpm_rpm_ratio)
            post_dpm += dpm
            post_rpm += rpm
            for destination, routed, suffix in (
                (CarbonPool.DPM, dpm, "dpm"),
                (CarbonPool.RPM, rpm, "rpm"),
            ):
                if routed > 0.0:
                    carbon_fluxes.append(
                        _carbon_flux(
                            state=initial_state,
                            source=carbon_source,
                            destination=destination,
                            amount=routed,
                            process=f"{process}_to_{suffix}",
                            parameters=parameters,
                            provenance=MANAGEMENT_PROVENANCE,
                        )
                    )
        if cover_export_c > 0.0:
            carbon_fluxes.append(
                _carbon_flux(
                    state=initial_state,
                    source="cover_crop_biomass_c",
                    destination=CarbonBoundary.RESIDUE_EXPORT,
                    amount=cover_export_c,
                    process="cover_crop_termination_biomass_export",
                    parameters=parameters,
                    provenance=MANAGEMENT_PROVENANCE,
                )
            )
        manure_dpm = manure_c * parameters.rothc.manure_dpm_fraction
        manure_rpm = manure_c * parameters.rothc.manure_rpm_fraction
        manure_protected = manure_c * parameters.rothc.manure_protected_fraction
        post_dpm += manure_dpm
        post_rpm += manure_rpm
        state = state.model_copy(
            update={
                "dpm_c": state.dpm_c + post_dpm,
                "rpm_c": state.rpm_c + post_rpm,
                "protected_soc_c": state.protected_soc_c + manure_protected,
                "available_p_kg_ha": state.available_p_kg_ha + manure_p + termination_return_p,
            }
        )
        for carbon_destination, amount, process in (
            (CarbonPool.DPM, manure_dpm, "farmyard_manure_to_dpm"),
            (CarbonPool.RPM, manure_rpm, "farmyard_manure_to_rpm"),
            (CarbonPool.PROTECTED_SOC, manure_protected, "farmyard_manure_to_protected_proxy"),
        ):
            if amount > 0.0:
                carbon_fluxes.append(
                    _carbon_flux(
                        state=initial_state,
                        source=CarbonBoundary.EXTERNAL_INPUTS,
                        destination=carbon_destination,
                        amount=amount,
                        process=process,
                        parameters=parameters,
                        provenance=MANAGEMENT_PROVENANCE,
                    )
                )
        for p_source, p_destination, amount, process in (
            (
                "cover_plant_p",
                PhosphorusPool.AVAILABLE,
                termination_return_p,
                "cover_crop_p_return",
            ),
            (
                PhosphorusPool.EXTERNAL_INPUTS,
                PhosphorusPool.AVAILABLE,
                manure_p,
                "farmyard_manure_p_input",
            ),
            (
                "cover_plant_p",
                "cover_crop_p_export",
                cover_export_p,
                "cover_crop_termination_p_export",
            ),
        ):
            if amount > 0.0:
                p_fluxes.append(
                    _phosphorus_flux(
                        state=initial_state,
                        source=p_source,
                        destination=p_destination,
                        amount=amount,
                        process=process,
                        parameters=parameters,
                        provenance=MANAGEMENT_PROVENANCE,
                    )
                )

        cover_gross = 0.0
        cover_net = 0.0
        cover_p_uptake = 0.0
        cover_amf_retained = 0.0
        cover_respiration = 0.0
        if runtime.cover_crop_active:
            cover_potential = parameters.management.cover_crop.monthly_potential_npp_t_c_ha.default
            growth_before_p = (
                cover_potential * amf_step.stress.temperature * amf_step.stress.moisture
            )
            demand = phosphorus_demand_kg_p_ha(
                growth_before_p,
                parameters.plant.carbon_fraction_of_dry_matter.default,
                parameters.plant.phosphorus_concentration_kg_p_per_kg_dm.default,
            )
            available_before_cover = state.available_p_kg_ha
            cover_amf_p = acquire_amf_phosphorus(
                live_biomass_t_c_ha=state.amf_live_c,
                available_p_kg_ha=available_before_cover,
                vmax_kg_p_per_t_amf_c_month=parameters.amf.p_uptake_vmax.default,
                half_saturation_kg_p_ha=parameters.amf.p_uptake_km.default,
                temperature_modifier=amf_step.stress.temperature,
                moisture_modifier=amf_step.stress.moisture,
                transfer_to_plant_fraction=parameters.amf.p_transfer_to_plant_fraction.default,
            )
            available_after_amf = available_before_cover - cover_amf_p.acquired_kg_p_ha
            direct = direct_phosphorus_uptake_kg_p_ha(
                available_after_amf,
                max(0.0, demand - cover_amf_p.transferred_to_plant_kg_p_ha),
                parameters.plant.direct_p_uptake_half_saturation.default,
            )
            plant_p = direct + cover_amf_p.transferred_to_plant_kg_p_ha
            cover_p_uptake = plant_p
            cover_amf_retained = cover_amf_p.retained_by_amf_kg_p_ha
            p_stress = phosphorus_stress_modifier(plant_p, demand)
            cover_gross = growth_before_p * p_stress
            cover_allocation = allocate_plant_carbon_to_amf(
                realised_plant_carbon_t_c_ha=cover_gross,
                base_fraction=parameters.amf.photosynthate_allocation_fraction.default,
                available_p_kg_ha=available_before_cover,
                p_feedback_minimum=parameters.amf.allocation_p_feedback_minimum.default,
                p_feedback_half_saturation_kg_p_ha=(
                    parameters.amf.allocation_p_half_saturation.default
                ),
                environmental_modifier=amf_step.stress.temperature * amf_step.stress.moisture,
                maximum_fraction=parameters.amf.photosynthate_allocation_fraction.maximum,
                host_active=True,
            )
            fungal = fungal_growth_and_respiration(
                allocated_carbon_t_c_ha=cover_allocation.allocated_t_c_ha,
                carbon_use_efficiency=parameters.amf.carbon_use_efficiency.default,
                turnover_t_c_ha=0.0,
            )
            cover_respiration = fungal.total_respiration_t_c_ha
            cover_net = cover_allocation.net_plant_t_c_ha
            partition = allocate_npp(
                cover_net, parameters.management.cover_crop.root_allocation_fraction.default
            )
            state = state.model_copy(
                update={
                    "available_p_kg_ha": available_after_amf - direct,
                    "amf_live_c": state.amf_live_c + fungal.biomass_growth_t_c_ha,
                }
            )
            runtime = runtime.model_copy(
                update={
                    "cover_shoot_c_t_ha": runtime.cover_shoot_c_t_ha + partition.shoot_t_c_ha,
                    "cover_root_c_t_ha": runtime.cover_root_c_t_ha + partition.root_t_c_ha,
                    "cover_plant_p_kg_ha": runtime.cover_plant_p_kg_ha + plant_p,
                }
            )
            if cover_gross > 0.0:
                carbon_fluxes.append(
                    _carbon_flux(
                        state=initial_state,
                        source=CarbonBoundary.EXTERNAL_INPUTS,
                        destination="cover_crop_realised_c",
                        amount=cover_gross,
                        process="cover_crop_carbon_assimilation",
                        parameters=parameters,
                        provenance=MANAGEMENT_PROVENANCE,
                    )
                )
            for cover_c_source, cover_c_destination, amount, process in (
                (
                    "cover_crop_realised_c",
                    "cover_crop_shoot_c",
                    partition.shoot_t_c_ha,
                    "cover_crop_net_carbon_to_shoot",
                ),
                (
                    "cover_crop_realised_c",
                    "cover_crop_root_c",
                    partition.root_t_c_ha,
                    "cover_crop_net_carbon_to_root",
                ),
                (
                    "cover_crop_realised_c",
                    AmfCarbonPool.SUBSTRATE.value,
                    cover_allocation.allocated_t_c_ha,
                    "cover_crop_carbon_allocation_to_amf",
                ),
                (
                    AmfCarbonPool.SUBSTRATE.value,
                    AmfCarbonPool.LIVE.value,
                    fungal.biomass_growth_t_c_ha,
                    "cover_crop_supported_amf_growth",
                ),
                (
                    AmfCarbonPool.SUBSTRATE.value,
                    CarbonBoundary.ATMOSPHERE.value,
                    fungal.total_respiration_t_c_ha,
                    "cover_crop_supported_amf_respiration",
                ),
            ):
                if amount > 0.0:
                    carbon_fluxes.append(
                        _carbon_flux(
                            state=initial_state,
                            source=cover_c_source,
                            destination=cover_c_destination,
                            amount=amount,
                            process=process,
                            parameters=parameters,
                            provenance=MANAGEMENT_PROVENANCE,
                        )
                    )
            for cover_p_source, cover_p_destination, amount, process in (
                (
                    PhosphorusPool.AVAILABLE.value,
                    PhosphorusPool.AMF.value,
                    cover_amf_p.acquired_kg_p_ha,
                    "cover_crop_amf_p_acquisition",
                ),
                (
                    PhosphorusPool.AVAILABLE.value,
                    "cover_plant_p",
                    direct,
                    "cover_crop_direct_p_uptake",
                ),
                (
                    PhosphorusPool.AMF.value,
                    "cover_plant_p",
                    cover_amf_p.transferred_to_plant_kg_p_ha,
                    "cover_crop_amf_p_transfer",
                ),
                (
                    PhosphorusPool.AMF.value,
                    PhosphorusPool.AMF_RETAINED.value,
                    cover_amf_retained,
                    "cover_crop_amf_p_retention",
                ),
            ):
                if amount > 0.0:
                    p_fluxes.append(
                        _phosphorus_flux(
                            state=initial_state,
                            source=cover_p_source,
                            destination=cover_p_destination,
                            amount=amount,
                            process=process,
                            parameters=parameters,
                            provenance=MANAGEMENT_PROVENANCE,
                        )
                    )

        if runtime.tillage_effect_months_remaining > 0:
            remaining = runtime.tillage_effect_months_remaining - 1
            runtime = runtime.model_copy(
                update={
                    "tillage_effect_months_remaining": remaining,
                    "decomposition_multiplier": (
                        runtime.decomposition_multiplier if remaining else 1.0
                    ),
                    "amf_turnover_multiplier": runtime.amf_turnover_multiplier
                    if remaining
                    else 1.0,
                }
            )
        if runtime.soil_cover_suppression_months_remaining > 0:
            runtime = runtime.model_copy(
                update={
                    "soil_cover_suppression_months_remaining": (
                        runtime.soil_cover_suppression_months_remaining - 1
                    )
                }
            )

        base_exports = amf_step.harvested_biomass_carbon_t_c_ha + math.fsum(
            record.amount_t_c_ha
            for record in amf_step.carbon_fluxes
            if record.destination_pool == CarbonBoundary.RESIDUE_EXPORT
        )
        carbon_balance = _balance_carbon(
            month_index=month_index,
            initial=initial_carbon,
            final=_managed_carbon_total(state, runtime),
            crop_input=amf_step.gross_realised_plant_carbon_t_c_ha,
            cover_input=cover_gross,
            manure_input=manure_c,
            respiration=(
                amf_step.carbon_core.respiration_t_c_ha
                + amf_step.fungal_respiration_t_c_ha
                + cover_respiration
            ),
            exports=base_exports + cover_export_c,
            parameters=parameters,
        )
        p_balance = _balance_phosphorus(
            month_index=month_index,
            initial=initial_p,
            final=state.available_p_kg_ha + runtime.cover_plant_p_kg_ha,
            application=original_month.external_available_p_kg_ha + event_p,
            manure=manure_p,
            crop_withdrawal=(
                amf_step.direct_plant_phosphorus_uptake_kg_p_ha
                + amf_step.amf_phosphorus_acquired_kg_p_ha
            ),
            cover_amf_retention=cover_amf_retained,
            cover_export=cover_export_p,
            parameters=parameters,
        )
        cost = math.fsum(event.event.cost_gbp_ha for event in applied)
        emissions = math.fsum(event.event.emissions_proxy_kg_co2e_ha for event in applied)
        steps.append(
            ManagementStepResult(
                initial_state=initial_state,
                final_state=state,
                initial_management_state=initial_runtime,
                final_management_state=runtime,
                applied_events=tuple(applied),
                amf_step=amf_step,
                tillage_amf_mortality_t_c_ha=tillage_mortality,
                tillage_incorporated_carbon_t_c_ha=incorporated_c,
                cover_crop_gross_carbon_t_c_ha=cover_gross,
                cover_crop_net_carbon_t_c_ha=cover_net,
                cover_crop_phosphorus_uptake_kg_p_ha=cover_p_uptake,
                cover_crop_residue_return_t_c_ha=termination_return_c,
                cover_crop_phosphorus_return_kg_p_ha=termination_return_p,
                manure_carbon_input_t_c_ha=manure_c,
                manure_phosphorus_input_kg_p_ha=manure_p,
                phosphorus_application_kg_p_ha=event_p,
                cost_gbp_ha=cost,
                emissions_proxy_kg_co2e_ha=emissions,
                carbon_fluxes=tuple(carbon_fluxes),
                phosphorus_fluxes=tuple(p_fluxes),
                carbon_balance=carbon_balance,
                phosphorus_balance=p_balance,
            )
        )

    schedule_hash = _policy_hash(policy)
    return ManagementSimulationResult(
        policy_id=policy.policy_id,
        policy_name=policy.name,
        seed=scenario.seed,
        configuration_hash=_configuration_hash(parameters, scenario.stable_hash()),
        schedule_hash=schedule_hash,
        initial_state=scenario.initial_state,
        final_state=state,
        final_management_state=runtime,
        steps=tuple(steps),
        applied_events=tuple(all_applied),
        cumulative_grain_yield_t_dm_ha=state.cumulative_yield_t_dm_ha,
        cumulative_cover_crop_carbon_input_t_c_ha=math.fsum(
            step.cover_crop_gross_carbon_t_c_ha for step in steps
        ),
        cumulative_respiration_t_c_ha=math.fsum(
            step.carbon_balance.respiration_t_c_ha for step in steps
        ),
        cumulative_cost_gbp_ha=math.fsum(step.cost_gbp_ha for step in steps),
        cumulative_emissions_proxy_kg_co2e_ha=math.fsum(
            step.emissions_proxy_kg_co2e_ha for step in steps
        ),
        cumulative_carbon_residual_t_c_ha=math.fsum(
            step.carbon_balance.residual_t_c_ha for step in steps
        ),
        cumulative_phosphorus_residual_kg_p_ha=math.fsum(
            step.phosphorus_balance.residual_kg_p_ha for step in steps
        ),
        amf_outcomes=tuple(step.amf_step.plant_outcome for step in steps),
        provenance=MANAGEMENT_PROVENANCE,
    )


def compare_management_scenarios(
    scenario: ManagementScenarioSet, parameters: ModelParameters
) -> ManagementComparisonResult:
    """Run every predefined policy in source order without ranking or optimisation."""
    return ManagementComparisonResult(
        scenario_name=scenario.name,
        scenario_version=scenario.version,
        results=tuple(
            run_management_policy(scenario, policy, parameters) for policy in scenario.policies
        ),
    )
