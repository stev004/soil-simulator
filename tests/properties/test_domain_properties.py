"""Property-based checks for bootstrap validation invariants."""

from __future__ import annotations

from typing import Any

import pytest
from hypothesis import given
from hypothesis import strategies as st
from pydantic import ValidationError

from soil_simulator.domain.models import FieldProperties, FieldState


@given(
    clay=st.floats(min_value=0.0, max_value=100.0, allow_nan=False, allow_infinity=False),
    split=st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
)
def test_compositional_texture_is_accepted(clay: float, split: float) -> None:
    remainder = 100.0 - clay
    silt = remainder * split
    sand = remainder - silt
    properties = FieldProperties(
        field_id="property-field",
        latitude_deg=None,
        longitude_deg=None,
        synthetic_archetype="generated-valid-texture",
        soil_depth_cm=23.0,
        clay_percent=clay,
        silt_percent=silt,
        sand_percent=sand,
        bulk_density_g_cm3=1.3,
        ph=6.5,
        cation_exchange_capacity_cmolc_kg=15.0,
        baseline_total_nitrogen_percent=0.15,
        baseline_soc_t_c_ha=55.0,
        drainage_class="well_drained",
        climate_normal_id="test",
        provenance="hypothesis",
    )
    texture_total = properties.clay_percent + properties.silt_percent + properties.sand_percent
    assert texture_total == pytest.approx(100.0)


@given(value=st.floats(max_value=-1.0e-12, allow_nan=False, allow_infinity=False))
def test_any_negative_carbon_stock_is_rejected(value: float) -> None:
    data: dict[str, Any] = {
        "month_index": 0,
        "plant_c": value,
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
    with pytest.raises(ValidationError):
        FieldState.model_validate(data)
