"""Strict quality-control checks for Phase 7 synthetic fields."""

from __future__ import annotations

import math
from collections.abc import Callable

from soil_simulator.domain.population import (
    PopulationGenerationConfig,
    PopulationQcResult,
    SyntheticField,
)

SimulatorProbe = Callable[[SyntheticField], None]


def quality_control(
    field: SyntheticField,
    config: PopulationGenerationConfig,
    *,
    simulator_probe: SimulatorProbe | None = None,
) -> PopulationQcResult:
    """Return every deterministic QC rejection reason for a virtual field."""
    reasons: list[str] = []
    properties = field.field
    state = field.initial_state
    values = (
        properties.clay_percent,
        properties.silt_percent,
        properties.sand_percent,
        properties.ph,
        properties.baseline_soc_t_c_ha,
        properties.bulk_density_g_cm3,
        state.available_p_kg_ha,
        *(
            value
            for month in field.weather
            for value in (
                month.mean_air_temperature_c,
                month.precipitation_mm,
                month.potential_evapotranspiration_mm,
            )
        ),
    )
    if any(not math.isfinite(value) for value in values):
        reasons.append("non_finite_value")
    if not math.isclose(
        properties.clay_percent + properties.silt_percent + properties.sand_percent,
        100.0,
        rel_tol=0.0,
        abs_tol=0.01,
    ):
        reasons.append("invalid_texture_composition")
    for name, value in state.model_dump(mode="python").items():
        if (
            isinstance(value, (int, float))
            and name != "topsoil_moisture_deficit_mm"
            and value < 0.0
        ):
            reasons.append("negative_stock")
            break
    if not (
        config.minimum_soc_t_c_ha.default
        <= properties.baseline_soc_t_c_ha
        <= config.maximum_soc_t_c_ha.default
    ):
        reasons.append("soc_out_of_range")
    if not (
        config.minimum_bulk_density_g_cm3.default
        <= properties.bulk_density_g_cm3
        <= config.maximum_bulk_density_g_cm3.default
    ):
        reasons.append("bulk_density_out_of_range")
    if not config.minimum_ph.default <= properties.ph <= config.maximum_ph.default:
        reasons.append("ph_out_of_range")
    if not (
        config.minimum_available_p_kg_ha.default
        <= state.available_p_kg_ha
        <= config.maximum_available_p_kg_ha.default
    ):
        reasons.append("available_p_out_of_range")
    soil_mass_t_ha = properties.bulk_density_g_cm3 * properties.soil_depth_cm * 100.0
    soc_percent = properties.baseline_soc_t_c_ha / soil_mass_t_ha * 100.0
    if not 0.3 <= soc_percent <= 8.0:
        reasons.append("inconsistent_soc_stock_and_bulk_density")
    if properties.sand_percent > 75.0 and properties.baseline_soc_t_c_ha > 100.0:
        reasons.append("impossible_high_soc_very_sandy_combination")
    if properties.ph < 4.5 and state.available_p_kg_ha > 60.0:
        reasons.append("impossible_acid_high_available_p_combination")
    if properties.drainage_class in {"waterlogged", "poorly_drained"}:
        reasons.append("drainage_outside_model_domain")
    if any(
        month.mean_air_temperature_c < -10.0
        or month.mean_air_temperature_c > 30.0
        or month.precipitation_mm > 250.0
        or month.potential_evapotranspiration_mm > 180.0
        for month in field.weather
    ):
        reasons.append("weather_outside_model_domain")
    if not field.spinup.converged:
        reasons.append("spinup_not_converged")
    if not math.isclose(
        field.spinup.achieved_soc_t_c_ha,
        field.spinup.target_soc_t_c_ha,
        rel_tol=0.0,
        abs_tol=1.0e-7,
    ):
        reasons.append("spinup_soc_target_mismatch")
    if simulator_probe is not None and not reasons:
        try:
            simulator_probe(field)
        except (ArithmeticError, RuntimeError, ValueError) as exc:
            reasons.append(f"simulator_failure:{type(exc).__name__}")
    return PopulationQcResult(passed=not reasons, reasons=tuple(reasons))
