"""Phase 9.5 scientific-remediation contracts and frozen evidence tests."""

from __future__ import annotations

import csv
import hashlib
import json
import math
from collections.abc import Mapping
from pathlib import Path
from typing import cast

import pytest

from soil_simulator.io.configuration import (
    load_management_scenarios,
    load_model_parameters,
)
from soil_simulator.ml.dataset import load_saved_population
from soil_simulator.phase95.accounting import accrue_accounting, load_accounting_schedule
from soil_simulator.phase95.baseline import verify_frozen_baseline
from soil_simulator.phase95.empirical import location_group_leakage
from soil_simulator.phase95.policies import (
    PHASE95_POLICY_IDS,
    duplicate_policy_report,
    phase95_policy_set,
)
from soil_simulator.phase95.readiness import publication_readiness
from soil_simulator.phase95.reporting import (
    HEADLINE_EFFECT_TARGETS,
    NON_ML_IDENTITY_TARGETS,
    headline_target_manifest,
)
from soil_simulator.phase95.sensitivity import (
    SensitivityParameter,
    morris_screen,
    sobol_indices,
)

ROOT = Path(__file__).parents[2]
ARTIFACTS = ROOT / "outputs/phase95_v0.9.5"


def _json(name: str) -> dict[str, object]:
    return cast(dict[str, object], json.loads((ARTIFACTS / name).read_text(encoding="utf-8")))


@pytest.mark.skipif(
    not (ROOT / "outputs" / "phase9_v0.9.0").is_dir(),
    reason="frozen outputs/phase9_v0.9.0/ are not committed (gitignored)",
)
def test_audited_v090_artifacts_remain_byte_identical() -> None:
    report = verify_frozen_baseline(ROOT, ROOT / "config/phase95/frozen_v090_sha256.json")
    assert report["passed"] is True
    assert report["missing"] == []
    assert report["undeclared"] == []


def test_headline_metrics_are_effect_only_and_identity_targets_are_not_ml() -> None:
    manifest = headline_target_manifest()
    assert all(target.startswith("delta_") for target in HEADLINE_EFFECT_TARGETS)
    assert set(NON_ML_IDENTITY_TARGETS) == set(
        cast(tuple[str, ...], manifest["excluded_from_ml_training_and_scoring"])
    )
    primary = cast(tuple[str, ...], manifest["primary_ml_targets"])
    assert not any("cost" in target or "emissions" in target for target in primary)


def test_duplicate_policy_is_detected_then_removed_from_phase95() -> None:
    scenarios = load_management_scenarios(ROOT / "config/scenarios/management_scenarios.yaml")
    parameters = load_model_parameters(ROOT / "config/model_defaults.yaml")
    report = duplicate_policy_report(scenarios, parameters)
    duplicate_groups = cast(tuple[tuple[str, ...], ...], report["duplicate_groups"])
    assert ("baseline", "no_till") in duplicate_groups
    policies = phase95_policy_set(
        scenarios.policies,
        120,
        start_date=scenarios.start_date,
    )
    assert tuple(policy.policy_id for policy in policies) == PHASE95_POLICY_IDS
    assert "no_till" not in PHASE95_POLICY_IDS


def test_horizon_aware_accounting_counts_only_scheduled_events() -> None:
    schedule = load_accounting_schedule(ROOT / "config/phase95/accounting.yaml")
    expected = {24: 2, 60: 5, 120: 10}
    for horizon, count in expected.items():
        phosphorus = accrue_accounting(schedule, "phosphorus", horizon)
        assert phosphorus.event_count == count
        assert phosphorus.cost_gbp_ha == 30.0 * count
        assert phosphorus.operational_emissions_kg_co2e_ha == 5.0 * count
        assert phosphorus.lifecycle_emissions_kg_co2e_ha == 15.0 * count
    cover = accrue_accounting(schedule, "cover_crop", 120)
    assert cover.event_count == 18
    assert sum(event.event_type == "cover_crop_establishment" for event in cover.events) == 9
    assert sum(event.event_type == "cover_crop_termination" for event in cover.events) == 9


def test_phosphorus_ablation_is_explicit_and_mass_balanced() -> None:
    result = _json("phosphorus_ablation.json")
    variants = cast(dict[str, dict[str, object]], result["variants_by_horizon"])
    for horizon in ("24", "60", "120"):
        current = cast(
            dict[str, float],
            variants[horizon]["phosphorus_current_plant_growth_response_effect"],
        )
        capped = cast(dict[str, float], variants[horizon]["phosphorus_capped_response_effect"])
        assert current["npp_t_c_ha"] >= capped["npp_t_c_ha"]
        baseline = cast(dict[str, float], variants[horizon]["no_phosphorus_intervention"])
        assert baseline["max_carbon_residual_t_c_ha"] < 1e-10
        assert baseline["max_phosphorus_residual_kg_p_ha"] < 1e-10
    assert result["phosphorus_excluded_from_headline_carbon_conclusion"] is True


def test_sensitivity_algorithms_replay_exactly() -> None:
    parameters = (
        SensitivityParameter("x", 0.0, 1.0, "uniform", "scenario_assumption", "test"),
        SensitivityParameter("z", 1.0, 2.0, "uniform", "scenario_assumption", "test"),
    )

    def evaluator(values: Mapping[str, float]) -> Mapping[str, float]:
        return {"policy|target|120": values["x"] + 2.0 * values["z"]}

    first_morris = morris_screen(parameters, evaluator, trajectories=4, levels=6, seed=95)
    second_morris = morris_screen(parameters, evaluator, trajectories=4, levels=6, seed=95)
    assert first_morris == second_morris
    first_sobol = sobol_indices(parameters, evaluator, sample_size=16, seed=96)
    second_sobol = sobol_indices(parameters, evaluator, sample_size=16, seed=96)
    assert first_sobol == second_sobol


def test_local_data_fixtures_have_frozen_hashes_and_honest_labels() -> None:
    validation = _json("long_term_validation.json")
    hoosfield = ROOT / "data/validation/hoosfield_soc_1852_1998_v1.csv"
    assert hashlib.sha256(hoosfield.read_bytes()).hexdigest() == validation["local_fixture_sha256"]
    empirical = _json("EMPIRICAL_PILOT_DATA_MANIFEST.json")
    assert empirical["status"] == "blocked"
    assert empirical["completed_empirical_locations"] == 0
    assert empirical["immutable_fixture_created"] is False


def test_phase95_artifact_hash_manifest_matches_every_declared_file() -> None:
    manifest = _json("artifact_hashes.json")
    files = cast(dict[str, str], manifest["files"])
    assert "artifact_hashes.json" not in files
    for relative, expected in files.items():
        assert hashlib.sha256((ARTIFACTS / relative).read_bytes()).hexdigest() == expected


@pytest.mark.skipif(
    not (ROOT / "outputs" / "phase86_v0.8.6").is_dir(),
    reason="frozen outputs/phase86_v0.8.6/ are not committed (gitignored)",
)
def test_location_groups_do_not_cross_partitions() -> None:
    population = load_saved_population(
        ROOT / "outputs/phase86_v0.8.6/frozen_final_population_and_batch.json"
    )
    report = location_group_leakage(population)
    assert report["passed"] is True
    assert report["overlaps"] == {}


def test_long_term_validation_metrics_and_no_calibration_leakage() -> None:
    result = _json("long_term_validation.json")
    assert result["run_type"] == "uncalibrated"
    assert result["calibration"] == "none; 1852 stocks initialise each trajectory only"
    with (ARTIFACTS / "long_term_validation.csv").open(encoding="utf-8", newline="") as handle:
        rows = tuple(csv.DictReader(handle))
    held = tuple(row for row in rows if row["data_role"] == "validation")
    residuals = tuple(
        float(row["simulated_soc_t_c_ha"]) - float(row["observed_soc_t_c_ha"]) for row in held
    )
    aggregate = cast(dict[str, float], result["aggregate_metrics"])
    assert math.isclose(
        aggregate["mae_t_c_ha"],
        math.fsum(abs(value) for value in residuals) / len(residuals),
    )
    assert all(row["data_role"] != "calibration" for row in rows)


def test_population_and_benchmark_replay_block_closed() -> None:
    population = _json("REVISED_POPULATION_MANIFEST.json")
    assert population["status"] == "not_generated_due_empirical_pilot_blocker"
    assert population["field_count"] == 0
    selection = (ARTIFACTS / "REMEDIATED_SELECTION_REGRET_REPORT.md").read_text(encoding="utf-8")
    assert "not rerun" in selection.lower()
    assert "no Phase 9.5 oracle-match or regret value" in selection


def test_publication_readiness_fails_closed() -> None:
    result = publication_readiness(
        {
            "stock_target_circularity_removed_from_headlines": True,
            "deterministic_accounting_removed_from_ml": True,
            "duplicate_no_till_resolved": True,
        }
    )
    assert result["passed"] is False
    assert result["exact_next_task"] == "remaining scientific remediation"
    frozen = _json("publication_readiness.json")
    assert frozen["passed"] is False
    assert frozen["manuscript_drafting_recommendation"] is False
