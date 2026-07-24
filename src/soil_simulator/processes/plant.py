"""Pure calculations for the provisional monthly spring-barley baseline."""

from __future__ import annotations

import math
from dataclasses import dataclass
from itertools import pairwise

from soil_simulator.domain.models import PlantParameters, RothCParameters

KG_PER_TONNE = 1000.0


@dataclass(frozen=True, slots=True)
class GrowthAllocation:
    """Realised NPP partition [t C ha-1]."""

    shoot_t_c_ha: float
    root_t_c_ha: float


@dataclass(frozen=True, slots=True)
class HarvestResult:
    """Harvest, export and residue carbon amounts [t C ha-1]."""

    grain_carbon_t_c_ha: float
    grain_yield_t_dm_ha: float
    harvested_biomass_carbon_t_c_ha: float
    retained_aboveground_residue_t_c_ha: float
    root_residue_t_c_ha: float
    aboveground_export_t_c_ha: float
    root_export_t_c_ha: float


def prescribed_potential_npp(calendar_month: int, parameters: PlantParameters) -> float:
    """Return configured monthly potential NPP [t C ha-1 month-1]."""
    if not 1 <= calendar_month <= 12:
        raise ValueError("calendar_month must be within [1, 12]")
    return (
        parameters.annual_potential_npp_t_c_ha.default
        * parameters.monthly_npp_profile[calendar_month - 1]
    )


def plant_temperature_modifier(temperature_c: float, parameters: PlantParameters) -> float:
    """Interpolate the configured bounded cereal temperature-response table."""
    if not math.isfinite(temperature_c):
        raise ValueError("temperature_c must be finite")
    points = parameters.temperature_response
    if temperature_c <= points[0].temperature_c:
        return points[0].modifier
    if temperature_c >= points[-1].temperature_c:
        return points[-1].modifier
    for left, right in pairwise(points):
        if temperature_c <= right.temperature_c:
            position = (temperature_c - left.temperature_c) / (
                right.temperature_c - left.temperature_c
            )
            return left.modifier + position * (right.modifier - left.modifier)
    raise ArithmeticError("temperature response interpolation failed")


def plant_moisture_modifier(rothc_moisture_modifier: float, parameters: RothCParameters) -> float:
    """Map RothC's configured moisture range linearly onto plant stress [0, 1].

    This is a provisional Phase 4 coupling, not a crop water-balance model.
    RothC's minimum modifier maps to complete plant-water stress and its
    maximum maps to no plant-water stress.
    """
    if not math.isfinite(rothc_moisture_modifier):
        raise ValueError("rothc_moisture_modifier must be finite")
    lower = parameters.moisture_modifier_minimum
    upper = parameters.moisture_modifier_maximum
    if upper <= lower:
        raise ValueError("RothC moisture modifier range must be positive")
    return min(1.0, max(0.0, (rothc_moisture_modifier - lower) / (upper - lower)))


def combine_stress_modifiers(temperature: float, moisture: float, phosphorus: float) -> float:
    """Multiply three bounded stress modifiers and defensively bound the result."""
    modifiers = (temperature, moisture, phosphorus)
    if any(not math.isfinite(value) or not 0.0 <= value <= 1.0 for value in modifiers):
        raise ValueError("stress modifiers must be finite and within [0, 1]")
    return min(1.0, max(0.0, temperature * moisture * phosphorus))


def allocate_npp(realised_npp_t_c_ha: float, root_fraction: float) -> GrowthAllocation:
    """Partition realised NPP between shoot and root carbon [t C ha-1]."""
    if not math.isfinite(realised_npp_t_c_ha) or realised_npp_t_c_ha < 0.0:
        raise ValueError("realised_npp_t_c_ha must be finite and non-negative")
    if not math.isfinite(root_fraction) or not 0.0 <= root_fraction <= 1.0:
        raise ValueError("root_fraction must be finite and within [0, 1]")
    root = realised_npp_t_c_ha * root_fraction
    return GrowthAllocation(shoot_t_c_ha=realised_npp_t_c_ha - root, root_t_c_ha=root)


def harvest_plant(
    *,
    shoot_c_t_ha: float,
    root_c_t_ha: float,
    harvest_index: float,
    aboveground_retained_fraction: float,
    root_residue_fraction: float,
    carbon_fraction_of_dry_matter: float,
) -> HarvestResult:
    """Harvest grain and route retained shoot/root residues [t C ha-1]."""
    stocks = (shoot_c_t_ha, root_c_t_ha)
    fractions = (harvest_index, aboveground_retained_fraction, root_residue_fraction)
    if any(not math.isfinite(value) or value < 0.0 for value in stocks):
        raise ValueError("plant stocks must be finite and non-negative")
    if any(not math.isfinite(value) or not 0.0 <= value <= 1.0 for value in fractions):
        raise ValueError("harvest and residue fractions must be within [0, 1]")
    if not math.isfinite(carbon_fraction_of_dry_matter) or not (
        0.0 < carbon_fraction_of_dry_matter <= 1.0
    ):
        raise ValueError("carbon_fraction_of_dry_matter must be within (0, 1]")

    grain = shoot_c_t_ha * harvest_index
    non_grain_shoot = shoot_c_t_ha - grain
    retained_shoot = non_grain_shoot * aboveground_retained_fraction
    aboveground_export = non_grain_shoot - retained_shoot
    root_residue = root_c_t_ha * root_residue_fraction
    root_export = root_c_t_ha - root_residue
    return HarvestResult(
        grain_carbon_t_c_ha=grain,
        grain_yield_t_dm_ha=grain / carbon_fraction_of_dry_matter,
        harvested_biomass_carbon_t_c_ha=grain + aboveground_export,
        retained_aboveground_residue_t_c_ha=retained_shoot,
        root_residue_t_c_ha=root_residue,
        aboveground_export_t_c_ha=aboveground_export,
        root_export_t_c_ha=root_export,
    )


def partition_residue_dpm_rpm(
    total_residue_t_c_ha: float, dpm_rpm_ratio: float
) -> tuple[float, float]:
    """Split residue carbon using ``DPM / RPM = ratio`` [t C ha-1]."""
    if not math.isfinite(total_residue_t_c_ha) or total_residue_t_c_ha < 0.0:
        raise ValueError("total_residue_t_c_ha must be finite and non-negative")
    if not math.isfinite(dpm_rpm_ratio) or dpm_rpm_ratio <= 0.0:
        raise ValueError("dpm_rpm_ratio must be finite and positive")
    dpm = total_residue_t_c_ha * dpm_rpm_ratio / (dpm_rpm_ratio + 1.0)
    return dpm, total_residue_t_c_ha - dpm
