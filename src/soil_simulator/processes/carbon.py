"""Pure first-order soil-carbon decay calculations.

Stocks use ``t C ha-1`` and configured rate constants use ``year-1``. The
time step is one month and the dimensionless RothC rate modifier is the
product of temperature, moisture and soil-cover modifiers.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class DecayResult:
    """Remaining and decomposed carbon after one monthly first-order step."""

    remaining_t_c_ha: float
    decomposed_t_c_ha: float


def first_order_decay(
    stock_t_c_ha: float,
    annual_rate: float,
    rate_modifier: float = 1.0,
) -> DecayResult:
    r"""Apply stable monthly first-order decay.

    The equations are
    :math:`Y_{t+1}=Y_t\exp(-k_Yabc/12)` and
    :math:`D_{Y,t}=Y_t-Y_{t+1}`. Inputs must be finite and non-negative.
    ``expm1`` avoids cancellation for rates close to zero.
    """
    if not math.isfinite(stock_t_c_ha) or stock_t_c_ha < 0.0:
        raise ValueError("stock_t_c_ha must be finite and non-negative")
    if not math.isfinite(annual_rate) or annual_rate < 0.0:
        raise ValueError("annual_rate must be finite and non-negative")
    if not math.isfinite(rate_modifier) or rate_modifier < 0.0:
        raise ValueError("rate_modifier must be finite and non-negative")

    decomposed_fraction = -math.expm1(-(annual_rate * rate_modifier) / 12.0)
    decomposed = stock_t_c_ha * decomposed_fraction
    remaining = stock_t_c_ha - decomposed
    if not math.isfinite(decomposed) or not math.isfinite(remaining):
        raise ArithmeticError("first-order decay produced a non-finite carbon value")
    if decomposed < 0.0 or remaining < 0.0:
        raise ArithmeticError("first-order decay produced a negative carbon value")
    return DecayResult(remaining_t_c_ha=remaining, decomposed_t_c_ha=decomposed)
