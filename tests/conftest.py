"""Shared deterministic examples for contract tests."""

from __future__ import annotations

from typing import Any

import pytest


@pytest.fixture
def field_properties_data() -> dict[str, Any]:
    """Return one valid synthetic topsoil record."""
    return {
        "field_id": "field-001",
        "synthetic_archetype": "medium-clay-p-limited",
        "soil_depth_cm": 23.0,
        "clay_percent": 30.0,
        "silt_percent": 40.0,
        "sand_percent": 30.0,
        "bulk_density_g_cm3": 1.3,
        "ph": 6.5,
        "cation_exchange_capacity_cmolc_kg": 15.0,
        "baseline_total_nitrogen_percent": 0.15,
        "baseline_soc_t_c_ha": 55.0,
        "drainage_class": "well_drained",
        "climate_normal_id": "era5-land-example",
        "provenance": "deterministic test fixture",
    }


@pytest.fixture
def field_state_data() -> dict[str, Any]:
    """Return one valid zero-state contract."""
    return {
        "month_index": 0,
        "plant_c": 0.0,
        "root_c": 0.0,
        "amf_live_c": 0.0,
        "amf_necromass_c": 0.0,
        "dpm_c": 0.0,
        "rpm_c": 0.0,
        "microbial_c": 0.0,
        "protected_soc_c": 0.0,
        "iom_c": 0.0,
        "available_p_kg_ha": 0.0,
        "topsoil_moisture_deficit_mm": 0.0,
        "crop_development": 0.0,
        "cumulative_yield_t_dm_ha": 0.0,
    }
