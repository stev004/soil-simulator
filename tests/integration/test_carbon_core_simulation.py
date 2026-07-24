"""Simple deterministic multi-month carbon-core integration tests."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from soil_simulator.domain.carbon import CarbonCoreMonth, CarbonInput
from soil_simulator.domain.models import FieldState
from soil_simulator.io.configuration import (
    load_carbon_core_scenario,
    load_model_parameters,
)
from soil_simulator.simulator.carbon_core import run_carbon_core

ROOT = Path(__file__).parents[2]
CONFIG_PATH = ROOT / "config" / "model_defaults.yaml"
SCENARIO_PATH = ROOT / "config" / "scenarios" / "carbon_core.yaml"


def test_predefined_scenario_runs_for_all_months_and_balances() -> None:
    parameters = load_model_parameters(CONFIG_PATH)
    scenario = load_carbon_core_scenario(SCENARIO_PATH)

    result = run_carbon_core(
        scenario.initial_state,
        scenario.monthly_steps,
        parameters,
        seed=scenario.seed,
    )

    assert len(result.steps) == len(scenario.monthly_steps)
    assert result.final_state.month_index == len(scenario.monthly_steps)
    assert result.final_state.iom_c == scenario.initial_state.iom_c
    assert result.cumulative_respiration_t_c_ha > 0.0
    assert result.cumulative_mass_balance.within_tolerance
    assert all(step.mass_balance.within_tolerance for step in result.steps)


def test_deterministic_replay_is_identical() -> None:
    parameters = load_model_parameters(CONFIG_PATH)
    scenario = load_carbon_core_scenario(SCENARIO_PATH)

    twenty_year_months = scenario.monthly_steps * 40
    first = run_carbon_core(
        scenario.initial_state,
        twenty_year_months,
        parameters,
        seed=scenario.seed,
    )
    second = run_carbon_core(
        scenario.initial_state,
        twenty_year_months,
        parameters,
        seed=scenario.seed,
    )

    assert first == second
    assert first.model_dump_json() == second.model_dump_json()


def test_all_zero_pools_and_inputs_remain_zero(field_state_data: dict[str, Any]) -> None:
    initial = FieldState.model_validate(field_state_data)
    zero = CarbonInput(classification="scenario_assumption", provenance="integration test")
    forcing = load_carbon_core_scenario(SCENARIO_PATH).monthly_steps[0].forcing
    month = CarbonCoreMonth(external_input=zero, forcing=forcing)
    result = run_carbon_core(initial, [month] * 24, load_model_parameters(CONFIG_PATH), seed=7)

    assert result.final_state.month_index == 24
    assert result.cumulative_respiration_t_c_ha == 0.0
    assert result.cumulative_mass_balance.residual_t_c_ha == 0.0
    assert all(step.fluxes == () for step in result.steps)


def test_negative_seed_is_rejected() -> None:
    scenario = load_carbon_core_scenario(SCENARIO_PATH)
    with pytest.raises(ValueError, match="seed must be non-negative"):
        run_carbon_core(
            scenario.initial_state,
            scenario.monthly_steps,
            load_model_parameters(CONFIG_PATH),
            seed=-1,
        )
