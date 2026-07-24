"""Scenario-direction regressions for the provisional Phase 4 baseline."""

from __future__ import annotations

from pathlib import Path

from soil_simulator.domain.models import ModelParameters
from soil_simulator.domain.plant import PlantMonth
from soil_simulator.io.configuration import load_model_parameters, load_plant_scenario
from soil_simulator.simulator.plant_baseline import run_plant_baseline

ROOT = Path(__file__).parents[2]
PARAMETERS = load_model_parameters(ROOT / "config" / "model_defaults.yaml")
SCENARIO = load_plant_scenario(ROOT / "config" / "scenarios" / "spring_barley_baseline.yaml")


def _water_scenario(*, dry: bool) -> tuple[PlantMonth, ...]:
    water = {"precipitation_mm": 0.0, "open_pan_evaporation_mm": 200.0}
    if not dry:
        water = {"precipitation_mm": 200.0, "open_pan_evaporation_mm": 0.0}
    return tuple(
        month.model_copy(update={"forcing": month.forcing.model_copy(update=water)})
        for month in SCENARIO.monthly_steps
    )


def _residue_parameters(retained: float) -> ModelParameters:
    values = PARAMETERS.model_dump(mode="python", by_alias=True)
    values["plant"]["aboveground_residue_retained_fraction"]["default"] = retained
    values["plant"]["root_residue_fraction"]["default"] = retained
    return ModelParameters.model_validate(values)


def test_drought_reduces_biomass_and_yield() -> None:
    wet = run_plant_baseline(SCENARIO.initial_state, _water_scenario(dry=False), PARAMETERS)
    dry = run_plant_baseline(SCENARIO.initial_state, _water_scenario(dry=True), PARAMETERS)
    assert dry.cumulative_realised_npp_t_c_ha < wet.cumulative_realised_npp_t_c_ha
    assert dry.cumulative_grain_yield_t_dm_ha < wet.cumulative_grain_yield_t_dm_ha


def test_phosphorus_limitation_reduces_biomass_and_yield() -> None:
    limited = run_plant_baseline(
        SCENARIO.initial_state.model_copy(update={"available_p_kg_ha": 0.1}),
        _water_scenario(dry=False),
        PARAMETERS,
    )
    sufficient = run_plant_baseline(
        SCENARIO.initial_state.model_copy(update={"available_p_kg_ha": 100.0}),
        _water_scenario(dry=False),
        PARAMETERS,
    )
    assert limited.cumulative_realised_npp_t_c_ha < sufficient.cumulative_realised_npp_t_c_ha
    assert limited.cumulative_grain_yield_t_dm_ha < sufficient.cumulative_grain_yield_t_dm_ha


def test_retained_residues_increase_soil_carbon_inputs_over_complete_removal() -> None:
    retained = run_plant_baseline(
        SCENARIO.initial_state, _water_scenario(dry=False), _residue_parameters(1.0)
    )
    removed = run_plant_baseline(
        SCENARIO.initial_state, _water_scenario(dry=False), _residue_parameters(0.0)
    )
    retained_inputs = (
        retained.cumulative_residue_to_dpm_t_c_ha + retained.cumulative_residue_to_rpm_t_c_ha
    )
    removed_inputs = (
        removed.cumulative_residue_to_dpm_t_c_ha + removed.cumulative_residue_to_rpm_t_c_ha
    )
    assert retained_inputs > removed_inputs
    assert removed_inputs == 0.0
