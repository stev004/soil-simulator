"""Property-based verification of deterministic carbon-core invariants."""

from __future__ import annotations

import math
from pathlib import Path

import pytest
from hypothesis import given
from hypothesis import strategies as st

from soil_simulator.domain.carbon import CarbonCoreMonth, CarbonInput, RothCForcing
from soil_simulator.domain.models import FieldState, ModelParameters
from soil_simulator.io.configuration import load_model_parameters
from soil_simulator.processes.carbon import first_order_decay
from soil_simulator.simulator.carbon_core import step_carbon_core

CONFIG_PATH = Path(__file__).parents[2] / "config" / "model_defaults.yaml"
PARAMETERS = load_model_parameters(CONFIG_PATH)
FINITE_STOCK = st.floats(min_value=0.0, max_value=1.0e4, allow_nan=False, allow_infinity=False)
FINITE_INPUT = st.floats(min_value=0.0, max_value=100.0, allow_nan=False, allow_infinity=False)
FINITE_RATE = st.floats(min_value=0.0, max_value=50.0, allow_nan=False, allow_infinity=False)


def _parameters_with_rates(rates: tuple[float, float, float, float]) -> ModelParameters:
    values = PARAMETERS.model_dump(mode="python", by_alias=True)
    values["rothc"].update(
        k_dpm_year=rates[0],
        k_rpm_year=rates[1],
        k_microbial_year=rates[2],
        k_protected_year=rates[3],
    )
    return ModelParameters.model_validate(values)


def _state(stocks: tuple[float, float, float, float, float]) -> FieldState:
    return FieldState(
        month_index=0,
        plant_c=0.0,
        root_c=0.0,
        amf_live_c=0.0,
        amf_necromass_c=0.0,
        dpm_c=stocks[0],
        rpm_c=stocks[1],
        microbial_c=stocks[2],
        protected_soc_c=stocks[3],
        iom_c=stocks[4],
        available_p_kg_ha=0.0,
        topsoil_moisture_deficit_mm=0.0,
        crop_development=0.0,
        cumulative_yield_t_dm_ha=0.0,
        aggregate_protection_index=None,
    )


def _month(inputs: tuple[float, float, float]) -> CarbonCoreMonth:
    return CarbonCoreMonth(
        external_input=CarbonInput(
            dpm_c=inputs[0],
            rpm_c=inputs[1],
            protected_soc_c=inputs[2],
            classification="scenario_assumption",
            provenance="Hypothesis generated",
        ),
        forcing=RothCForcing(
            mean_air_temperature_c=10.0,
            precipitation_mm=50.0,
            open_pan_evaporation_mm=50.0,
            is_covered=True,
            clay_percent=30.0,
            soil_depth_cm=23.0,
            provenance="Hypothesis fixed forcing",
        ),
    )


@given(
    stocks=st.tuples(FINITE_STOCK, FINITE_STOCK, FINITE_STOCK, FINITE_STOCK, FINITE_STOCK),
    inputs=st.tuples(FINITE_INPUT, FINITE_INPUT, FINITE_INPUT),
    rates=st.tuples(FINITE_RATE, FINITE_RATE, FINITE_RATE, FINITE_RATE),
)
def test_step_never_creates_negative_pools_and_always_balances(
    stocks: tuple[float, float, float, float, float],
    inputs: tuple[float, float, float],
    rates: tuple[float, float, float, float],
) -> None:
    result = step_carbon_core(
        _state(stocks),
        _month(inputs),
        _parameters_with_rates(rates),
    )
    final_pools = (
        result.final_state.dpm_c,
        result.final_state.rpm_c,
        result.final_state.microbial_c,
        result.final_state.protected_soc_c,
        result.final_state.iom_c,
    )
    assert all(math.isfinite(pool) and pool >= 0.0 for pool in final_pools)
    assert result.final_state.iom_c == stocks[4]
    assert result.mass_balance.within_tolerance
    assert abs(result.mass_balance.residual_t_c_ha) <= result.mass_balance.tolerance_t_c_ha


@given(stock=FINITE_STOCK, lower=FINITE_RATE, increment=FINITE_RATE)
def test_increasing_decay_rate_cannot_increase_remaining_stock(
    stock: float, lower: float, increment: float
) -> None:
    higher = lower + increment
    if not math.isfinite(higher):
        pytest.skip("generated rate addition exceeded finite float range")
    lower_remaining = first_order_decay(stock, lower).remaining_t_c_ha
    assert first_order_decay(stock, higher).remaining_t_c_ha <= lower_remaining + 1.0e-12


@given(stock=FINITE_STOCK)
def test_zero_decay_preserves_any_finite_stock(stock: float) -> None:
    result = first_order_decay(stock, 0.0)
    assert result.remaining_t_c_ha == stock
    assert result.decomposed_t_c_ha == 0.0
