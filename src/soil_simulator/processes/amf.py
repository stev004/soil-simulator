"""Pure deterministic AMF carbon and phosphorus calculations.

Carbon stocks and fluxes use ``t C ha-1`` and phosphorus uses ``kg P ha-1``.
The equations follow ``docs/MODEL_SPEC.md`` section 7. Respiration is split
operationally between replacement of current-month turnover (maintenance) and
net biomass expansion (growth); that split is provisional and introduces no
additional empirical coefficient.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AmfCarbonAllocation:
    """Plant-to-AMF carbon allocation [t C ha-1]."""

    effective_fraction: float
    allocated_t_c_ha: float
    net_plant_t_c_ha: float


@dataclass(frozen=True, slots=True)
class AmfGrowthRespiration:
    """AMF biomass production and respiration [t C ha-1]."""

    biomass_growth_t_c_ha: float
    maintenance_respiration_t_c_ha: float
    growth_respiration_t_c_ha: float

    @property
    def total_respiration_t_c_ha(self) -> float:
        """Return maintenance plus growth respiration [t C ha-1]."""
        return self.maintenance_respiration_t_c_ha + self.growth_respiration_t_c_ha


@dataclass(frozen=True, slots=True)
class AmfNecromassRouting:
    """Decay and routing of pre-existing fungal necromass [t C ha-1]."""

    decomposed_t_c_ha: float
    remaining_t_c_ha: float
    to_dpm_t_c_ha: float
    to_rpm_t_c_ha: float
    to_protected_t_c_ha: float


@dataclass(frozen=True, slots=True)
class AmfPhosphorusAcquisition:
    """AMF acquisition and subsequent transfer of available P [kg P ha-1]."""

    acquired_kg_p_ha: float
    transferred_to_plant_kg_p_ha: float
    retained_by_amf_kg_p_ha: float


def _non_negative_finite(value: float, name: str) -> None:
    if not math.isfinite(value) or value < 0.0:
        raise ValueError(f"{name} must be finite and non-negative")


def _fraction(value: float, name: str) -> None:
    if not math.isfinite(value) or not 0.0 <= value <= 1.0:
        raise ValueError(f"{name} must be finite and within [0, 1]")


def phosphorus_allocation_feedback(
    available_p_kg_ha: float,
    minimum_factor: float,
    half_saturation_kg_p_ha: float,
) -> float:
    r"""Return smooth high-P suppression of AMF allocation [dimensionless].

    ``f = f_min + (1-f_min) K_P / (K_P + P)`` from MODEL_SPEC section 7.6.
    """
    _non_negative_finite(available_p_kg_ha, "available_p_kg_ha")
    _fraction(minimum_factor, "minimum_factor")
    if not math.isfinite(half_saturation_kg_p_ha) or half_saturation_kg_p_ha <= 0.0:
        raise ValueError("half_saturation_kg_p_ha must be finite and positive")
    return minimum_factor + (1.0 - minimum_factor) * half_saturation_kg_p_ha / (
        half_saturation_kg_p_ha + available_p_kg_ha
    )


def allocate_plant_carbon_to_amf(
    *,
    realised_plant_carbon_t_c_ha: float,
    base_fraction: float,
    available_p_kg_ha: float,
    p_feedback_minimum: float,
    p_feedback_half_saturation_kg_p_ha: float,
    environmental_modifier: float,
    maximum_fraction: float,
    host_active: bool,
) -> AmfCarbonAllocation:
    """Allocate a bounded proportion of realised plant carbon to AMF.

    The effective fraction is zero without an active host. Otherwise the
    configured base fraction is multiplied by smooth P limitation and bounded
    environmental terms, then capped by the configured upper allocation bound.
    The lower biological-prior bound constrains the base parameter, not the
    context-dependent effective fraction, which may approach zero at high P.
    """
    _non_negative_finite(realised_plant_carbon_t_c_ha, "realised_plant_carbon_t_c_ha")
    _fraction(base_fraction, "base_fraction")
    _fraction(environmental_modifier, "environmental_modifier")
    _fraction(maximum_fraction, "maximum_fraction")
    if not host_active or realised_plant_carbon_t_c_ha == 0.0:
        return AmfCarbonAllocation(0.0, 0.0, realised_plant_carbon_t_c_ha)
    p_feedback = phosphorus_allocation_feedback(
        available_p_kg_ha,
        p_feedback_minimum,
        p_feedback_half_saturation_kg_p_ha,
    )
    effective_fraction = min(maximum_fraction, base_fraction * p_feedback * environmental_modifier)
    allocated = realised_plant_carbon_t_c_ha * effective_fraction
    return AmfCarbonAllocation(
        effective_fraction=effective_fraction,
        allocated_t_c_ha=allocated,
        net_plant_t_c_ha=realised_plant_carbon_t_c_ha - allocated,
    )


def fungal_turnover_t_c_ha(live_biomass_t_c_ha: float, turnover_per_month: float) -> float:
    r"""Return monthly AMF biomass turnover ``B(1-exp(-k))`` [t C ha-1]."""
    _non_negative_finite(live_biomass_t_c_ha, "live_biomass_t_c_ha")
    _non_negative_finite(turnover_per_month, "turnover_per_month")
    return live_biomass_t_c_ha * -math.expm1(-turnover_per_month)


def fungal_growth_and_respiration(
    *,
    allocated_carbon_t_c_ha: float,
    carbon_use_efficiency: float,
    turnover_t_c_ha: float,
) -> AmfGrowthRespiration:
    """Return fungal growth plus maintenance/growth respiration [t C ha-1].

    Total respiration is the MODEL_SPEC CUE complement. Its maintenance share
    is the respiration associated with growth that replaces current turnover;
    the remainder is assigned to net biomass expansion. This accounting split
    is provisional but conservative and avoids an unsupported maintenance
    coefficient.
    """
    _non_negative_finite(allocated_carbon_t_c_ha, "allocated_carbon_t_c_ha")
    _fraction(carbon_use_efficiency, "carbon_use_efficiency")
    _non_negative_finite(turnover_t_c_ha, "turnover_t_c_ha")
    growth = allocated_carbon_t_c_ha * carbon_use_efficiency
    total_respiration = allocated_carbon_t_c_ha - growth
    if growth == 0.0 or carbon_use_efficiency == 0.0:
        maintenance_respiration = 0.0
    else:
        replacement_growth = min(growth, turnover_t_c_ha)
        replacement_substrate = replacement_growth / carbon_use_efficiency
        maintenance_respiration = min(
            total_respiration,
            replacement_substrate * (1.0 - carbon_use_efficiency),
        )
    growth_respiration = max(0.0, total_respiration - maintenance_respiration)
    return AmfGrowthRespiration(growth, maintenance_respiration, growth_respiration)


def decay_and_route_necromass(
    *,
    necromass_t_c_ha: float,
    decay_rate_year: float,
    temperature_modifier: float,
    moisture_modifier: float,
    to_dpm_fraction: float,
    to_rpm_fraction: float,
    to_protected_fraction: float,
) -> AmfNecromassRouting:
    """Decay pre-existing necromass and route it conservatively [t C ha-1]."""
    for value, name in (
        (necromass_t_c_ha, "necromass_t_c_ha"),
        (decay_rate_year, "decay_rate_year"),
        (temperature_modifier, "temperature_modifier"),
        (moisture_modifier, "moisture_modifier"),
    ):
        _non_negative_finite(value, name)
    for value, name in (
        (to_dpm_fraction, "to_dpm_fraction"),
        (to_rpm_fraction, "to_rpm_fraction"),
        (to_protected_fraction, "to_protected_fraction"),
    ):
        _fraction(value, name)
    if not math.isclose(
        to_dpm_fraction + to_rpm_fraction + to_protected_fraction,
        1.0,
        rel_tol=0.0,
        abs_tol=1.0e-12,
    ):
        raise ValueError("necromass routing fractions must sum to 1")
    exponent = decay_rate_year * temperature_modifier * moisture_modifier / 12.0
    decomposed = necromass_t_c_ha * -math.expm1(-exponent)
    return AmfNecromassRouting(
        decomposed_t_c_ha=decomposed,
        remaining_t_c_ha=necromass_t_c_ha - decomposed,
        to_dpm_t_c_ha=decomposed * to_dpm_fraction,
        to_rpm_t_c_ha=decomposed * to_rpm_fraction,
        to_protected_t_c_ha=decomposed * to_protected_fraction,
    )


def acquire_amf_phosphorus(
    *,
    live_biomass_t_c_ha: float,
    available_p_kg_ha: float,
    vmax_kg_p_per_t_amf_c_month: float,
    half_saturation_kg_p_ha: float,
    temperature_modifier: float,
    moisture_modifier: float,
    transfer_to_plant_fraction: float,
) -> AmfPhosphorusAcquisition:
    r"""Acquire stock-capped P with the specified Michaelis--Menten equation."""
    for value, name in (
        (live_biomass_t_c_ha, "live_biomass_t_c_ha"),
        (available_p_kg_ha, "available_p_kg_ha"),
        (vmax_kg_p_per_t_amf_c_month, "vmax_kg_p_per_t_amf_c_month"),
    ):
        _non_negative_finite(value, name)
    if not math.isfinite(half_saturation_kg_p_ha) or half_saturation_kg_p_ha <= 0.0:
        raise ValueError("half_saturation_kg_p_ha must be finite and positive")
    _fraction(temperature_modifier, "temperature_modifier")
    _fraction(moisture_modifier, "moisture_modifier")
    _fraction(transfer_to_plant_fraction, "transfer_to_plant_fraction")
    potential = (
        vmax_kg_p_per_t_amf_c_month
        * live_biomass_t_c_ha
        * available_p_kg_ha
        / (half_saturation_kg_p_ha + available_p_kg_ha)
        * temperature_modifier
        * moisture_modifier
    )
    acquired = min(available_p_kg_ha, potential)
    transferred = acquired * transfer_to_plant_fraction
    return AmfPhosphorusAcquisition(
        acquired_kg_p_ha=acquired,
        transferred_to_plant_kg_p_ha=transferred,
        retained_by_amf_kg_p_ha=acquired - transferred,
    )
