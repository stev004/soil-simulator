"""Unit tests for one-month carbon-core behavior and flow traceability."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from soil_simulator.domain.carbon import CarbonCoreMonth, CarbonInput, RothCForcing
from soil_simulator.domain.models import FieldState, ModelParameters
from soil_simulator.io.configuration import load_model_parameters
from soil_simulator.simulator.carbon_core import soil_carbon_total, step_carbon_core

CONFIG_PATH = Path(__file__).parents[2] / "config" / "model_defaults.yaml"


def _state(field_state_data: dict[str, Any]) -> FieldState:
    field_state_data.update(
        dpm_c=2.0,
        rpm_c=10.0,
        microbial_c=1.0,
        protected_soc_c=35.0,
        iom_c=7.0,
    )
    return FieldState.model_validate(field_state_data)


def _zero_decay(parameters: ModelParameters) -> ModelParameters:
    values = parameters.model_dump(mode="python", by_alias=True)
    values["rothc"].update(
        k_dpm_year=0.0,
        k_rpm_year=0.0,
        k_microbial_year=0.0,
        k_protected_year=0.0,
    )
    return ModelParameters.model_validate(values)


def _month(external_input: CarbonInput, parameters: ModelParameters) -> CarbonCoreMonth:
    temperature_for_unit_modifier = (
        parameters.rothc.temperature_exponent_numerator
        / math.log(parameters.rothc.temperature_numerator - 1.0)
        - parameters.rothc.temperature_offset_c
    )
    return CarbonCoreMonth(
        external_input=external_input,
        forcing=RothCForcing(
            mean_air_temperature_c=temperature_for_unit_modifier,
            precipitation_mm=100.0,
            open_pan_evaporation_mm=0.0,
            is_covered=False,
            clay_percent=23.4,
            soil_depth_cm=23.0,
            provenance="unit-test forcing",
        ),
    )


def test_zero_input_decay_matches_each_configured_rate(field_state_data: dict[str, Any]) -> None:
    parameters = load_model_parameters(CONFIG_PATH)
    initial = _state(field_state_data)
    zero_input = CarbonInput(classification="scenario_assumption", provenance="unit test")

    result = step_carbon_core(initial, _month(zero_input, parameters), parameters)

    assert result.final_state.dpm_c == pytest.approx(2.0 * math.exp(-10.0 / 12.0))
    assert result.final_state.rpm_c == pytest.approx(10.0 * math.exp(-0.3 / 12.0))
    assert result.final_state.microbial_c > 1.0 * math.exp(-0.66 / 12.0)
    assert result.final_state.protected_soc_c > 35.0 * math.exp(-0.02 / 12.0)
    assert result.final_state.iom_c == 7.0
    assert result.mass_balance.within_tolerance
    assert abs(result.mass_balance.residual_t_c_ha) <= result.mass_balance.tolerance_t_c_ha


def test_zero_decay_preserves_active_and_inert_pools(field_state_data: dict[str, Any]) -> None:
    parameters = _zero_decay(load_model_parameters(CONFIG_PATH))
    initial = _state(field_state_data)
    zero_input = CarbonInput(classification="scenario_assumption", provenance="unit test")

    result = step_carbon_core(initial, _month(zero_input, parameters), parameters)

    assert soil_carbon_total(result.final_state) == soil_carbon_total(initial)
    assert result.final_state.model_copy(update={"month_index": 0}) == initial
    assert result.fluxes == ()


def test_ledger_records_inputs_and_each_respiration_loss(field_state_data: dict[str, Any]) -> None:
    parameters = load_model_parameters(CONFIG_PATH)
    initial = _state(field_state_data)
    external_input = CarbonInput(
        dpm_c=0.2,
        rpm_c=0.1,
        protected_soc_c=0.02,
        classification="scenario_assumption",
        provenance="traceable unit-test input",
    )

    result = step_carbon_core(initial, _month(external_input, parameters), parameters)

    input_records = [record for record in result.fluxes if record.source_pool == "external_inputs"]
    respiration_records = [
        record for record in result.fluxes if record.destination_pool == "atmosphere"
    ]
    assert {record.destination_pool for record in input_records} == {
        "dpm_c",
        "rpm_c",
        "protected_soc_c",
    }
    assert {record.source_pool for record in respiration_records} == {
        "dpm_c",
        "rpm_c",
        "microbial_c",
        "protected_soc_c",
    }
    assert math.fsum(record.amount_t_c_ha for record in input_records) == pytest.approx(0.32)
    assert result.transfer_to_microbial_t_c_ha > 0.0
    assert result.transfer_to_protected_t_c_ha > 0.0
    assert result.transfer_to_microbial_t_c_ha / result.transfer_to_protected_t_c_ha == (
        pytest.approx(0.46 / 0.54)
    )
    assert all(record.parameter_version == parameters.model.version for record in result.fluxes)
    assert all(record.uncertainty_t_c_ha is None for record in result.fluxes)


def test_non_core_state_passes_through_unchanged(field_state_data: dict[str, Any]) -> None:
    field_state_data.update(
        plant_c=1.0,
        root_c=2.0,
        amf_live_c=0.2,
        amf_necromass_c=0.3,
        available_p_kg_ha=4.0,
        crop_development=0.5,
        cumulative_yield_t_dm_ha=3.0,
    )
    initial = _state(field_state_data)
    result = step_carbon_core(
        initial,
        _month(
            CarbonInput(classification="scenario_assumption", provenance="unit test"),
            load_model_parameters(CONFIG_PATH),
        ),
        load_model_parameters(CONFIG_PATH),
    )
    for field in (
        "plant_c",
        "root_c",
        "amf_live_c",
        "amf_necromass_c",
        "available_p_kg_ha",
        "crop_development",
        "cumulative_yield_t_dm_ha",
    ):
        assert getattr(result.final_state, field) == getattr(initial, field)


@pytest.mark.parametrize("invalid", [-0.1, float("nan"), float("inf")])
def test_external_carbon_input_rejects_negative_or_non_finite_values(invalid: float) -> None:
    with pytest.raises(ValidationError):
        CarbonInput(
            dpm_c=invalid,
            classification="scenario_assumption",
            provenance="invalid unit test",
        )


def test_zero_environmental_modifier_prevents_all_decay(field_state_data: dict[str, Any]) -> None:
    parameters = load_model_parameters(CONFIG_PATH)
    initial = _state(field_state_data)
    month = CarbonCoreMonth(
        external_input=CarbonInput(classification="scenario_assumption", provenance="unit test"),
        forcing=RothCForcing(
            mean_air_temperature_c=-6.0,
            precipitation_mm=0.0,
            open_pan_evaporation_mm=0.0,
            is_covered=False,
            clay_percent=23.4,
            soil_depth_cm=23.0,
            provenance="zero modifier unit test",
        ),
    )
    result = step_carbon_core(initial, month, parameters)
    assert result.modifiers.combined == 0.0
    assert result.final_state.model_copy(update={"month_index": 0}) == initial
    assert result.fluxes == ()


def test_official_post_decomposition_input_timing_and_legacy_compatibility(
    field_state_data: dict[str, Any],
) -> None:
    field_state_data["dpm_c"] = 0.0
    initial = FieldState.model_validate(field_state_data)
    parameters = load_model_parameters(CONFIG_PATH)
    month = _month(
        CarbonInput(
            dpm_c=1.0,
            classification="scenario_assumption",
            provenance="input timing test",
        ),
        parameters,
    )

    official = step_carbon_core(initial, month, parameters)
    legacy_values = parameters.model_dump(mode="python", by_alias=True)
    legacy_values["rothc"]["external_input_timing"] = "legacy_pre_decomposition"
    legacy_parameters = ModelParameters.model_validate(legacy_values)
    legacy = step_carbon_core(initial, month, legacy_parameters)

    assert official.external_input_timing == "post_decomposition"
    assert official.final_state.dpm_c == 1.0
    assert legacy.final_state.dpm_c < 1.0
    assert official.mass_balance.within_tolerance
    assert legacy.mass_balance.within_tolerance
