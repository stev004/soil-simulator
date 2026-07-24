"""Unit tests for every bootstrap domain validation category."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from typing import Any

import pytest
from pydantic import ValidationError

from soil_simulator.domain.models import (
    FieldProperties,
    FieldState,
    FluxRecord,
    ManagementEvent,
    ModelParameter,
    SimulationManifest,
    WeatherMonth,
)


def test_field_properties_accept_texture_rounding_tolerance(
    field_properties_data: dict[str, Any],
) -> None:
    field_properties_data["sand_percent"] = 30.009
    assert FieldProperties.model_validate(field_properties_data).sand_percent == 30.009


def test_field_properties_reject_invalid_texture_sum(
    field_properties_data: dict[str, Any],
) -> None:
    field_properties_data["sand_percent"] = 29.0
    with pytest.raises(ValidationError, match="must sum to"):
        FieldProperties.model_validate(field_properties_data)


def test_field_properties_reject_non_positive_depth(
    field_properties_data: dict[str, Any],
) -> None:
    field_properties_data["soil_depth_cm"] = 0.0
    with pytest.raises(ValidationError):
        FieldProperties.model_validate(field_properties_data)


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_field_properties_reject_non_finite_values(
    field_properties_data: dict[str, Any], value: float
) -> None:
    field_properties_data["baseline_soc_t_c_ha"] = value
    with pytest.raises(ValidationError):
        FieldProperties.model_validate(field_properties_data)


def test_field_properties_require_coordinate_pair_or_archetype(
    field_properties_data: dict[str, Any],
) -> None:
    field_properties_data["synthetic_archetype"] = None
    with pytest.raises(ValidationError, match="coordinate pair or synthetic_archetype"):
        FieldProperties.model_validate(field_properties_data)


def test_field_properties_reject_partial_coordinate_pair(
    field_properties_data: dict[str, Any],
) -> None:
    field_properties_data.update(synthetic_archetype=None, latitude_deg=52.0)
    with pytest.raises(ValidationError, match="must be supplied together"):
        FieldProperties.model_validate(field_properties_data)


@pytest.mark.parametrize(
    "stock_name",
    [
        "plant_c",
        "root_c",
        "amf_live_c",
        "amf_necromass_c",
        "dpm_c",
        "rpm_c",
        "microbial_c",
        "protected_soc_c",
        "iom_c",
        "available_p_kg_ha",
        "cumulative_yield_t_dm_ha",
    ],
)
def test_field_state_rejects_every_negative_stock(
    field_state_data: dict[str, Any], stock_name: str
) -> None:
    field_state_data[stock_name] = -0.001
    with pytest.raises(ValidationError):
        FieldState.model_validate(field_state_data)


@pytest.mark.parametrize("fraction_name", ["crop_development", "aggregate_protection_index"])
def test_field_state_rejects_invalid_fractions(
    field_state_data: dict[str, Any], fraction_name: str
) -> None:
    field_state_data[fraction_name] = 1.01
    with pytest.raises(ValidationError):
        FieldState.model_validate(field_state_data)


def test_field_state_rejects_non_finite_moisture_deficit(
    field_state_data: dict[str, Any],
) -> None:
    field_state_data["topsoil_moisture_deficit_mm"] = float("nan")
    with pytest.raises(ValidationError):
        FieldState.model_validate(field_state_data)


def test_field_state_enforces_negative_rothc_moisture_deficit_convention(
    field_state_data: dict[str, Any],
) -> None:
    field_state_data["topsoil_moisture_deficit_mm"] = -10.0
    assert FieldState.model_validate(field_state_data).topsoil_moisture_deficit_mm == -10.0
    field_state_data["topsoil_moisture_deficit_mm"] = 0.01
    with pytest.raises(ValidationError):
        FieldState.model_validate(field_state_data)


def test_weather_rejects_negative_water_and_non_finite_temperature() -> None:
    base = {
        "year": 2026,
        "month": 7,
        "mean_air_temperature_c": 15.0,
        "precipitation_mm": 60.0,
        "potential_evapotranspiration_mm": 55.0,
        "source_id": "era5-land",
        "provenance": "test",
    }
    for name, value in (
        ("precipitation_mm", -1.0),
        ("potential_evapotranspiration_mm", -1.0),
        ("mean_air_temperature_c", float("inf")),
    ):
        invalid = {**base, name: value}
        with pytest.raises(ValidationError):
            WeatherMonth.model_validate(invalid)


def test_management_event_rejects_invalid_event_and_cost() -> None:
    base = {
        "event_id": "tillage-1",
        "event_type": "tillage",
        "event_date": date(2026, 3, 1),
        "amount": 1.0,
        "units": "operation_ha^-1",
        "parameters": [{"name": "tillage_level", "value": "reduced"}],
        "cost_gbp_ha": 10.0,
        "emissions_proxy_kg_co2e_ha": 2.0,
        "parameter_provenance": "provisional test effects",
        "source_classification": "scenario_assumption",
        "provenance": "scenario fixture",
    }
    assert ManagementEvent.model_validate(base).event_type == "tillage"
    with pytest.raises(ValidationError):
        ManagementEvent.model_validate({**base, "event_type": "biochar"})
    with pytest.raises(ValidationError):
        ManagementEvent.model_validate({**base, "cost_gbp_ha": -1.0})


def test_model_parameter_validates_bounds_and_fractions() -> None:
    base = {
        "name": "allocation",
        "default": 0.5,
        "min": 0.0,
        "max": 1.0,
        "unit": "fraction",
        "classification": "scenario_assumption",
        "version_introduced": "0.1.0",
    }
    assert ModelParameter.model_validate(base).default == 0.5
    with pytest.raises(ValidationError, match="default must lie"):
        ModelParameter.model_validate({**base, "default": 1.1})
    with pytest.raises(ValidationError, match="min must be"):
        ModelParameter.model_validate({**base, "min": 0.8, "max": 0.2})
    with pytest.raises(ValidationError, match="unit 'fraction'"):
        ModelParameter.model_validate({**base, "max": 1.1})
    with pytest.raises(ValidationError):
        ModelParameter.model_validate({**base, "default": float("nan")})
    with pytest.raises(ValidationError):
        ModelParameter.model_validate({**base, "classification": "unsupported"})


def test_flux_record_rejects_negative_or_non_finite_amount() -> None:
    base = {
        "month_index": 0,
        "source_pool": "plant_c",
        "destination_pool": "root_c",
        "amount_t_c_ha": 0.1,
        "process": "contract-test-only",
        "parameter_version": "0.1.0",
        "provenance": "unit test",
    }
    assert FluxRecord.model_validate(base).amount_t_c_ha == 0.1
    for invalid_amount in (-0.1, float("inf")):
        with pytest.raises(ValidationError):
            FluxRecord.model_validate({**base, "amount_t_c_ha": invalid_amount})


def test_manifest_validates_hash_seeds_and_timestamps() -> None:
    started = datetime(2026, 7, 20, tzinfo=UTC)
    base = {
        "run_id": "run-001",
        "model_version": "0.1.0",
        "configuration_hash": "a" * 64,
        "git_commit": "uncommitted",
        "environment_lockfile": "uv.lock",
        "field_ids": ["field-001"],
        "policy_ids": ["baseline"],
        "random_seed": 1,
        "weather_seed": 2,
        "biological_parameter_seed": 3,
        "input_data_versions": [],
        "started_at": started,
        "test_gate_status": "not-run",
    }
    assert SimulationManifest.model_validate(base).started_at == started
    with pytest.raises(ValidationError):
        SimulationManifest.model_validate({**base, "configuration_hash": "not-a-hash"})
    with pytest.raises(ValidationError):
        SimulationManifest.model_validate({**base, "random_seed": -1})
    with pytest.raises(ValidationError, match="timezone-aware"):
        SimulationManifest.model_validate({**base, "started_at": started.replace(tzinfo=None)})
    with pytest.raises(ValidationError, match="cannot precede"):
        SimulationManifest.model_validate({**base, "completed_at": started - timedelta(seconds=1)})


def test_models_are_immutable(field_state_data: dict[str, Any]) -> None:
    state = FieldState.model_validate(field_state_data)
    with pytest.raises(ValidationError):
        state.__setattr__("plant_c", 1.0)
