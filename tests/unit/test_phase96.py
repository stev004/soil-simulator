"""Phase 9.6 empirical-grounding and fail-closed evidence contracts."""

from __future__ import annotations

import csv
import hashlib
import json
import math
from pathlib import Path
from typing import cast

from soil_simulator.phase96.empirical import (
    build_empirical_records,
    harmonise_soilgrids,
)
from soil_simulator.phase96.pipeline import _pilot_qc
from soil_simulator.phase96.statistics import covariance_matrix
from soil_simulator.phase96.values import as_float

ROOT = Path(__file__).parents[2]
ARTIFACTS = ROOT / "outputs/phase96_v0.9.6"
ARCHIVED_PRISM_BUNDLE = ROOT / "manuscript/archive/prism_imports/v2_bundle"


def _json(name: str) -> dict[str, object]:
    return cast(dict[str, object], json.loads((ARTIFACTS / name).read_text(encoding="utf-8")))


def _soil_layer(name: str, divisor: float, values: tuple[float, float, float]) -> dict[str, object]:
    labels = ("0-5cm", "5-15cm", "15-30cm")
    return {
        "name": name,
        "unit_measure": {"d_factor": divisor},
        "depths": [
            {"label": label, "values": {"Q0.5": value}}
            for label, value in zip(labels, values, strict=True)
        ],
    }


def test_soilgrids_depth_units_stock_and_texture_closure() -> None:
    layers = [
        _soil_layer("bdod", 100.0, (120.0, 130.0, 140.0)),
        _soil_layer("cec", 10.0, (100.0, 110.0, 120.0)),
        _soil_layer("clay", 10.0, (200.0, 300.0, 400.0)),
        _soil_layer("nitrogen", 100.0, (200.0, 300.0, 400.0)),
        _soil_layer("phh2o", 10.0, (60.0, 65.0, 70.0)),
        _soil_layer("sand", 10.0, (500.0, 400.0, 300.0)),
        _soil_layer("silt", 10.0, (300.0, 300.0, 300.0)),
        _soil_layer("soc", 10.0, (300.0, 200.0, 100.0)),
    ]
    record, correction = harmonise_soilgrids({"properties": {"layers": layers}})
    assert math.isclose(
        record["soc_stock_t_c_ha_0_23cm"],
        30.0 * 1.2 * 5.0 * 0.1 + 20.0 * 1.3 * 10.0 * 0.1 + 10.0 * 1.4 * 8.0 * 0.1,
    )
    assert math.isclose(
        record["clay_percent"] + record["silt_percent"] + record["sand_percent"],
        100.0,
    )
    assert correction["rule"] == (
        "renormalise thickness-weighted independently predicted texture fractions"
    )


def test_cached_pilot_is_complete_paired_and_rejects_missing_without_imputation() -> None:
    locations, monthly, corrections = build_empirical_records(ROOT / "data/raw/phase96_empirical")
    accepted, paired, range_rejected = _pilot_qc(locations, monthly)
    source_rejected = [item for item in corrections if item["source_record_status"] == "rejected"]
    assert len(corrections) == 64
    assert len(accepted) == 56
    assert len(paired) == 56 * 20 * 12
    assert max(as_float(row["potential_evapotranspiration_mm_month"]) for row in paired) < 180.0
    assert range_rejected == []
    assert len(source_rejected) == 8
    assert all("missing Q0.5" in str(item["reasons"]) for item in source_rejected)
    assert len({str(row["location_id"]) for row in paired}) == 56


def test_covariance_is_sample_covariance() -> None:
    records = [{"x": 1.0, "y": 2.0}, {"x": 2.0, "y": 4.0}, {"x": 3.0, "y": 6.0}]
    covariance = covariance_matrix(records, ("x", "y"))
    assert covariance == {"x": {"x": 1.0, "y": 2.0}, "y": {"x": 2.0, "y": 4.0}}


def test_generated_location_groups_are_isolated_and_cover_every_empirical_seed() -> None:
    manifest = _json("generated_population_manifest.json")
    leakage = cast(dict[str, object], manifest["location_group_leakage"])
    assert leakage["passed"] is True
    assert leakage["overlaps"] == {}
    assert manifest["empirical_location_count"] == 56
    assert manifest["field_count"] == 112


def test_validation_roles_metrics_and_source_forcing_improvement() -> None:
    diagnosis = _json("long_term_diagnosis.json")
    old = cast(dict[str, object], diagnosis["uncalibrated_phase95_benchmark"])
    corrected = cast(dict[str, object], diagnosis["uncalibrated_source_corrected_forcing"])
    old_metrics = cast(dict[str, float], old["aggregate_metrics"])
    corrected_metrics = cast(dict[str, float], corrected["aggregate_metrics"])
    assert corrected_metrics["rmse_t_c_ha"] < old_metrics["rmse_t_c_ha"]
    calibration = cast(dict[str, object], diagnosis["optional_calibration"])
    assert calibration["calibration_data"] == (
        "unfertilized and annual-FYM observations through 1965"
    )
    assert calibration["held_out_data"] == (
        "post-1965 temporal observations plus entire FYM-cessation treatment"
    )
    with (ARTIFACTS / "validation_trajectories.csv").open(encoding="utf-8", newline="") as handle:
        rows = tuple(csv.DictReader(handle))
    calibrated = [row for row in rows if row["run"] == "optional_calibrated"]
    assert all(
        row["evaluation_role"] == "held_out_treatment"
        for row in calibrated
        if row["treatment"] == "fym_1852_1871" and row["year"] != "1852"
    )
    assert all(row["residual_t_c_ha"] for row in rows)
    assert all(
        row["uncertainty_lower_t_c_ha"] and row["uncertainty_upper_t_c_ha"] for row in calibrated
    )


def test_effect_dataset_excludes_circular_targets_and_retains_accounting_metadata() -> None:
    with (ARTIFACTS / "effect_only_dataset.csv").open(encoding="utf-8", newline="") as handle:
        rows = tuple(csv.DictReader(handle))
    targets = {row["target_name"] for row in rows}
    assert targets == {
        "delta_yield_t_dm_ha",
        "delta_total_soc_t_c_ha",
        "delta_protected_soc_proxy_t_c_ha",
        "delta_respiration_t_c_ha",
    }
    assert not any(
        "final" in target or "cost" in target or "emissions" in target for target in targets
    )
    assert all(row["accounting_classification"] for row in rows)
    assert all("deterministic_cost_gbp_ha" in row for row in rows)
    assert all(row["policy_id"] not in {"baseline", "no_till"} for row in rows)


def test_downstream_selector_and_publication_gates_fail_closed() -> None:
    prediction = _json("prediction_gate_report.json")
    gates = cast(dict[str, bool], prediction["gates"])
    assert gates["independent_empirical_effect_validation"] is False
    assert prediction["downstream_selection_executed"] is False
    assert (ARTIFACTS / "DOWNSTREAM_BENCHMARK_STOP_DECISION.md").exists()
    readiness = _json("publication_readiness.json")
    assert readiness["passed"] is False
    blockers = cast(list[str], readiness["remaining_blockers"])
    assert "held_out_cessation_failure_resolved" in blockers
    assert "effect_prediction_gates_passed" in blockers
    assert "independent_empirical_effect_validation" in blockers
    assert readiness["manuscript_drafting_recommendation"] == (
        "do_not_start_Prism_manuscript_drafting"
    )


def test_source_and_artifact_hash_manifests_replay_offline() -> None:
    sources = _json("EMPIRICAL_SOURCE_MANIFEST.json")
    raw_files = cast(list[dict[str, object]], sources["raw_files"])
    assert len(raw_files) == 68
    for item in raw_files:
        path = ROOT / str(item["path"])
        assert hashlib.sha256(path.read_bytes()).hexdigest() == item["sha256"]
    historical_path = ARTIFACTS / "artifact_hashes.json"
    corrected_path = ROOT / "outputs/phase97_v0.9.7/corrected_phase96_artifact_hashes.json"
    manifest = cast(dict[str, object], json.loads(corrected_path.read_text(encoding="utf-8")))
    assert manifest["historical_manifest_modified"] is False
    assert (
        manifest["historical_manifest_sha256"]
        == hashlib.sha256(historical_path.read_bytes()).hexdigest()
    )
    changes = cast(list[dict[str, object]], manifest["changes_since_phase96_freeze"])
    assert any(item["path"] == "docs/AUDIT_soil_simulator_v0.9.0.md" for item in changes)
    files = cast(dict[str, str], manifest["files"])
    assert files
    phase98_corrections = cast(
        dict[str, object],
        json.loads(
            (ROOT / "manuscript/archive/v2/phase98_current_byte_corrections.json").read_text(
                encoding="utf-8"
            )
        ),
    )
    correction_rows = cast(
        list[dict[str, object]], phase98_corrections["changes_since_phase97_freeze"]
    )
    corrections = {str(item["path"]): str(item["current_sha256"]) for item in correction_rows}
    assert set(corrections) == {"README.md"}
    for relative, expected in files.items():
        if relative in corrections:
            current = hashlib.sha256((ARCHIVED_PRISM_BUNDLE / relative).read_bytes()).hexdigest()
            assert current == corrections[relative]
        elif relative == "pyproject.toml":
            continue  # licence and author metadata changed after the freeze (public readiness)
        else:
            current = hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()
            assert current == expected
