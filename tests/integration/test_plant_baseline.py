"""Integrated Phase 4 plant, P, harvest, residue and replay tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from soil_simulator.domain.models import FieldState, ModelParameters
from soil_simulator.domain.plant import PlantMonth
from soil_simulator.io.configuration import load_model_parameters, load_plant_scenario
from soil_simulator.simulator.plant_baseline import run_plant_baseline, step_plant_baseline

ROOT = Path(__file__).parents[2]
PARAMETERS = load_model_parameters(ROOT / "config" / "model_defaults.yaml")
SCENARIO = load_plant_scenario(ROOT / "config" / "scenarios" / "spring_barley_baseline.yaml")


def _zero_decay(parameters: ModelParameters) -> ModelParameters:
    values = parameters.model_dump(mode="python", by_alias=True)
    values["rothc"].update(
        k_dpm_year=0.0,
        k_rpm_year=0.0,
        k_microbial_year=0.0,
        k_protected_year=0.0,
    )
    return ModelParameters.model_validate(values)


def _initial(**updates: float) -> FieldState:
    return SCENARIO.initial_state.model_copy(update=updates)


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


def test_zero_potential_npp_produces_no_growth_or_p_uptake() -> None:
    result = step_plant_baseline(_initial(), SCENARIO.monthly_steps[0], PARAMETERS)
    assert result.potential_npp_t_c_ha == 0.0
    assert result.realised_npp_t_c_ha == 0.0
    assert result.shoot_growth_t_c_ha == 0.0
    assert result.root_growth_t_c_ha == 0.0
    assert result.phosphorus_uptake_kg_p_ha == 0.0


def test_phosphorus_limitation_uptake_depletion_and_no_negative_pool() -> None:
    initial = _initial(available_p_kg_ha=0.1)
    result = step_plant_baseline(initial, _wet_growth_month(), PARAMETERS)
    assert 0.0 < result.stress.phosphorus < 1.0
    assert result.phosphorus_uptake_kg_p_ha == pytest.approx(0.1)
    assert result.final_state.available_p_kg_ha == 0.0
    assert result.final_state.available_p_kg_ha >= 0.0
    assert result.phosphorus_mass_balance.within_tolerance


def test_external_phosphorus_input_is_recorded_and_balanced() -> None:
    month = _wet_growth_month().model_copy(update={"external_available_p_kg_ha": 5.0})
    result = step_plant_baseline(_initial(available_p_kg_ha=0.0), month, PARAMETERS)
    assert any(
        record.process == "external_available_phosphorus_input"
        for record in result.phosphorus_fluxes
    )
    assert any(record.process == "plant_phosphorus_uptake" for record in result.phosphorus_fluxes)
    assert result.phosphorus_mass_balance.within_tolerance


def test_integrated_harvest_transfers_residue_after_rothc_decomposition() -> None:
    initial = _initial(
        plant_c=2.0,
        root_c=1.0,
        dpm_c=0.0,
        rpm_c=0.0,
        microbial_c=0.0,
        protected_soc_c=0.0,
        iom_c=0.0,
    )
    january_harvest = SCENARIO.monthly_steps[0].model_copy(update={"harvest": True})
    result = step_plant_baseline(initial, january_harvest, PARAMETERS)
    expected_residue = 2.0 * (1.0 - 0.45) + 1.0
    assert result.grain_yield_t_dm_ha == pytest.approx(2.0)
    assert result.harvested_biomass_carbon_t_c_ha == pytest.approx(0.9)
    assert result.residue_to_dpm_t_c_ha + result.residue_to_rpm_t_c_ha == pytest.approx(
        expected_residue
    )
    assert result.final_state.dpm_c == pytest.approx(result.residue_to_dpm_t_c_ha)
    assert result.final_state.rpm_c == pytest.approx(result.residue_to_rpm_t_c_ha)
    assert result.residue_to_dpm_t_c_ha / result.residue_to_rpm_t_c_ha == pytest.approx(1.44)
    assert result.final_state.plant_c == 0.0
    assert result.final_state.root_c == 0.0
    assert result.carbon_mass_balance.within_tolerance


def test_shoot_root_growth_and_whole_system_carbon_balance() -> None:
    result = step_plant_baseline(_initial(), _wet_growth_month(), _zero_decay(PARAMETERS))
    assert result.shoot_growth_t_c_ha / result.realised_npp_t_c_ha == pytest.approx(0.7)
    assert result.root_growth_t_c_ha / result.realised_npp_t_c_ha == pytest.approx(0.3)
    assert result.carbon_mass_balance.within_tolerance
    assert (
        abs(result.carbon_mass_balance.residual_t_c_ha)
        <= result.carbon_mass_balance.tolerance_t_c_ha
    )


def test_deterministic_twenty_year_replay_is_identical() -> None:
    months = SCENARIO.monthly_steps * 20
    first = run_plant_baseline(SCENARIO.initial_state, months, PARAMETERS, seed=SCENARIO.seed)
    second = run_plant_baseline(SCENARIO.initial_state, months, PARAMETERS, seed=SCENARIO.seed)
    assert first == second
    assert first.model_dump_json() == second.model_dump_json()
    assert first.final_state.month_index == 240
    assert first.cumulative_carbon_mass_balance.within_tolerance
    assert first.cumulative_phosphorus_mass_balance.within_tolerance
