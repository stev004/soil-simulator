"""Phase 7 population contracts, perturbation, spin-up, QC and manifest tests."""

from __future__ import annotations

import hashlib
import math
from pathlib import Path

import pytest

from soil_simulator.domain.enums import PopulationSplit
from soil_simulator.io.configuration import load_model_parameters
from soil_simulator.io.population_configuration import load_population_config
from soil_simulator.population.adapters import (
    CachedYamlDatasetAdapter,
    DatasetAdapterError,
    VersionedLocalYamlAdapter,
)
from soil_simulator.population.generator import generate_population
from soil_simulator.population.quality import quality_control
from soil_simulator.population.reporting import population_summary

ROOT = Path(__file__).parents[2]
PARAMETERS = load_model_parameters(ROOT / "config" / "model_defaults.yaml")
CONFIG = load_population_config(ROOT / "config" / "populations" / "phase7_population.yaml")
DATASET_PATH = ROOT / "data" / "processed" / "phase7_empirical_seed_fixture_v1.yaml"
DATASET = VersionedLocalYamlAdapter().load(DATASET_PATH)
POPULATION = generate_population(
    dataset=DATASET,
    config=CONFIG,
    parameters=PARAMETERS,
    population_size=10,
    generation_seed=314159,
)


def test_versioned_local_and_cached_adapters_preserve_provenance() -> None:
    assert DATASET.dataset_version == "1.0.0"
    assert len(DATASET.seeds) == 10
    expected_hash = hashlib.sha256(DATASET_PATH.read_bytes()).hexdigest()
    assert CachedYamlDatasetAdapter(expected_hash).load(DATASET_PATH) == DATASET
    with pytest.raises(DatasetAdapterError, match="hash mismatch"):
        CachedYamlDatasetAdapter("0" * 64).load(DATASET_PATH)


def test_population_replays_exactly_for_fixed_seed() -> None:
    replay = generate_population(
        dataset=DATASET,
        config=CONFIG,
        parameters=PARAMETERS,
        population_size=10,
        generation_seed=314159,
    )
    assert POPULATION.model_dump_json() == replay.model_dump_json()
    assert POPULATION.manifest.population_hash == replay.manifest.population_hash


def test_compositional_texture_and_bounded_perturbation() -> None:
    seeds = {seed.seed_id: seed for seed in DATASET.seeds}
    for field in POPULATION.fields:
        seed = seeds[field.empirical_seed_id]
        texture_total = (
            field.field.clay_percent + field.field.silt_percent + field.field.sand_percent
        )
        assert math.isclose(texture_total, 100.0, rel_tol=0.0, abs_tol=1.0e-12)
        assert seed.soc_t_c_ha * 0.75 <= field.field.baseline_soc_t_c_ha <= seed.soc_t_c_ha * 1.25
        assert (
            seed.available_p_kg_ha * 0.75
            <= field.initial_state.available_p_kg_ha
            <= seed.available_p_kg_ha * 1.25
        )
        assert (
            seed.bulk_density_g_cm3 * 0.88
            <= field.field.bulk_density_g_cm3
            <= seed.bulk_density_g_cm3 * 1.12
        )


def test_weather_resamples_only_complete_coherent_years() -> None:
    records = {record.weather_year_id: record for record in DATASET.weather_years}
    for field in POPULATION.fields:
        assert len(field.weather) == 12 * len(field.weather_year_ids)
        for block_index, weather_year_id in enumerate(field.weather_year_ids):
            block = field.weather[block_index * 12 : (block_index + 1) * 12]
            record = records[weather_year_id]
            assert [month.month for month in block] == list(range(1, 13))
            assert {month.source_id for month in block} == {weather_year_id}
            assert tuple(month.mean_air_temperature_c for month in block) == record.temperature_c
            assert tuple(month.precipitation_mm for month in block) == record.rainfall_mm


def test_seed_group_split_prevents_leakage() -> None:
    split_by_seed: dict[str, set[PopulationSplit]] = {}
    for field in POPULATION.fields:
        split_by_seed.setdefault(field.empirical_seed_id, set()).add(field.population_split)
    assert all(len(splits) == 1 for splits in split_by_seed.values())
    assert {split.value for splits in split_by_seed.values() for split in splits} == {
        "train",
        "validation",
        "test",
    }
    assert population_summary(POPULATION)["split_counts"] == {
        "test": 2,
        "train": 6,
        "validation": 2,
    }


def test_named_archetypes_and_initial_amf_states_are_present() -> None:
    assert {field.archetype for field in POPULATION.fields} == {
        "low-carbon-sandy-field",
        "clay-rich-high-carbon-field",
        "phosphorus-limited-field",
        "drought-prone-field",
        "intensively-tilled-low-amf-field",
    }
    assert all(field.initial_state.amf_live_c > 0.0 for field in POPULATION.fields)


def test_spinup_matches_soc_and_records_convergence() -> None:
    for field in POPULATION.fields:
        assert field.spinup.converged
        assert field.spinup.years_run <= CONFIG.spinup_max_years.default
        assert field.spinup.relative_cycle_change <= CONFIG.spinup_relative_tolerance.default
        assert math.isclose(
            field.spinup.achieved_soc_t_c_ha,
            field.field.baseline_soc_t_c_ha,
            rel_tol=0.0,
            abs_tol=1.0e-10,
        )
        assert field.initial_state.iom_c > 0.0
        assert field.initial_state.protected_soc_c > field.initial_state.dpm_c


def test_quality_control_rejects_impossible_and_simulator_failure_cases() -> None:
    field = POPULATION.fields[0]
    invalid_properties = field.field.model_copy(update={"bulk_density_g_cm3": 1.95})
    invalid = field.model_copy(update={"field": invalid_properties})
    assert "bulk_density_out_of_range" in quality_control(invalid, CONFIG).reasons

    def fail_probe(_field: object) -> None:
        raise ValueError("intentional simulator failure")

    result = quality_control(field, CONFIG, simulator_probe=fail_probe)
    assert not result.passed
    assert result.reasons == ("simulator_failure:ValueError",)


def test_manifest_records_versions_groups_draws_and_rejections() -> None:
    manifest = POPULATION.manifest
    assert manifest.manifest_version == "0.7.0"
    assert manifest.accepted_count == 10
    assert manifest.rejected_count == 0
    assert len(manifest.configuration_hash) == 64
    assert len(manifest.population_hash) == 64
    assert len(manifest.fields) == 10
    assert all(entry.weather_year_ids for entry in manifest.fields)
    assert all(len(entry.uncertainty_draws) == 7 for entry in manifest.fields)
    assert all(
        draw.classification.value
        in {
            "established_model",
            "literature_informed_prior",
            "scenario_assumption",
            "calibrated",
        }
        for entry in manifest.fields
        for draw in entry.uncertainty_draws
    )
