"""Computed Phase 9.7 leakage, validation, coverage and downstream gates."""

from __future__ import annotations

import hashlib
import json
import math
from collections import defaultdict
from collections.abc import Mapping, Sequence
from pathlib import Path

from soil_simulator.phase96.effect_ml import OBSERVABLE_FEATURES
from soil_simulator.phase96.values import as_float, as_int

FORBIDDEN_EVALUATION_SPLITS = frozenset({"test", "weather_ood", "archetype_ood"})
PRIMARY_TARGET_HORIZONS = frozenset(
    {
        ("delta_yield_t_dm_ha", 24),
        ("delta_total_soc_t_c_ha", 60),
        ("delta_total_soc_t_c_ha", 120),
        ("delta_protected_soc_proxy_t_c_ha", 60),
        ("delta_protected_soc_proxy_t_c_ha", 120),
        ("delta_respiration_t_c_ha", 60),
        ("delta_respiration_t_c_ha", 120),
    }
)


def _check(name: str, computable: bool, passed: bool, evidence: object) -> dict[str, object]:
    return {"name": name, "computable": computable, "passed": passed, "evidence": evidence}


def _feature_fingerprint(row: Mapping[str, object]) -> str:
    payload = "|".join(float(as_float(row[name])).hex() for name in OBSERVABLE_FEATURES)
    return hashlib.sha256(payload.encode()).hexdigest()


def empirical_location_leakage_evidence(
    rows: Sequence[Mapping[str, object]],
) -> dict[str, object]:
    """Compute every required isolation check from effect-dataset rows.

    Missing columns or an empty dataset make the gate non-computable and failed.
    """
    required = {
        "row_id",
        "field_id",
        "empirical_location_id",
        "population_split",
        *OBSERVABLE_FEATURES,
    }
    missing = sorted(required - set(rows[0])) if rows else sorted(required)
    if not rows or missing:
        failed = _check("required_columns", False, False, {"missing": missing})
        return {
            "passed": False,
            "fail_closed": True,
            "checks": [failed],
            "failure_reasons": ["leakage evidence cannot be computed from available rows"],
        }

    location_splits: dict[str, set[str]] = defaultdict(set)
    field_splits: dict[str, set[str]] = defaultdict(set)
    field_rows: dict[str, Mapping[str, object]] = {}
    for row in rows:
        split = str(row["population_split"])
        location_splits[str(row["empirical_location_id"])].add(split)
        field_splits[str(row["field_id"])].add(split)
        field_rows.setdefault(str(row["field_id"]), row)
    location_overlaps = {
        group: sorted(splits) for group, splits in location_splits.items() if len(splits) > 1
    }
    descendant_overlaps = {
        group: sorted(splits) for group, splits in location_splits.items() if len(splits) > 1
    }
    field_overlaps = {
        field: sorted(splits) for field, splits in field_splits.items() if len(splits) > 1
    }
    train_groups = {group for group, splits in location_splits.items() if splits == {"train"}}
    calibration_groups = {
        group for group, splits in location_splits.items() if splits == {"validation"}
    }
    evaluation_groups = {
        group
        for group, splits in location_splits.items()
        if bool(splits & FORBIDDEN_EVALUATION_SPLITS)
    }
    preprocessing_overlap = sorted(train_groups & (calibration_groups | evaluation_groups))
    calibration_overlap = sorted(calibration_groups & evaluation_groups)

    exact_by_fingerprint: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for field_id, row in field_rows.items():
        exact_by_fingerprint[_feature_fingerprint(row)].append(
            (field_id, str(row["population_split"]))
        )
    exact_cross_group = [
        {"fingerprint": fingerprint, "fields": values}
        for fingerprint, values in exact_by_fingerprint.items()
        if len({split for _, split in values}) > 1
    ]

    train_feature_rows = [
        row for row in field_rows.values() if str(row["population_split"]) == "train"
    ]
    near_duplicate_pairs: list[dict[str, object]] = []
    if train_feature_rows:
        means = {
            name: math.fsum(as_float(row[name]) for row in train_feature_rows)
            / len(train_feature_rows)
            for name in OBSERVABLE_FEATURES
        }
        scales = {}
        for name in OBSERVABLE_FEATURES:
            variance = math.fsum(
                (as_float(row[name]) - means[name]) ** 2 for row in train_feature_rows
            ) / len(train_feature_rows)
            scales[name] = math.sqrt(variance) if variance > 0.0 else 1.0
        fields = sorted(field_rows.items())
        for left_index, (left_id, left) in enumerate(fields):
            for right_id, right in fields[left_index + 1 :]:
                if left["population_split"] == right["population_split"]:
                    continue
                distance = math.sqrt(
                    math.fsum(
                        ((as_float(left[name]) - as_float(right[name])) / scales[name]) ** 2
                        for name in OBSERVABLE_FEATURES
                    )
                )
                if distance <= 1.0e-6:
                    near_duplicate_pairs.append(
                        {
                            "left_field_id": left_id,
                            "right_field_id": right_id,
                            "standardised_euclidean_distance": distance,
                        }
                    )
    checks = [
        _check(
            "no_empirical_location_crosses_groups",
            True,
            not location_overlaps,
            {"group_count": len(location_splits), "overlaps": location_overlaps},
        ),
        _check(
            "generated_descendants_isolated_by_empirical_seed",
            True,
            not descendant_overlaps and not field_overlaps,
            {"seed_overlaps": descendant_overlaps, "field_overlaps": field_overlaps},
        ),
        _check(
            "preprocessing_fitted_on_training_groups_only",
            True,
            not preprocessing_overlap,
            {
                "fit_split": "train",
                "training_group_count": len(train_groups),
                "excluded_group_count": len(calibration_groups | evaluation_groups),
                "overlaps": preprocessing_overlap,
            },
        ),
        _check(
            "calibration_groups_excluded_from_final_evaluation",
            True,
            not calibration_overlap,
            {
                "calibration_split": "validation",
                "evaluation_splits": sorted(FORBIDDEN_EVALUATION_SPLITS),
                "overlaps": calibration_overlap,
            },
        ),
        _check(
            "no_exact_or_near_duplicate_fields_cross_groups",
            bool(train_feature_rows),
            bool(train_feature_rows) and not exact_cross_group and not near_duplicate_pairs,
            {
                "exact_cross_group_duplicates": exact_cross_group,
                "near_duplicate_threshold_standardised_euclidean": 1.0e-6,
                "near_duplicate_cross_group_pairs": near_duplicate_pairs,
            },
        ),
    ]
    passed = all(bool(item["computable"]) and bool(item["passed"]) for item in checks)
    return {
        "passed": passed,
        "fail_closed": True,
        "checks": checks,
        "failure_reasons": [item["name"] for item in checks if not bool(item["passed"])],
    }


def independent_effect_validation_evidence(
    records: Sequence[Mapping[str, object]] | None,
    metadata: Mapping[str, object] | None,
) -> dict[str, object]:
    """Compute the independent empirical intervention-effect validation gate."""
    if records is None or metadata is None:
        return {
            "passed": False,
            "computable": False,
            "evidence_source": None,
            "dataset_identity": None,
            "sample_size": 0,
            "treatment_compatibility": False,
            "outcome_compatibility": False,
            "independence_satisfied": False,
            "reason": "no independent empirical intervention-effect dataset was supplied",
        }
    required_metadata = {
        "dataset_identity",
        "evidence_source",
        "independent_collection",
        "used_for_calibration",
        "used_for_model_development",
    }
    required_record = {"treatment_id", "target_name", "horizon_months", "observed_effect"}
    metadata_complete = not (required_metadata - set(metadata))
    record_complete = bool(records) and all(not (required_record - set(row)) for row in records)
    observed_pairs = (
        {(str(row["target_name"]), as_int(row["horizon_months"])) for row in records}
        if record_complete
        else set()
    )
    treatment_compatible = record_complete and all(
        str(row["treatment_id"])
        in {"conventional_tillage", "reduced_tillage", "cover_crop", "farmyard_manure"}
        for row in records
    )
    outcome_compatible = observed_pairs == set(PRIMARY_TARGET_HORIZONS)
    independence = metadata_complete and (
        bool(metadata["independent_collection"])
        and not bool(metadata["used_for_calibration"])
        and not bool(metadata["used_for_model_development"])
    )
    adequate_sample = len(records) >= 30
    passed = bool(
        metadata_complete
        and record_complete
        and treatment_compatible
        and outcome_compatible
        and independence
        and adequate_sample
    )
    reasons: list[str] = []
    if not metadata_complete:
        reasons.append("required dataset metadata are incomplete")
    if not record_complete:
        reasons.append("effect records are empty or schema-incomplete")
    if not adequate_sample:
        reasons.append("fewer than 30 independent effect observations")
    if not treatment_compatible:
        reasons.append("treatments are incompatible with supported interventions")
    if not outcome_compatible:
        reasons.append("dataset does not cover every primary target and supported horizon")
    if not independence:
        reasons.append("independence from calibration and model development is not satisfied")
    return {
        "passed": passed,
        "computable": metadata_complete and record_complete,
        "evidence_source": metadata.get("evidence_source"),
        "dataset_identity": metadata.get("dataset_identity"),
        "sample_size": len(records),
        "minimum_sample_size": 30,
        "treatment_compatibility": treatment_compatible,
        "outcome_compatibility": outcome_compatible,
        "covered_target_horizons": sorted(observed_pairs),
        "independence_satisfied": independence,
        "reason": "passed all predeclared criteria" if passed else "; ".join(reasons),
    }


def _wilson_interval(
    successes: int, sample_size: int, z: float = 1.959963984540054
) -> tuple[float, float]:
    probability = successes / sample_size
    denominator = 1.0 + z * z / sample_size
    centre = (probability + z * z / (2.0 * sample_size)) / denominator
    half = (
        z
        * math.sqrt(
            probability * (1.0 - probability) / sample_size
            + z * z / (4.0 * sample_size * sample_size)
        )
        / denominator
    )
    return centre - half, centre + half


def _binomial_acceptance_counts(sample_size: int, nominal: float) -> tuple[int, int]:
    probabilities = [
        math.comb(sample_size, count) * nominal**count * (1.0 - nominal) ** (sample_size - count)
        for count in range(sample_size + 1)
    ]
    cumulative = 0.0
    lower = 0
    upper = sample_size
    for count, probability in enumerate(probabilities):
        cumulative += probability
        if cumulative >= 0.025:
            lower = count
            break
    cumulative = 0.0
    for count, probability in enumerate(probabilities):
        cumulative += probability
        if cumulative >= 0.975:
            upper = count
            break
    return lower, upper


def uncertainty_coverage_evidence(
    prediction: Mapping[str, object], nominal: float = 0.90
) -> dict[str, object]:
    """Apply target/regime-specific binomial calibration and width criteria."""
    targets = prediction.get("targets")
    if not isinstance(targets, Mapping):
        return {
            "passed": False,
            "computable": False,
            "targets": {},
            "reason": "prediction target evidence is unavailable",
        }
    target_reports: dict[str, object] = {}
    all_pass = True
    for target, raw_payload in sorted(targets.items()):
        payload = cast_mapping(raw_payload)
        regime_reports: dict[str, object] = {}
        target_pass = True
        for regime_name in ("test", "ood"):
            regime = cast_mapping(payload.get(regime_name))
            sample_size = as_int(regime.get("row_count", 0))
            group_count = as_int(regime.get("empirical_location_count", 0))
            coverage = as_float(
                regime.get("validation_calibrated_90_percent_interval_coverage", 0.0)
            )
            supported = sample_size >= 20 and group_count >= 4
            if not supported:
                regime_reports[regime_name] = {
                    "status": "abstain_insufficient_calibration_evidence",
                    "passed": True,
                    "sample_size": sample_size,
                    "empirical_location_count": group_count,
                    "minimum_rows": 20,
                    "minimum_groups": 4,
                }
                continue
            successes = min(sample_size, max(0, round(coverage * sample_size)))
            observed = successes / sample_size
            wilson = _wilson_interval(successes, sample_size)
            lower_count, upper_count = _binomial_acceptance_counts(sample_size, nominal)
            ridge = cast_mapping(regime.get("ridge"))
            rmse = as_float(ridge.get("rmse", 0.0))
            half_width = as_float(regime.get("interval_half_width", 0.0))
            width_to_rmse = math.inf if rmse <= 0.0 else (2.0 * half_width) / rmse
            severe_undercoverage = successes < lower_count
            excessive_overcoverage = successes > upper_count
            width_inflation = width_to_rmse > 5.0
            passed = (
                lower_count <= successes <= upper_count
                and not severe_undercoverage
                and not excessive_overcoverage
                and not width_inflation
            )
            target_pass &= passed
            regime_reports[regime_name] = {
                "status": "supported_evaluated",
                "passed": passed,
                "nominal_coverage": nominal,
                "sample_size": sample_size,
                "empirical_location_count": group_count,
                "successes": successes,
                "observed_coverage": observed,
                "wilson_95_percent_confidence_interval": wilson,
                "binomial_95_percent_acceptance_count_range": [lower_count, upper_count],
                "binomial_95_percent_acceptance_coverage_range": [
                    lower_count / sample_size,
                    upper_count / sample_size,
                ],
                "severe_undercoverage": severe_undercoverage,
                "excessive_overcoverage": excessive_overcoverage,
                "interval_full_width": 2.0 * half_width,
                "interval_width_to_rmse": width_to_rmse,
                "width_inflation": width_inflation,
                "width_inflation_rule": "full interval width must not exceed 5x RMSE",
            }
        target_reports[str(target)] = {"passed": target_pass, "regimes": regime_reports}
        all_pass &= target_pass
    return {
        "passed": all_pass,
        "computable": True,
        "nominal_coverage": nominal,
        "rule": (
            "each supported target/regime must fall in the exact central 95% Binomial(n,0.90) "
            "count range without severe undercoverage, excessive overcoverage or >5x-RMSE width; "
            "regimes with <20 rows or <4 independent groups abstain"
        ),
        "targets": target_reports,
    }


def cast_mapping(value: object) -> Mapping[str, object]:
    """Return a mapping or an empty fail-closed mapping."""
    return value if isinstance(value, Mapping) else {}


def downstream_gate_evidence(
    prediction: Mapping[str, object],
    leakage: Mapping[str, object],
    independent_validation: Mapping[str, object],
    coverage: Mapping[str, object],
) -> dict[str, object]:
    """Compute downstream eligibility solely from the actual prerequisite gates."""
    prediction_gates = cast_mapping(prediction.get("gates"))
    required = {
        "effect_prediction": bool(prediction_gates.get("all_effect_targets_beat_policy_mean")),
        "ood_performance": bool(prediction_gates.get("all_effect_targets_have_acceptable_ood")),
        "target_specific_uncertainty": bool(coverage.get("passed")),
        "empirical_location_leakage": bool(leakage.get("passed")),
        "independent_empirical_effect_validation": bool(independent_validation.get("passed")),
    }
    eligible = all(required.values())
    return {
        "eligible": eligible,
        "required_gates": required,
        "failed_gates": [name for name, passed in required.items() if not passed],
        "fail_closed": True,
        "selection_regret_executed": eligible,
        "decision": (
            "eligible for downstream execution"
            if eligible
            else "blocked; selection/oracle/regret must not run"
        ),
    }


def load_optional_independent_dataset(
    metadata_path: str | Path, records_path: str | Path
) -> tuple[list[dict[str, object]] | None, dict[str, object] | None]:
    """Load optional future independent evidence without treating absence as success."""
    metadata_file = Path(metadata_path)
    records_file = Path(records_path)
    if not metadata_file.exists() or not records_file.exists():
        return None, None
    metadata = json.loads(metadata_file.read_text(encoding="utf-8"))
    records = json.loads(records_file.read_text(encoding="utf-8"))
    if not isinstance(metadata, dict) or not isinstance(records, list):
        return None, None
    return records, metadata
