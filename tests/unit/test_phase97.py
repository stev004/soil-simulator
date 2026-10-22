"""Phase 9.7 independent-audit defect-closure contracts."""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping
from pathlib import Path
from typing import cast

from soil_simulator.phase95.sensitivity import SensitivityParameter
from soil_simulator.phase97.calibration import calibration_boundary_profile
from soil_simulator.phase97.gates import (
    downstream_gate_evidence,
    empirical_location_leakage_evidence,
    independent_effect_validation_evidence,
    uncertainty_coverage_evidence,
)
from soil_simulator.phase97.manifests import (
    canonical_set_digest,
    corrected_phase96_manifest,
    verify_manifest,
)
from soil_simulator.phase97.sensitivity import (
    ConvergenceRule,
    SobolSettings,
    convergence_diagnostics,
    estimate_indices,
    run_nested_sobol,
    sobol_unit_matrices,
    transform_unit_row,
)

ROOT = Path(__file__).parents[2]
ARTIFACTS = ROOT / "outputs/phase97_v0.9.7"
ARCHIVED_PRISM_BUNDLE = ROOT / "manuscript/archive/prism_imports/v2_bundle"


def _parameter(name: str) -> SensitivityParameter:
    return SensitivityParameter(
        name=name,
        minimum=0.0,
        maximum=1.0,
        distribution="uniform",
        classification="scenario_assumption",
        source="unit test",
    )


def test_scipy_sobol_design_is_deterministic_and_power_of_two_only() -> None:
    left_a, left_b, left_hash = sobol_unit_matrices(3, 128, 970021)
    right_a, right_b, right_hash = sobol_unit_matrices(3, 128, 970021)
    assert left_hash == right_hash
    assert left_a.tobytes() == right_a.tobytes()
    assert left_b.tobytes() == right_b.tobytes()
    assert len({tuple(row) for row in left_a}) == 128
    try:
        sobol_unit_matrices(3, 96, 970021)
    except ValueError as error:
        assert "power of two" in str(error)
    else:  # pragma: no cover - defensive
        raise AssertionError("invalid Sobol base sample size was accepted")


def test_distribution_transforms_preserve_declared_bounds() -> None:
    parameters = (
        SensitivityParameter("u", 2.0, 4.0, "uniform", "scenario_assumption", "test"),
        SensitivityParameter("d", 1.0, 5.0, "uniform_discrete", "established_model", "test"),
        SensitivityParameter("l", 0.1, 10.0, "log_uniform", "literature_informed_prior", "test"),
    )
    low = transform_unit_row(parameters, (0.0, 0.0, 0.0))
    high = transform_unit_row(parameters, (1.0, 1.0, 1.0))
    assert low["u"] == 2.0 and low["d"] == 1.0
    assert high["u"] == 4.0 and high["d"] == 5.0
    assert math.isclose(low["l"], 0.1)
    assert math.isclose(high["l"], 10.0)


def test_sobol_first_and_total_order_indices_for_additive_model() -> None:
    parameters = (_parameter("x"), _parameter("y"))

    def evaluator(values: Mapping[str, float]) -> Mapping[str, float]:
        return {"policy|target|60": values["x"] + 2.0 * values["y"]}

    settings = SobolSettings(
        seed=970022,
        base_sample_sizes=(128, 256, 512, 1024),
        bootstrap_replicates=100,
        confidence_level=0.95,
        evaluation_workers=1,
        selected_parameter_names=("x", "y"),
        convergence_rule=ConvergenceRule(0.10, 0.90, 0.30, 0.25),
    )
    result = run_nested_sobol(parameters, evaluator, settings, retained_outputs=lambda _: True)
    estimates = cast(dict[str, dict[str, object]], result["estimates"])
    largest = cast(dict[str, dict[str, object]], estimates["1024"]["outputs"])
    indices = cast(dict[str, dict[str, float]], largest["policy|target|60"]["indices"])
    assert math.isclose(indices["x"]["first_order"], 0.2, abs_tol=0.03)
    assert math.isclose(indices["x"]["total_order"], 0.2, abs_tol=0.03)
    assert math.isclose(indices["y"]["first_order"], 0.8, abs_tol=0.03)
    assert math.isclose(indices["y"]["total_order"], 0.8, abs_tol=0.03)
    sampling = cast(dict[str, object], result["sampling_manifest"])
    assert sampling["sampler"] == "scipy.stats.qmc.Sobol"
    assert sampling["construction"] == "one 2D Sobol design split column-wise into A and B"


def test_negative_sobol_estimates_are_not_clipped() -> None:
    evaluations_a = ({"out": 0.0}, {"out": 1.0}, {"out": 2.0}, {"out": 3.0})
    evaluations_b = ({"out": 3.0}, {"out": 2.0}, {"out": 1.0}, {"out": 0.0})
    hybrids = {"x": ({"out": 0.0}, {"out": 0.0}, {"out": 0.0}, {"out": 0.0})}
    result = estimate_indices(
        evaluations_a,
        evaluations_b,
        hybrids,
        parameter_names=("x",),
        bootstrap_replicates=100,
        confidence_level=0.95,
        bootstrap_seed=7,
    )
    outputs = cast(dict[str, dict[str, object]], result["outputs"])
    indices = cast(dict[str, dict[str, object]], outputs["out"]["indices"])
    assert cast(float, indices["x"]["first_order"]) < 0.0
    assert indices["x"]["first_order_negative"] is True


def test_convergence_rule_reports_nonconvergence_honestly() -> None:
    def estimate(first: float, total: float) -> dict[str, object]:
        return {
            "outputs": {
                "out": {
                    "indices": {
                        "x": {
                            "first_order": first,
                            "total_order": total,
                            "first_order_confidence_interval": [first - 0.2, first + 0.2],
                            "total_order_confidence_interval": [total - 0.2, total + 0.2],
                        }
                    }
                }
            }
        }

    result = convergence_diagnostics(
        {128: estimate(0.1, 0.2), 256: estimate(0.5, 0.7)},
        ConvergenceRule(0.1, 0.9, 0.2, 0.1),
    )
    assert result["convergence_reached"] is False
    assert result["status"] == "not_converged_results_not_final"


def _effect_row(field: str, location: str, split: str, offset: float) -> dict[str, object]:
    row: dict[str, object] = {
        "row_id": f"{field}|policy|24|target",
        "field_id": field,
        "empirical_location_id": location,
        "population_split": split,
    }
    feature_names = (
        "clay_percent",
        "silt_percent",
        "sand_percent",
        "bulk_density_g_cm3",
        "ph",
        "cation_exchange_capacity_cmolc_kg",
        "baseline_total_nitrogen_percent",
        "baseline_soc_t_c_ha",
        "mean_temperature_c",
        "annual_precipitation_mm",
        "annual_pet_mm",
    )
    row.update({name: offset + index + 1.0 for index, name in enumerate(feature_names)})
    return row


def test_empirical_location_descendant_preprocessing_and_calibration_isolation() -> None:
    rows = [
        _effect_row("train-field", "train-location", "train", 0.0),
        _effect_row("validation-field", "validation-location", "validation", 10.0),
        _effect_row("test-field", "test-location", "test", 20.0),
        _effect_row("ood-field", "ood-location", "weather_ood", 30.0),
    ]
    evidence = empirical_location_leakage_evidence(rows)
    assert evidence["passed"] is True
    contaminated = [*rows, _effect_row("descendant", "train-location", "test", 40.0)]
    failed = empirical_location_leakage_evidence(contaminated)
    assert failed["passed"] is False
    reasons = cast(list[str], failed["failure_reasons"])
    assert "no_empirical_location_crosses_groups" in reasons
    assert "generated_descendants_isolated_by_empirical_seed" in reasons


def test_duplicate_fields_crossing_groups_fail_leakage_gate() -> None:
    train = _effect_row("train-field", "train-location", "train", 0.0)
    duplicate = _effect_row("test-field", "test-location", "test", 0.0)
    evidence = empirical_location_leakage_evidence(
        [
            train,
            duplicate,
            _effect_row("validation-field", "validation-location", "validation", 10.0),
        ]
    )
    assert evidence["passed"] is False
    assert "no_exact_or_near_duplicate_fields_cross_groups" in cast(
        list[str], evidence["failure_reasons"]
    )


def test_independent_validation_is_computed_and_missing_evidence_fails_closed() -> None:
    missing = independent_effect_validation_evidence(None, None)
    assert missing["passed"] is False
    assert missing["computable"] is False
    target_pairs = (
        ("delta_yield_t_dm_ha", 24),
        ("delta_total_soc_t_c_ha", 60),
        ("delta_total_soc_t_c_ha", 120),
        ("delta_protected_soc_proxy_t_c_ha", 60),
        ("delta_protected_soc_proxy_t_c_ha", 120),
        ("delta_respiration_t_c_ha", 60),
        ("delta_respiration_t_c_ha", 120),
    )
    records = [
        {
            "treatment_id": "cover_crop",
            "target_name": target,
            "horizon_months": horizon,
            "observed_effect": float(index),
        }
        for index in range(35)
        for target, horizon in (target_pairs[index % len(target_pairs)],)
    ]
    metadata = {
        "dataset_identity": "independent-fixture",
        "evidence_source": "unit-test source",
        "independent_collection": True,
        "used_for_calibration": False,
        "used_for_model_development": False,
    }
    passed = independent_effect_validation_evidence(records, metadata)
    assert passed["passed"] is True
    contaminated = dict(metadata, used_for_calibration=True)
    assert independent_effect_validation_evidence(records, contaminated)["passed"] is False


def _prediction(coverage: float) -> dict[str, object]:
    regime = {
        "row_count": 100,
        "empirical_location_count": 10,
        "validation_calibrated_90_percent_interval_coverage": coverage,
        "interval_half_width": 1.0,
        "ridge": {"rmse": 1.0},
    }
    return {"targets": {"target|60": {"test": regime, "ood": regime}}}


def test_target_specific_uncertainty_coverage_rejects_severe_undercoverage() -> None:
    assert uncertainty_coverage_evidence(_prediction(0.90))["passed"] is True
    failed = uncertainty_coverage_evidence(_prediction(0.60))
    assert failed["passed"] is False
    targets = cast(dict[str, dict[str, object]], failed["targets"])
    regimes = cast(dict[str, dict[str, object]], targets["target|60"]["regimes"])
    assert regimes["test"]["severe_undercoverage"] is True


def test_calibration_boundary_profile_detects_improving_upper_edge() -> None:
    diagnosis = {
        "optional_calibration": {
            "predeclared_parameters": {
                "fym_carbon_factor": {"bounds": [0.9, 1.1], "classification": "calibrated"}
            },
            "best_parameters": {"fym_carbon_factor": 1.1},
            "candidate_summary": [
                {
                    "fym_carbon_factor": 0.9,
                    "calibration_objective_mean_treatment_rmse_t_c_ha": 4.0,
                },
                {
                    "fym_carbon_factor": 1.0,
                    "calibration_objective_mean_treatment_rmse_t_c_ha": 3.0,
                },
                {
                    "fym_carbon_factor": 1.1,
                    "calibration_objective_mean_treatment_rmse_t_c_ha": 2.0,
                },
            ],
            "identifiability": {"within_10_percent_of_minimum_count": 2},
            "held_out_treatment_metrics": {"rmse_t_c_ha": 7.5},
        }
    }
    profile = calibration_boundary_profile(diagnosis)
    assert profile["boundary_constrained"] is True
    assert profile["objective_likely_improves_beyond_bound"] is True
    assert profile["bound_widened"] is False
    assert profile["general_calibration_success"] is False


def test_downstream_gate_is_computed_from_prerequisites() -> None:
    prediction = {
        "gates": {
            "all_effect_targets_beat_policy_mean": True,
            "all_effect_targets_have_acceptable_ood": True,
        }
    }
    passed = downstream_gate_evidence(
        prediction, {"passed": True}, {"passed": True}, {"passed": True}
    )
    assert passed["eligible"] is True
    blocked = downstream_gate_evidence(
        prediction, {"passed": True}, {"passed": False}, {"passed": True}
    )
    assert blocked["eligible"] is False
    assert blocked["selection_regret_executed"] is False


def test_audit_document_hash_correction_preserves_historical_manifest(tmp_path: Path) -> None:
    audit = tmp_path / "docs/AUDIT_soil_simulator_v0.9.0.md"
    audit.parent.mkdir(parents=True)
    audit.write_text("current audit\n", encoding="utf-8")
    historical_path = tmp_path / "outputs/phase96_v0.9.6/artifact_hashes.json"
    historical_path.parent.mkdir(parents=True)
    old_hash = hashlib.sha256(b"old audit\n").hexdigest()
    historical = {
        "version": "0.9.6",
        "files": {"docs/AUDIT_soil_simulator_v0.9.0.md": old_hash},
        "artifact_set_sha256": canonical_set_digest(
            {"docs/AUDIT_soil_simulator_v0.9.0.md": old_hash}
        ),
    }
    historical_path.write_text(json.dumps(historical), encoding="utf-8")
    before = historical_path.read_bytes()
    corrected = corrected_phase96_manifest(tmp_path)
    assert historical_path.read_bytes() == before
    assert corrected["historical_manifest_modified"] is False
    changes = cast(list[dict[str, object]], corrected["changes_since_phase96_freeze"])
    assert changes[0]["path"] == "docs/AUDIT_soil_simulator_v0.9.0.md"
    assert "preserved" in str(changes[0]["reason"])
    assert verify_manifest(tmp_path, corrected) == []


# pyproject.toml changed after the freeze (MIT licence and author metadata, public-readiness
# branch); README.md changed in Phase 9.8 and again for public readiness. No scientific content.
POST_FREEZE_METADATA_CHANGES = ["README.md", "pyproject.toml"]


def test_checked_in_phase97_artifact_hashes_replay_with_phase98_documentation_record() -> None:
    if not (ARTIFACTS / "artifact_hashes.json").exists():
        return
    manifest = cast(
        dict[str, object],
        json.loads((ARTIFACTS / "artifact_hashes.json").read_text(encoding="utf-8")),
    )
    assert sorted(verify_manifest(ROOT, manifest)) == POST_FREEZE_METADATA_CHANGES
    correction = cast(
        dict[str, object],
        json.loads(
            (ROOT / "manuscript/archive/v2/phase98_current_byte_corrections.json").read_text(
                encoding="utf-8"
            )
        ),
    )
    changes = cast(list[dict[str, object]], correction["changes_since_phase97_freeze"])
    assert [item["path"] for item in changes] == ["README.md"]
    assert changes[0]["scientific_content_changed"] is False
    assert (
        changes[0]["current_sha256"]
        == hashlib.sha256((ARCHIVED_PRISM_BUNDLE / "README.md").read_bytes()).hexdigest()
    )
    corrected = cast(
        dict[str, object],
        json.loads(
            (ARTIFACTS / "corrected_phase96_artifact_hashes.json").read_text(encoding="utf-8")
        ),
    )
    assert sorted(verify_manifest(ROOT, corrected)) == POST_FREEZE_METADATA_CHANGES
