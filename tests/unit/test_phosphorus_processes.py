"""Unit verification for available-phosphorus demand and withdrawal."""

from __future__ import annotations

import pytest

from soil_simulator.processes.phosphorus import (
    phosphorus_demand_kg_p_ha,
    phosphorus_stress_modifier,
    phosphorus_uptake_kg_p_ha,
)


def test_phosphorus_demand_converts_carbon_to_dry_matter_and_tissue_p() -> None:
    assert phosphorus_demand_kg_p_ha(0.45, 0.45, 0.002) == pytest.approx(2.0)


def test_phosphorus_limitation_and_zero_demand() -> None:
    assert phosphorus_stress_modifier(1.0, 4.0) == 0.25
    assert phosphorus_stress_modifier(4.0, 4.0) == 1.0
    assert phosphorus_stress_modifier(0.0, 0.0) == 1.0


def test_phosphorus_uptake_cannot_exceed_pool_or_demand() -> None:
    assert phosphorus_uptake_kg_p_ha(1.0, 4.0) == 1.0
    assert phosphorus_uptake_kg_p_ha(4.0, 1.0) == 1.0
    assert phosphorus_uptake_kg_p_ha(0.0, 4.0) == 0.0
