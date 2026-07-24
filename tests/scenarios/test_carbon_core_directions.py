"""Regression checks of Phase 3 carbon-core scientific intent."""

from __future__ import annotations

from pathlib import Path

from soil_simulator.domain.carbon import CarbonCoreMonth, CarbonInput
from soil_simulator.io.configuration import (
    load_carbon_core_scenario,
    load_model_parameters,
)
from soil_simulator.simulator.carbon_core import run_carbon_core, step_carbon_core

ROOT = Path(__file__).parents[2]
PARAMETERS = load_model_parameters(ROOT / "config" / "model_defaults.yaml")
SCENARIO = load_carbon_core_scenario(ROOT / "config" / "scenarios" / "carbon_core.yaml")


def _zero_month(template_index: int = 0) -> CarbonCoreMonth:
    return CarbonCoreMonth(
        external_input=CarbonInput(
            classification="scenario_assumption", provenance="direction test"
        ),
        forcing=SCENARIO.monthly_steps[template_index].forcing,
    )


def test_no_external_inputs_deplete_total_active_carbon_but_not_iom() -> None:
    initial = SCENARIO.initial_state
    result = run_carbon_core(initial, [_zero_month()] * 12, PARAMETERS, seed=20260720)

    assert result.final_state.dpm_c < initial.dpm_c
    assert result.final_state.rpm_c < initial.rpm_c
    initial_active = initial.dpm_c + initial.rpm_c + initial.microbial_c + initial.protected_soc_c
    final_active = (
        result.final_state.dpm_c
        + result.final_state.rpm_c
        + result.final_state.microbial_c
        + result.final_state.protected_soc_c
    )
    assert final_active < initial_active
    assert result.final_state.iom_c == initial.iom_c


def test_warmer_non_extreme_month_increases_respiration() -> None:
    base = _zero_month()
    cool = base.model_copy(
        update={"forcing": base.forcing.model_copy(update={"mean_air_temperature_c": 5.0})}
    )
    warm = base.model_copy(
        update={"forcing": base.forcing.model_copy(update={"mean_air_temperature_c": 15.0})}
    )
    cool_result = step_carbon_core(SCENARIO.initial_state, cool, PARAMETERS)
    warm_result = step_carbon_core(SCENARIO.initial_state, warm, PARAMETERS)
    assert warm_result.modifiers.temperature > cool_result.modifiers.temperature
    assert warm_result.respiration_t_c_ha > cool_result.respiration_t_c_ha


def test_higher_clay_routes_more_decomposed_carbon_to_retained_pools() -> None:
    base = _zero_month()
    low = base.model_copy(
        update={"forcing": base.forcing.model_copy(update={"clay_percent": 10.0})}
    )
    high = base.model_copy(
        update={"forcing": base.forcing.model_copy(update={"clay_percent": 60.0})}
    )
    low_result = step_carbon_core(SCENARIO.initial_state, low, PARAMETERS)
    high_result = step_carbon_core(SCENARIO.initial_state, high, PARAMETERS)
    assert high_result.modifiers.retained_fraction > low_result.modifiers.retained_fraction
    assert high_result.modifiers.co2_fraction < low_result.modifiers.co2_fraction
