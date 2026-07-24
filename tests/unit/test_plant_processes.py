"""Unit verification for pure Phase 4 plant and residue calculations."""

from __future__ import annotations

from pathlib import Path

import pytest

from soil_simulator.io.configuration import load_model_parameters
from soil_simulator.processes.plant import (
    allocate_npp,
    combine_stress_modifiers,
    harvest_plant,
    partition_residue_dpm_rpm,
    plant_moisture_modifier,
    plant_temperature_modifier,
    prescribed_potential_npp,
)

PARAMETERS = load_model_parameters(Path(__file__).parents[2] / "config" / "model_defaults.yaml")


def test_prescribed_monthly_npp_uses_configured_profile() -> None:
    assert prescribed_potential_npp(1, PARAMETERS.plant) == 0.0
    assert prescribed_potential_npp(6, PARAMETERS.plant) == pytest.approx(6.0 * 0.27)


def test_temperature_stress_has_full_and_severe_configured_endpoints() -> None:
    assert plant_temperature_modifier(15.0, PARAMETERS.plant) == 1.0
    assert plant_temperature_modifier(35.0, PARAMETERS.plant) == 0.0
    assert plant_temperature_modifier(5.0, PARAMETERS.plant) == pytest.approx(0.5)


def test_water_stress_has_full_and_severe_configured_endpoints() -> None:
    assert plant_moisture_modifier(1.0, PARAMETERS.rothc) == 1.0
    assert plant_moisture_modifier(0.2, PARAMETERS.rothc) == 0.0


def test_stress_combination_is_transparent_and_bounded() -> None:
    assert combine_stress_modifiers(0.5, 0.4, 0.25) == pytest.approx(0.05)
    with pytest.raises(ValueError, match=r"within \[0, 1\]"):
        combine_stress_modifiers(1.1, 1.0, 1.0)


def test_shoot_root_allocation_conserves_realised_npp() -> None:
    allocation = allocate_npp(2.0, 0.3)
    assert allocation.shoot_t_c_ha == pytest.approx(1.4)
    assert allocation.root_t_c_ha == pytest.approx(0.6)
    assert allocation.shoot_t_c_ha + allocation.root_t_c_ha == 2.0


def test_harvest_yield_and_residue_architecture() -> None:
    result = harvest_plant(
        shoot_c_t_ha=2.0,
        root_c_t_ha=1.0,
        harvest_index=0.45,
        aboveground_retained_fraction=0.5,
        root_residue_fraction=1.0,
        carbon_fraction_of_dry_matter=0.45,
    )
    assert result.grain_carbon_t_c_ha == pytest.approx(0.9)
    assert result.grain_yield_t_dm_ha == pytest.approx(2.0)
    assert result.retained_aboveground_residue_t_c_ha == pytest.approx(0.55)
    assert result.aboveground_export_t_c_ha == pytest.approx(0.55)
    assert result.root_residue_t_c_ha == 1.0


def test_dpm_rpm_partition_matches_configured_ratio_and_conserves_residue() -> None:
    dpm, rpm = partition_residue_dpm_rpm(2.44, PARAMETERS.rothc.crop_dpm_rpm_ratio)
    assert dpm == pytest.approx(1.44)
    assert rpm == pytest.approx(1.0)
    assert dpm / rpm == pytest.approx(1.44)
    assert dpm + rpm == pytest.approx(2.44)
