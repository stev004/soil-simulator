"""Parity with Rothamsted's published January 1852 Hoosfield calculation."""

from __future__ import annotations

import math
from pathlib import Path

import pytest

from soil_simulator.domain.carbon import CarbonCoreMonth, CarbonInput, RothCForcing
from soil_simulator.domain.models import FieldState
from soil_simulator.io.configuration import load_model_parameters
from soil_simulator.simulator.carbon_core import step_carbon_core

PARAMETERS = load_model_parameters(Path(__file__).parents[2] / "config" / "model_defaults.yaml")
OFFICIAL_COMBINED_MODIFIER = 0.3561
# The official worked example reports abc but not its component weather values.
# This temperature is the exact inverse of official a(T) for a=0.3561; wet,
# bare forcing makes b=c=1, exercising the integrated modifier path.
DERIVED_TEMPERATURE_C = (
    PARAMETERS.rothc.temperature_exponent_numerator
    / math.log(PARAMETERS.rothc.temperature_numerator / OFFICIAL_COMBINED_MODIFIER - 1.0)
    - PARAMETERS.rothc.temperature_offset_c
)


def test_january_1852_hoosfield_pool_update_matches_published_example() -> None:
    initial = FieldState(
        month_index=0,
        plant_c=0.0,
        root_c=0.0,
        amf_live_c=0.0,
        amf_necromass_c=0.0,
        dpm_c=0.1533,
        rpm_c=4.4852,
        microbial_c=0.6671,
        protected_soc_c=25.8576,
        iom_c=2.7,
        available_p_kg_ha=0.0,
        topsoil_moisture_deficit_mm=0.0,
        crop_development=0.0,
        cumulative_yield_t_dm_ha=0.0,
        aggregate_protection_index=None,
    )
    month = CarbonCoreMonth(
        external_input=CarbonInput(
            classification="scenario_assumption",
            provenance="No input in official January 1852 Hoosfield example",
        ),
        forcing=RothCForcing(
            mean_air_temperature_c=DERIVED_TEMPERATURE_C,
            precipitation_mm=100.0,
            open_pan_evaporation_mm=0.0,
            is_covered=False,
            clay_percent=23.4,
            soil_depth_cm=23.0,
            provenance=(
                "Wet bare forcing chosen to reproduce official reported combined modifier 0.3561"
            ),
        ),
    )

    result = step_carbon_core(initial, month, PARAMETERS)

    assert result.modifiers.combined == pytest.approx(OFFICIAL_COMBINED_MODIFIER, abs=1e-14)
    # Coleman, Prout & Milne (2024), section 2.2, reports four-decimal outputs.
    assert result.final_state.dpm_c == pytest.approx(0.1140, abs=1.0e-4)
    assert result.final_state.rpm_c == pytest.approx(4.4455, abs=1.0e-4)
    assert result.final_state.microbial_c == pytest.approx(0.6651, abs=1.0e-4)
    assert result.final_state.protected_soc_c == pytest.approx(25.8551, abs=1.0e-4)
    assert result.respiration_t_c_ha == pytest.approx(0.0836, abs=1.0e-4)
    assert result.mass_balance.within_tolerance
