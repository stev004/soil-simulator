"""Integrated Phase 5 AMF carbon, P, routing, and replay tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from soil_simulator.domain.models import ModelParameters
from soil_simulator.domain.plant import PlantMonth
from soil_simulator.io.configuration import load_model_parameters, load_plant_scenario
from soil_simulator.simulator.amf_extension import run_amf_extension, step_amf_extension

ROOT = Path(__file__).parents[2]
PARAMETERS = load_model_parameters(ROOT / "config" / "model_defaults.yaml")
SCENARIO = load_plant_scenario(ROOT / "config" / "scenarios" / "spring_barley_baseline.yaml")


def _parameters(**defaults: float) -> ModelParameters:
    values = PARAMETERS.model_dump(mode="python", by_alias=True)
    for name, value in defaults.items():
        values["amf"][name]["default"] = value
    return ModelParameters.model_validate(values)


def _wet_growth_month(*, harvest: bool = False) -> PlantMonth:
    template = SCENARIO.monthly_steps[5]
    return template.model_copy(
        update={
            "harvest": harvest,
            "forcing": template.forcing.model_copy(
                update={"precipitation_mm": 200.0, "open_pan_evaporation_mm": 0.0}
            ),
        }
    )


def test_fungal_carbon_cost_respiration_and_balances() -> None:
    state = SCENARIO.initial_state.model_copy(
        update={"amf_live_c": 0.0, "amf_necromass_c": 0.0, "available_p_kg_ha": 100.0}
    )
    result = step_amf_extension(state, _wet_growth_month(), PARAMETERS)
    assert result.plant_to_amf_carbon_t_c_ha > 0.0
    assert result.net_plant_carbon_t_c_ha < result.gross_realised_plant_carbon_t_c_ha
    assert result.fungal_respiration_t_c_ha > 0.0
    assert result.fungal_biomass_growth_t_c_ha + result.fungal_respiration_t_c_ha == (
        pytest.approx(result.plant_to_amf_carbon_t_c_ha)
    )
    assert result.carbon_mass_balance.within_tolerance
    assert result.phosphorus_mass_balance.within_tolerance


def test_turnover_enters_necromass_then_preexisting_necromass_routes_post_decomposition() -> None:
    state = SCENARIO.initial_state.model_copy(update={"amf_live_c": 0.2, "amf_necromass_c": 0.3})
    result = step_amf_extension(state, SCENARIO.monthly_steps[0], PARAMETERS)
    assert result.fungal_turnover_t_c_ha > 0.0
    assert result.necromass_decomposition_t_c_ha > 0.0
    assert result.necromass_to_dpm_t_c_ha > 0.0
    assert result.necromass_to_rpm_t_c_ha > 0.0
    assert result.necromass_to_protected_t_c_ha > 0.0
    assert result.final_state.amf_necromass_c > 0.0
    assert result.carbon_mass_balance.within_tolerance


def test_amf_phosphorus_transfer_is_recorded_without_creating_p() -> None:
    state = SCENARIO.initial_state.model_copy(
        update={"amf_live_c": 1.0, "amf_necromass_c": 0.0, "available_p_kg_ha": 0.5}
    )
    result = step_amf_extension(state, _wet_growth_month(), PARAMETERS)
    assert result.amf_phosphorus_acquired_kg_p_ha > 0.0
    assert result.amf_phosphorus_transferred_kg_p_ha > 0.0
    assert result.amf_phosphorus_transferred_kg_p_ha <= (result.amf_phosphorus_acquired_kg_p_ha)
    assert any(
        record.process == "amf_phosphorus_transfer_to_plant" for record in result.phosphorus_fluxes
    )
    assert result.phosphorus_mass_balance.within_tolerance


def test_deterministic_twenty_year_amf_replay_is_identical() -> None:
    months = SCENARIO.monthly_steps * 20
    first = run_amf_extension(SCENARIO.initial_state, months, PARAMETERS, seed=SCENARIO.seed)
    second = run_amf_extension(SCENARIO.initial_state, months, PARAMETERS, seed=SCENARIO.seed)
    assert first == second
    assert first.model_dump_json() == second.model_dump_json()
    assert first.final_state.month_index == 240
    assert first.cumulative_carbon_mass_balance.within_tolerance
    assert first.cumulative_phosphorus_mass_balance.within_tolerance
