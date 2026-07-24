"""Property checks for Phase 7 compositional and bounded perturbation helpers."""

from __future__ import annotations

import math
import random
from pathlib import Path

from hypothesis import given
from hypothesis import strategies as st

from soil_simulator.population.adapters import VersionedLocalYamlAdapter
from soil_simulator.population.generator import _bounded_seed_relative, _compositional_texture

ROOT = Path(__file__).parents[2]
DATASET = VersionedLocalYamlAdapter().load(
    ROOT / "data" / "processed" / "phase7_empirical_seed_fixture_v1.yaml"
)


@given(st.integers(min_value=0, max_value=2**32 - 1), st.floats(min_value=0.0, max_value=0.35))
def test_compositional_perturbation_always_returns_valid_texture(
    random_seed: int, standard_deviation: float
) -> None:
    clay, silt, sand = _compositional_texture(
        DATASET.seeds[random_seed % len(DATASET.seeds)],
        random.Random(random_seed),
        standard_deviation,
    )
    assert clay > 0.0
    assert silt > 0.0
    assert sand > 0.0
    assert math.isclose(clay + silt + sand, 100.0, rel_tol=0.0, abs_tol=1.0e-12)


@given(
    st.floats(min_value=-1.0e6, max_value=1.0e6, allow_nan=False, allow_infinity=False),
    st.floats(min_value=1.0e-6, max_value=1.0e6, allow_nan=False, allow_infinity=False),
    st.floats(min_value=0.0, max_value=0.9, allow_nan=False, allow_infinity=False),
)
def test_seed_relative_bound_never_exceeds_declared_limit(
    candidate: float, seed_value: float, relative_limit: float
) -> None:
    bounded = _bounded_seed_relative(candidate, seed_value, relative_limit)
    assert seed_value * (1.0 - relative_limit) <= bounded
    assert bounded <= seed_value * (1.0 + relative_limit)
