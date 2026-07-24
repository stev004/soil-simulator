"""Batch Phase 6 baseline and intervention execution for synthetic fields."""

from __future__ import annotations

import math
from datetime import date

from soil_simulator.domain.carbon import RothCForcing
from soil_simulator.domain.enums import ParameterSource
from soil_simulator.domain.management import ManagementPolicy, ManagementScenarioSet
from soil_simulator.domain.models import ModelParameters
from soil_simulator.domain.plant import PlantMonth
from soil_simulator.domain.population import (
    PopulationBatchFailure,
    PopulationBatchFieldResult,
    PopulationBatchResult,
    PopulationGenerationConfig,
    SyntheticField,
    SyntheticPopulation,
)
from soil_simulator.simulator.management import run_management_policy


def parameters_for_field(field: SyntheticField, parameters: ModelParameters) -> ModelParameters:
    """Return validated configuration with only explicit field draws overridden."""
    values = parameters.model_dump(mode="python", by_alias=True)
    for name in (
        "photosynthate_allocation_fraction",
        "carbon_use_efficiency",
        "turnover_per_month",
        "p_uptake_vmax",
    ):
        values["amf"][name]["default"] = field.uncertainty_value(name)
    turnover_draw = field.uncertainty_value("turnover_per_month")
    maximum_runtime_multiplier = max(
        parameters.management.tillage.conventional.amf_turnover_multiplier.default,
        parameters.management.tillage.reduced.amf_turnover_multiplier.default,
        parameters.management.tillage.no_till.amf_turnover_multiplier.default,
    )
    values["amf"]["turnover_per_month"]["max"] = max(
        parameters.amf.turnover_per_month.maximum,
        turnover_draw * maximum_runtime_multiplier,
    )
    stabilisation = field.uncertainty_value("necromass_stabilisation_fraction")
    non_protected = 1.0 - stabilisation
    ratio = parameters.rothc.crop_dpm_rpm_ratio
    values["amf"]["necromass_stabilisation_fraction"]["default"] = stabilisation
    values["amf"]["necromass_to_dpm_fraction"]["default"] = non_protected * ratio / (1.0 + ratio)
    values["amf"]["necromass_to_rpm_fraction"]["default"] = non_protected / (1.0 + ratio)
    values["management"]["tillage"]["conventional"]["amf_pulse_mortality"]["default"] = (
        field.uncertainty_value("conventional_amf_pulse_mortality")
    )
    return ModelParameters.model_validate(values)


def _plant_month(
    field: SyntheticField, month_index: int, config: PopulationGenerationConfig
) -> PlantMonth:
    weather = field.weather[month_index]
    calendar_month = weather.month
    return PlantMonth(
        calendar_month=calendar_month,
        forcing=RothCForcing(
            mean_air_temperature_c=weather.mean_air_temperature_c,
            precipitation_mm=weather.precipitation_mm,
            open_pan_evaporation_mm=(
                weather.potential_evapotranspiration_mm
                / config.weather_pet_to_open_pan_divisor.default
            ),
            is_covered=3 <= calendar_month <= 9,
            clay_percent=field.field.clay_percent,
            soil_depth_cm=field.field.soil_depth_cm,
            provenance=weather.provenance,
        ),
        external_available_p_kg_ha=0.0,
        harvest=calendar_month == 9,
        classification=ParameterSource.SCENARIO_ASSUMPTION,
        provenance=f"Phase 7 field forcing for {field.field.field_id}",
    )


def _scenario_for_field(
    field: SyntheticField,
    template: ManagementScenarioSet,
    config: PopulationGenerationConfig,
    horizon_months: int | None = None,
) -> ManagementScenarioSet:
    eligible = set(field.intervention_eligibility)
    policies = tuple(policy for policy in template.policies if policy.policy_id in eligible)
    if not policies:
        raise ValueError(f"field {field.field.field_id} has no eligible Phase 6 policies")
    resolved_horizon = len(field.weather) if horizon_months is None else horizon_months
    if resolved_horizon < 1 or resolved_horizon > len(field.weather):
        raise ValueError(f"invalid horizon {resolved_horizon} for {field.field.field_id}")
    return ManagementScenarioSet(
        name=f"phase7:{field.field.field_id}",
        version="0.7.0",
        seed=field.generation_seed,
        start_date=template.start_date,
        initial_state=field.initial_state,
        monthly_steps=tuple(
            _plant_month(field, index, config) for index in range(resolved_horizon)
        ),
        policies=policies,
        classification=ParameterSource.SCENARIO_ASSUMPTION,
        provenance=(
            f"Phase 7 field-specific Phase 6 input; population seed {field.empirical_seed_id}; "
            "synthetic outcomes are not field validation"
        ),
    )


def probe_field(
    field: SyntheticField,
    parameters: ModelParameters,
    config: PopulationGenerationConfig,
) -> None:
    """Execute one Phase 6 baseline month and require C/P balance."""
    baseline = ManagementPolicy(
        policy_id="baseline",
        name="Phase 7 QC baseline probe",
        events=(),
        classification=ParameterSource.SCENARIO_ASSUMPTION,
        provenance="Phase 7 simulator-execution QC probe",
    )
    scenario = ManagementScenarioSet(
        name=f"phase7-qc:{field.field.field_id}",
        version="0.7.0",
        seed=field.generation_seed,
        start_date=date(2026, 1, 1),
        initial_state=field.initial_state,
        monthly_steps=(_plant_month(field, 0, config),),
        policies=(baseline,),
        classification=ParameterSource.SCENARIO_ASSUMPTION,
        provenance="Phase 7 strict one-month Phase 6 execution probe",
    )
    result = run_management_policy(scenario, baseline, parameters_for_field(field, parameters))
    if any(
        not step.carbon_balance.within_tolerance or not step.phosphorus_balance.within_tolerance
        for step in result.steps
    ):
        raise ValueError("Phase 6 balance invariant failed during population QC")


def run_population_batch(
    population: SyntheticPopulation,
    template: ManagementScenarioSet,
    parameters: ModelParameters,
    config: PopulationGenerationConfig,
    *,
    horizons_months: tuple[int, ...] | None = None,
) -> PopulationBatchResult:
    """Run every policy at one or more horizons without changing Phase 3--6 equations."""
    horizons = (
        (len(population.fields[0].weather),)
        if horizons_months is None and population.fields
        else horizons_months
    )
    if not horizons or len(set(horizons)) != len(horizons):
        raise ValueError("batch horizons must be non-empty and unique")
    outcomes: list[PopulationBatchFieldResult] = []
    failures: list[PopulationBatchFailure] = []
    for field in population.fields:
        try:
            field_parameters = parameters_for_field(field, parameters)
        except (ArithmeticError, RuntimeError, ValueError) as exc:
            failures.append(
                PopulationBatchFailure(
                    field_id=field.field.field_id,
                    policy_id="scenario_construction",
                    reason=f"{type(exc).__name__}: {exc}",
                )
            )
            continue
        for horizon in horizons:
            try:
                scenario = _scenario_for_field(field, template, config, horizon)
            except (ArithmeticError, RuntimeError, ValueError) as exc:
                failures.append(
                    PopulationBatchFailure(
                        field_id=field.field.field_id,
                        policy_id=f"scenario_construction_h{horizon}",
                        reason=f"{type(exc).__name__}: {exc}",
                    )
                )
                continue
            for policy in scenario.policies:
                try:
                    result = run_management_policy(scenario, policy, field_parameters)
                except (ArithmeticError, RuntimeError, ValueError) as exc:
                    failures.append(
                        PopulationBatchFailure(
                            field_id=field.field.field_id,
                            policy_id=f"{policy.policy_id}@{horizon}",
                            reason=f"{type(exc).__name__}: {exc}",
                        )
                    )
                    continue
                carbon_residual = max(
                    (abs(step.carbon_balance.residual_t_c_ha) for step in result.steps),
                    default=0.0,
                )
                phosphorus_residual = max(
                    (abs(step.phosphorus_balance.residual_kg_p_ha) for step in result.steps),
                    default=0.0,
                )
                final_soc = math.fsum(
                    (
                        result.final_state.dpm_c,
                        result.final_state.rpm_c,
                        result.final_state.microbial_c,
                        result.final_state.protected_soc_c,
                        result.final_state.iom_c,
                    )
                )
                outcomes.append(
                    PopulationBatchFieldResult(
                        field_id=field.field.field_id,
                        policy_id=policy.policy_id,
                        simulation_horizon_months=len(result.steps),
                        population_split=field.population_split,
                        archetype=field.archetype,
                        yield_t_dm_ha=result.cumulative_grain_yield_t_dm_ha,
                        final_total_soc_t_c_ha=final_soc,
                        final_protected_soc_proxy_t_c_ha=result.final_state.protected_soc_c,
                        cumulative_respiration_t_c_ha=result.cumulative_respiration_t_c_ha,
                        final_available_phosphorus_kg_p_ha=(result.final_state.available_p_kg_ha),
                        final_amf_live_c_t_ha=result.final_state.amf_live_c,
                        cost_gbp_ha=result.cumulative_cost_gbp_ha,
                        emissions_proxy_kg_co2e_ha=(result.cumulative_emissions_proxy_kg_co2e_ha),
                        maximum_carbon_residual_t_c_ha=carbon_residual,
                        maximum_phosphorus_residual_kg_p_ha=phosphorus_residual,
                    )
                )
    maximum_carbon = max(
        (outcome.maximum_carbon_residual_t_c_ha for outcome in outcomes), default=0.0
    )
    maximum_phosphorus = max(
        (outcome.maximum_phosphorus_residual_kg_p_ha for outcome in outcomes), default=0.0
    )
    return PopulationBatchResult(
        population_hash=population.manifest.population_hash,
        scenario_version=(
            template.version
            if horizons_months is None
            else f"{template.version}:horizons={','.join(str(value) for value in horizons)}"
        ),
        results=tuple(outcomes),
        failures=tuple(failures),
        maximum_carbon_residual_t_c_ha=maximum_carbon,
        maximum_phosphorus_residual_kg_p_ha=maximum_phosphorus,
    )
