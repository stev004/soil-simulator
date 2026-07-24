"""Unit tests for pure deterministic AMF equations."""

from __future__ import annotations

import math

import pytest

from soil_simulator.processes.amf import (
    acquire_amf_phosphorus,
    allocate_plant_carbon_to_amf,
    decay_and_route_necromass,
    fungal_growth_and_respiration,
    fungal_turnover_t_c_ha,
    phosphorus_allocation_feedback,
)


def test_zero_realised_carbon_has_zero_amf_allocation() -> None:
    result = allocate_plant_carbon_to_amf(
        realised_plant_carbon_t_c_ha=0.0,
        base_fraction=0.062,
        available_p_kg_ha=1.0,
        p_feedback_minimum=0.0,
        p_feedback_half_saturation_kg_p_ha=10.0,
        environmental_modifier=1.0,
        maximum_fraction=0.2,
        host_active=True,
    )
    assert result.allocated_t_c_ha == 0.0
    assert result.effective_fraction == 0.0


def test_allocation_is_bounded_and_subtracted_from_plant_carbon() -> None:
    result = allocate_plant_carbon_to_amf(
        realised_plant_carbon_t_c_ha=1.0,
        base_fraction=1.0,
        available_p_kg_ha=0.0,
        p_feedback_minimum=0.0,
        p_feedback_half_saturation_kg_p_ha=10.0,
        environmental_modifier=1.0,
        maximum_fraction=0.2,
        host_active=True,
    )
    assert result.effective_fraction == 0.2
    assert result.allocated_t_c_ha == 0.2
    assert result.net_plant_t_c_ha == 0.8


def test_high_p_smoothly_suppresses_allocation_feedback() -> None:
    low = phosphorus_allocation_feedback(1.0, 0.0, 10.0)
    high = phosphorus_allocation_feedback(100.0, 0.0, 10.0)
    assert 0.0 < high < low < 1.0


def test_growth_and_maintenance_respiration_close_amf_carbon() -> None:
    result = fungal_growth_and_respiration(
        allocated_carbon_t_c_ha=0.1,
        carbon_use_efficiency=0.45,
        turnover_t_c_ha=0.02,
    )
    assert result.biomass_growth_t_c_ha == pytest.approx(0.045)
    assert result.maintenance_respiration_t_c_ha > 0.0
    assert result.growth_respiration_t_c_ha > 0.0
    assert result.biomass_growth_t_c_ha + result.total_respiration_t_c_ha == pytest.approx(0.1)


def test_fungal_turnover_is_bounded_by_live_biomass() -> None:
    turnover = fungal_turnover_t_c_ha(2.0, 1.0)
    assert turnover == pytest.approx(2.0 * (1.0 - math.exp(-1.0)))
    assert 0.0 < turnover < 2.0
    assert fungal_turnover_t_c_ha(0.0, 6.0) == 0.0


def test_necromass_routing_is_non_negative_and_conservative() -> None:
    result = decay_and_route_necromass(
        necromass_t_c_ha=1.0,
        decay_rate_year=1.0,
        temperature_modifier=1.0,
        moisture_modifier=1.0,
        to_dpm_fraction=0.5,
        to_rpm_fraction=0.35,
        to_protected_fraction=0.15,
    )
    assert result.decomposed_t_c_ha > 0.0
    assert result.to_dpm_t_c_ha > 0.0
    assert result.to_rpm_t_c_ha > 0.0
    assert result.to_protected_t_c_ha > 0.0
    assert result.remaining_t_c_ha + result.decomposed_t_c_ha == pytest.approx(1.0)
    assert (
        result.to_dpm_t_c_ha + result.to_rpm_t_c_ha + result.to_protected_t_c_ha
    ) == pytest.approx(result.decomposed_t_c_ha)


def test_zero_fungal_biomass_has_zero_p_acquisition() -> None:
    result = acquire_amf_phosphorus(
        live_biomass_t_c_ha=0.0,
        available_p_kg_ha=10.0,
        vmax_kg_p_per_t_amf_c_month=3.0,
        half_saturation_kg_p_ha=10.0,
        temperature_modifier=1.0,
        moisture_modifier=1.0,
        transfer_to_plant_fraction=1.0,
    )
    assert result.acquired_kg_p_ha == 0.0
    assert result.transferred_to_plant_kg_p_ha == 0.0


def test_amf_p_acquisition_is_stock_capped_and_transfer_is_conservative() -> None:
    result = acquire_amf_phosphorus(
        live_biomass_t_c_ha=10.0,
        available_p_kg_ha=0.5,
        vmax_kg_p_per_t_amf_c_month=3.0,
        half_saturation_kg_p_ha=2.0,
        temperature_modifier=1.0,
        moisture_modifier=1.0,
        transfer_to_plant_fraction=0.75,
    )
    assert result.acquired_kg_p_ha == 0.5
    assert result.transferred_to_plant_kg_p_ha == pytest.approx(0.375)
    assert result.retained_by_amf_kg_p_ha == pytest.approx(0.125)
