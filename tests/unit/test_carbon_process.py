"""Unit tests for stable first-order carbon decay."""

from __future__ import annotations

import math

import pytest

from soil_simulator.processes.carbon import first_order_decay


def test_first_order_decay_matches_monthly_equation() -> None:
    result = first_order_decay(stock_t_c_ha=12.0, annual_rate=0.66)
    assert result.remaining_t_c_ha == pytest.approx(12.0 * math.exp(-0.66 / 12.0))
    assert result.decomposed_t_c_ha == pytest.approx(12.0 - result.remaining_t_c_ha)


def test_first_order_decay_is_exact_for_zero_rate_or_stock() -> None:
    assert first_order_decay(8.0, 0.0).remaining_t_c_ha == 8.0
    assert first_order_decay(8.0, 0.0).decomposed_t_c_ha == 0.0
    assert first_order_decay(0.0, 10.0).remaining_t_c_ha == 0.0


@pytest.mark.parametrize(
    ("stock", "rate"),
    [(-1.0, 1.0), (1.0, -1.0), (float("inf"), 1.0), (1.0, float("nan"))],
)
def test_first_order_decay_rejects_invalid_values(stock: float, rate: float) -> None:
    with pytest.raises(ValueError, match="finite and non-negative"):
        first_order_decay(stock, rate)
