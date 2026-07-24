"""Property-based checks for Phase 4 phosphorus and residue invariants."""

from __future__ import annotations

import math

from hypothesis import given
from hypothesis import strategies as st

from soil_simulator.processes.phosphorus import (
    phosphorus_stress_modifier,
    phosphorus_uptake_kg_p_ha,
)
from soil_simulator.processes.plant import partition_residue_dpm_rpm

NON_NEGATIVE = st.floats(min_value=0.0, max_value=1.0e6, allow_nan=False, allow_infinity=False)


@given(available=NON_NEGATIVE, demand=NON_NEGATIVE)
def test_phosphorus_uptake_is_bounded_and_pool_never_negative(
    available: float, demand: float
) -> None:
    uptake = phosphorus_uptake_kg_p_ha(available, demand)
    assert 0.0 <= uptake <= available
    assert uptake <= demand
    assert available - uptake >= 0.0
    stress = phosphorus_stress_modifier(available, demand)
    assert math.isfinite(stress)
    assert 0.0 <= stress <= 1.0


@given(residue=NON_NEGATIVE, ratio=st.floats(min_value=1.0e-6, max_value=1.0e6))
def test_residue_partition_is_finite_non_negative_and_conservative(
    residue: float, ratio: float
) -> None:
    dpm, rpm = partition_residue_dpm_rpm(residue, ratio)
    assert math.isfinite(dpm) and math.isfinite(rpm)
    assert dpm >= 0.0 and rpm >= 0.0
    assert math.isclose(dpm + rpm, residue, rel_tol=1.0e-12, abs_tol=1.0e-12)
