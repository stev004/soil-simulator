"""Pure RothC monthly rate-modifier and carbon-partition calculations.

Equations and constants follow the official Rothamsted Research RothC model
description and ``RothC_Py`` v1.0.0 (DOI: 10.5281/zenodo.10732265). Moisture
uses RothC's negative deficit convention: zero is field capacity and more
negative values represent progressively drier topsoil.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from soil_simulator.domain.models import RothCParameters


@dataclass(frozen=True, slots=True)
class MoistureModifierResult:
    """Updated accumulated TSMD [mm] and dimensionless moisture modifier."""

    accumulated_tsmd_mm: float
    maximum_tsmd_mm: float
    bare_soil_maximum_tsmd_mm: float
    modifier: float


@dataclass(frozen=True, slots=True)
class CarbonPartition:
    """Clay-dependent fractions of decomposed carbon; fractions sum to one."""

    co2_to_retained_ratio: float
    co2_fraction: float
    retained_fraction: float
    microbial_fraction: float
    protected_fraction: float


def _finite(value: float, name: str) -> None:
    if not math.isfinite(value):
        raise ValueError(f"{name} must be finite")


def temperature_modifier(temperature_c: float, parameters: RothCParameters) -> float:
    r"""Return official RothC temperature modifier ``a(T)`` [dimensionless].

    For temperatures below the official-code cutoff, the modifier is zero.
    Otherwise ``a = 47.91 / (exp(106.06 / (T + 18.27)) + 1)`` using the
    corresponding configured established-model constants. The cutoff also
    keeps evaluation away from the equation's singularity.
    """
    _finite(temperature_c, "temperature_c")
    if temperature_c < parameters.temperature_cutoff_c:
        return 0.0
    denominator_temperature = temperature_c + parameters.temperature_offset_c
    if denominator_temperature <= 0.0:
        return 0.0
    exponent = parameters.temperature_exponent_numerator / denominator_temperature
    try:
        return parameters.temperature_numerator / (math.exp(exponent) + 1.0)
    except OverflowError:
        return 0.0


def maximum_topsoil_moisture_deficit_mm(
    clay_percent: float,
    soil_depth_cm: float,
    parameters: RothCParameters,
) -> float:
    r"""Return RothC maximum TSMD [mm] using its negative-deficit convention."""
    _finite(clay_percent, "clay_percent")
    _finite(soil_depth_cm, "soil_depth_cm")
    if not 0.0 <= clay_percent <= 100.0:
        raise ValueError("clay_percent must be within [0, 100]")
    if soil_depth_cm <= 0.0:
        raise ValueError("soil_depth_cm must be positive")
    maximum_at_reference_depth = -(
        parameters.maximum_tsmd_base_mm
        + parameters.maximum_tsmd_clay_linear * clay_percent
        - parameters.maximum_tsmd_clay_quadratic * clay_percent * clay_percent
    )
    return maximum_at_reference_depth * soil_depth_cm / parameters.reference_soil_depth_cm


def moisture_modifier(
    *,
    previous_accumulated_tsmd_mm: float,
    precipitation_mm: float,
    open_pan_evaporation_mm: float,
    is_covered: bool,
    clay_percent: float,
    soil_depth_cm: float,
    parameters: RothCParameters,
) -> MoistureModifierResult:
    """Accumulate RothC TSMD and return monthly moisture modifier ``b``.

    The monthly water increment is rainfall minus 0.75 times open-pan
    evaporation. Accumulated TSMD is capped at zero (field capacity) and at
    the cover-dependent dry limit. For bare soil, if the prior deficit is
    already below the bare-soil limit, further drying is prevented but
    rainfall can still wet the soil. All water quantities are ``mm month-1``.
    """
    for value, name in (
        (previous_accumulated_tsmd_mm, "previous_accumulated_tsmd_mm"),
        (precipitation_mm, "precipitation_mm"),
        (open_pan_evaporation_mm, "open_pan_evaporation_mm"),
    ):
        _finite(value, name)
    if previous_accumulated_tsmd_mm > 0.0:
        raise ValueError("previous_accumulated_tsmd_mm must be zero or negative")
    if precipitation_mm < 0.0 or open_pan_evaporation_mm < 0.0:
        raise ValueError("water inputs must be non-negative")

    maximum = maximum_topsoil_moisture_deficit_mm(clay_percent, soil_depth_cm, parameters)
    bare_maximum = parameters.bare_soil_maximum_tsmd_fraction * maximum
    water_increment = (
        precipitation_mm
        - parameters.evapotranspiration_from_open_pan_fraction * open_pan_evaporation_mm
    )
    candidate = min(0.0, previous_accumulated_tsmd_mm + water_increment)
    if is_covered:
        accumulated = max(maximum, candidate)
    else:
        dry_limit = min(bare_maximum, previous_accumulated_tsmd_mm)
        accumulated = max(dry_limit, candidate)

    threshold = parameters.moisture_threshold_fraction * maximum
    if accumulated > threshold:
        modifier = parameters.moisture_modifier_maximum
    else:
        modifier = parameters.moisture_modifier_minimum + (
            parameters.moisture_modifier_maximum - parameters.moisture_modifier_minimum
        ) * (maximum - accumulated) / (maximum - threshold)
    return MoistureModifierResult(
        accumulated_tsmd_mm=accumulated,
        maximum_tsmd_mm=maximum,
        bare_soil_maximum_tsmd_mm=bare_maximum,
        modifier=modifier,
    )


def soil_cover_modifier(is_covered: bool, parameters: RothCParameters) -> float:
    """Return official RothC soil-cover modifier ``c`` [dimensionless]."""
    return parameters.covered_soil_modifier if is_covered else parameters.bare_soil_modifier


def clay_carbon_partition(clay_percent: float, parameters: RothCParameters) -> CarbonPartition:
    r"""Return RothC clay-dependent CO2, BIO and HUM fractions.

    ``x = 1.67 * (1.85 + 1.60 * exp(-0.0786 * clay_percent))`` is the
    ``CO2 / (BIO + HUM)`` ratio. Therefore ``x/(x+1)`` is respired and
    ``1/(x+1)`` is retained, with retained carbon routed 46% to microbial
    biomass and 54% to the humified/protected SOC proxy.
    """
    _finite(clay_percent, "clay_percent")
    if not 0.0 <= clay_percent <= 100.0:
        raise ValueError("clay_percent must be within [0, 100]")
    ratio = parameters.co2_retained_ratio_scale * (
        parameters.co2_retained_ratio_intercept
        + parameters.co2_retained_ratio_clay_scale
        * math.exp(-parameters.co2_retained_ratio_clay_exponent * clay_percent)
    )
    co2_fraction = ratio / (ratio + 1.0)
    retained_fraction = 1.0 / (ratio + 1.0)
    return CarbonPartition(
        co2_to_retained_ratio=ratio,
        co2_fraction=co2_fraction,
        retained_fraction=retained_fraction,
        microbial_fraction=retained_fraction * parameters.retained_to_microbial_fraction,
        protected_fraction=retained_fraction * parameters.retained_to_protected_fraction,
    )
