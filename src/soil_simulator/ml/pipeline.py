"""Phase 8.5 leakage-resistant intervention-outcome diagnostic pipeline."""

from __future__ import annotations

import hashlib
import json
import math
import random
import time
from dataclasses import dataclass, replace
from pathlib import Path
from typing import cast

from soil_simulator.domain.enums import PopulationSplit
from soil_simulator.ml.dataset import write_dataset_manifest, write_ml_dataset
from soil_simulator.ml.evaluation import (
    fit_group_conformal_half_widths,
    grouped_interval_diagnostics,
    interval_diagnostics,
    pearson_correlation,
    policy_vector,
    regression_metrics,
    residual_diagnostics,
    target_matrix,
)
from soil_simulator.ml.models import (
    MultiTargetModel,
    PerPolicyModel,
    RandomForestModel,
    RidgeModel,
    fit_global_mean,
    fit_per_policy,
    fit_policy_mean,
    fit_random_forest,
    fit_ridge,
    model_from_dict,
)
from soil_simulator.ml.preprocessing import (
    FittedPreprocessor,
    fit_preprocessor,
    preprocessor_from_dict,
)
from soil_simulator.ml.schema import (
    CLAIM_BOUNDARY,
    DATASET_VERSION,
    FEATURE_SETS,
    FULL_STATE_EXTRA_NUMERIC_FEATURES,
    HORIZON_TARGET_APPLICABILITY,
    TARGETS,
    MlDatasetManifest,
    MlRow,
    Phase8BenchmarkConfig,
)

PRIMARY_SELECTION_TASKS = (
    "delta_crop_yield_t_dm_ha@24",
    "delta_final_total_soc_t_c_ha@60",
    "delta_final_total_soc_t_c_ha@120",
    "delta_final_protected_soc_proxy_t_c_ha@60",
    "delta_final_protected_soc_proxy_t_c_ha@120",
)


@dataclass(frozen=True)
class _TaskRuntime:
    target: str
    horizon: int
    observable_primary: MultiTargetModel
    full_primary: MultiTargetModel
    test_rows: tuple[MlRow, ...]
    test_actual: tuple[tuple[float, ...], ...]
    observable_prediction: tuple[tuple[float, ...], ...]
    full_prediction: tuple[tuple[float, ...], ...]
    observable_preprocessor: FittedPreprocessor
    full_preprocessor: FittedPreprocessor


def _json_write(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, allow_nan=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _save_preprocessor(path: Path, value: FittedPreprocessor) -> FittedPreprocessor:
    _json_write(path, value.model_dump())
    return preprocessor_from_dict(json.loads(path.read_text(encoding="utf-8")))


def _save_model(path: Path, value: MultiTargetModel) -> MultiTargetModel:
    _json_write(path, value.model_dump())
    return model_from_dict(json.loads(path.read_text(encoding="utf-8")))


def _matrix(
    rows: tuple[MlRow, ...], preprocessor: FittedPreprocessor
) -> tuple[tuple[float, ...], ...]:
    return tuple(preprocessor.transform(row) for row in rows)


def _task_rows(
    rows: tuple[MlRow, ...], target: str, horizon: int, split: PopulationSplit
) -> tuple[MlRow, ...]:
    if horizon not in HORIZON_TARGET_APPLICABILITY[target]:
        raise ValueError(f"target {target} is not valid at horizon {horizon}")
    return tuple(
        row
        for row in rows
        if row.population_split is split and row.simulation_horizon_months == horizon
    )


def _score(
    actual: tuple[tuple[float, ...], ...],
    predicted: tuple[tuple[float, ...], ...],
    target: str,
) -> float:
    values = regression_metrics(actual, predicted, (target,))[target]
    variation = cast(float, values["natural_field_to_field_sd"])
    rmse = cast(float, values["rmse"])
    return rmse / variation if variation > 0.0 else rmse


def _metrics(
    actual: tuple[tuple[float, ...], ...],
    predicted: tuple[tuple[float, ...], ...],
    target: str,
) -> dict[str, float | None]:
    return regression_metrics(actual, predicted, (target,))[target]


def _fit_per_policy_ridge(
    matrix: tuple[tuple[float, ...], ...],
    targets: tuple[tuple[float, ...], ...],
    policies: tuple[str, ...],
    target: str,
    feature_names: tuple[str, ...],
    alpha: float,
) -> PerPolicyModel:
    return fit_per_policy(
        matrix,
        targets,
        policies,
        lambda policy_matrix, policy_targets, _policy: fit_ridge(
            policy_matrix, policy_targets, (target,), feature_names, alpha
        ),
    )


def _fit_per_policy_forest(
    matrix: tuple[tuple[float, ...], ...],
    targets: tuple[tuple[float, ...], ...],
    policies: tuple[str, ...],
    target: str,
    feature_names: tuple[str, ...],
    *,
    tree_count: int,
    max_depth: int,
    min_leaf: int,
    feature_fraction: float,
    random_seed: int,
) -> PerPolicyModel:
    def fit_one(
        policy_matrix: tuple[tuple[float, ...], ...],
        policy_targets: tuple[tuple[float, ...], ...],
        policy: str,
    ) -> MultiTargetModel:
        policy_offset = int.from_bytes(hashlib.sha256(policy.encode()).digest()[:4], "big")
        return fit_random_forest(
            policy_matrix,
            policy_targets,
            (target,),
            feature_names,
            tree_count=tree_count,
            max_depth=max_depth,
            min_leaf=min_leaf,
            feature_fraction=feature_fraction,
            random_seed=random_seed + policy_offset,
        )

    return fit_per_policy(matrix, targets, policies, fit_one)


def _tune_models(
    train_rows: tuple[MlRow, ...],
    validation_rows: tuple[MlRow, ...],
    target: str,
    preprocessor: FittedPreprocessor,
    config: Phase8BenchmarkConfig,
    *,
    include_per_policy: bool,
    seed_offset: int,
) -> tuple[dict[str, MultiTargetModel], list[dict[str, object]]]:
    train_matrix = _matrix(train_rows, preprocessor)
    validation_matrix = _matrix(validation_rows, preprocessor)
    train_targets = target_matrix(train_rows, (target,))
    validation_targets = target_matrix(validation_rows, (target,))
    train_policies = policy_vector(train_rows)
    validation_policies = policy_vector(validation_rows)
    selected: dict[str, MultiTargetModel] = {
        "global_mean": fit_global_mean(train_targets, (target,)),
        "policy_mean": fit_policy_mean(train_targets, train_policies, (target,)),
    }
    tuning: list[dict[str, object]] = []
    ridge_candidates: list[tuple[float, RidgeModel]] = []
    per_policy_ridge_candidates: list[tuple[float, PerPolicyModel]] = []
    for alpha in config.ridge_alphas:
        ridge = fit_ridge(
            train_matrix, train_targets, (target,), preprocessor.output_feature_names, alpha
        )
        score = _score(
            validation_targets,
            ridge.predict(validation_matrix, validation_policies),
            target,
        )
        ridge_candidates.append((score, ridge))
        tuning.append({"model": "pooled_ridge", "alpha": alpha, "validation_score": score})
        if include_per_policy:
            separate = _fit_per_policy_ridge(
                train_matrix,
                train_targets,
                train_policies,
                target,
                preprocessor.output_feature_names,
                alpha,
            )
            separate_score = _score(
                validation_targets,
                separate.predict(validation_matrix, validation_policies),
                target,
            )
            per_policy_ridge_candidates.append((separate_score, separate))
            tuning.append(
                {
                    "model": "per_policy_ridge",
                    "alpha": alpha,
                    "validation_score": separate_score,
                }
            )
    selected["pooled_ridge"] = min(ridge_candidates, key=lambda item: item[0])[1]
    if per_policy_ridge_candidates:
        selected["per_policy_ridge"] = min(per_policy_ridge_candidates, key=lambda item: item[0])[1]
    forest_candidates: list[tuple[float, RandomForestModel]] = []
    per_policy_forest_candidates: list[tuple[float, PerPolicyModel]] = []
    candidate_index = 0
    for tree_count in config.forest_tree_counts:
        for max_depth in config.forest_max_depths:
            candidate_seed = config.random_seed + seed_offset + candidate_index
            forest = fit_random_forest(
                train_matrix,
                train_targets,
                (target,),
                preprocessor.output_feature_names,
                tree_count=tree_count,
                max_depth=max_depth,
                min_leaf=config.forest_min_leaf,
                feature_fraction=config.forest_feature_fraction,
                random_seed=candidate_seed,
            )
            score = _score(
                validation_targets,
                forest.predict(validation_matrix, validation_policies),
                target,
            )
            forest_candidates.append((score, forest))
            tuning.append(
                {
                    "model": "pooled_forest",
                    "tree_count": tree_count,
                    "max_depth": max_depth,
                    "validation_score": score,
                }
            )
            if include_per_policy:
                separate_forest = _fit_per_policy_forest(
                    train_matrix,
                    train_targets,
                    train_policies,
                    target,
                    preprocessor.output_feature_names,
                    tree_count=tree_count,
                    max_depth=max_depth,
                    min_leaf=config.forest_min_leaf,
                    feature_fraction=config.forest_feature_fraction,
                    random_seed=candidate_seed,
                )
                separate_score = _score(
                    validation_targets,
                    separate_forest.predict(validation_matrix, validation_policies),
                    target,
                )
                per_policy_forest_candidates.append((separate_score, separate_forest))
                tuning.append(
                    {
                        "model": "per_policy_forest",
                        "tree_count": tree_count,
                        "max_depth": max_depth,
                        "validation_score": separate_score,
                    }
                )
            candidate_index += 1
    selected["pooled_forest"] = min(forest_candidates, key=lambda item: item[0])[1]
    if per_policy_forest_candidates:
        selected["per_policy_forest"] = min(per_policy_forest_candidates, key=lambda item: item[0])[
            1
        ]
    return selected, tuning


def _validation_score(
    model: MultiTargetModel,
    rows: tuple[MlRow, ...],
    target: str,
    preprocessor: FittedPreprocessor,
) -> float:
    return _score(
        target_matrix(rows, (target,)),
        model.predict(_matrix(rows, preprocessor), policy_vector(rows)),
        target,
    )


def _group_metrics(
    rows: tuple[MlRow, ...],
    actual: tuple[tuple[float, ...], ...],
    predicted: tuple[tuple[float, ...], ...],
    target: str,
    attribute: str,
) -> dict[str, dict[str, float | None]]:
    groups: dict[str, list[int]] = {}
    for index, row in enumerate(rows):
        groups.setdefault(str(getattr(row, attribute)), []).append(index)
    return {
        group: _metrics(
            tuple(actual[index] for index in indices),
            tuple(predicted[index] for index in indices),
            target,
        )
        for group, indices in sorted(groups.items())
    }


def _importance(model: MultiTargetModel) -> dict[str, float]:
    if isinstance(model, PerPolicyModel):
        child = [_importance(value) for value in model.policy_models.values()]
        child_names = sorted({name for values in child for name in values})
        return {
            name: math.fsum(values.get(name, 0.0) for values in child) / len(child)
            for name in child_names
        }
    if isinstance(model, RandomForestModel):
        names = model.feature_names
        values = model.feature_importances
    elif isinstance(model, RidgeModel):
        names = model.feature_names
        values = tuple(abs(value) for value in model.coefficients[0][1:])
    else:
        return {}
    aggregated: dict[str, float] = {}
    for name, value in zip(names, values, strict=True):
        base = name.split("=", maxsplit=1)[0]
        aggregated[base] = aggregated.get(base, 0.0) + value
    total = math.fsum(aggregated.values())
    if total > 0.0:
        aggregated = {name: value / total for name, value in aggregated.items()}
    return dict(sorted(aggregated.items(), key=lambda item: (-item[1], item[0])))


def _hidden_residual_correlations(
    rows: tuple[MlRow, ...],
    actual: tuple[tuple[float, ...], ...],
    predicted: tuple[tuple[float, ...], ...],
) -> dict[str, float | None]:
    residuals = [pred[0] - obs[0] for pred, obs in zip(predicted, actual, strict=True)]
    result: dict[str, float | None] = {}
    for name in FULL_STATE_EXTRA_NUMERIC_FEATURES:
        values = [float(row.features[name]) for row in rows]
        try:
            result[name] = pearson_correlation(values, residuals)
        except ValueError:
            result[name] = None
    return dict(
        sorted(
            result.items(),
            key=lambda item: (
                -(abs(item[1]) if isinstance(item[1], float) else -1.0),
                item[0],
            ),
        )
    )


def _leakage_audit(rows: tuple[MlRow, ...]) -> dict[str, object]:
    groups: dict[str, set[str]] = {}
    fields: dict[str, set[str]] = {}
    for row in rows:
        groups.setdefault(row.empirical_seed_id, set()).add(row.population_split.value)
        fields.setdefault(row.field_id, set()).add(row.population_split.value)
    crossing_groups = sorted(group for group, splits in groups.items() if len(splits) > 1)
    crossing_fields = sorted(field for field, splits in fields.items() if len(splits) > 1)
    final_splits = {
        PopulationSplit.TEST,
        PopulationSplit.ARCHETYPE_OOD,
        PopulationSplit.WEATHER_OOD,
    }
    development_groups = {
        row.empirical_seed_id
        for row in rows
        if row.population_split in {PopulationSplit.TRAIN, PopulationSplit.VALIDATION}
    }
    final_groups = {row.empirical_seed_id for row in rows if row.population_split in final_splits}
    passed = not crossing_groups and not crossing_fields and not development_groups & final_groups
    return {
        "passed": passed,
        "crossing_empirical_seed_groups": crossing_groups,
        "crossing_fields": crossing_fields,
        "development_final_group_overlap": sorted(development_groups & final_groups),
        "preprocessing_fit_partition": "train only",
        "calibration_partition": "validation empirical-seed groups only",
        "final_test_partitions_used_for_tuning": False,
    }


def _evaluate_ood(
    rows: tuple[MlRow, ...],
    target: str,
    horizon: int,
    model: MultiTargetModel,
    preprocessor: FittedPreprocessor,
) -> dict[str, object]:
    result: dict[str, object] = {}
    for split in (PopulationSplit.ARCHETYPE_OOD, PopulationSplit.WEATHER_OOD):
        held = _task_rows(rows, target, horizon, split)
        if not held:
            result[split.value] = {"row_count": 0, "metrics": None}
            continue
        actual = target_matrix(held, (target,))
        predicted = model.predict(_matrix(held, preprocessor), policy_vector(held))
        result[split.value] = {
            "row_count": len(held),
            "empirical_seed_groups": sorted({row.empirical_seed_id for row in held}),
            "metrics": _metrics(actual, predicted, target),
            "by_archetype": _group_metrics(held, actual, predicted, target, "archetype"),
            "by_weather_regime": _group_metrics(held, actual, predicted, target, "weather_regime"),
        }
    return result


def _run_task(
    rows: tuple[MlRow, ...],
    target: str,
    horizon: int,
    observable_preprocessor: FittedPreprocessor,
    full_preprocessor: FittedPreprocessor,
    config: Phase8BenchmarkConfig,
    models_dir: Path,
    task_index: int,
) -> tuple[dict[str, object], _TaskRuntime, dict[str, str]]:
    train = _task_rows(rows, target, horizon, PopulationSplit.TRAIN)
    validation = _task_rows(rows, target, horizon, PopulationSplit.VALIDATION)
    test = _task_rows(rows, target, horizon, PopulationSplit.TEST)
    if not train or not validation or not test:
        raise ValueError(f"task {target}@{horizon} lacks train, validation, or final-test rows")
    observable_models, observable_tuning = _tune_models(
        train,
        validation,
        target,
        observable_preprocessor,
        config,
        include_per_policy=True,
        seed_offset=task_index * 100,
    )
    full_models, full_tuning = _tune_models(
        train,
        validation,
        target,
        full_preprocessor,
        config,
        include_per_policy=False,
        seed_offset=50_000 + task_index * 100,
    )
    nonlinear_names = ("pooled_forest", "per_policy_forest")
    observable_primary_name = min(
        nonlinear_names,
        key=lambda name: _validation_score(
            observable_models[name], validation, target, observable_preprocessor
        ),
    )
    full_primary_name = min(
        ("pooled_ridge", "pooled_forest"),
        key=lambda name: _validation_score(
            full_models[name], validation, target, full_preprocessor
        ),
    )
    task_key = f"{target}@{horizon}"
    saved: dict[str, MultiTargetModel] = {}
    hashes: dict[str, str] = {}
    save_names = {
        "global_mean": observable_models["global_mean"],
        "policy_mean": observable_models["policy_mean"],
        "pooled_ridge": observable_models["pooled_ridge"],
        "per_policy_ridge": observable_models["per_policy_ridge"],
        "pooled_forest": observable_models["pooled_forest"],
        "per_policy_forest": observable_models["per_policy_forest"],
        "full_state_primary": full_models[full_primary_name],
    }
    task_dir = models_dir / task_key.replace("@", "__h")
    for name, model in save_names.items():
        saved[name] = _save_model(task_dir / f"{name}.json", model)
        hashes[f"{task_key}/{name}"] = saved[name].stable_hash()
    observable_primary = saved[observable_primary_name]
    full_primary = saved["full_state_primary"]
    test_actual = target_matrix(test, (target,))
    test_predictions = {
        name: model.predict(_matrix(test, observable_preprocessor), policy_vector(test))
        for name, model in saved.items()
        if name != "full_state_primary"
    }
    full_prediction = full_primary.predict(_matrix(test, full_preprocessor), policy_vector(test))
    validation_prediction = observable_primary.predict(
        _matrix(validation, observable_preprocessor), policy_vector(validation)
    )
    widths, calibration = fit_group_conformal_half_widths(
        validation,
        target_matrix(validation, (target,)),
        validation_prediction,
        config.conformal_alpha,
        config.minimum_calibration_groups,
        (target,),
    )
    uncertainty = interval_diagnostics(
        test_actual, test_predictions[observable_primary_name], widths, (target,)
    )[target]
    grouped_uncertainty = {
        "by_empirical_seed": grouped_interval_diagnostics(
            test,
            test_actual,
            test_predictions[observable_primary_name],
            widths,
            lambda row: row.empirical_seed_id,
            config.minimum_subgroup_interval_rows,
            (target,),
        ),
        "by_archetype": grouped_interval_diagnostics(
            test,
            test_actual,
            test_predictions[observable_primary_name],
            widths,
            lambda row: row.archetype,
            config.minimum_subgroup_interval_rows,
            (target,),
        ),
    }
    primary_prediction = test_predictions[observable_primary_name]
    observable_metrics = _metrics(test_actual, primary_prediction, target)
    full_metrics = _metrics(test_actual, full_prediction, target)
    observable_mae = cast(float, observable_metrics["mae"])
    full_mae = cast(float, full_metrics["mae"])
    report = {
        "target": target,
        "horizon_months": horizon,
        "prediction_mode": "paired_intervention_minus_baseline"
        if target.startswith("delta_")
        else "direct_final_outcome",
        "observable_primary_model": observable_primary_name,
        "observable_primary_selection_rule": (
            "lower validation-group normalised RMSE among pooled and separate-policy forests; "
            "complexity itself is never a selection criterion"
        ),
        "full_state_diagnostic_model": full_primary_name,
        "tuning": {
            "observable": observable_tuning,
            "full_state": full_tuning,
            "final_test_or_ood_used": False,
        },
        "final_test_metrics": {
            name: _metrics(test_actual, prediction, target)
            for name, prediction in test_predictions.items()
        }
        | {"full_state_primary": full_metrics},
        "pooled_vs_separate_policy": {
            name: _metrics(test_actual, test_predictions[name], target)
            for name in ("pooled_ridge", "per_policy_ridge", "pooled_forest", "per_policy_forest")
        },
        "policy_errors": _group_metrics(test, test_actual, primary_prediction, target, "policy_id"),
        "subgroup_errors": {
            "archetype": _group_metrics(test, test_actual, primary_prediction, target, "archetype"),
            "weather_regime": _group_metrics(
                test, test_actual, primary_prediction, target, "weather_regime"
            ),
            "phosphorus_status": _group_metrics(
                test, test_actual, primary_prediction, target, "phosphorus_status"
            ),
            "empirical_seed": _group_metrics(
                test, test_actual, primary_prediction, target, "empirical_seed_id"
            ),
        },
        "residual_diagnostics": residual_diagnostics(test_actual, primary_prediction, (target,))[
            target
        ],
        "feature_importance": _importance(observable_primary),
        "uncertainty": {
            "method": "validation-empirical-seed-group conformal absolute residual",
            "nominal_coverage": 1.0 - config.conformal_alpha,
            "half_width": widths[target],
            "final_test": uncertainty,
            "calibration": calibration,
            "subgroups": grouped_uncertainty,
        },
        "out_of_distribution": _evaluate_ood(
            rows, target, horizon, observable_primary, observable_preprocessor
        ),
        "hidden_state_gap": {
            "observable_mae": observable_mae,
            "full_state_mae": full_mae,
            "mae_reduction_fraction_from_hidden_state": (
                None if observable_mae <= 0.0 else (observable_mae - full_mae) / observable_mae
            ),
        },
        "residual_correlation_with_hidden_state": _hidden_residual_correlations(
            test, test_actual, primary_prediction
        ),
    }
    runtime = _TaskRuntime(
        target=target,
        horizon=horizon,
        observable_primary=observable_primary,
        full_primary=full_primary,
        test_rows=test,
        test_actual=test_actual,
        observable_prediction=primary_prediction,
        full_prediction=full_prediction,
        observable_preprocessor=observable_preprocessor,
        full_preprocessor=full_preprocessor,
    )
    return report, runtime, hashes


def _correlation_audit(
    rows: tuple[MlRow, ...], runtimes: dict[str, _TaskRuntime], random_seed: int
) -> dict[str, object]:
    first_by_field: dict[str, MlRow] = {}
    for row in rows:
        first_by_field.setdefault(row.field_id, row)
    field_rows = tuple(first_by_field[field] for field in sorted(first_by_field))
    pairs = {
        "clay_soc": ("clay_percent", "baseline_soc_t_c_ha"),
        "soc_bulk_density": ("baseline_soc_t_c_ha", "bulk_density_g_cm3"),
        "available_p_amf": ("initial_available_phosphorus_kg_p_ha", "initial_amf_live_c_t_ha"),
    }
    report: dict[str, object] = {}
    for pair_index, (label, (left, right)) in enumerate(pairs.items()):
        report[label] = {
            "features": [left, right],
            "population_correlation": pearson_correlation(
                [float(row.features[left]) for row in field_rows],
                [float(row.features[right]) for row in field_rows],
            ),
            "engineered_assumption": True,
        }
        degradations: dict[str, float | None] = {}
        for task_key in PRIMARY_SELECTION_TASKS:
            runtime = runtimes[task_key]
            shuffled_values = [float(row.features[right]) for row in runtime.test_rows]
            random.Random(random_seed + pair_index).shuffle(shuffled_values)
            disrupted = tuple(
                replace(row, features={**row.features, right: shuffled_values[index]})
                for index, row in enumerate(runtime.test_rows)
            )
            use_full = label == "available_p_amf"
            model = runtime.full_primary if use_full else runtime.observable_primary
            preprocessor = (
                runtime.full_preprocessor if use_full else runtime.observable_preprocessor
            )
            baseline_prediction = (
                runtime.full_prediction if use_full else runtime.observable_prediction
            )
            baseline = _score(runtime.test_actual, baseline_prediction, runtime.target)
            stressed = _score(
                runtime.test_actual,
                model.predict(_matrix(disrupted, preprocessor), policy_vector(disrupted)),
                runtime.target,
            )
            degradations[task_key] = None if baseline <= 0.0 else (stressed - baseline) / baseline
        cast(dict[str, object], report[label])["primary_task_performance_degradation"] = (
            degradations
        )
    return report


def calculate_success_gates(
    task_reports: dict[str, dict[str, object]],
    leakage_audit: dict[str, object],
    config: Phase8BenchmarkConfig,
) -> dict[str, object]:
    """Calculate predeclared Phase 9 gates without selecting on test R-squared."""
    primary_ratios: list[float] = []
    policy_ratios: list[float] = []
    ridge_ratios: list[float] = []
    uncertainty_passes: list[bool] = []
    ood_ratios: dict[str, list[float]] = {"archetype_ood": [], "weather_ood": []}
    for task_key in PRIMARY_SELECTION_TASKS:
        task = task_reports[task_key]
        metrics = cast(dict[str, dict[str, float | None]], task["final_test_metrics"])
        primary_name = cast(str, task["observable_primary_model"])
        for destination, model_name in (
            (primary_ratios, primary_name),
            (policy_ratios, "policy_mean"),
        ):
            item = metrics[model_name]
            variation = cast(float, item["natural_field_to_field_sd"])
            destination.append(
                cast(float, item["mae"]) / variation if variation > 0.0 else math.inf
            )
        ridge_candidates: list[float] = []
        for model_name in ("pooled_ridge", "per_policy_ridge"):
            item = metrics[model_name]
            variation = cast(float, item["natural_field_to_field_sd"])
            ridge_candidates.append(
                cast(float, item["mae"]) / variation if variation > 0.0 else math.inf
            )
        ridge_ratios.append(min(ridge_candidates))
        uncertainty = cast(dict[str, object], task["uncertainty"])
        final_interval = cast(dict[str, float], uncertainty["final_test"])
        calibration = cast(dict[str, object], uncertainty["calibration"])
        uncertainty_passes.append(
            bool(calibration["calibration_claim_supported"])
            and abs(final_interval["coverage"] - (1.0 - config.conformal_alpha))
            <= config.coverage_tolerance
        )
        ood = cast(dict[str, object], task["out_of_distribution"])
        for split in ood_ratios:
            split_result = cast(dict[str, object], ood[split])
            split_metrics = cast(dict[str, float | None] | None, split_result["metrics"])
            if split_metrics is not None:
                variation = cast(float, split_metrics["natural_field_to_field_sd"])
                if variation > 0.0:
                    ood_ratios[split].append(cast(float, split_metrics["mae"]) / variation)
    primary_mean = math.fsum(primary_ratios) / len(primary_ratios)
    policy_mean = math.fsum(policy_ratios) / len(policy_ratios)
    ridge_mean = math.fsum(ridge_ratios) / len(ridge_ratios)
    ood_means: dict[str, float | None] = {
        split: (math.fsum(values) / len(values) if values else None)
        for split, values in ood_ratios.items()
    }
    gates = {
        "no_final_test_leakage": bool(leakage_audit["passed"]),
        "group_aware_uncertainty_close_to_nominal_for_primary_targets": all(uncertainty_passes),
        "primary_ml_outperforms_policy_mean_on_effects": primary_mean < policy_mean,
        "primary_ml_outperforms_regularised_linear_on_effects": primary_mean < ridge_mean,
        "acceptable_on_at_least_one_untouched_ood_holdout": any(
            value is not None and value <= config.acceptable_ood_mae_sd_ratio
            for value in ood_means.values()
        ),
        "selection_not_based_only_on_in_distribution_r_squared": True,
    }
    passed = all(gates.values())
    return {
        "passed": passed,
        "gates": gates,
        "aggregate_primary_effect_mae_over_sd": primary_mean,
        "aggregate_policy_mean_effect_mae_over_sd": policy_mean,
        "aggregate_best_regularised_linear_effect_mae_over_sd": ridge_mean,
        "ood_primary_effect_mae_over_sd": ood_means,
        "recommendation": (
            "Phase 9 intervention-selection experiments may be scoped, while retaining the "
            "synthetic non-causal boundary."
            if passed
            else "Do not build an ML intervention selector yet; improve population support, "
            "calibration, and OOD effect prediction first."
        ),
    }


def _benchmark_table(report: dict[str, object]) -> str:
    tasks = cast(dict[str, dict[str, object]], report["tasks"])
    lines = [
        "Phase 8.5 synthetic intervention-outcome diagnostics (non-causal; no selection)",
        "Task                                                        Model                "
        "MAE      MAE/SD       R2  Coverage",
    ]
    for task_key in PRIMARY_SELECTION_TASKS:
        task = tasks[task_key]
        model = cast(str, task["observable_primary_model"])
        metrics = cast(dict[str, dict[str, float | None]], task["final_test_metrics"])[model]
        uncertainty = cast(dict[str, object], task["uncertainty"])
        interval = cast(dict[str, float], uncertainty["final_test"])
        r_squared = metrics["r_squared"]
        relative = metrics["mae_relative_to_natural_variation"]
        lines.append(
            f"{task_key:<59} {model:<19} {cast(float, metrics['mae']):>8.4g} "
            f"{('n/a' if relative is None else f'{relative:.3f}'):>11} "
            f"{('n/a' if r_squared is None else f'{r_squared:.3f}'):>8} "
            f"{interval['coverage']:>9.3f}"
        )
    gates = cast(dict[str, object], report["phase9_success_gates"])
    lines.extend(
        ["", f"Phase 9 gates passed: {gates['passed']}", cast(str, gates["recommendation"])]
    )
    return "\n".join(lines)


def _write_reports(output_dir: Path, report: dict[str, object]) -> None:
    gates = cast(dict[str, object], report["phase9_success_gates"])
    tasks = cast(dict[str, dict[str, object]], report["tasks"])
    lines = [
        "# Phase 8.5 intervention-outcome diagnostic evaluation",
        "",
        CLAIM_BOUNDARY,
        "",
        "The final test, complete-archetype OOD, and extreme-weather OOD empirical-seed "
        "groups were untouched by preprocessing, tuning, and uncertainty calibration.",
        "",
        "| Primary task | Nonlinear model | MAE | MAE / field SD | Coverage |",
        "|---|---|---:|---:|---:|",
    ]
    for task_key in PRIMARY_SELECTION_TASKS:
        task = tasks[task_key]
        model = cast(str, task["observable_primary_model"])
        metrics = cast(dict[str, dict[str, float | None]], task["final_test_metrics"])[model]
        uncertainty = cast(dict[str, object], task["uncertainty"])
        interval = cast(dict[str, float], uncertainty["final_test"])
        lines.append(
            f"| {task_key} | {model} | {cast(float, metrics['mae']):.6g} | "
            f"{cast(float, metrics['mae_relative_to_natural_variation']):.4f} | "
            f"{interval['coverage']:.4f} |"
        )
    lines.extend(
        [
            "",
            f"**Phase 9 gates passed:** `{gates['passed']}`.",
            "",
            cast(str, gates["recommendation"]),
            "",
            "`protected_soc` remains a simulator proxy, not measured MAOC. See the JSON "
            "report for every horizon, baseline, policy, subgroup, uncertainty abstention, "
            "OOD test, residual-hidden-state correlation, and deterministic hash.",
        ]
    )
    (output_dir / "evaluation_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    card = [
        "# Model card: Phase 8.5 observable intervention-outcome diagnostics",
        "",
        "- Intended use: diagnose prediction of synthetic simulator outcomes on unseen "
        "synthetic empirical-seed groups.",
        "- Prohibited use: intervention selection, policy optimisation, farmer recommendations, "
        "causal inference, or real-field claims.",
        "- Population: 50 deterministic synthetic, non-representative seed groups derived "
        "from ten local demonstration templates with revised residual covariance.",
        "- Splits: training and validation groups plus untouched final-test, complete-archetype "
        "OOD, and extreme-weather OOD groups.",
        "- Horizons: crop-yield targets at 24 months; carbon-stock and carbon/respiration "
        "intervention-effect targets at 60 and 120 months.",
        "- Observable inputs: soil-test-like properties, baseline total SOC, seasonal weather "
        "indices, management-history indicators, coarse soil-test P status, policy, and horizon.",
        "- Excluded from observable inputs: raw simulator available-P stock, hidden pools, "
        "spin-up state, coordinates/region identifiers, archetype labels, and latent draws.",
        "- Models: global and policy means, pooled and separate-policy ridge, pooled and "
        "separate-policy deterministic forests; nonlinear selection uses validation error.",
        "- Uncertainty: empirical-seed-group-aware residual calibration on validation groups "
        "only; small subgroup coverage explicitly abstains.",
        f"- Phase 9 gate result: {gates['passed']}. {gates['recommendation']}",
        "- Claim boundary: " + CLAIM_BOUNDARY,
    ]
    (output_dir / "MODEL_CARD.md").write_text("\n".join(card) + "\n", encoding="utf-8")


def run_benchmark(
    rows: tuple[MlRow, ...],
    dataset_manifest: MlDatasetManifest,
    config: Phase8BenchmarkConfig,
    output_dir: Path,
) -> tuple[dict[str, object], str]:
    """Run Phase 8.5 diagnostics while keeping all final partitions untouched."""
    output_dir.mkdir(parents=True, exist_ok=True)
    write_ml_dataset(output_dir / f"training_dataset_v{DATASET_VERSION}.csv", rows)
    write_dataset_manifest(output_dir / "dataset_manifest.json", dataset_manifest)
    leakage = _leakage_audit(rows)
    if not leakage["passed"]:
        raise ValueError("final split leakage detected")
    train = tuple(row for row in rows if row.population_split is PopulationSplit.TRAIN)
    validation = tuple(row for row in rows if row.population_split is PopulationSplit.VALIDATION)
    if not train or not validation:
        raise ValueError("training and validation groups must be non-empty")
    start = time.perf_counter()
    observable_preprocessor = _save_preprocessor(
        output_dir / "preprocessing" / "observable_features.json",
        fit_preprocessor(train, FEATURE_SETS["observable_features"]),
    )
    full_preprocessor = _save_preprocessor(
        output_dir / "preprocessing" / "full_simulator_state.json",
        fit_preprocessor(train, FEATURE_SETS["full_simulator_state"]),
    )
    task_reports: dict[str, dict[str, object]] = {}
    runtimes: dict[str, _TaskRuntime] = {}
    hashes: dict[str, str] = {}
    task_index = 0
    for target in TARGETS:
        for horizon in HORIZON_TARGET_APPLICABILITY[target]:
            task_key = f"{target}@{horizon}"
            task_report, runtime, task_hashes = _run_task(
                rows,
                target,
                horizon,
                observable_preprocessor,
                full_preprocessor,
                config,
                output_dir / "models",
                task_index,
            )
            task_reports[task_key] = task_report
            runtimes[task_key] = runtime
            hashes.update(task_hashes)
            task_index += 1
    correlation_audit = _correlation_audit(rows, runtimes, config.random_seed)
    gates = calculate_success_gates(task_reports, leakage, config)
    runtime_seconds = time.perf_counter() - start
    report: dict[str, object] = {
        "report_version": "0.8.5",
        "claim_boundary": CLAIM_BOUNDARY,
        "dataset_hash": dataset_manifest.dataset_hash,
        "population_hash": dataset_manifest.population_hash,
        "model_configuration_hash": dataset_manifest.model_configuration_hash,
        "ml_configuration_hash": config.stable_hash(),
        "population_design": {
            "empirical_seed_group_count": dataset_manifest.empirical_seed_group_count,
            "split_empirical_seed_group_counts": dataset_manifest.split_empirical_seed_group_counts,
            "synthetic_and_non_representative": True,
            "revised_covariance_assumptions": dataset_manifest.revised_covariance_assumptions,
        },
        "horizon_target_applicability": HORIZON_TARGET_APPLICABILITY,
        "feature_sets": {
            "observable_features": dataset_manifest.observable_features,
            "full_simulator_state": dataset_manifest.full_simulator_state,
            "observable_measurement_rationale": (
                dataset_manifest.observable_feature_measurement_rationale
            ),
        },
        "leakage_audit": leakage,
        "tasks": task_reports,
        "direct_vs_paired_summary": {
            "direct_tasks": sorted(key for key in task_reports if not key.startswith("delta_")),
            "paired_effect_tasks": sorted(key for key in task_reports if key.startswith("delta_")),
        },
        "yield_and_respiration_diagnostic": {
            key: {
                "hidden_state_gap": task_reports[key]["hidden_state_gap"],
                "candidate_missing_observables_from_residual_correlations": list(
                    cast(
                        dict[str, object],
                        task_reports[key]["residual_correlation_with_hidden_state"],
                    )
                )[:5],
                "subgroup_errors": task_reports[key]["subgroup_errors"],
            }
            for key in task_reports
            if key.startswith("crop_yield") or key.startswith("cumulative_respiration")
        },
        "engineered_correlation_audit": correlation_audit,
        "phase9_success_gates": gates,
        "deterministic_model_hashes": dict(sorted(hashes.items())),
        "preprocessing_hashes": {
            "observable_features": observable_preprocessor.stable_hash(),
            "full_simulator_state": full_preprocessor.stable_hash(),
        },
        "runtime_seconds": runtime_seconds,
        "final_evaluation_policy": (
            "Preprocessing used training rows only; model/hyperparameter choice and interval "
            "calibration used validation groups only; final-test and OOD outcomes never tuned "
            "any artifact. Final partitions were evaluated after serialization."
        ),
    }
    _json_write(output_dir / "evaluation_report.json", report)
    _write_reports(output_dir, report)
    table = _benchmark_table(report)
    (output_dir / "benchmark_table.txt").write_text(table + "\n", encoding="utf-8")
    return report, table
