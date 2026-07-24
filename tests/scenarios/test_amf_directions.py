"""Scenario-direction tests for beneficial, neutral, and harmful AMF outcomes."""

from __future__ import annotations

from pathlib import Path

from soil_simulator.domain.models import ModelParameters
from soil_simulator.domain.plant import PlantMonth
from soil_simulator.io.configuration import load_model_parameters, load_plant_scenario
from soil_simulator.simulator.amf_extension import step_amf_extension

ROOT = Path(__file__).parents[2]
PARAMETERS = load_model_parameters(ROOT / "config" / "model_defaults.yaml")
SCENARIO = load_plant_scenario(ROOT / "config" / "scenarios" / "spring_barley_baseline.yaml")


def _parameters(**defaults: float) -> ModelParameters:
    values = PARAMETERS.model_dump(mode="python", by_alias=True)
    for name, value in defaults.items():
        values["amf"][name]["default"] = value
    return ModelParameters.model_validate(values)


def _wet_growth_month() -> PlantMonth:
    template = SCENARIO.monthly_steps[5]
    return template.model_copy(
        update={
            "forcing": template.forcing.model_copy(
                update={"precipitation_mm": 200.0, "open_pan_evaporation_mm": 0.0}
            )
        }
    )


def test_amf_can_be_beneficial_under_p_limitation() -> None:
    parameters = _parameters(p_uptake_vmax=3.0, photosynthate_allocation_fraction=0.02)
    state = SCENARIO.initial_state.model_copy(
        update={"amf_live_c": 1.0, "amf_necromass_c": 0.0, "available_p_kg_ha": 0.5}
    )
    result = step_amf_extension(state, _wet_growth_month(), parameters)
    assert result.plant_outcome == "beneficial"
    assert result.net_plant_carbon_effect_t_c_ha > 0.0


def test_amf_is_neutral_when_p_is_effectively_sufficient_and_cost_approaches_zero() -> None:
    state = SCENARIO.initial_state.model_copy(
        update={"amf_live_c": 0.0, "amf_necromass_c": 0.0, "available_p_kg_ha": 1.0e12}
    )
    result = step_amf_extension(state, _wet_growth_month(), PARAMETERS)
    assert result.plant_outcome == "neutral"
    assert abs(result.net_plant_carbon_effect_t_c_ha) <= (
        PARAMETERS.numerics.absolute_mass_balance_tolerance
    )


def test_amf_is_harmful_when_carbon_cost_exceeds_p_benefit() -> None:
    state = SCENARIO.initial_state.model_copy(
        update={"amf_live_c": 0.0, "amf_necromass_c": 0.0, "available_p_kg_ha": 100.0}
    )
    result = step_amf_extension(state, _wet_growth_month(), PARAMETERS)
    assert result.plant_outcome == "harmful"
    assert result.net_plant_carbon_effect_t_c_ha < 0.0


def test_more_live_fungal_biomass_does_not_automatically_raise_protected_carbon() -> None:
    month_without_growth = SCENARIO.monthly_steps[0]
    low = step_amf_extension(
        SCENARIO.initial_state.model_copy(update={"amf_live_c": 0.0, "amf_necromass_c": 0.0}),
        month_without_growth,
        PARAMETERS,
    )
    high = step_amf_extension(
        SCENARIO.initial_state.model_copy(update={"amf_live_c": 10.0, "amf_necromass_c": 0.0}),
        month_without_growth,
        PARAMETERS,
    )
    assert high.fungal_turnover_t_c_ha > low.fungal_turnover_t_c_ha
    assert high.necromass_to_protected_t_c_ha == low.necromass_to_protected_t_c_ha == 0.0
    assert high.final_state.protected_soc_c == low.final_state.protected_soc_c
