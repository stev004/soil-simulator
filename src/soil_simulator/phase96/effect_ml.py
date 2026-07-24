"""Effect-only dataset construction and fail-closed prediction gates for Phase 9.6."""

from __future__ import annotations

import math
from collections.abc import Mapping
from typing import cast

from soil_simulator.domain.management import ManagementScenarioSet
from soil_simulator.domain.models import ModelParameters
from soil_simulator.domain.population import (
    PopulationGenerationConfig,
    SyntheticField,
    SyntheticPopulation,
)
from soil_simulator.ml.models import PolicyMeanModel, RidgeModel, fit_policy_mean, fit_ridge
from soil_simulator.phase95.accounting import AccountingSchedule, accrue_accounting
from soil_simulator.phase95.analysis import _difference, _scenario, _trajectory_summary
from soil_simulator.phase96.values import as_float, as_int
from soil_simulator.population.batch import parameters_for_field
from soil_simulator.simulator.management import run_management_policy

POLICY_IDS = (
    "conventional_tillage",
    "reduced_tillage",
    "cover_crop",
    "phosphorus",
    "farmyard_manure",
)
OBSERVABLE_FEATURES = (
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


def _field_features(field: SyntheticField) -> dict[str, float]:
    properties = field.field
    weather = field.weather
    years = len(weather) / 12.0
    return {
        "clay_percent": properties.clay_percent,
        "silt_percent": properties.silt_percent,
        "sand_percent": properties.sand_percent,
        "bulk_density_g_cm3": properties.bulk_density_g_cm3,
        "ph": properties.ph,
        "cation_exchange_capacity_cmolc_kg": properties.cation_exchange_capacity_cmolc_kg,
        "baseline_total_nitrogen_percent": properties.baseline_total_nitrogen_percent,
        "baseline_soc_t_c_ha": properties.baseline_soc_t_c_ha,
        "mean_temperature_c": math.fsum(month.mean_air_temperature_c for month in weather)
        / len(weather),
        "annual_precipitation_mm": math.fsum(month.precipitation_mm for month in weather) / years,
        "annual_pet_mm": math.fsum(month.potential_evapotranspiration_mm for month in weather)
        / years,
    }


def build_effect_rows(
    population: SyntheticPopulation,
    template: ManagementScenarioSet,
    parameters: ModelParameters,
    population_config: PopulationGenerationConfig,
    accounting_schedule: AccountingSchedule,
) -> list[dict[str, object]]:
    """Simulate paired biological effects and retain schedule-derived accounting metadata."""
    rows: list[dict[str, object]] = []
    for field in population.fields:
        scenario = _scenario(field, template, population_config, 120)
        field_parameters = parameters_for_field(field, parameters)
        trajectories = {
            policy.policy_id: run_management_policy(scenario, policy, field_parameters)
            for policy in scenario.policies
        }
        features = _field_features(field)
        for horizon in (24, 60, 120):
            baseline = _trajectory_summary(trajectories["baseline"], horizon)
            for policy_id in POLICY_IDS:
                accounting = accrue_accounting(accounting_schedule, policy_id, horizon)
                effect = _difference(
                    _trajectory_summary(trajectories[policy_id], horizon), baseline
                )
                target_names = (
                    ("delta_yield_t_dm_ha",)
                    if horizon == 24
                    else (
                        "delta_total_soc_t_c_ha",
                        "delta_protected_soc_proxy_t_c_ha",
                        "delta_respiration_t_c_ha",
                    )
                )
                source_names = {
                    "delta_yield_t_dm_ha": "yield_t_dm_ha",
                    "delta_total_soc_t_c_ha": "total_soc_t_c_ha",
                    "delta_protected_soc_proxy_t_c_ha": "protected_soc_proxy_t_c_ha",
                    "delta_respiration_t_c_ha": "respiration_t_c_ha",
                }
                for target_name in target_names:
                    rows.append(
                        {
                            "row_id": (
                                f"{field.field.field_id}|{policy_id}|{horizon}|{target_name}"
                            ),
                            "field_id": field.field.field_id,
                            "empirical_location_id": field.empirical_seed_id,
                            "region_id": field.region_id,
                            "population_split": field.population_split.value,
                            "policy_id": policy_id,
                            "horizon_months": horizon,
                            "target_name": target_name,
                            "target_value": effect[source_names[target_name]],
                            "headline_eligible": policy_id != "phosphorus",
                            "deterministic_cost_gbp_ha": accounting.cost_gbp_ha,
                            "deterministic_operational_emissions_kg_co2e_ha": (
                                accounting.operational_emissions_kg_co2e_ha
                            ),
                            "deterministic_lifecycle_emissions_kg_co2e_ha": (
                                accounting.lifecycle_emissions_kg_co2e_ha
                            ),
                            "accounting_classification": (
                                "scenario_assumption_not_prediction_target"
                            ),
                            **features,
                        }
                    )
    return rows


def _matrix_fit(
    rows: list[dict[str, object]],
) -> tuple[dict[str, float], dict[str, float], tuple[tuple[float, ...], ...]]:
    means = {
        name: math.fsum(as_float(row[name]) for row in rows) / len(rows)
        for name in OBSERVABLE_FEATURES
    }
    scales: dict[str, float] = {}
    for name in OBSERVABLE_FEATURES:
        variance = math.fsum((as_float(row[name]) - means[name]) ** 2 for row in rows) / len(rows)
        scales[name] = math.sqrt(variance) if variance > 0.0 else 1.0
    return means, scales, _matrix_transform(rows, means, scales)


def _matrix_transform(
    rows: list[dict[str, object]], means: Mapping[str, float], scales: Mapping[str, float]
) -> tuple[tuple[float, ...], ...]:
    return tuple(
        (
            *((as_float(row[name]) - means[name]) / scales[name] for name in OBSERVABLE_FEATURES),
            *(1.0 if row["policy_id"] == policy else 0.0 for policy in POLICY_IDS),
        )
        for row in rows
    )


def _error(actual: tuple[float, ...], predicted: tuple[float, ...]) -> dict[str, float | None]:
    if not actual or len(actual) != len(predicted):
        raise ValueError("prediction metric inputs are empty or misaligned")
    residuals = tuple(predict - observe for observe, predict in zip(actual, predicted, strict=True))
    mean = math.fsum(actual) / len(actual)
    total = math.fsum((value - mean) ** 2 for value in actual)
    return {
        "mae": math.fsum(abs(value) for value in residuals) / len(residuals),
        "rmse": math.sqrt(math.fsum(value * value for value in residuals) / len(residuals)),
        "bias": math.fsum(residuals) / len(residuals),
        "r_squared": None
        if total == 0.0
        else 1.0 - math.fsum(value * value for value in residuals) / total,
    }


def _quantile(values: tuple[float, ...], probability: float) -> float:
    ordered = sorted(values)
    rank = min(len(ordered) - 1, math.ceil(probability * len(ordered)) - 1)
    return ordered[max(rank, 0)]


def _evaluate_partition(
    partition: list[dict[str, object]],
    means: Mapping[str, float],
    scales: Mapping[str, float],
    ridge_model: RidgeModel,
    policy_model: PolicyMeanModel,
    half_width: float,
) -> dict[str, object]:
    matrix = _matrix_transform(partition, means, scales)
    actual = tuple(as_float(row["target_value"]) for row in partition)
    partition_policies = tuple(str(row["policy_id"]) for row in partition)
    ridge_predictions = tuple(value[0] for value in ridge_model.predict(matrix, tuple()))
    mean_predictions = tuple(value[0] for value in policy_model.predict(matrix, partition_policies))
    coverage = math.fsum(
        abs(predicted - observed) <= half_width
        for observed, predicted in zip(actual, ridge_predictions, strict=True)
    ) / len(actual)
    return {
        "row_count": len(partition),
        "empirical_location_count": len({str(row["empirical_location_id"]) for row in partition}),
        "ridge": _error(actual, ridge_predictions),
        "policy_mean": _error(actual, mean_predictions),
        "validation_calibrated_90_percent_interval_coverage": coverage,
        "interval_half_width": half_width,
    }


def prediction_benchmark(rows: list[dict[str, object]]) -> dict[str, object]:
    """Compare ridge to policy means and decide whether downstream selection may run."""
    eligible = [row for row in rows if bool(row["headline_eligible"])]
    combinations = sorted(
        {(str(row["target_name"]), as_int(row["horizon_months"])) for row in eligible}
    )
    results: dict[str, object] = {}
    prediction_gate = True
    ood_gate = True
    uncertainty_gate = True
    for target_name, horizon in combinations:
        subset = [
            row
            for row in eligible
            if row["target_name"] == target_name and as_int(row["horizon_months"]) == horizon
        ]
        split = {
            name: [row for row in subset if row["population_split"] == name]
            for name in ("train", "validation", "test", "weather_ood")
        }
        train = split["train"]
        validation = split["validation"]
        test = split["test"]
        means, scales, train_matrix = _matrix_fit(train)
        train_targets = tuple((as_float(row["target_value"]),) for row in train)
        target_names = (target_name,)
        policies = tuple(str(row["policy_id"]) for row in train)
        policy_model = fit_policy_mean(train_targets, policies, target_names)
        validation_matrix = _matrix_transform(validation, means, scales)
        validation_targets = tuple(as_float(row["target_value"]) for row in validation)
        best_model = None
        best_score = math.inf
        for alpha in (0.1, 1.0, 10.0):
            model = fit_ridge(
                train_matrix,
                train_targets,
                target_names,
                (*OBSERVABLE_FEATURES, *(f"policy={policy}" for policy in POLICY_IDS)),
                alpha,
            )
            predictions = tuple(value[0] for value in model.predict(validation_matrix, tuple()))
            score_value = _error(validation_targets, predictions)["rmse"]
            assert score_value is not None
            score = score_value
            if score < best_score:
                best_model, best_score = model, score
        assert best_model is not None
        validation_predictions = tuple(
            value[0] for value in best_model.predict(validation_matrix, tuple())
        )
        half_width = _quantile(
            tuple(
                abs(predicted - actual)
                for actual, predicted in zip(
                    validation_targets, validation_predictions, strict=True
                )
            ),
            0.90,
        )

        test_result = _evaluate_partition(test, means, scales, best_model, policy_model, half_width)
        ood_result = _evaluate_partition(
            split["weather_ood"], means, scales, best_model, policy_model, half_width
        )
        test_ridge_metrics = cast(dict[str, float | None], test_result["ridge"])
        test_policy_metrics = cast(dict[str, float | None], test_result["policy_mean"])
        ood_ridge_metrics = cast(dict[str, float | None], ood_result["ridge"])
        ood_policy_metrics = cast(dict[str, float | None], ood_result["policy_mean"])
        test_ridge = test_ridge_metrics["rmse"]
        test_policy = test_policy_metrics["rmse"]
        ood_ridge = ood_ridge_metrics["rmse"]
        ood_policy = ood_policy_metrics["rmse"]
        if test_ridge is None or test_policy is None:
            raise ValueError("test RMSE is unexpectedly undefined")
        if ood_ridge is None or ood_policy is None:
            raise ValueError("OOD RMSE is unexpectedly undefined")
        beats_baseline = test_ridge < test_policy
        acceptable_ood = ood_ridge <= 1.10 * ood_policy
        calibrated = (
            0.80
            <= as_float(test_result["validation_calibrated_90_percent_interval_coverage"])
            <= 1.0
        )
        prediction_gate &= beats_baseline
        ood_gate &= acceptable_ood
        uncertainty_gate &= calibrated
        results[f"{target_name}|{horizon}"] = {
            "selected_alpha": best_model.alpha,
            "validation_rmse": best_score,
            "test": test_result,
            "ood": ood_result,
            "beats_policy_mean_on_test": beats_baseline,
            "acceptable_ood": acceptable_ood,
            "uncertainty_calibrated": calibrated,
        }
    independent_effect_validation = False
    all_gates = prediction_gate and ood_gate and uncertainty_gate and independent_effect_validation
    return {
        "targets": results,
        "gates": {
            "all_effect_targets_beat_policy_mean": prediction_gate,
            "all_effect_targets_have_acceptable_ood": ood_gate,
            "all_effect_targets_have_calibrated_uncertainty": uncertainty_gate,
            "empirical_location_leakage_check": True,
            "independent_empirical_effect_validation": independent_effect_validation,
        },
        "downstream_selection_executed": all_gates,
        "stop_decision": None
        if all_gates
        else (
            "Stop: at least one predeclared prediction, OOD, uncertainty or independent-effect "
            "validation gate failed; no Phase 9.6 selector, oracle or regret benchmark was run."
        ),
        "feature_separation": {
            "observable": list(OBSERVABLE_FEATURES),
            "latent_excluded": [
                "AMF allocation",
                "AMF CUE",
                "AMF turnover",
                "necromass stabilisation",
                "hidden initial pools",
                "spin-up diagnostics",
            ],
        },
        "excluded_headline_targets": [
            "final stock levels",
            "deterministic cost",
            "deterministic emissions",
            "phosphorus",
        ],
    }
