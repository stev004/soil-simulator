"""Reference tests for official RothC modifiers and clay partitioning."""

from __future__ import annotations

from pathlib import Path

import pytest

from soil_simulator.io.configuration import load_model_parameters
from soil_simulator.processes.rothc import (
    clay_carbon_partition,
    maximum_topsoil_moisture_deficit_mm,
    moisture_modifier,
    soil_cover_modifier,
    temperature_modifier,
)

PARAMETERS = load_model_parameters(
    Path(__file__).parents[2] / "config" / "model_defaults.yaml"
).rothc


@pytest.mark.parametrize(
    ("temperature_c", "expected"),
    [
        (-6.0, 0.0),
        (-5.0, 0.01618811582303663),
        (0.0, 0.143872428330698),
        (10.0, 1.0990400705164),
        (20.0, 2.82149253049831),
    ],
)
def test_temperature_modifier_official_reference_values(
    temperature_c: float, expected: float
) -> None:
    assert temperature_modifier(temperature_c, PARAMETERS) == pytest.approx(expected, rel=1e-13)


def test_maximum_tsmd_matches_rothamsted_worked_value() -> None:
    assert maximum_topsoil_moisture_deficit_mm(23.4, 23.0, PARAMETERS) == pytest.approx(-44.9444)


def test_moisture_deficit_accumulates_caps_and_resets_using_official_table() -> None:
    rainfall = (74.0, 59.0, 62.0, 51.0, 52.0, 57.0, 34.0, 55.0, 58.0, 56.0, 75.0)
    evaporation = (8.0, 10.0, 27.0, 49.0, 83.0, 99.0, 103.0, 91.0, 69.0, 34.0, 16.0)
    expected = (0.0, 0.0, 0.0, 0.0, -10.25, -27.5, -44.9444, -44.9444, -38.6944, -8.1944, 0.0)
    accumulated = 0.0
    for rain, evap, expected_deficit in zip(rainfall, evaporation, expected, strict=True):
        result = moisture_modifier(
            previous_accumulated_tsmd_mm=accumulated,
            precipitation_mm=rain,
            open_pan_evaporation_mm=evap,
            is_covered=True,
            clay_percent=23.4,
            soil_depth_cm=23.0,
            parameters=PARAMETERS,
        )
        accumulated = result.accumulated_tsmd_mm
        assert accumulated == pytest.approx(expected_deficit, abs=1e-12)
    assert accumulated == 0.0


def test_bare_soil_limit_prevents_additional_drying_but_allows_wetting() -> None:
    bare_limit = 0.556 * maximum_topsoil_moisture_deficit_mm(23.4, 23.0, PARAMETERS)
    dry = moisture_modifier(
        previous_accumulated_tsmd_mm=0.0,
        precipitation_mm=0.0,
        open_pan_evaporation_mm=100.0,
        is_covered=False,
        clay_percent=23.4,
        soil_depth_cm=23.0,
        parameters=PARAMETERS,
    )
    assert dry.accumulated_tsmd_mm == pytest.approx(bare_limit)
    already_drier = moisture_modifier(
        previous_accumulated_tsmd_mm=-35.0,
        precipitation_mm=0.0,
        open_pan_evaporation_mm=100.0,
        is_covered=False,
        clay_percent=23.4,
        soil_depth_cm=23.0,
        parameters=PARAMETERS,
    )
    assert already_drier.accumulated_tsmd_mm == -35.0
    wetter = moisture_modifier(
        previous_accumulated_tsmd_mm=-35.0,
        precipitation_mm=20.0,
        open_pan_evaporation_mm=0.0,
        is_covered=False,
        clay_percent=23.4,
        soil_depth_cm=23.0,
        parameters=PARAMETERS,
    )
    assert wetter.accumulated_tsmd_mm == -15.0


def test_covered_and_bare_soil_modifiers_match_official_constants() -> None:
    assert soil_cover_modifier(is_covered=True, parameters=PARAMETERS) == 0.6
    assert soil_cover_modifier(is_covered=False, parameters=PARAMETERS) == 1.0


def test_clay_partition_conserves_carbon_and_retains_more_at_higher_clay() -> None:
    low = clay_carbon_partition(10.0, PARAMETERS)
    high = clay_carbon_partition(60.0, PARAMETERS)
    assert low.co2_fraction + low.microbial_fraction + low.protected_fraction == pytest.approx(1.0)
    assert high.retained_fraction > low.retained_fraction
    assert high.co2_fraction < low.co2_fraction


def test_rothamsted_clay_ratio_and_microbial_protected_routing() -> None:
    partition = clay_carbon_partition(23.4, PARAMETERS)
    assert partition.co2_to_retained_ratio == pytest.approx(3.514182798867504)
    assert partition.microbial_fraction / partition.retained_fraction == pytest.approx(0.46)
    assert partition.protected_fraction / partition.retained_fraction == pytest.approx(0.54)
