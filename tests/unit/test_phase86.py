"""Phase 8.6 repeated-evidence, freeze, selection, and abstention tests."""

from __future__ import annotations

from pathlib import Path
from typing import cast

import pytest

from soil_simulator.domain.population import SyntheticPopulation
from soil_simulator.io.configuration import load_model_parameters
from soil_simulator.io.phase86_configuration import load_phase86_benchmark_config
from soil_simulator.io.population_configuration import load_population_config
from soil_simulator.ml.phase86 import (
    ApplicabilityDecision,
    applicability_allows,
    build_seed_plan,
    uncertainty_interval_or_abstain,
)
from soil_simulator.ml.phase86_schema import predeclared_model_choice
from soil_simulator.population.adapters import VersionedLocalYamlAdapter
from soil_simulator.population.foundation import (
    PHASE86_WEATHER_OOD_REGIONS,
    expand_phase86_foundation,
    soc_bulk_density_correlation,
)
from soil_simulator.population.generator import generate_population

ROOT = Path(__file__).parents[2]
ML_CONFIG = load_phase86_benchmark_config(ROOT / "config" / "ml" / "phase86_benchmark.yaml")
POPULATION_CONFIG = load_population_config(
    ROOT / "config" / "populations" / "phase86_population.yaml"
)
PARAMETERS = load_model_parameters(ROOT / "config" / "model_defaults.yaml")
BASE_DATASET = VersionedLocalYamlAdapter().load(
    ROOT / "data" / "processed" / "phase7_empirical_seed_fixture_v1.yaml"
)


def test_repeated_seed_orchestration_is_independent_and_deterministic() -> None:
    first = build_seed_plan(ML_CONFIG)
    second = build_seed_plan(ML_CONFIG)
    assert first == second
    assert len(first) >= 10
    assert len({entry.population_seed for entry in first}) == len(first)
    assert len({entry.weather_seed for entry in first}) > 1
    assert len({entry.biological_seed for entry in first}) > 1
    final_seeds = {
        ML_CONFIG.final_foundation_seed,
        ML_CONFIG.final_population_seed,
        ML_CONFIG.final_weather_resampling_seed,
        ML_CONFIG.final_biological_parameter_seed,
    }
    development_seeds = {
        value
        for entry in first
        for value in (
            entry.foundation_seed,
            entry.population_seed,
            entry.weather_seed,
            entry.biological_seed,
        )
    }
    assert not final_seeds & development_seeds


def test_phase86_foundation_has_all_untouched_weather_regimes_and_weaker_correlation() -> None:
    foundation = expand_phase86_foundation(
        BASE_DATASET,
        group_count=ML_CONFIG.foundation_group_count,
        random_seed=ML_CONFIG.development_foundation_seeds[0],
    )
    assert len(foundation.seeds) == 75
    assert set(PHASE86_WEATHER_OOD_REGIONS) <= {seed.region_id for seed in foundation.seeds}
    for region in PHASE86_WEATHER_OOD_REGIONS:
        assert sum(seed.region_id == region for seed in foundation.seeds) == 5
    assert abs(soc_bulk_density_correlation(foundation)) < 0.35
    assert (
        foundation.model_dump_json()
        == expand_phase86_foundation(
            BASE_DATASET,
            group_count=ML_CONFIG.foundation_group_count,
            random_seed=ML_CONFIG.development_foundation_seeds[0],
        ).model_dump_json()
    )


def test_population_weather_and_biological_seed_streams_replay_independently() -> None:
    foundation = expand_phase86_foundation(
        BASE_DATASET,
        group_count=75,
        random_seed=ML_CONFIG.development_foundation_seeds[0],
    )

    def no_probe(_field: object) -> None:
        return None

    def make_population(weather_seed: int, biological_seed: int) -> SyntheticPopulation:
        return generate_population(
            dataset=foundation,
            config=POPULATION_CONFIG,
            parameters=PARAMETERS,
            population_size=3,
            generation_seed=ML_CONFIG.population_seeds[0],
            simulator_probe=no_probe,
            weather_resampling_seed=weather_seed,
            biological_parameter_seed=biological_seed,
        )

    first = make_population(
        ML_CONFIG.weather_resampling_seeds[0], ML_CONFIG.biological_parameter_seeds[0]
    )
    replay = make_population(
        ML_CONFIG.weather_resampling_seeds[0], ML_CONFIG.biological_parameter_seeds[0]
    )
    changed_weather = make_population(
        ML_CONFIG.weather_resampling_seeds[1], ML_CONFIG.biological_parameter_seeds[0]
    )
    changed_biology = make_population(
        ML_CONFIG.weather_resampling_seeds[0], ML_CONFIG.biological_parameter_seeds[1]
    )
    assert first.model_dump_json() == replay.model_dump_json()
    assert first.fields[0].field == changed_weather.fields[0].field
    assert first.fields[0].weather != changed_weather.fields[0].weather
    assert first.fields[0].uncertainty_draws == changed_weather.fields[0].uncertainty_draws
    assert first.fields[0].weather == changed_biology.fields[0].weather
    assert first.fields[0].uncertainty_draws != changed_biology.fields[0].uncertainty_draws
    assert first.manifest.weather_resampling_seed == ML_CONFIG.weather_resampling_seeds[0]
    assert first.manifest.biological_parameter_seed == ML_CONFIG.biological_parameter_seeds[0]


def test_predeclared_selection_chooses_simplest_model_within_tolerance() -> None:
    selected, audit = predeclared_model_choice(
        {
            "policy_mean": 0.70,
            "pooled_ridge": 0.51,
            "per_policy_ridge": 0.50,
            "pooled_forest": 0.49,
            "per_policy_forest": 0.48,
        },
        relative_tolerance=0.07,
    )
    assert selected == "pooled_ridge"
    assert audit["r_squared_used_for_selection"] is False
    assert "pooled_ridge" in cast(tuple[str, ...], audit["eligible_models_in_complexity_order"])


def test_applicability_domain_enforces_uncertainty_abstention() -> None:
    decisions = (
        ApplicabilityDecision("delta_crop_yield_t_dm_ha@24", "dry", True, "supported", 25, 0.4),
        ApplicabilityDecision(
            "delta_crop_yield_t_dm_ha@24", "hot_dry", False, "unsupported", 25, 1.2
        ),
    )
    widths = {
        "delta_crop_yield_t_dm_ha@24": {
            "dry": 0.5,
            "hot_dry": 2.0,
        }
    }
    assert applicability_allows(decisions, "delta_crop_yield_t_dm_ha@24", "dry")
    interval = uncertainty_interval_or_abstain(
        prediction=1.0,
        task="delta_crop_yield_t_dm_ha@24",
        regime="dry",
        decisions=decisions,
        half_widths=widths,
    )
    assert interval == {
        "abstained": False,
        "lower": 0.5,
        "upper": 1.5,
        "reason": "group-aware development calibration",
    }
    abstention = uncertainty_interval_or_abstain(
        prediction=1.0,
        task="delta_crop_yield_t_dm_ha@24",
        regime="hot_dry",
        decisions=decisions,
        half_widths=widths,
    )
    assert abstention["abstained"] is True
    assert abstention["lower"] is None
    assert abstention["upper"] is None


def test_frozen_final_seed_overlap_is_rejected_and_protocol_hash_replays() -> None:
    assert (
        ML_CONFIG.stable_hash()
        == load_phase86_benchmark_config(
            ROOT / "config" / "ml" / "phase86_benchmark.yaml"
        ).stable_hash()
    )
    with pytest.raises(ValueError, match="frozen-final seeds"):
        ML_CONFIG.model_copy(
            update={"final_population_seed": ML_CONFIG.population_seeds[0]}
        ).__class__.model_validate(
            {
                **ML_CONFIG.model_dump(mode="python"),
                "final_population_seed": ML_CONFIG.population_seeds[0],
            }
        )
