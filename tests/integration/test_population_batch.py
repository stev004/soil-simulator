"""Phase 7 integration tests against the verified Phase 6 batch boundary."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from soil_simulator.cli import main
from soil_simulator.io.configuration import load_management_scenarios, load_model_parameters
from soil_simulator.io.population_configuration import load_population_config
from soil_simulator.population.adapters import VersionedLocalYamlAdapter
from soil_simulator.population.batch import run_population_batch
from soil_simulator.population.generator import generate_population

ROOT = Path(__file__).parents[2]
PARAMETERS = load_model_parameters(ROOT / "config" / "model_defaults.yaml")
CONFIG = load_population_config(ROOT / "config" / "populations" / "phase7_population.yaml")
DATASET = VersionedLocalYamlAdapter().load(
    ROOT / "data" / "processed" / "phase7_empirical_seed_fixture_v1.yaml"
)
TEMPLATE = load_management_scenarios(ROOT / "config" / "scenarios" / "management_scenarios.yaml")
POPULATION = generate_population(
    dataset=DATASET,
    config=CONFIG,
    parameters=PARAMETERS,
    population_size=10,
    generation_seed=271828,
)


def test_batch_runs_baseline_and_eligible_interventions_with_phase6_balance() -> None:
    batch = run_population_batch(POPULATION, TEMPLATE, PARAMETERS, CONFIG)
    assert not batch.failures
    assert len([result for result in batch.results if result.policy_id == "baseline"]) == 10
    assert {result.policy_id for result in batch.results} == {
        policy.policy_id for policy in TEMPLATE.policies
    }
    assert batch.maximum_carbon_residual_t_c_ha <= 1.0e-9
    assert batch.maximum_phosphorus_residual_kg_p_ha <= 1.0e-9
    assert all(result.final_total_soc_t_c_ha >= 0.0 for result in batch.results)


def test_batch_replays_deterministically() -> None:
    first = run_population_batch(POPULATION, TEMPLATE, PARAMETERS, CONFIG)
    second = run_population_batch(POPULATION, TEMPLATE, PARAMETERS, CONFIG)
    assert first.model_dump_json() == second.model_dump_json()


def test_population_cli_prints_table_and_optionally_exports_json(
    capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    output_path = tmp_path / "population.json"
    assert (
        main(
            [
                "generate-population",
                "--count",
                "1",
                "--seed",
                "123",
                "--json-output",
                str(output_path),
            ]
        )
        == 0
    )
    captured = capsys.readouterr()
    assert "Variable" in captured.out
    assert "Accepted 1" in captured.out
    exported = json.loads(output_path.read_text(encoding="utf-8"))
    assert exported["manifest"]["accepted_count"] == 1
    assert len(exported["fields"]) == 1


def test_population_batch_cli_prints_intervention_comparison(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert main(["run-population-batch", "--count", "1", "--seed", "456"]) == 0
    captured = capsys.readouterr()
    assert "Policy" in captured.out
    assert "Delta protected" in captured.out
    assert "Failures 0" in captured.out
