"""Phase 8.5 dataset, leakage, model, uncertainty, and artifact tests."""

from __future__ import annotations

import csv
import json
import math
from dataclasses import replace
from pathlib import Path
from typing import cast

import pytest

from soil_simulator.cli import main
from soil_simulator.domain.enums import PopulationSplit
from soil_simulator.domain.population import SyntheticPopulation
from soil_simulator.io.configuration import load_management_scenarios, load_model_parameters
from soil_simulator.io.ml_configuration import load_ml_benchmark_config
from soil_simulator.io.population_configuration import load_population_config
from soil_simulator.ml.dataset import (
    assert_group_isolation,
    build_ml_dataset,
    construct_paired_targets,
)
from soil_simulator.ml.evaluation import (
    fit_conformal_half_widths,
    fit_group_conformal_half_widths,
    interval_diagnostics,
)
from soil_simulator.ml.models import (
    fit_global_mean,
    fit_policy_mean,
    fit_random_forest,
    model_from_dict,
)
from soil_simulator.ml.pipeline import calculate_success_gates, run_benchmark
from soil_simulator.ml.preprocessing import fit_preprocessor, preprocessor_from_dict
from soil_simulator.ml.schema import FEATURE_SETS, TARGETS
from soil_simulator.population.adapters import VersionedLocalYamlAdapter
from soil_simulator.population.batch import run_population_batch
from soil_simulator.population.foundation import (
    expand_synthetic_foundation,
    soc_bulk_density_correlation,
)
from soil_simulator.population.generator import generate_population

ROOT = Path(__file__).parents[2]
PARAMETERS = load_model_parameters(ROOT / "config" / "model_defaults.yaml")
POPULATION_CONFIG = load_population_config(
    ROOT / "config" / "populations" / "phase85_population.yaml"
)
ML_CONFIG = load_ml_benchmark_config(ROOT / "config" / "ml" / "phase8_benchmark.yaml")
BASE_EMPIRICAL_DATASET = VersionedLocalYamlAdapter().load(
    ROOT / "data" / "processed" / "phase7_empirical_seed_fixture_v1.yaml"
)
EMPIRICAL_DATASET = expand_synthetic_foundation(BASE_EMPIRICAL_DATASET)
SCENARIOS = load_management_scenarios(ROOT / "config" / "scenarios" / "management_scenarios.yaml")
POPULATION = generate_population(
    dataset=EMPIRICAL_DATASET,
    config=POPULATION_CONFIG,
    parameters=PARAMETERS,
    population_size=50,
    generation_seed=8675309,
)
BATCH = run_population_batch(
    POPULATION,
    SCENARIOS,
    PARAMETERS,
    POPULATION_CONFIG,
    horizons_months=ML_CONFIG.simulation_horizons_months,
)
ROWS, MANIFEST = build_ml_dataset(POPULATION, BATCH, ML_CONFIG)


def test_target_construction_and_paired_baseline_matching() -> None:
    paired = construct_paired_targets(BATCH.results)
    baseline_rows = [outcome for outcome in BATCH.results if outcome.policy_id == "baseline"]
    assert baseline_rows
    for outcome in baseline_rows:
        values = paired[(outcome.field_id, outcome.policy_id, outcome.simulation_horizon_months)]
        assert set(values) == set(TARGETS)
        assert all(values[name] == 0.0 for name in TARGETS if name.startswith("delta_"))
    intervention = next(outcome for outcome in BATCH.results if outcome.policy_id != "baseline")
    baseline = next(
        outcome
        for outcome in BATCH.results
        if outcome.field_id == intervention.field_id and outcome.policy_id == "baseline"
    )
    effect = paired[
        (intervention.field_id, intervention.policy_id, intervention.simulation_horizon_months)
    ]
    assert math.isclose(
        effect["delta_final_total_soc_t_c_ha"],
        intervention.final_total_soc_t_c_ha - baseline.final_total_soc_t_c_ha,
    )
    without_one_baseline = tuple(
        outcome
        for outcome in BATCH.results
        if not (outcome.field_id == baseline.field_id and outcome.policy_id == "baseline")
    )
    with pytest.raises(ValueError, match="missing paired baseline"):
        construct_paired_targets(without_one_baseline)


def test_expanded_group_splitting_and_correlation_weakening() -> None:
    assert len(EMPIRICAL_DATASET.seeds) == 50
    assert abs(soc_bulk_density_correlation(EMPIRICAL_DATASET)) < 0.65
    group_splits: dict[str, set[PopulationSplit]] = {}
    for field in POPULATION.fields:
        group_splits.setdefault(field.empirical_seed_id, set()).add(field.population_split)
    assert len(group_splits) == 50
    assert all(len(splits) == 1 for splits in group_splits.values())
    counts = {
        split: sum(1 for splits in group_splits.values() if split in splits)
        for split in PopulationSplit
    }
    assert counts == {
        PopulationSplit.TRAIN: 25,
        PopulationSplit.VALIDATION: 10,
        PopulationSplit.TEST: 5,
        PopulationSplit.ARCHETYPE_OOD: 5,
        PopulationSplit.WEATHER_OOD: 5,
    }


def test_horizon_specific_target_construction() -> None:
    assert {outcome.simulation_horizon_months for outcome in BATCH.results} == {24, 60, 120}
    assert all(
        row.simulation_horizon_months == 24 for row in ROWS if row.simulation_horizon_months == 24
    )
    one_field = POPULATION.fields[0].field.field_id
    baseline_horizons = {
        outcome.simulation_horizon_months
        for outcome in BATCH.results
        if outcome.field_id == one_field and outcome.policy_id == "baseline"
    }
    assert baseline_horizons == {24, 60, 120}


def test_frozen_groups_and_feature_set_separation_prevent_leakage() -> None:
    assert_group_isolation(ROWS)
    first = ROWS[0]
    leaking = replace(first, population_split=PopulationSplit.TEST)
    with pytest.raises(ValueError, match="group leakage"):
        assert_group_isolation((*ROWS, leaking))
    observable = set(FEATURE_SETS["observable_features"].names)
    full = set(FEATURE_SETS["full_simulator_state"].names)
    assert observable < full
    assert not any(name.startswith("latent_") for name in observable)
    assert "initial_amf_live_c_t_ha" not in observable
    assert not observable.intersection(TARGETS)
    assert not {"field_id", "empirical_seed_id", "population_split", "archetype"}.intersection(
        observable
    )


def test_preprocessing_is_fitted_on_training_only_and_serializes() -> None:
    train = tuple(row for row in ROWS if row.population_split is PopulationSplit.TRAIN)
    validation = tuple(row for row in ROWS if row.population_split is PopulationSplit.VALIDATION)
    preprocessor = fit_preprocessor(train, FEATURE_SETS["observable_features"])
    soc_index = preprocessor.numeric_features.index("baseline_soc_t_c_ha")
    expected = sum(float(row.features["baseline_soc_t_c_ha"]) for row in train) / len(train)
    assert preprocessor.numeric_means[soc_index] == expected
    with pytest.raises(ValueError, match="training rows only"):
        fit_preprocessor(train + validation, FEATURE_SETS["observable_features"])
    restored = preprocessor_from_dict(preprocessor.model_dump())
    assert restored == preprocessor
    assert restored.transform(validation[0]) == preprocessor.transform(validation[0])


def test_baseline_means_use_only_supplied_training_targets() -> None:
    targets = ((1.0, 10.0), (3.0, 30.0), (1000.0, 1000.0))
    names = ("a", "b")
    global_model = fit_global_mean(targets[:2], names)
    assert global_model.means == (2.0, 20.0)
    policy_model = fit_policy_mean(targets[:2], ("baseline", "cover"), names)
    prediction = policy_model.predict(((), (), ()), ("baseline", "cover", "unseen"))
    assert prediction == ((1.0, 10.0), (3.0, 30.0), (2.0, 20.0))


def test_training_and_model_serialization_are_deterministic() -> None:
    matrix = tuple((float(index), float(index % 3)) for index in range(30))
    targets = tuple((2.0 * row[0] + row[1], row[0] - row[1]) for row in matrix)
    first = fit_random_forest(
        matrix,
        targets,
        ("one", "two"),
        ("x", "z"),
        tree_count=4,
        max_depth=3,
        min_leaf=2,
        feature_fraction=1.0,
        random_seed=12345,
    )
    second = fit_random_forest(
        matrix,
        targets,
        ("one", "two"),
        ("x", "z"),
        tree_count=4,
        max_depth=3,
        min_leaf=2,
        feature_fraction=1.0,
        random_seed=12345,
    )
    assert first.stable_hash() == second.stable_hash()
    restored = model_from_dict(first.model_dump())
    assert restored.stable_hash() == first.stable_hash()
    assert restored.predict(matrix, ("p",) * len(matrix)) == first.predict(
        matrix, ("p",) * len(matrix)
    )


def test_multihorizon_replay_and_dataset_artifact_hash_are_deterministic() -> None:
    one_field = SyntheticPopulation(fields=(POPULATION.fields[0],), manifest=POPULATION.manifest)
    first = run_population_batch(
        one_field,
        SCENARIOS,
        PARAMETERS,
        POPULATION_CONFIG,
        horizons_months=ML_CONFIG.simulation_horizons_months,
    )
    second = run_population_batch(
        one_field,
        SCENARIOS,
        PARAMETERS,
        POPULATION_CONFIG,
        horizons_months=ML_CONFIG.simulation_horizons_months,
    )
    assert first == second
    rebuilt_rows, rebuilt_manifest = build_ml_dataset(POPULATION, BATCH, ML_CONFIG)
    assert rebuilt_rows == ROWS
    assert rebuilt_manifest.dataset_hash == MANIFEST.dataset_hash


def test_uncertainty_coverage_calculation_is_exact() -> None:
    actual = ((0.0,), (1.0,), (2.0,), (3.0,))
    calibration_prediction = ((0.0,), (2.0,), (2.0,), (5.0,))
    widths = fit_conformal_half_widths(actual, calibration_prediction, 0.25, ("target",))
    assert widths == {"target": 2.0}
    held_out_prediction = ((1.0,), (1.0,), (5.0,), (3.0,))
    diagnostics = interval_diagnostics(actual, held_out_prediction, widths, ("target",))["target"]
    assert diagnostics["coverage"] == 0.75
    assert diagnostics["mean_interval_width"] == 4.0


def test_group_aware_uncertainty_uses_validation_groups_and_can_abstain() -> None:
    validation = tuple(
        row
        for row in ROWS
        if row.population_split is PopulationSplit.VALIDATION
        and row.simulation_horizon_months == 24
        and row.policy_id == "baseline"
    )
    actual = tuple((float(index),) for index in range(len(validation)))
    predicted = tuple((float(index) + 0.5,) for index in range(len(validation)))
    widths, audit = fit_group_conformal_half_widths(
        validation, actual, predicted, 0.1, 8, ("target",)
    )
    assert widths == {"target": 0.5}
    assert audit["calibration_group_count"] == 10
    assert audit["calibration_claim_supported"] is True
    _, abstention = fit_group_conformal_half_widths(
        validation[:3], actual[:3], predicted[:3], 0.1, 8, ("target",)
    )
    assert abstention["calibration_claim_supported"] is False
    assert "abstain" in cast(str, abstention["claim"])


def test_full_benchmark_exports_artifacts_and_held_out_archetypes(tmp_path: Path) -> None:
    smoke_config = ML_CONFIG.model_copy(
        update={
            "ridge_alphas": (0.1,),
            "forest_tree_counts": (2,),
            "forest_max_depths": (2,),
            "forest_min_leaf": 2,
        }
    )
    output_dir = tmp_path / "phase8"
    report, table = run_benchmark(ROWS, MANIFEST, smoke_config, output_dir)
    tasks = cast(dict[str, dict[str, object]], report["tasks"])
    leakage = cast(dict[str, object], report["leakage_audit"])
    correlation = cast(dict[str, object], report["engineered_correlation_audit"])
    assert "delta_final_protected_soc_proxy_t_c_ha@120" in tasks
    assert leakage["final_test_partitions_used_for_tuning"] is False
    task = tasks["delta_final_protected_soc_proxy_t_c_ha@120"]
    ood = cast(dict[str, object], task["out_of_distribution"])
    assert cast(int, cast(dict[str, object], ood["archetype_ood"])["row_count"]) > 0
    assert cast(int, cast(dict[str, object], ood["weather_ood"])["row_count"]) > 0
    assert "available_p_amf" in correlation
    assert "per_policy_forest" in table or "pooled_forest" in table
    assert (output_dir / "training_dataset_v0.8.5.csv").exists()
    with (output_dir / "training_dataset_v0.8.5.csv").open(encoding="utf-8", newline="") as handle:
        header = next(csv.reader(handle))
    assert len(header) == len(set(header))
    assert (output_dir / "dataset_manifest.json").exists()
    assert (output_dir / "preprocessing" / "observable_features.json").exists()
    assert any((output_dir / "models").rglob("per_policy_forest.json"))
    assert (output_dir / "evaluation_report.json").exists()
    assert (output_dir / "evaluation_report.md").exists()
    assert (output_dir / "MODEL_CARD.md").exists()
    saved = json.loads((output_dir / "evaluation_report.json").read_text(encoding="utf-8"))
    assert "not real-field validation" in saved["claim_boundary"]
    assert saved["deterministic_model_hashes"] == report["deterministic_model_hashes"]


def test_success_gate_calculation_requires_all_predeclared_conditions() -> None:
    task_reports: dict[str, dict[str, object]] = {}
    for task_key in (
        "delta_crop_yield_t_dm_ha@24",
        "delta_final_total_soc_t_c_ha@60",
        "delta_final_total_soc_t_c_ha@120",
        "delta_final_protected_soc_proxy_t_c_ha@60",
        "delta_final_protected_soc_proxy_t_c_ha@120",
    ):
        task_reports[task_key] = {
            "observable_primary_model": "pooled_forest",
            "final_test_metrics": {
                "pooled_forest": {"mae": 0.4, "natural_field_to_field_sd": 1.0},
                "policy_mean": {"mae": 0.7, "natural_field_to_field_sd": 1.0},
                "pooled_ridge": {"mae": 0.6, "natural_field_to_field_sd": 1.0},
                "per_policy_ridge": {"mae": 0.5, "natural_field_to_field_sd": 1.0},
            },
            "uncertainty": {
                "final_test": {"coverage": 0.9},
                "calibration": {"calibration_claim_supported": True},
            },
            "out_of_distribution": {
                "archetype_ood": {"metrics": {"mae": 0.8, "natural_field_to_field_sd": 1.0}},
                "weather_ood": {"metrics": {"mae": 1.2, "natural_field_to_field_sd": 1.0}},
            },
        }
    gates = calculate_success_gates(task_reports, {"passed": True}, ML_CONFIG)
    assert gates["passed"] is True
    failed = calculate_success_gates(task_reports, {"passed": False}, ML_CONFIG)
    assert failed["passed"] is False
    assert "Do not build" in cast(str, failed["recommendation"])


def test_ml_cli_prints_table_and_optionally_exports_json(
    capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    saved = tmp_path / "saved.json"
    saved.write_text(
        json.dumps(
            {
                "population_manifest": POPULATION.manifest.model_dump(mode="json"),
                "fields": [field.model_dump(mode="json") for field in POPULATION.fields],
                "batch": BATCH.model_dump(mode="json"),
            },
            allow_nan=False,
        ),
        encoding="utf-8",
    )
    json_output = tmp_path / "report.json"
    assert (
        main(
            [
                "benchmark-intervention-ml",
                str(saved),
                str(saved),
                "--output-dir",
                str(tmp_path / "artifacts"),
                "--json-output",
                str(json_output),
            ]
        )
        == 0
    )
    captured = capsys.readouterr()
    assert "Phase 8.5 synthetic intervention-outcome diagnostics" in captured.out
    assert "forest" in captured.out
    assert json.loads(json_output.read_text(encoding="utf-8"))["report_version"] == "0.8.5"
