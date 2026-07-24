"""Property-based invariants for Phase 5 AMF calculations."""

from __future__ import annotations

import math

from hypothesis import given
from hypothesis import strategies as st

from soil_simulator.processes.amf import (
    acquire_amf_phosphorus,
    fungal_growth_and_respiration,
    fungal_turnover_t_c_ha,
)

NON_NEGATIVE = st.floats(min_value=0.0, max_value=1.0e5, allow_nan=False, allow_infinity=False)
FRACTION = st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False)


@given(live=NON_NEGATIVE, turnover_rate=NON_NEGATIVE)
def test_turnover_cannot_exceed_live_biomass(live: float, turnover_rate: float) -> None:
    turnover = fungal_turnover_t_c_ha(live, turnover_rate)
    assert math.isfinite(turnover)
    assert 0.0 <= turnover <= live


@given(allocation=NON_NEGATIVE, cue=FRACTION, turnover=NON_NEGATIVE)
def test_fungal_growth_and_respiration_conserve_allocation(
    allocation: float, cue: float, turnover: float
) -> None:
    result = fungal_growth_and_respiration(
        allocated_carbon_t_c_ha=allocation,
        carbon_use_efficiency=cue,
        turnover_t_c_ha=turnover,
    )
    assert result.biomass_growth_t_c_ha >= 0.0
    assert result.maintenance_respiration_t_c_ha >= 0.0
    assert result.growth_respiration_t_c_ha >= 0.0
    assert math.isclose(
        result.biomass_growth_t_c_ha + result.total_respiration_t_c_ha,
        allocation,
        rel_tol=1.0e-12,
        abs_tol=1.0e-12,
    )


@given(live=NON_NEGATIVE, available=NON_NEGATIVE, transfer=FRACTION)
def test_amf_p_acquisition_cannot_create_or_overdraw_p(
    live: float, available: float, transfer: float
) -> None:
    result = acquire_amf_phosphorus(
        live_biomass_t_c_ha=live,
        available_p_kg_ha=available,
        vmax_kg_p_per_t_amf_c_month=1.0,
        half_saturation_kg_p_ha=10.0,
        temperature_modifier=1.0,
        moisture_modifier=1.0,
        transfer_to_plant_fraction=transfer,
    )
    assert 0.0 <= result.acquired_kg_p_ha <= available
    assert 0.0 <= result.transferred_to_plant_kg_p_ha <= result.acquired_kg_p_ha
    assert math.isclose(
        result.transferred_to_plant_kg_p_ha + result.retained_by_amf_kg_p_ha,
        result.acquired_kg_p_ha,
        rel_tol=1.0e-12,
        abs_tol=1.0e-12,
    )
