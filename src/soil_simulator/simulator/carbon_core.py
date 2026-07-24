"""Verified deterministic RothC-style monthly soil-carbon core.

The kernel updates DPM, RPM, microbial biomass, the humified/protected SOC
proxy, IOM, accumulated topsoil moisture deficit and ``month_index``. External
inputs use the configured timing: official-compatible post-decomposition by
default, with an explicit legacy pre-decomposition migration mode. All other
future-module state variables pass through unchanged.
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Mapping
from typing import Final

from soil_simulator.domain.carbon import (
    CarbonCoreMonth,
    CarbonCoreSimulationResult,
    CarbonCoreStepResult,
    RothCModifierDiagnostic,
)
from soil_simulator.domain.enums import CarbonBoundary, CarbonPool, ExternalInputTiming
from soil_simulator.domain.models import FieldState, FluxRecord, ModelParameters
from soil_simulator.processes.carbon import first_order_decay
from soil_simulator.processes.rothc import (
    clay_carbon_partition,
    moisture_modifier,
    soil_cover_modifier,
    temperature_modifier,
)
from soil_simulator.simulator.errors import NumericalSafetyError
from soil_simulator.simulator.ledger import FluxLedger, verify_mass_balance

CORE_PROVENANCE: Final = (
    "soil_simulator Phase 3 RothC-style monthly carbon core; equations from "
    "Rothamsted Research RothC_Py v1.0.0, DOI 10.5281/zenodo.10732265"
)


def soil_carbon_total(state: FieldState) -> float:
    """Return total carbon in the five implemented soil pools [t C ha-1]."""
    return math.fsum(
        (
            state.dpm_c,
            state.rpm_c,
            state.microbial_c,
            state.protected_soc_c,
            state.iom_c,
        )
    )


def _flux(
    *,
    month_index: int,
    source: str,
    destination: str,
    amount_t_c_ha: float,
    process: str,
    parameters: ModelParameters,
    provenance: str,
) -> FluxRecord:
    return FluxRecord(
        month_index=month_index,
        source_pool=source,
        destination_pool=destination,
        amount_t_c_ha=amount_t_c_ha,
        uncertainty_t_c_ha=None,
        process=process,
        parameter_version=parameters.model.version,
        provenance=provenance,
    )


def _validate_calculated_pools(month_index: int, pools: Mapping[CarbonPool, float]) -> None:
    for name, value in pools.items():
        if not math.isfinite(value):
            raise NumericalSafetyError(
                f"month {month_index}: calculated pool {name} is non-finite ({value!r})"
            )
        if value < 0.0:
            raise NumericalSafetyError(
                f"month {month_index}: calculated pool {name} is negative ({value:.17g})"
            )


def step_carbon_core(
    state: FieldState,
    month: CarbonCoreMonth,
    parameters: ModelParameters,
) -> CarbonCoreStepResult:
    """Advance the five-pool RothC-style carbon core by exactly one month.

    Temperature, accumulated moisture deficit and cover modifiers multiply
    every active pool's configured annual decay rate. Each decomposed amount
    is split by the official clay-dependent CO2/(BIO+HUM) ratio, and retained
    carbon is routed by the configured 46% microbial / 54% protected split.
    """
    month_index = state.month_index
    forcing = month.forcing
    external_input = month.external_input
    try:
        temperature = temperature_modifier(forcing.mean_air_temperature_c, parameters.rothc)
        moisture = moisture_modifier(
            previous_accumulated_tsmd_mm=state.topsoil_moisture_deficit_mm,
            precipitation_mm=forcing.precipitation_mm,
            open_pan_evaporation_mm=forcing.open_pan_evaporation_mm,
            is_covered=forcing.is_covered,
            clay_percent=forcing.clay_percent,
            soil_depth_cm=forcing.soil_depth_cm,
            parameters=parameters.rothc,
        )
        cover = soil_cover_modifier(forcing.is_covered, parameters.rothc)
        partition = clay_carbon_partition(forcing.clay_percent, parameters.rothc)
    except (ArithmeticError, ValueError) as exc:
        raise NumericalSafetyError(
            f"month {month_index}: RothC modifier calculation failed: {exc}"
        ) from exc
    combined_modifier = temperature * moisture.modifier * cover
    modifiers = RothCModifierDiagnostic(
        temperature=temperature,
        moisture=moisture.modifier,
        cover=cover,
        combined=combined_modifier,
        previous_accumulated_tsmd_mm=state.topsoil_moisture_deficit_mm,
        accumulated_tsmd_mm=moisture.accumulated_tsmd_mm,
        maximum_tsmd_mm=moisture.maximum_tsmd_mm,
        bare_soil_maximum_tsmd_mm=moisture.bare_soil_maximum_tsmd_mm,
        co2_to_retained_ratio=partition.co2_to_retained_ratio,
        co2_fraction=partition.co2_fraction,
        retained_fraction=partition.retained_fraction,
    )

    input_by_pool = {
        CarbonPool.DPM: external_input.dpm_c,
        CarbonPool.RPM: external_input.rpm_c,
        CarbonPool.PROTECTED_SOC: external_input.protected_soc_c,
    }
    ledger = FluxLedger()
    for input_destination, amount in input_by_pool.items():
        if amount > 0.0:
            ledger = ledger.appended(
                _flux(
                    month_index=month_index,
                    source=CarbonBoundary.EXTERNAL_INPUTS,
                    destination=input_destination,
                    amount_t_c_ha=amount,
                    process="external_carbon_input",
                    parameters=parameters,
                    provenance=external_input.provenance,
                )
            )

    add_before_decay = (
        parameters.rothc.external_input_timing is ExternalInputTiming.LEGACY_PRE_DECOMPOSITION
    )
    stocks_for_decay = {
        CarbonPool.DPM: state.dpm_c + (external_input.dpm_c if add_before_decay else 0.0),
        CarbonPool.RPM: state.rpm_c + (external_input.rpm_c if add_before_decay else 0.0),
        CarbonPool.MICROBIAL: state.microbial_c,
        CarbonPool.PROTECTED_SOC: state.protected_soc_c
        + (external_input.protected_soc_c if add_before_decay else 0.0),
        CarbonPool.IOM: state.iom_c,
    }
    _validate_calculated_pools(month_index, stocks_for_decay)
    rates = {
        CarbonPool.DPM: parameters.rothc.k_dpm_year,
        CarbonPool.RPM: parameters.rothc.k_rpm_year,
        CarbonPool.MICROBIAL: parameters.rothc.k_microbial_year,
        CarbonPool.PROTECTED_SOC: parameters.rothc.k_protected_year,
    }
    remaining: dict[CarbonPool, float] = {CarbonPool.IOM: stocks_for_decay[CarbonPool.IOM]}
    respiration_amounts: list[float] = []
    microbial_amounts: list[float] = []
    protected_amounts: list[float] = []
    for pool, annual_rate in rates.items():
        try:
            decay = first_order_decay(stocks_for_decay[pool], annual_rate, combined_modifier)
        except (ArithmeticError, ValueError) as exc:
            raise NumericalSafetyError(f"month {month_index}: {pool} decay failed: {exc}") from exc
        remaining[pool] = decay.remaining_t_c_ha
        if decay.decomposed_t_c_ha == 0.0:
            continue
        respiration = decay.decomposed_t_c_ha * partition.co2_fraction
        to_microbial = decay.decomposed_t_c_ha * partition.microbial_fraction
        to_protected = decay.decomposed_t_c_ha * partition.protected_fraction
        respiration_amounts.append(respiration)
        microbial_amounts.append(to_microbial)
        protected_amounts.append(to_protected)
        routing_records: tuple[tuple[str, float, str], ...] = (
            (
                CarbonBoundary.ATMOSPHERE.value,
                respiration,
                "rothc_heterotrophic_respiration",
            ),
            (CarbonPool.MICROBIAL.value, to_microbial, "rothc_retained_to_microbial"),
            (CarbonPool.PROTECTED_SOC.value, to_protected, "rothc_retained_to_protected"),
        )
        for destination, amount, process in routing_records:
            ledger = ledger.appended(
                _flux(
                    month_index=month_index,
                    source=pool,
                    destination=destination,
                    amount_t_c_ha=amount,
                    process=process,
                    parameters=parameters,
                    provenance=CORE_PROVENANCE,
                )
            )

    respiration_total = math.fsum(respiration_amounts)
    microbial_total = math.fsum(microbial_amounts)
    protected_total = math.fsum(protected_amounts)
    final_pools = {
        CarbonPool.DPM: remaining[CarbonPool.DPM]
        + (0.0 if add_before_decay else external_input.dpm_c),
        CarbonPool.RPM: remaining[CarbonPool.RPM]
        + (0.0 if add_before_decay else external_input.rpm_c),
        CarbonPool.MICROBIAL: remaining[CarbonPool.MICROBIAL] + microbial_total,
        CarbonPool.PROTECTED_SOC: remaining[CarbonPool.PROTECTED_SOC]
        + protected_total
        + (0.0 if add_before_decay else external_input.protected_soc_c),
        CarbonPool.IOM: remaining[CarbonPool.IOM],
    }
    _validate_calculated_pools(month_index, final_pools)

    updated_values = state.model_dump()
    updated_values.update(
        month_index=month_index + 1,
        dpm_c=final_pools[CarbonPool.DPM],
        rpm_c=final_pools[CarbonPool.RPM],
        microbial_c=final_pools[CarbonPool.MICROBIAL],
        protected_soc_c=final_pools[CarbonPool.PROTECTED_SOC],
        iom_c=final_pools[CarbonPool.IOM],
        topsoil_moisture_deficit_mm=moisture.accumulated_tsmd_mm,
    )
    final_state = FieldState.model_validate(updated_values)
    mass_balance = verify_mass_balance(
        month_index=month_index,
        initial_carbon_t_c_ha=soil_carbon_total(state),
        final_carbon_t_c_ha=soil_carbon_total(final_state),
        ledger=ledger,
        numerics=parameters.numerics,
    )
    return CarbonCoreStepResult(
        initial_state=state,
        final_state=final_state,
        fluxes=ledger.records,
        modifiers=modifiers,
        respiration_t_c_ha=respiration_total,
        transfer_to_microbial_t_c_ha=microbial_total,
        transfer_to_protected_t_c_ha=protected_total,
        mass_balance=mass_balance,
        external_input_timing=parameters.rothc.external_input_timing,
        provenance=CORE_PROVENANCE,
    )


def run_carbon_core(
    initial_state: FieldState,
    monthly_steps: Iterable[CarbonCoreMonth],
    parameters: ModelParameters,
    *,
    seed: int | None = None,
) -> CarbonCoreSimulationResult:
    """Run a deterministic multi-month trajectory with seed provenance."""
    resolved_seed = parameters.numerics.default_seed if seed is None else seed
    if resolved_seed < 0:
        raise ValueError("seed must be non-negative")

    state = initial_state
    steps: list[CarbonCoreStepResult] = []
    ledger = FluxLedger()
    for month in monthly_steps:
        result = step_carbon_core(state, month, parameters)
        steps.append(result)
        ledger = ledger.extended(result.fluxes)
        state = result.final_state

    cumulative_mass_balance = verify_mass_balance(
        month_index=state.month_index,
        initial_carbon_t_c_ha=soil_carbon_total(initial_state),
        final_carbon_t_c_ha=soil_carbon_total(state),
        ledger=ledger,
        numerics=parameters.numerics,
    )
    return CarbonCoreSimulationResult(
        seed=resolved_seed,
        initial_state=initial_state,
        final_state=state,
        steps=tuple(steps),
        fluxes=ledger.records,
        cumulative_respiration_t_c_ha=math.fsum(step.respiration_t_c_ha for step in steps),
        cumulative_transfer_to_microbial_t_c_ha=math.fsum(
            step.transfer_to_microbial_t_c_ha for step in steps
        ),
        cumulative_transfer_to_protected_t_c_ha=math.fsum(
            step.transfer_to_protected_t_c_ha for step in steps
        ),
        cumulative_mass_balance=cumulative_mass_balance,
        external_input_timing=parameters.rothc.external_input_timing,
        provenance=CORE_PROVENANCE,
    )
