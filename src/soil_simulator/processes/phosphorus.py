"""Pure available-phosphorus demand, stress and uptake calculations."""

from __future__ import annotations

import math

from soil_simulator.processes.plant import KG_PER_TONNE


def phosphorus_demand_kg_p_ha(
    carbon_growth_t_c_ha: float,
    carbon_fraction_of_dry_matter: float,
    phosphorus_concentration_kg_p_per_kg_dm: float,
) -> float:
    """Return P needed to support carbon growth at configured tissue P [kg P ha-1]."""
    values = (
        carbon_growth_t_c_ha,
        carbon_fraction_of_dry_matter,
        phosphorus_concentration_kg_p_per_kg_dm,
    )
    if any(not math.isfinite(value) for value in values):
        raise ValueError("phosphorus demand inputs must be finite")
    if carbon_growth_t_c_ha < 0.0 or phosphorus_concentration_kg_p_per_kg_dm < 0.0:
        raise ValueError("growth and phosphorus concentration must be non-negative")
    if not 0.0 < carbon_fraction_of_dry_matter <= 1.0:
        raise ValueError("carbon_fraction_of_dry_matter must be within (0, 1]")
    dry_matter_t_ha = carbon_growth_t_c_ha / carbon_fraction_of_dry_matter
    return dry_matter_t_ha * KG_PER_TONNE * phosphorus_concentration_kg_p_per_kg_dm


def phosphorus_stress_modifier(available_p_kg_ha: float, demand_kg_p_ha: float) -> float:
    """Return the bounded fraction of monthly P demand that can be met."""
    if any(
        not math.isfinite(value) or value < 0.0 for value in (available_p_kg_ha, demand_kg_p_ha)
    ):
        raise ValueError("available P and demand must be finite and non-negative")
    if demand_kg_p_ha == 0.0:
        return 1.0
    return min(1.0, available_p_kg_ha / demand_kg_p_ha)


def phosphorus_uptake_kg_p_ha(available_p_kg_ha: float, demand_kg_p_ha: float) -> float:
    """Withdraw no more than available P or plant demand [kg P ha-1]."""
    if any(
        not math.isfinite(value) or value < 0.0 for value in (available_p_kg_ha, demand_kg_p_ha)
    ):
        raise ValueError("available P and demand must be finite and non-negative")
    return min(available_p_kg_ha, demand_kg_p_ha)


def direct_phosphorus_uptake_kg_p_ha(
    available_p_kg_ha: float,
    demand_kg_p_ha: float,
    half_saturation_kg_p_ha: float,
) -> float:
    """Return stock/demand-capped root-pathway Michaelis--Menten P uptake.

    This provisional aggregate equation distinguishes finite direct-root access
    from AMF access while both withdraw from the same available-P stock.
    """
    if any(
        not math.isfinite(value) or value < 0.0 for value in (available_p_kg_ha, demand_kg_p_ha)
    ):
        raise ValueError("available P and demand must be finite and non-negative")
    if not math.isfinite(half_saturation_kg_p_ha) or half_saturation_kg_p_ha <= 0.0:
        raise ValueError("half_saturation_kg_p_ha must be finite and positive")
    kinetic_capacity = (
        demand_kg_p_ha * available_p_kg_ha / (half_saturation_kg_p_ha + available_p_kg_ha)
    )
    return min(available_p_kg_ha, demand_kg_p_ha, kinetic_capacity)
