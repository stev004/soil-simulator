"""Phase 8.6 repeated-population intervention-effect evidence pipeline.

This module orchestrates only synthetic data generation and supervised outcome
benchmarking. It neither changes simulator equations nor selects interventions.
"""

from __future__ import annotations

import hashlib
import json
import math
import statistics
import time
from collections import Counter
from dataclasses import dataclass, replace
from pathlib import Path
from typing import cast

from soil_simulator.domain.enums import PopulationSplit
from soil_simulator.domain.management import ManagementScenarioSet
from soil_simulator.domain.models import ModelParameters
from soil_simulator.domain.population import (
    EmpiricalDataset,
    PopulationGenerationConfig,
)
from soil_simulator.ml.dataset import build_ml_dataset, load_ml_dataset_csv, write_ml_dataset
from soil_simulator.ml.evaluation import (
    fit_group_conformal_half_widths,
    interval_diagnostics,
    policy_vector,
    residual_diagnostics,
    target_matrix,
)
from soil_simulator.ml.models import (
    MultiTargetModel,
    fit_policy_mean,
    fit_random_forest,
    fit_ridge,
    model_from_dict,
)
from soil_simulator.ml.phase86_schema import (
    PHASE86_MODEL_COMPLEXITY,
    PHASE86_PRIMARY_TASKS,
    PHASE86_VERSION,
    PHASE86_WEATHER_REGIMES,
    Phase86BenchmarkConfig,
    predeclared_model_choice,
)
from soil_simulator.ml.pipeline import (
    _fit_per_policy_forest,
    _fit_per_policy_ridge,
    _matrix,
    _metrics,
    _score,
    _tune_models,
)
from soil_simulator.ml.preprocessing import (
    FittedPreprocessor,
    fit_preprocessor,
    preprocessor_from_dict,
)
from soil_simulator.ml.schema import CLAIM_BOUNDARY, FEATURE_SETS, MlRow, Phase8BenchmarkConfig
from soil_simulator.population.batch import run_population_batch
from soil_simulator.population.foundation import expand_phase86_foundation
from soil_simulator.population.generator import generate_population


@dataclass(frozen=True)
class SeedPlanEntry:
    """Independent seed identities for one development experiment."""

    run_id: str
    foundation_seed: int
    population_seed: int
    weather_seed: int
    biological_seed: int


@dataclass(frozen=True)
class ApplicabilityDecision:
    """Frozen target-regime support decision made before final evaluation."""

    target_task: str
    regime: str
    supported: bool
    reason: str
    calibration_group_count: int
    development_median_mae_over_sd: float | None


def build_seed_plan(config: Phase86BenchmarkConfig) -> tuple[SeedPlanEntry, ...]:
    """Pair repeated seed streams deterministically without collapsing their identity."""
    return tuple(
        SeedPlanEntry(
            run_id=f"development-{index + 1:02d}",
            foundation_seed=config.development_foundation_seeds[index],
            population_seed=population_seed,
            weather_seed=config.weather_resampling_seeds[
                index % len(config.weather_resampling_seeds)
            ],
            biological_seed=config.biological_parameter_seeds[
                (index * 3) % len(config.biological_parameter_seeds)
            ],
        )
        for index, population_seed in enumerate(config.population_seeds)
    )


def applicability_allows(
    decisions: tuple[ApplicabilityDecision, ...], target_task: str, regime: str
) -> bool:
    """Enforce abstention outside the frozen target-by-regime domain."""
    matches = [
        item for item in decisions if item.target_task == target_task and item.regime == regime
    ]
    if len(matches) != 1:
        return False
    return matches[0].supported


def _task_parts(task: str) -> tuple[str, int]:
    target, horizon = task.rsplit("@", maxsplit=1)
    return target, int(horizon)


def _rows(
    rows: tuple[MlRow, ...],
    task: str,
    *,
    split: PopulationSplit | None = None,
    regime: str | None = None,
) -> tuple[MlRow, ...]:
    _, horizon = _task_parts(task)
    return tuple(
        row
        for row in rows
        if row.simulation_horizon_months == horizon
        and (split is None or row.population_split is split)
        and (regime is None or row.weather_regime == regime)
    )


def _namespace_rows(rows: tuple[MlRow, ...], namespace: str) -> tuple[MlRow, ...]:
    return tuple(
        replace(
            row,
            field_id=f"{namespace}:{row.field_id}",
            empirical_seed_id=f"{namespace}:{row.empirical_seed_id}",
        )
        for row in rows
    )


def _distribution(values: list[float]) -> dict[str, float]:
    if not values:
        raise ValueError("cannot summarise an empty performance distribution")
    ordered = sorted(values)

    def percentile(fraction: float) -> float:
        if len(ordered) == 1:
            return ordered[0]
        position = fraction * (len(ordered) - 1)
        lower = math.floor(position)
        upper = math.ceil(position)
        weight = position - lower
        return ordered[lower] * (1.0 - weight) + ordered[upper] * weight

    return {
        "median": statistics.median(ordered),
        "q1": percentile(0.25),
        "q3": percentile(0.75),
        "iqr": percentile(0.75) - percentile(0.25),
        "worst": max(ordered),
        "best": min(ordered),
    }


def uncertainty_interval_or_abstain(
    *,
    prediction: float,
    task: str,
    regime: str,
    decisions: tuple[ApplicabilityDecision, ...],
    half_widths: dict[str, dict[str, float]],
) -> dict[str, float | str | bool | None]:
    """Return an interval only inside the pre-frozen applicability domain."""
    if not applicability_allows(decisions, task, regime):
        return {
            "abstained": True,
            "lower": None,
            "upper": None,
            "reason": "unsupported target-regime combination or insufficient calibration groups",
        }
    half_width = half_widths[task][regime]
    return {
        "abstained": False,
        "lower": prediction - half_width,
        "upper": prediction + half_width,
        "reason": "group-aware development calibration",
    }


def _best_hyperparameters(tuning: list[dict[str, object]], family: str) -> dict[str, float | int]:
    if family == "policy_mean":
        return {}
    candidates = [item for item in tuning if item["model"] == family]
    if not candidates:
        raise ValueError(f"no tuning records for {family}")
    winner = min(candidates, key=lambda item: float(cast(float, item["validation_score"])))
    return {
        key: cast(float | int, value)
        for key, value in winner.items()
        if key not in {"model", "validation_score"}
    }


def _modal_hyperparameters(values: list[dict[str, float | int]]) -> dict[str, float | int]:
    encoded = [json.dumps(value, sort_keys=True, separators=(",", ":")) for value in values]
    winner = min(Counter(encoded).items(), key=lambda item: (-item[1], item[0]))[0]
    return cast(dict[str, float | int], json.loads(winner))


def _fit_family(
    family: str,
    rows: tuple[MlRow, ...],
    target: str,
    preprocessor: FittedPreprocessor,
    hyperparameters: dict[str, float | int],
    config: Phase86BenchmarkConfig,
    random_seed: int,
) -> MultiTargetModel:
    matrix = _matrix(rows, preprocessor)
    targets = target_matrix(rows, (target,))
    policies = policy_vector(rows)
    if family == "policy_mean":
        return fit_policy_mean(targets, policies, (target,))
    if family == "pooled_ridge":
        return fit_ridge(
            matrix,
            targets,
            (target,),
            preprocessor.output_feature_names,
            float(hyperparameters["alpha"]),
        )
    if family == "per_policy_ridge":
        return _fit_per_policy_ridge(
            matrix,
            targets,
            policies,
            target,
            preprocessor.output_feature_names,
            float(hyperparameters["alpha"]),
        )
    tree_count = int(hyperparameters["tree_count"])
    max_depth = int(hyperparameters["max_depth"])
    if family == "pooled_forest":
        return fit_random_forest(
            matrix,
            targets,
            (target,),
            preprocessor.output_feature_names,
            tree_count=tree_count,
            max_depth=max_depth,
            min_leaf=config.forest_min_leaf,
            feature_fraction=config.forest_feature_fraction,
            random_seed=random_seed,
        )
    if family == "per_policy_forest":
        return _fit_per_policy_forest(
            matrix,
            targets,
            policies,
            target,
            preprocessor.output_feature_names,
            tree_count=tree_count,
            max_depth=max_depth,
            min_leaf=config.forest_min_leaf,
            feature_fraction=config.forest_feature_fraction,
            random_seed=random_seed,
        )
    raise ValueError(f"unknown candidate family {family}")


def _evaluate_model(
    model: MultiTargetModel,
    rows: tuple[MlRow, ...],
    target: str,
    preprocessor: FittedPreprocessor,
) -> dict[str, float | None]:
    actual = target_matrix(rows, (target,))
    predicted = model.predict(_matrix(rows, preprocessor), policy_vector(rows))
    return _metrics(actual, predicted, target)


def _json_write(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, allow_nan=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _semantic_hash(payload: object) -> str:
    canonical = json.dumps(
        payload, allow_nan=False, ensure_ascii=True, separators=(",", ":"), sort_keys=True
    )
    return hashlib.sha256(canonical.encode()).hexdigest()


def _save_model(path: Path, model: MultiTargetModel) -> MultiTargetModel:
    _json_write(path, model.model_dump())
    restored = model_from_dict(json.loads(path.read_text(encoding="utf-8")))
    if restored.stable_hash() != model.stable_hash():
        raise RuntimeError("serialized model hash changed during round trip")
    return restored


def _save_preprocessor(path: Path, value: FittedPreprocessor) -> None:
    _json_write(path, value.model_dump())


def _run_development_experiment(
    *,
    plan: SeedPlanEntry,
    base_dataset: EmpiricalDataset,
    population_config: PopulationGenerationConfig,
    parameters: ModelParameters,
    scenario: ManagementScenarioSet,
    config: Phase86BenchmarkConfig,
) -> tuple[tuple[MlRow, ...], dict[str, object]]:
    dataset = expand_phase86_foundation(
        base_dataset,
        group_count=config.foundation_group_count,
        random_seed=plan.foundation_seed,
    )
    population = generate_population(
        dataset=dataset,
        config=population_config,
        parameters=parameters,
        population_size=config.development_population_size,
        generation_seed=plan.population_seed,
        weather_resampling_seed=plan.weather_seed,
        biological_parameter_seed=plan.biological_seed,
    )
    batch = run_population_batch(
        population,
        scenario,
        parameters,
        population_config,
        horizons_months=config.simulation_horizons_months,
    )
    if batch.failures:
        raise RuntimeError(f"{plan.run_id} contains simulator failures")
    rows, manifest = build_ml_dataset(population, batch, config, dataset_version=PHASE86_VERSION)
    preprocessor = fit_preprocessor(
        tuple(row for row in rows if row.population_split is PopulationSplit.TRAIN),
        FEATURE_SETS["observable_features"],
    )
    task_results: dict[str, object] = {}
    tuning_config = cast(Phase8BenchmarkConfig, config)
    for task_index, task in enumerate(PHASE86_PRIMARY_TASKS):
        target, _ = _task_parts(task)
        train = _rows(rows, task, split=PopulationSplit.TRAIN)
        validation = _rows(rows, task, split=PopulationSplit.VALIDATION)
        test = _rows(rows, task, split=PopulationSplit.TEST)
        if not train or not validation or not test:
            raise RuntimeError(f"{plan.run_id}/{task} lacks a frozen split")
        models, tuning = _tune_models(
            train,
            validation,
            target,
            preprocessor,
            tuning_config,
            include_per_policy=True,
            seed_offset=task_index * 1_000,
        )
        candidate_validation: dict[str, float] = {}
        candidate_test: dict[str, dict[str, float | None]] = {}
        candidate_weather: dict[str, dict[str, dict[str, float | None]]] = {}
        hyperparameters: dict[str, dict[str, float | int]] = {}
        for family in PHASE86_MODEL_COMPLEXITY:
            model = models[family]
            validation_actual = target_matrix(validation, (target,))
            validation_prediction = model.predict(
                _matrix(validation, preprocessor), policy_vector(validation)
            )
            candidate_validation[family] = _score(validation_actual, validation_prediction, target)
            candidate_test[family] = _evaluate_model(model, test, target, preprocessor)
            hyperparameters[family] = _best_hyperparameters(tuning, family)
            candidate_weather[family] = {}
            for regime in PHASE86_WEATHER_REGIMES[1:]:
                held = _rows(
                    rows,
                    task,
                    split=PopulationSplit.WEATHER_OOD,
                    regime=regime,
                )
                candidate_weather[family][regime] = _evaluate_model(
                    model, held, target, preprocessor
                )
        task_results[task] = {
            "validation_scores": candidate_validation,
            "test_metrics": candidate_test,
            "weather_ood_metrics": candidate_weather,
            "best_hyperparameters": hyperparameters,
        }
    return _namespace_rows(rows, plan.run_id), {
        "run_id": plan.run_id,
        "seeds": {
            "foundation": plan.foundation_seed,
            "population": plan.population_seed,
            "weather_resampling": plan.weather_seed,
            "latent_biological": plan.biological_seed,
        },
        "population_hash": population.manifest.population_hash,
        "dataset_hash": manifest.dataset_hash,
        "field_count": len(population.fields),
        "empirical_seed_group_count": manifest.empirical_seed_group_count,
        "maximum_carbon_residual_t_c_ha": batch.maximum_carbon_residual_t_c_ha,
        "maximum_phosphorus_residual_kg_p_ha": batch.maximum_phosphorus_residual_kg_p_ha,
        "tasks": task_results,
    }


def _selection_and_distributions(
    run_reports: list[dict[str, object]], config: Phase86BenchmarkConfig
) -> tuple[dict[str, object], dict[str, dict[str, float | int]]]:
    selections: dict[str, object] = {}
    frozen_hyperparameters: dict[str, dict[str, float | int]] = {}
    for task in PHASE86_PRIMARY_TASKS:
        validation_distributions: dict[str, dict[str, float]] = {}
        median_scores: dict[str, float] = {}
        for family in PHASE86_MODEL_COMPLEXITY:
            values = [
                float(
                    cast(dict[str, object], cast(dict[str, object], run["tasks"])[task])[
                        "validation_scores"
                    ][family]  # type: ignore[index]
                )
                for run in run_reports
            ]
            validation_distributions[family] = _distribution(values)
            median_scores[family] = validation_distributions[family]["median"]
        selected, rule = predeclared_model_choice(
            median_scores, config.model_selection_relative_tolerance
        )
        hyperparameter_values = [
            cast(
                dict[str, float | int],
                cast(dict[str, object], cast(dict[str, object], run["tasks"])[task])[
                    "best_hyperparameters"
                ][selected],  # type: ignore[index]
            )
            for run in run_reports
        ]
        frozen_hyperparameters[task] = _modal_hyperparameters(hyperparameter_values)
        selected_metrics = [
            cast(
                dict[str, float | None],
                cast(dict[str, object], cast(dict[str, object], run["tasks"])[task])[
                    "test_metrics"
                ][selected],  # type: ignore[index]
            )
            for run in run_reports
        ]
        policy_metrics = [
            cast(
                dict[str, float | None],
                cast(dict[str, object], cast(dict[str, object], run["tasks"])[task])[
                    "test_metrics"
                ]["policy_mean"],  # type: ignore[index]
            )
            for run in run_reports
        ]
        selected_ratios = [
            float(cast(float, item["mae_relative_to_natural_variation"]))
            for item in selected_metrics
        ]
        repeated_metric_distributions = {
            metric: _distribution([float(cast(float, item[metric])) for item in selected_metrics])
            for metric in ("mae", "rmse", "r_squared", "mae_relative_to_natural_variation")
        }
        policy_metric_distributions = {
            metric: _distribution([float(cast(float, item[metric])) for item in policy_metrics])
            for metric in ("mae", "rmse", "r_squared", "mae_relative_to_natural_variation")
        }
        best_run_index = min(range(len(selected_ratios)), key=selected_ratios.__getitem__)
        worst_run_index = max(range(len(selected_ratios)), key=selected_ratios.__getitem__)
        failure_count = sum(
            1
            for selected_item, mean_item in zip(selected_metrics, policy_metrics, strict=True)
            if float(cast(float, selected_item["mae"])) >= float(cast(float, mean_item["mae"]))
        )
        weather_distributions: dict[str, object] = {}
        for regime in PHASE86_WEATHER_REGIMES[1:]:
            values = [
                cast(
                    float,
                    cast(
                        dict[str, float | None],
                        cast(
                            dict[str, object],
                            cast(dict[str, object], run["tasks"])[task],
                        )["weather_ood_metrics"][selected][regime],  # type: ignore[index]
                    )["mae_relative_to_natural_variation"],
                )
                for run in run_reports
            ]
            weather_distributions[regime] = _distribution(values)
        selections[task] = {
            "selected_model": selected,
            "selection_rule": rule,
            "validation_score_distributions": validation_distributions,
            "frozen_hyperparameters": frozen_hyperparameters[task],
            "repeated_test_mae_over_sd": _distribution(selected_ratios),
            "repeated_test_metric_distributions": repeated_metric_distributions,
            "best_run_id": str(run_reports[best_run_index]["run_id"]),
            "worst_run_id": str(run_reports[worst_run_index]["run_id"]),
            "policy_mean_test_mae_over_sd": _distribution(
                [
                    float(cast(float, item["mae_relative_to_natural_variation"]))
                    for item in policy_metrics
                ]
            ),
            "policy_mean_test_metric_distributions": policy_metric_distributions,
            "failure_frequency_against_policy_mean": failure_count / len(run_reports),
            "weather_ood_mae_over_sd": weather_distributions,
        }
    return selections, frozen_hyperparameters


def _calibrate_and_freeze_domain(
    *,
    development_rows: tuple[MlRow, ...],
    models: dict[str, MultiTargetModel],
    preprocessor: FittedPreprocessor,
    selections: dict[str, object],
    config: Phase86BenchmarkConfig,
) -> tuple[
    dict[str, dict[str, float]],
    dict[str, object],
    tuple[ApplicabilityDecision, ...],
]:
    widths: dict[str, dict[str, float]] = {}
    calibration: dict[str, dict[str, object]] = {}
    decisions: list[ApplicabilityDecision] = []
    for task in PHASE86_PRIMARY_TASKS:
        target, _ = _task_parts(task)
        widths[task] = {}
        calibration[task] = {}
        selection = cast(dict[str, object], selections[task])
        for regime in PHASE86_WEATHER_REGIMES:
            calibration_rows = (
                _rows(development_rows, task, split=PopulationSplit.VALIDATION)
                if regime == "temperate"
                else _rows(
                    development_rows,
                    task,
                    split=PopulationSplit.WEATHER_OOD,
                    regime=regime,
                )
            )
            actual = target_matrix(calibration_rows, (target,))
            predicted = models[task].predict(
                _matrix(calibration_rows, preprocessor), policy_vector(calibration_rows)
            )
            fitted, diagnostics = fit_group_conformal_half_widths(
                calibration_rows,
                actual,
                predicted,
                config.conformal_alpha,
                config.minimum_calibration_groups,
                (target,),
            )
            widths[task][regime] = fitted[target]
            group_count = int(cast(int, diagnostics["calibration_group_count"]))
            if regime == "temperate":
                development_error = float(
                    cast(dict[str, float], selection["repeated_test_mae_over_sd"])["median"]
                )
            else:
                development_error = float(
                    cast(dict[str, dict[str, float]], selection["weather_ood_mae_over_sd"])[regime][
                        "median"
                    ]
                )
            supported = (
                group_count >= config.minimum_calibration_groups
                and development_error <= config.supported_regime_max_median_mae_sd
            )
            reason = (
                "supported by repeated development error and sufficient independent "
                "calibration groups"
                if supported
                else "abstain: repeated error exceeded the predeclared limit or calibration "
                "groups were insufficient"
            )
            decision = ApplicabilityDecision(
                target_task=task,
                regime=regime,
                supported=supported,
                reason=reason,
                calibration_group_count=group_count,
                development_median_mae_over_sd=development_error,
            )
            decisions.append(decision)
            calibration[task][regime] = {
                **diagnostics,
                "half_width": fitted[target],
                "applicability_supported": supported,
                "applicability_reason": reason,
            }
    return widths, cast(dict[str, object], calibration), tuple(decisions)


def _final_evaluation(
    *,
    rows: tuple[MlRow, ...],
    models: dict[str, MultiTargetModel],
    policy_means: dict[str, MultiTargetModel],
    preprocessor: FittedPreprocessor,
    widths: dict[str, dict[str, float]],
    decisions: tuple[ApplicabilityDecision, ...],
) -> dict[str, object]:
    tasks: dict[str, object] = {}
    core_splits = {
        PopulationSplit.TRAIN,
        PopulationSplit.VALIDATION,
        PopulationSplit.TEST,
    }
    for task in PHASE86_PRIMARY_TASKS:
        target, _ = _task_parts(task)
        core = tuple(row for row in _rows(rows, task) if row.population_split in core_splits)
        actual = target_matrix(core, (target,))
        prediction = models[task].predict(_matrix(core, preprocessor), policy_vector(core))
        baseline_prediction = policy_means[task].predict(
            _matrix(core, preprocessor), policy_vector(core)
        )
        core_supported = applicability_allows(decisions, task, "temperate")
        core_interval = (
            interval_diagnostics(
                actual,
                prediction,
                {target: widths[task]["temperate"]},
                (target,),
            )[target]
            if core_supported
            else None
        )
        task_result: dict[str, object] = {
            "untouched_core": {
                "row_count": len(core),
                "empirical_seed_group_count": len({row.empirical_seed_id for row in core}),
                "selected_model_metrics": _metrics(actual, prediction, target),
                "policy_mean_metrics": _metrics(actual, baseline_prediction, target),
                "residual_diagnostics": residual_diagnostics(actual, prediction, (target,))[target],
                "uncertainty": {
                    "abstained": not core_supported,
                    "nominal_coverage": 0.9,
                    "diagnostics": core_interval,
                    "claim": (
                        "synthetic held-out coverage assessed inside the frozen "
                        "applicability domain"
                        if core_supported
                        else "abstain: temperate regime was unsupported before final evaluation"
                    ),
                },
            },
            "weather_ood": {},
        }
        regimes = cast(dict[str, object], task_result["weather_ood"])
        for regime in PHASE86_WEATHER_REGIMES[1:]:
            held = _rows(
                rows,
                task,
                split=PopulationSplit.WEATHER_OOD,
                regime=regime,
            )
            held_actual = target_matrix(held, (target,))
            held_prediction = models[task].predict(_matrix(held, preprocessor), policy_vector(held))
            supported = applicability_allows(decisions, task, regime)
            interval = (
                interval_diagnostics(
                    held_actual,
                    held_prediction,
                    {target: widths[task][regime]},
                    (target,),
                )[target]
                if supported
                else None
            )
            regimes[regime] = {
                "row_count": len(held),
                "empirical_seed_group_count": len({row.empirical_seed_id for row in held}),
                "metrics": _metrics(held_actual, held_prediction, target),
                "uncertainty": {
                    "abstained": not supported,
                    "nominal_coverage": 0.9,
                    "diagnostics": interval,
                    "claim": (
                        "synthetic held-out coverage assessed inside the frozen "
                        "applicability domain"
                        if supported
                        else "abstain: regime was unsupported before final evaluation"
                    ),
                },
            }
        tasks[task] = task_result
    return {"tasks": tasks}


def _success_gates(
    *,
    selections: dict[str, object],
    final_evaluation: dict[str, object],
    decisions: tuple[ApplicabilityDecision, ...],
    config: Phase86BenchmarkConfig,
) -> dict[str, object]:
    beats_consistently = all(
        cast(float, cast(dict[str, object], value)["failure_frequency_against_policy_mean"])
        <= config.maximum_repeat_failure_frequency
        for value in selections.values()
    )
    stable = all(
        float(
            cast(
                dict[str, float],
                cast(dict[str, object], value)["repeated_test_mae_over_sd"],
            )["iqr"]
        )
        <= config.maximum_repeat_iqr_mae_sd
        for value in selections.values()
    )
    final_tasks = cast(dict[str, object], final_evaluation["tasks"])
    final_acceptable = True
    for task in PHASE86_PRIMARY_TASKS:
        core = cast(dict[str, object], cast(dict[str, object], final_tasks[task])["untouched_core"])
        selected_metrics = cast(dict[str, float | None], core["selected_model_metrics"])
        mean_metrics = cast(dict[str, float | None], core["policy_mean_metrics"])
        final_acceptable &= float(
            cast(float, selected_metrics["mae_relative_to_natural_variation"])
        ) <= config.maximum_final_mae_sd and float(cast(float, selected_metrics["mae"])) < float(
            cast(float, mean_metrics["mae"])
        )
    nominal = 1.0 - config.conformal_alpha
    uncertainty_valid = True
    for decision in decisions:
        task_result = cast(dict[str, object], final_tasks[decision.target_task])
        if decision.regime == "temperate":
            core = cast(dict[str, object], task_result["untouched_core"])
            uncertainty = cast(dict[str, object], core["uncertainty"])
        else:
            weather = cast(dict[str, object], task_result["weather_ood"])
            uncertainty = cast(
                dict[str, object],
                cast(dict[str, object], weather[decision.regime])["uncertainty"],
            )
        if decision.supported:
            diagnostics = cast(dict[str, float], uncertainty["diagnostics"])
            uncertainty_valid &= abs(diagnostics["coverage"] - nominal) <= config.coverage_tolerance
        else:
            uncertainty_valid &= bool(uncertainty["abstained"])
    supported_by_task = {
        task: {
            decision.regime
            for decision in decisions
            if decision.target_task == task
            and decision.regime != "temperate"
            and decision.supported
        }
        for task in PHASE86_PRIMARY_TASKS
    }
    supported_climate_regimes = sorted(
        set.intersection(*(set(values) for values in supported_by_task.values()))
    )
    climate_gate = len(supported_climate_regimes) >= config.minimum_supported_climate_regimes
    gates = {
        "selected_observable_model_beats_policy_mean_consistently": beats_consistently,
        "performance_stable_across_repeated_seeds": stable,
        "acceptable_error_on_untouched_final_population": final_acceptable,
        "uncertainty_calibrated_or_explicitly_abstaining": uncertainty_valid,
        "acceptable_in_minimum_supported_climate_regimes": climate_gate,
        "no_nonlinear_over_ridge_requirement": True,
        "final_population_unused_for_selection_or_calibration": True,
    }
    passed = all(gates.values())
    restricted = passed and any(not decision.supported for decision in decisions)
    return {
        "gates": gates,
        "passed": passed,
        "restricted_applicability": restricted,
        "supported_weather_regimes": supported_climate_regimes,
        "target_specific_supported_weather_regimes": {
            task: sorted(values) for task, values in supported_by_task.items()
        },
        "recommendation": (
            "Restricted Phase 9 regret benchmarking is justified only inside the frozen "
            "applicability domain; intervention selection is not implemented."
            if passed
            else "Do not build an ML intervention selector; repeat-model, final-population, "
            "uncertainty, or climate-support gates remain unmet."
        ),
    }


def benchmark_table(report: dict[str, object]) -> str:
    """Render the primary repeated and frozen-final evidence as a CLI table."""
    selections = cast(dict[str, object], report["model_selection"])
    final_tasks = cast(
        dict[str, object], cast(dict[str, object], report["final_evaluation"])["tasks"]
    )
    lines = [
        "Phase 8.6 repeated synthetic intervention-effect benchmark",
        "task | model | repeat median [IQR] MAE/SD | failures | final MAE/SD | supported weather",
        "-" * 126,
    ]
    domain = cast(list[dict[str, object]], report["applicability_domain"])
    for task in PHASE86_PRIMARY_TASKS:
        selection = cast(dict[str, object], selections[task])
        distribution = cast(dict[str, float], selection["repeated_test_mae_over_sd"])
        core = cast(dict[str, object], cast(dict[str, object], final_tasks[task])["untouched_core"])
        metrics = cast(dict[str, float], core["selected_model_metrics"])
        supported = (
            ",".join(
                str(item["regime"])
                for item in domain
                if item["target_task"] == task
                and item["regime"] != "temperate"
                and item["supported"] is True
            )
            or "none (abstain)"
        )
        lines.append(
            f"{task} | {selection['selected_model']} | {distribution['median']:.4f} "
            f"[{distribution['iqr']:.4f}] | "
            f"{cast(float, selection['failure_frequency_against_policy_mean']):.1%} | "
            f"{metrics['mae_relative_to_natural_variation']:.4f} | {supported}"
        )
    gates = cast(dict[str, object], report["phase9_gates"])
    lines.extend(
        [
            "",
            f"Phase 9 gates: {'PASS' if gates['passed'] else 'FAIL'}",
            str(gates["recommendation"]),
            f"Claim boundary: {CLAIM_BOUNDARY}",
        ]
    )
    return "\n".join(lines)


def write_phase86_narrative_artifacts(report: dict[str, object], output_dir: Path) -> None:
    """Write a concise evaluation narrative and synthetic-only model card."""
    selections = cast(dict[str, object], report["model_selection"])
    final_tasks = cast(
        dict[str, object], cast(dict[str, object], report["final_evaluation"])["tasks"]
    )
    gates = cast(dict[str, object], report["phase9_gates"])
    rows = []
    for task in PHASE86_PRIMARY_TASKS:
        selection = cast(dict[str, object], selections[task])
        repeat = cast(dict[str, float], selection["repeated_test_mae_over_sd"])
        core = cast(dict[str, object], cast(dict[str, object], final_tasks[task])["untouched_core"])
        metrics = cast(dict[str, float], core["selected_model_metrics"])
        rows.append(
            f"| `{task}` | {selection['selected_model']} | {repeat['median']:.4f} | "
            f"{repeat['iqr']:.4f} | "
            f"{cast(float, selection['failure_frequency_against_policy_mean']):.1%} | "
            f"{metrics['mae_relative_to_natural_variation']:.4f} |"
        )
    supported = ", ".join(cast(list[str], gates["supported_weather_regimes"])) or "none"
    evaluation = "\n".join(
        [
            "# Phase 8.6 evaluation report",
            "",
            "All results are synthetic simulator prediction diagnostics. They are non-causal, "
            "not real-field validation, and not intervention recommendations.",
            "",
            "## Primary repeated and frozen-final results",
            "",
            "| Paired-effect task | Selected model | Repeat median MAE/SD | IQR | Failure "
            "frequency | Frozen-final MAE/SD |",
            "|---|---:|---:|---:|---:|---:|",
            *rows,
            "",
            "Selection used median validation normalised RMSE and chose the least complex "
            "candidate within the predeclared 5% tolerance. Test, weather-OOD and final "
            "outcomes did not select models or hyperparameters.",
            "",
            "## Uncertainty and applicability",
            "",
            f"Supported dedicated weather regimes: {supported}. Unsupported target-regime "
            "pairs abstain from interval claims. Widths were fitted by target and regime from "
            "development validation/OOD groups before the final population was instantiated.",
            "",
            "## Phase 9 decision",
            "",
            f"Overall gates: **{'PASS' if gates['passed'] else 'FAIL'}**. "
            f"{gates['recommendation']}",
            "",
            "See `evaluation_report.json`, `frozen_protocol.json`, and "
            "`benchmark_table.txt` for complete per-run, OOD, coverage, provenance, and hash "
            "details.",
        ]
    )
    model_card = "\n".join(
        [
            "# Phase 8.6 observable intervention-effect model card",
            "",
            "## Intended use",
            "",
            "Research-only prediction of five paired intervention-minus-baseline outcomes in "
            "the frozen synthetic simulator: yield effect at 24 months, and total-SOC and "
            "protected-SOC-proxy effects at 5 and 10 years.",
            "",
            "## Prohibited use",
            "",
            "Do not use these models to select interventions, advise farmers, infer causality, "
            "or claim real-field validity. `protected_soc` is a model proxy, not measured MAOC.",
            "",
            "## Inputs and exclusions",
            "",
            "The model uses the documented observable feature registry only: defensible soil "
            "measurements, weather-history summaries, management-history indicators, policy "
            "identity, and horizon. IDs, split labels, outcomes, hidden pools, spin-up state, "
            "and latent biological draws are excluded.",
            "",
            "## Training and selection",
            "",
            "Ten independent synthetic populations vary foundation, field, weather-resampling, "
            "and latent-biological seeds. Candidate families were fixed as policy mean, pooled "
            "ridge, per-policy ridge, pooled forest, and per-policy forest. Ridge is a valid ML "
            "candidate; nonlinear complexity receives no preference.",
            "",
            "## Evaluation and uncertainty",
            "",
            "Performance is reported as distributions across repeated held-out groups and once "
            "on a separately generated frozen population. Group-aware residual widths are "
            "target/regime specific. Unsupported regimes and small calibration sets abstain.",
            "",
            "## Applicability and limitations",
            "",
            f"Dedicated supported weather regimes: {supported}. The applicable domain is "
            "target-specific and synthetic. It does not include structural simulator error, "
            "empirical representativeness, future climate validity, or causal transport to "
            "farms.",
            "",
            "## Decision",
            "",
            f"Phase 9 gates: **{'PASS' if gates['passed'] else 'FAIL'}**. "
            f"{gates['recommendation']}",
        ]
    )
    (output_dir / "evaluation_report.md").write_text(evaluation + "\n", encoding="utf-8")
    (output_dir / "MODEL_CARD.md").write_text(model_card + "\n", encoding="utf-8")


def refresh_phase86_artifact_diagnostics(
    output_dir: Path, config: Phase86BenchmarkConfig
) -> dict[str, object]:
    """Recompute interval diagnostics from serialized artifacts without refitting.

    This provides a deterministic replay path for coverage reporting. It never
    changes preprocessing, selected models, hyperparameters, interval widths,
    applicability decisions, predictions, or the frozen final population.
    """
    report = cast(
        dict[str, object],
        json.loads((output_dir / "evaluation_report.json").read_text(encoding="utf-8")),
    )
    protocol = cast(
        dict[str, object],
        json.loads((output_dir / "frozen_protocol.json").read_text(encoding="utf-8")),
    )
    selections, _ = _selection_and_distributions(
        cast(list[dict[str, object]], report["repeated_experiments"]), config
    )
    frozen_selected = cast(dict[str, str], protocol["selected_models"])
    if any(
        cast(dict[str, object], selections[task])["selected_model"] != frozen_selected[task]
        for task in PHASE86_PRIMARY_TASKS
    ):
        raise RuntimeError("replayed selection differs from the frozen protocol")
    report["model_selection"] = selections
    rows = load_ml_dataset_csv(output_dir / "frozen_final_dataset_v0.8.6.csv")
    preprocessor = preprocessor_from_dict(
        json.loads(
            (output_dir / "preprocessing" / "observable_preprocessor.json").read_text(
                encoding="utf-8"
            )
        )
    )
    models = {
        task: model_from_dict(
            json.loads(
                (output_dir / "models" / f"{task.replace('@', '__h')}.json").read_text(
                    encoding="utf-8"
                )
            )
        )
        for task in PHASE86_PRIMARY_TASKS
    }
    widths = cast(dict[str, dict[str, float]], protocol["calibration_half_widths"])
    decisions_list: list[ApplicabilityDecision] = []
    for raw in cast(list[object], protocol["applicability_domain"]):
        item = cast(dict[str, object], raw)
        error = item["development_median_mae_over_sd"]
        decisions_list.append(
            ApplicabilityDecision(
                target_task=str(item["target_task"]),
                regime=str(item["regime"]),
                supported=bool(item["supported"]),
                reason=str(item["reason"]),
                calibration_group_count=int(cast(int, item["calibration_group_count"])),
                development_median_mae_over_sd=(
                    None if error is None else float(cast(float, error))
                ),
            )
        )
    decisions = tuple(decisions_list)
    final_evaluation = cast(dict[str, object], report["final_evaluation"])
    final_tasks = cast(dict[str, object], final_evaluation["tasks"])
    for task in PHASE86_PRIMARY_TASKS:
        target, _ = _task_parts(task)
        core = tuple(
            row
            for row in _rows(rows, task)
            if row.population_split
            in {PopulationSplit.TRAIN, PopulationSplit.VALIDATION, PopulationSplit.TEST}
        )
        actual = target_matrix(core, (target,))
        predicted = models[task].predict(_matrix(core, preprocessor), policy_vector(core))
        supported = applicability_allows(decisions, task, "temperate")
        diagnostics = (
            interval_diagnostics(
                actual,
                predicted,
                {target: widths[task]["temperate"]},
                (target,),
            )[target]
            if supported
            else None
        )
        core_report = cast(
            dict[str, object], cast(dict[str, object], final_tasks[task])["untouched_core"]
        )
        core_report["uncertainty"] = {
            "abstained": not supported,
            "nominal_coverage": 1.0 - config.conformal_alpha,
            "diagnostics": diagnostics,
            "claim": (
                "synthetic held-out coverage assessed inside the frozen applicability domain"
                if supported
                else "abstain: temperate regime was unsupported before final evaluation"
            ),
        }
    gates = _success_gates(
        selections=selections,
        final_evaluation=final_evaluation,
        decisions=decisions,
        config=config,
    )
    report["phase9_gates"] = gates
    semantic = {
        key: value
        for key, value in report.items()
        if key not in {"runtime_seconds", "deterministic_report_hash"}
    }
    report["deterministic_report_hash"] = _semantic_hash(semantic)
    _json_write(output_dir / "evaluation_report.json", report)
    table = benchmark_table(report)
    (output_dir / "benchmark_table.txt").write_text(table + "\n", encoding="utf-8")
    write_phase86_narrative_artifacts(report, output_dir)
    return report


def run_phase86_benchmark(
    *,
    base_dataset: EmpiricalDataset,
    population_config: PopulationGenerationConfig,
    parameters: ModelParameters,
    scenario: ManagementScenarioSet,
    config: Phase86BenchmarkConfig,
    output_dir: Path,
) -> tuple[dict[str, object], str]:
    """Run development repeats, freeze decisions, then instantiate final data once."""
    started = time.perf_counter()
    output_dir.mkdir(parents=True, exist_ok=True)
    plan = build_seed_plan(config)
    development_rows: list[MlRow] = []
    run_reports: list[dict[str, object]] = []
    for entry in plan:
        namespaced_rows, run_report = _run_development_experiment(
            plan=entry,
            base_dataset=base_dataset,
            population_config=population_config,
            parameters=parameters,
            scenario=scenario,
            config=config,
        )
        development_rows.extend(namespaced_rows)
        run_reports.append(run_report)
    combined = tuple(development_rows)
    selections, frozen_hyperparameters = _selection_and_distributions(run_reports, config)
    train = tuple(row for row in combined if row.population_split is PopulationSplit.TRAIN)
    preprocessor = fit_preprocessor(train, FEATURE_SETS["observable_features"])
    _save_preprocessor(output_dir / "preprocessing" / "observable_preprocessor.json", preprocessor)
    models: dict[str, MultiTargetModel] = {}
    policy_means: dict[str, MultiTargetModel] = {}
    model_hashes: dict[str, str] = {}
    for task_index, task in enumerate(PHASE86_PRIMARY_TASKS):
        target, _ = _task_parts(task)
        task_train = _rows(train, task)
        selected_family = str(cast(dict[str, object], selections[task])["selected_model"])
        model = _fit_family(
            selected_family,
            task_train,
            target,
            preprocessor,
            frozen_hyperparameters[task],
            config,
            config.random_seed + 100_000 + task_index,
        )
        models[task] = _save_model(
            output_dir / "models" / f"{task.replace('@', '__h')}.json", model
        )
        policy_means[task] = fit_policy_mean(
            target_matrix(task_train, (target,)), policy_vector(task_train), (target,)
        )
        model_hashes[task] = models[task].stable_hash()
    widths, calibration, decisions = _calibrate_and_freeze_domain(
        development_rows=combined,
        models=models,
        preprocessor=preprocessor,
        selections=selections,
        config=config,
    )
    frozen_protocol = {
        "phase": "8.6",
        "protocol_hash": config.stable_hash(),
        "development_population_hashes": [run["population_hash"] for run in run_reports],
        "selected_models": {
            task: cast(dict[str, object], value)["selected_model"]
            for task, value in selections.items()
        },
        "frozen_hyperparameters": frozen_hyperparameters,
        "model_hashes": model_hashes,
        "preprocessing_hash": preprocessor.stable_hash(),
        "calibration_half_widths": widths,
        "applicability_domain": [item.__dict__ for item in decisions],
        "final_seed_commitment": {
            "foundation": config.final_foundation_seed,
            "population": config.final_population_seed,
            "weather_resampling": config.final_weather_resampling_seed,
            "latent_biological": config.final_biological_parameter_seed,
        },
        "final_outcomes_seen": False,
        "claim_boundary": CLAIM_BOUNDARY,
    }
    frozen_protocol["frozen_decision_hash"] = _semantic_hash(frozen_protocol)
    _json_write(output_dir / "frozen_protocol.json", frozen_protocol)

    # The final population is intentionally created only after the preceding artifact exists.
    final_dataset = expand_phase86_foundation(
        base_dataset,
        group_count=config.foundation_group_count,
        random_seed=config.final_foundation_seed,
    )
    final_population = generate_population(
        dataset=final_dataset,
        config=population_config,
        parameters=parameters,
        population_size=config.final_population_size,
        generation_seed=config.final_population_seed,
        weather_resampling_seed=config.final_weather_resampling_seed,
        biological_parameter_seed=config.final_biological_parameter_seed,
    )
    final_batch = run_population_batch(
        final_population,
        scenario,
        parameters,
        population_config,
        horizons_months=config.simulation_horizons_months,
    )
    if final_batch.failures:
        raise RuntimeError("frozen final population contains simulator failures")
    _json_write(
        output_dir / "frozen_final_population_and_batch.json",
        {
            "population_manifest": final_population.manifest.model_dump(mode="json"),
            "fields": [field.model_dump(mode="json") for field in final_population.fields],
            "batch": final_batch.model_dump(mode="json"),
        },
    )
    final_rows, final_manifest = build_ml_dataset(
        final_population, final_batch, config, dataset_version=PHASE86_VERSION
    )
    write_ml_dataset(
        output_dir / "frozen_final_dataset_v0.8.6.csv",
        final_rows,
        dataset_version=PHASE86_VERSION,
    )
    _json_write(
        output_dir / "frozen_final_dataset_manifest.json", final_manifest.model_dump(mode="json")
    )
    final_evaluation = _final_evaluation(
        rows=final_rows,
        models=models,
        policy_means=policy_means,
        preprocessor=preprocessor,
        widths=widths,
        decisions=decisions,
    )
    final_evaluation.update(
        {
            "population_hash": final_population.manifest.population_hash,
            "dataset_hash": final_manifest.dataset_hash,
            "maximum_carbon_residual_t_c_ha": final_batch.maximum_carbon_residual_t_c_ha,
            "maximum_phosphorus_residual_kg_p_ha": final_batch.maximum_phosphorus_residual_kg_p_ha,
            "generated_after_frozen_decision_hash": frozen_protocol["frozen_decision_hash"],
            "seed_overlap_with_development": False,
        }
    )
    gates = _success_gates(
        selections=selections,
        final_evaluation=final_evaluation,
        decisions=decisions,
        config=config,
    )
    report_without_runtime = {
        "report_version": PHASE86_VERSION,
        "claim_boundary": CLAIM_BOUNDARY,
        "protocol_hash": config.stable_hash(),
        "frozen_decision_hash": frozen_protocol["frozen_decision_hash"],
        "observable_feature_set": FEATURE_SETS["observable_features"].names,
        "latent_features_exposed": False,
        "primary_targets": PHASE86_PRIMARY_TASKS,
        "model_complexity_order": PHASE86_MODEL_COMPLEXITY,
        "seed_plan": [item.__dict__ for item in plan],
        "repeated_experiments": run_reports,
        "model_selection": selections,
        "model_hashes": model_hashes,
        "preprocessing_hash": preprocessor.stable_hash(),
        "uncertainty_calibration": calibration,
        "applicability_domain": [item.__dict__ for item in decisions],
        "final_evaluation": final_evaluation,
        "phase9_gates": gates,
    }
    report = {
        **report_without_runtime,
        "deterministic_report_hash": _semantic_hash(report_without_runtime),
        "runtime_seconds": time.perf_counter() - started,
    }
    table = benchmark_table(report)
    _json_write(output_dir / "evaluation_report.json", report)
    (output_dir / "benchmark_table.txt").write_text(table + "\n", encoding="utf-8")
    write_phase86_narrative_artifacts(report, output_dir)
    return report, table
