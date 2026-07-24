"""Deterministic Phase 4 spring-barley, available-P and residue baseline."""

from __future__ import annotations

import math
from collections.abc import Iterable
from typing import Final

from soil_simulator.domain.carbon import CarbonCoreMonth, CarbonInput
from soil_simulator.domain.enums import CarbonBoundary, CarbonPool, PhosphorusPool
from soil_simulator.domain.models import (
    FieldState,
    FluxRecord,
    ModelParameters,
    NumericalParameters,
)
from soil_simulator.domain.plant import (
    PhosphorusFluxRecord,
    PhosphorusMassBalanceDiagnostic,
    PlantCarbonMassBalanceDiagnostic,
    PlantMonth,
    PlantSimulationResult,
    PlantStepResult,
    PlantStressDiagnostic,
)
from soil_simulator.processes.phosphorus import (
    phosphorus_demand_kg_p_ha,
    phosphorus_stress_modifier,
    phosphorus_uptake_kg_p_ha,
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
from soil_simulator.processes.rothc import moisture_modifier
from soil_simulator.simulator.carbon_core import step_carbon_core
from soil_simulator.simulator.errors import MassBalanceError, NumericalSafetyError

PLANT_PROVENANCE: Final = (
    "soil_simulator Phase 4 deterministic spring-barley/P baseline v0.4.0; "
    "provisional relationships documented in docs/PLANT_PHOSPHORUS_BASELINE.md"
)


def ecosystem_carbon_total(state: FieldState) -> float:
    """Return carbon in all represented plant, AMF and soil pools [t C ha-1]."""
    return math.fsum(
        (
            state.plant_c,
            state.root_c,
            state.amf_live_c,
            state.amf_necromass_c,
            state.dpm_c,
            state.rpm_c,
            state.microbial_c,
            state.protected_soc_c,
            state.iom_c,
        )
    )


def _carbon_flux(
    *,
    state: FieldState,
    source: str,
    destination: str,
    amount: float,
    process: str,
    parameters: ModelParameters,
    provenance: str,
) -> FluxRecord:
    return FluxRecord(
        month_index=state.month_index,
        source_pool=source,
        destination_pool=destination,
        amount_t_c_ha=amount,
        uncertainty_t_c_ha=None,
        process=process,
        parameter_version=parameters.model.version,
        provenance=provenance,
    )


def _phosphorus_flux(
    *,
    state: FieldState,
    source: str,
    destination: str,
    amount: float,
    process: str,
    parameters: ModelParameters,
    provenance: str,
) -> PhosphorusFluxRecord:
    return PhosphorusFluxRecord(
        month_index=state.month_index,
        source_pool=source,
        destination_pool=destination,
        amount_kg_p_ha=amount,
        process=process,
        parameter_version=parameters.model.version,
        provenance=provenance,
    )


def _tolerance(left: float, right: float, numerics: NumericalParameters) -> tuple[float, float]:
    scale = max(abs(left), abs(right))
    tolerance = max(
        numerics.absolute_mass_balance_tolerance,
        numerics.relative_mass_balance_tolerance * scale,
    )
    return scale, tolerance


def _carbon_balance(
    *,
    month_index: int,
    initial: float,
    final: float,
    npp: float,
    other_inputs: float,
    respiration: float,
    harvest_exports: float,
    residue_exports: float,
    numerics: NumericalParameters,
) -> PlantCarbonMassBalanceDiagnostic:
    left = initial + npp + other_inputs
    right = final + respiration + harvest_exports + residue_exports
    residual = left - right
    scale, tolerance = _tolerance(left, right, numerics)
    diagnostic = PlantCarbonMassBalanceDiagnostic(
        month_index=month_index,
        initial_carbon_t_c_ha=initial,
        npp_inputs_t_c_ha=npp,
        other_external_inputs_t_c_ha=other_inputs,
        respiration_losses_t_c_ha=respiration,
        harvest_exports_t_c_ha=harvest_exports,
        residue_exports_t_c_ha=residue_exports,
        final_carbon_t_c_ha=final,
        residual_t_c_ha=residual,
        relative_residual=abs(residual) / scale if scale > 0.0 else 0.0,
        tolerance_t_c_ha=tolerance,
        within_tolerance=abs(residual) <= tolerance,
    )
    if not diagnostic.within_tolerance:
        raise MassBalanceError(
            f"month {month_index}: Phase 4 carbon residual {residual:.17g} t C ha-1 "
            f"exceeds tolerance {tolerance:.17g}"
        )
    return diagnostic


def _phosphorus_balance(
    *,
    month_index: int,
    initial: float,
    final: float,
    external: float,
    uptake: float,
    numerics: NumericalParameters,
) -> PhosphorusMassBalanceDiagnostic:
    left = initial + external
    right = final + uptake
    residual = left - right
    scale, tolerance = _tolerance(left, right, numerics)
    diagnostic = PhosphorusMassBalanceDiagnostic(
        month_index=month_index,
        initial_available_p_kg_ha=initial,
        external_inputs_kg_p_ha=external,
        plant_uptake_kg_p_ha=uptake,
        final_available_p_kg_ha=final,
        residual_kg_p_ha=residual,
        relative_residual=abs(residual) / scale if scale > 0.0 else 0.0,
        tolerance_kg_p_ha=tolerance,
        within_tolerance=abs(residual) <= tolerance,
    )
    if not diagnostic.within_tolerance:
        raise MassBalanceError(
            f"month {month_index}: available-P residual {residual:.17g} kg P ha-1 "
            f"exceeds tolerance {tolerance:.17g}"
        )
    return diagnostic


def _validate_state(state: FieldState) -> None:
    values = state.model_dump(mode="python")
    for name, value in values.items():
        if isinstance(value, (int, float)) and not math.isfinite(float(value)):
            raise NumericalSafetyError(f"final state variable {name} is non-finite")


def step_plant_baseline(
    state: FieldState,
    month: PlantMonth,
    parameters: ModelParameters,
) -> PlantStepResult:
    """Advance plant, available P and the verified RothC core by one month."""
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

    p_available_after_input = state.available_p_kg_ha + month.external_available_p_kg_ha
    growth_before_p = potential_npp * temperature_stress * moisture_stress
    p_demand = phosphorus_demand_kg_p_ha(
        growth_before_p,
        parameters.plant.carbon_fraction_of_dry_matter.default,
        parameters.plant.phosphorus_concentration_kg_p_per_kg_dm.default,
    )
    phosphorus_stress = phosphorus_stress_modifier(p_available_after_input, p_demand)
    combined_stress = combine_stress_modifiers(
        temperature_stress, moisture_stress, phosphorus_stress
    )
    realised_npp = potential_npp * combined_stress
    p_uptake = phosphorus_uptake_kg_p_ha(p_available_after_input, p_demand)
    final_available_p = p_available_after_input - p_uptake
    if final_available_p < 0.0:
        if abs(final_available_p) <= parameters.numerics.absolute_mass_balance_tolerance:
            final_available_p = 0.0
        else:
            raise NumericalSafetyError(
                f"month {month_index}: available P became negative ({final_available_p})"
            )

    allocation = allocate_npp(realised_npp, parameters.plant.root_allocation_fraction.default)
    pre_decomposition_values = state.model_dump(mode="python")
    pre_decomposition_values.update(
        {
            "plant_c": state.plant_c + allocation.shoot_t_c_ha,
            "root_c": state.root_c + allocation.root_t_c_ha,
            "available_p_kg_ha": final_available_p,
            "crop_development": min(
                1.0,
                state.crop_development
                + parameters.plant.monthly_npp_profile[month.calendar_month - 1],
            ),
        }
    )
    pre_decomposition = FieldState.model_validate(pre_decomposition_values)
    core_result = step_carbon_core(
        pre_decomposition,
        CarbonCoreMonth(
            external_input=CarbonInput(
                classification="scenario_assumption",
                provenance="Phase 4 generated residues are added after decomposition",
            ),
            forcing=forcing,
        ),
        parameters,
    )

    carbon_fluxes: list[FluxRecord] = []
    if allocation.shoot_t_c_ha > 0.0:
        carbon_fluxes.append(
            _carbon_flux(
                state=state,
                source=CarbonBoundary.EXTERNAL_INPUTS,
                destination="plant_c",
                amount=allocation.shoot_t_c_ha,
                process="plant_npp_to_shoot",
                parameters=parameters,
                provenance=PLANT_PROVENANCE,
            )
        )
    if allocation.root_t_c_ha > 0.0:
        carbon_fluxes.append(
            _carbon_flux(
                state=state,
                source=CarbonBoundary.EXTERNAL_INPUTS,
                destination="root_c",
                amount=allocation.root_t_c_ha,
                process="plant_npp_to_root",
                parameters=parameters,
                provenance=PLANT_PROVENANCE,
            )
        )

    p_fluxes: list[PhosphorusFluxRecord] = []
    if month.external_available_p_kg_ha > 0.0:
        p_fluxes.append(
            _phosphorus_flux(
                state=state,
                source=PhosphorusPool.EXTERNAL_INPUTS,
                destination=PhosphorusPool.AVAILABLE,
                amount=month.external_available_p_kg_ha,
                process="external_available_phosphorus_input",
                parameters=parameters,
                provenance=month.provenance,
            )
        )
    if p_uptake > 0.0:
        p_fluxes.append(
            _phosphorus_flux(
                state=state,
                source=PhosphorusPool.AVAILABLE,
                destination=PhosphorusPool.PLANT,
                amount=p_uptake,
                process="plant_phosphorus_uptake",
                parameters=parameters,
                provenance=PLANT_PROVENANCE,
            )
        )

    grain_c = 0.0
    grain_yield = 0.0
    harvested_c = 0.0
    above_residue = 0.0
    root_residue = 0.0
    residue_dpm = 0.0
    residue_rpm = 0.0
    aboveground_export = 0.0
    root_export = 0.0
    final_state = core_result.final_state
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
        grain_c = harvest.grain_carbon_t_c_ha
        grain_yield = harvest.grain_yield_t_dm_ha
        harvested_c = harvest.harvested_biomass_carbon_t_c_ha
        above_residue = harvest.retained_aboveground_residue_t_c_ha
        root_residue = harvest.root_residue_t_c_ha
        aboveground_export = harvest.aboveground_export_t_c_ha
        root_export = harvest.root_export_t_c_ha

        shoot_dpm, shoot_rpm = partition_residue_dpm_rpm(
            above_residue, parameters.rothc.crop_dpm_rpm_ratio
        )
        root_dpm, root_rpm = partition_residue_dpm_rpm(
            root_residue, parameters.rothc.crop_dpm_rpm_ratio
        )
        residue_dpm = shoot_dpm + root_dpm
        residue_rpm = shoot_rpm + root_rpm

        transfers = (
            ("plant_c", CarbonBoundary.HARVEST_EXPORT.value, grain_c, "grain_harvest"),
            (
                "plant_c",
                CarbonBoundary.HARVEST_EXPORT.value,
                aboveground_export,
                "unretained_aboveground_biomass_removal",
            ),
            ("root_c", CarbonBoundary.RESIDUE_EXPORT.value, root_export, "unretained_root_export"),
            ("plant_c", CarbonPool.DPM.value, shoot_dpm, "shoot_residue_to_dpm"),
            ("plant_c", CarbonPool.RPM.value, shoot_rpm, "shoot_residue_to_rpm"),
            ("root_c", CarbonPool.DPM.value, root_dpm, "root_residue_to_dpm"),
            ("root_c", CarbonPool.RPM.value, root_rpm, "root_residue_to_rpm"),
        )
        for source, destination, amount, process in transfers:
            if amount > 0.0:
                carbon_fluxes.append(
                    _carbon_flux(
                        state=state,
                        source=source,
                        destination=destination,
                        amount=amount,
                        process=process,
                        parameters=parameters,
                        provenance=PLANT_PROVENANCE,
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
                "cumulative_yield_t_dm_ha": (final_state.cumulative_yield_t_dm_ha + grain_yield),
            }
        )
        final_state = FieldState.model_validate(final_values)

    carbon_fluxes.extend(core_result.fluxes)
    _validate_state(final_state)
    carbon_balance = _carbon_balance(
        month_index=month_index,
        initial=ecosystem_carbon_total(state),
        final=ecosystem_carbon_total(final_state),
        npp=realised_npp,
        other_inputs=0.0,
        respiration=core_result.respiration_t_c_ha,
        harvest_exports=harvested_c,
        residue_exports=root_export,
        numerics=parameters.numerics,
    )
    p_balance = _phosphorus_balance(
        month_index=month_index,
        initial=state.available_p_kg_ha,
        final=final_state.available_p_kg_ha,
        external=month.external_available_p_kg_ha,
        uptake=p_uptake,
        numerics=parameters.numerics,
    )
    return PlantStepResult(
        initial_state=state,
        final_state=final_state,
        potential_npp_t_c_ha=potential_npp,
        realised_npp_t_c_ha=realised_npp,
        stress=PlantStressDiagnostic(
            temperature=temperature_stress,
            moisture=moisture_stress,
            phosphorus=phosphorus_stress,
            combined=combined_stress,
        ),
        shoot_growth_t_c_ha=allocation.shoot_t_c_ha,
        root_growth_t_c_ha=allocation.root_t_c_ha,
        phosphorus_demand_kg_p_ha=p_demand,
        phosphorus_uptake_kg_p_ha=p_uptake,
        grain_carbon_t_c_ha=grain_c,
        grain_yield_t_dm_ha=grain_yield,
        harvested_biomass_carbon_t_c_ha=harvested_c,
        aboveground_residue_carbon_t_c_ha=above_residue,
        root_residue_carbon_t_c_ha=root_residue,
        residue_to_dpm_t_c_ha=residue_dpm,
        residue_to_rpm_t_c_ha=residue_rpm,
        carbon_fluxes=tuple(carbon_fluxes),
        phosphorus_fluxes=tuple(p_fluxes),
        carbon_core=core_result,
        carbon_mass_balance=carbon_balance,
        phosphorus_mass_balance=p_balance,
        provenance=PLANT_PROVENANCE,
    )


def run_plant_baseline(
    initial_state: FieldState,
    monthly_steps: Iterable[PlantMonth],
    parameters: ModelParameters,
    *,
    seed: int | None = None,
) -> PlantSimulationResult:
    """Run a deterministic multi-month Phase 4 trajectory with provenance."""
    resolved_seed = parameters.numerics.default_seed if seed is None else seed
    if resolved_seed < 0:
        raise ValueError("seed must be non-negative")
    months = tuple(monthly_steps)
    steps: list[PlantStepResult] = []
    state = initial_state
    for month in months:
        result = step_plant_baseline(state, month, parameters)
        steps.append(result)
        state = result.final_state

    npp = math.fsum(step.realised_npp_t_c_ha for step in steps)
    potential_npp = math.fsum(step.potential_npp_t_c_ha for step in steps)
    respiration = math.fsum(step.carbon_core.respiration_t_c_ha for step in steps)
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
        npp=npp,
        other_inputs=0.0,
        respiration=respiration,
        harvest_exports=harvest_exports,
        residue_exports=residue_exports,
        numerics=parameters.numerics,
    )
    p_external = math.fsum(month.external_available_p_kg_ha for month in months)
    p_uptake = math.fsum(step.phosphorus_uptake_kg_p_ha for step in steps)
    cumulative_p_balance = _phosphorus_balance(
        month_index=state.month_index,
        initial=initial_state.available_p_kg_ha,
        final=state.available_p_kg_ha,
        external=p_external,
        uptake=p_uptake,
        numerics=parameters.numerics,
    )
    return PlantSimulationResult(
        seed=resolved_seed,
        configuration_hash=parameters.stable_hash(),
        initial_state=initial_state,
        final_state=state,
        steps=tuple(steps),
        carbon_fluxes=tuple(record for step in steps for record in step.carbon_fluxes),
        phosphorus_fluxes=tuple(record for step in steps for record in step.phosphorus_fluxes),
        cumulative_potential_npp_t_c_ha=potential_npp,
        cumulative_realised_npp_t_c_ha=npp,
        cumulative_phosphorus_uptake_kg_p_ha=p_uptake,
        cumulative_grain_yield_t_dm_ha=math.fsum(step.grain_yield_t_dm_ha for step in steps),
        cumulative_residue_to_dpm_t_c_ha=math.fsum(step.residue_to_dpm_t_c_ha for step in steps),
        cumulative_residue_to_rpm_t_c_ha=math.fsum(step.residue_to_rpm_t_c_ha for step in steps),
        cumulative_carbon_mass_balance=cumulative_carbon_balance,
        cumulative_phosphorus_mass_balance=cumulative_p_balance,
        provenance=PLANT_PROVENANCE,
    )
