"""RothC-compatible periodic spin-up for coherent Phase 7 initial pools."""

from __future__ import annotations

import math
from dataclasses import dataclass

from soil_simulator.domain.enums import ParameterSource
from soil_simulator.domain.models import FieldState, ModelParameters, WeatherMonth
from soil_simulator.domain.population import PopulationGenerationConfig, SpinUpDiagnostic
from soil_simulator.processes.carbon import first_order_decay
from soil_simulator.processes.rothc import (
    clay_carbon_partition,
    moisture_modifier,
    soil_cover_modifier,
    temperature_modifier,
)


@dataclass(frozen=True, slots=True)
class SpinUpResult:
    """Starting state and periodic-equilibrium diagnostic."""

    state: FieldState
    diagnostic: SpinUpDiagnostic


def spin_up_carbon_pools(
    *,
    baseline_soc_t_c_ha: float,
    clay_percent: float,
    available_p_kg_ha: float,
    amf_live_c_t_ha: float,
    amf_necromass_c_t_ha: float,
    weather: tuple[WeatherMonth, ...],
    parameters: ModelParameters,
    config: PopulationGenerationConfig,
) -> SpinUpResult:
    """Spin a unit-input RothC system to a periodic cycle, then scale to SOC.

    Repeating complete sampled weather years preserves the model's moisture
    memory. Because the RothC core is linear in active carbon stocks and input,
    scaling the converged periodic state and reference input to the requested
    active SOC retains the equilibrium pool proportions.
    """
    if len(weather) < 12 or len(weather) % 12:
        raise ValueError("spin-up weather must contain one or more complete years")
    iom = parameters.rothc.iom_coefficient * baseline_soc_t_c_ha**parameters.rothc.iom_exponent
    target_active = baseline_soc_t_c_ha - iom - amf_live_c_t_ha - amf_necromass_c_t_ha
    if target_active <= 0.0:
        raise ValueError("baseline SOC is insufficient for IOM and AMF starting stocks")

    reference_annual_input = config.spinup_reference_annual_input_t_c_ha.default
    monthly_input = reference_annual_input / 12.0
    dpm_input = (
        monthly_input
        * parameters.rothc.crop_dpm_rpm_ratio
        / (1.0 + parameters.rothc.crop_dpm_rpm_ratio)
    )
    rpm_input = monthly_input - dpm_input
    dpm = rpm = microbial = protected = 0.0
    tsmd = 0.0
    previous_cycle = (dpm, rpm, microbial, protected)
    relative_change = math.inf
    converged = False
    years_run = 0
    maximum_years = int(config.spinup_max_years.default)
    complete_year_count = len(weather) // 12

    for year_index in range(maximum_years):
        year_offset = (year_index % complete_year_count) * 12
        selected_year = weather[year_offset : year_offset + 12]
        for month in selected_year:
            is_covered = 3 <= month.month <= 9
            temperature = temperature_modifier(month.mean_air_temperature_c, parameters.rothc)
            moisture = moisture_modifier(
                previous_accumulated_tsmd_mm=tsmd,
                precipitation_mm=month.precipitation_mm,
                open_pan_evaporation_mm=(
                    month.potential_evapotranspiration_mm
                    / config.weather_pet_to_open_pan_divisor.default
                ),
                is_covered=is_covered,
                clay_percent=clay_percent,
                soil_depth_cm=parameters.model.soil_depth_cm,
                parameters=parameters.rothc,
            )
            tsmd = moisture.accumulated_tsmd_mm
            combined = (
                temperature * moisture.modifier * soil_cover_modifier(is_covered, parameters.rothc)
            )
            partition = clay_carbon_partition(clay_percent, parameters.rothc)
            remaining: list[float] = []
            decomposed: list[float] = []
            for stock, rate in (
                (dpm, parameters.rothc.k_dpm_year),
                (rpm, parameters.rothc.k_rpm_year),
                (microbial, parameters.rothc.k_microbial_year),
                (protected, parameters.rothc.k_protected_year),
            ):
                decay = first_order_decay(stock, rate, combined)
                remaining.append(decay.remaining_t_c_ha)
                decomposed.append(decay.decomposed_t_c_ha)
            total_decomposed = math.fsum(decomposed)
            dpm = remaining[0] + dpm_input
            rpm = remaining[1] + rpm_input
            microbial = remaining[2] + total_decomposed * partition.microbial_fraction
            protected = remaining[3] + total_decomposed * partition.protected_fraction
        years_run = year_index + 1
        if years_run % complete_year_count == 0:
            current_cycle = (dpm, rpm, microbial, protected)
            denominator = max(math.fsum(current_cycle), 1.0e-12)
            relative_change = (
                max(
                    abs(current - previous)
                    for current, previous in zip(current_cycle, previous_cycle, strict=True)
                )
                / denominator
            )
            if years_run >= 20 and relative_change <= config.spinup_relative_tolerance.default:
                converged = True
                break
            previous_cycle = current_cycle

    unit_active = math.fsum((dpm, rpm, microbial, protected))
    if not math.isfinite(unit_active) or unit_active <= 0.0:
        raise ValueError("spin-up produced no finite active carbon")
    scale = target_active / unit_active
    state = FieldState(
        month_index=0,
        plant_c=0.0,
        root_c=0.0,
        amf_live_c=amf_live_c_t_ha,
        amf_necromass_c=amf_necromass_c_t_ha,
        dpm_c=dpm * scale,
        rpm_c=rpm * scale,
        microbial_c=microbial * scale,
        protected_soc_c=protected * scale,
        iom_c=iom,
        available_p_kg_ha=available_p_kg_ha,
        topsoil_moisture_deficit_mm=tsmd,
        crop_development=0.0,
        cumulative_yield_t_dm_ha=0.0,
        aggregate_protection_index=None,
    )
    achieved = math.fsum(
        (
            state.amf_live_c,
            state.amf_necromass_c,
            state.dpm_c,
            state.rpm_c,
            state.microbial_c,
            state.protected_soc_c,
            state.iom_c,
        )
    )
    return SpinUpResult(
        state=state,
        diagnostic=SpinUpDiagnostic(
            years_run=years_run,
            converged=converged,
            relative_cycle_change=relative_change,
            target_soc_t_c_ha=baseline_soc_t_c_ha,
            achieved_soc_t_c_ha=achieved,
            equilibrium_annual_input_t_c_ha=reference_annual_input * scale,
            classification=ParameterSource.SCENARIO_ASSUMPTION,
            provenance=(
                "Phase 7 periodic RothC spin-up under complete sampled weather years; "
                "scaled to target SOC under provisional historical input A035"
            ),
        ),
    )
