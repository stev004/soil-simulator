"""Phase 9.5 ML target framing and circularity diagnostics."""

from __future__ import annotations

import csv
import math
from collections.abc import Iterable
from pathlib import Path

HEADLINE_EFFECT_TARGETS: tuple[str, ...] = (
    "delta_crop_yield_t_dm_ha@24",
    "delta_final_total_soc_t_c_ha@60",
    "delta_final_total_soc_t_c_ha@120",
    "delta_final_protected_soc_proxy_t_c_ha@60",
    "delta_final_protected_soc_proxy_t_c_ha@120",
    "delta_cumulative_respiration_t_c_ha@60",
    "delta_cumulative_respiration_t_c_ha@120",
)

DIAGNOSTIC_ONLY_TARGETS: dict[str, str] = {
    "final_total_soc_t_c_ha": (
        "persistence-dominated stock target; not evidence of intervention-effect learning"
    ),
    "final_protected_soc_proxy_t_c_ha": (
        "persistence-dominated model-proxy stock target; not measured MAOC and not evidence "
        "of intervention-effect learning"
    ),
    "intervention_cost_gbp_ha": (
        "deterministic policy-identity lookup; compute from schedules, never score as ML skill"
    ),
    "emissions_proxy_kg_co2e_ha": (
        "deterministic policy-identity lookup; compute from schedules, never score as ML skill"
    ),
}

NON_ML_IDENTITY_TARGETS: tuple[str, ...] = (
    "intervention_cost_gbp_ha",
    "delta_intervention_cost_gbp_ha",
    "emissions_proxy_kg_co2e_ha",
    "delta_emissions_proxy_kg_co2e_ha",
)


def headline_target_manifest() -> dict[str, object]:
    """Return the frozen Phase 9.5 headline/diagnostic target contract."""
    return {
        "version": "0.9.5",
        "primary_ml_targets": HEADLINE_EFFECT_TARGETS,
        "diagnostic_only_targets": DIAGNOSTIC_ONLY_TARGETS,
        "excluded_from_ml_training_and_scoring": NON_ML_IDENTITY_TARGETS,
        "claim_boundary": (
            "Paired effects are synthetic simulator targets, not causal field effects."
        ),
    }


def pearson(values_x: Iterable[float], values_y: Iterable[float]) -> float:
    """Return finite Pearson correlation, or zero for a constant vector."""
    x = tuple(values_x)
    y = tuple(values_y)
    if len(x) != len(y) or not x:
        raise ValueError("correlation inputs must have equal non-zero length")
    mean_x = math.fsum(x) / len(x)
    mean_y = math.fsum(y) / len(y)
    dx = tuple(value - mean_x for value in x)
    dy = tuple(value - mean_y for value in y)
    denominator = math.sqrt(math.fsum(value * value for value in dx)) * math.sqrt(
        math.fsum(value * value for value in dy)
    )
    if denominator == 0.0:
        return 0.0
    return math.fsum(a * b for a, b in zip(dx, dy, strict=True)) / denominator


def _single_feature_fit(x: tuple[float, ...], y: tuple[float, ...]) -> tuple[float, ...]:
    mean_x = math.fsum(x) / len(x)
    mean_y = math.fsum(y) / len(y)
    variance = math.fsum((value - mean_x) ** 2 for value in x)
    slope = (
        0.0
        if variance == 0.0
        else math.fsum((a - mean_x) * (b - mean_y) for a, b in zip(x, y, strict=True)) / variance
    )
    intercept = mean_y - slope * mean_x
    return tuple(intercept + slope * value for value in x)


def _metrics(actual: tuple[float, ...], predicted: tuple[float, ...]) -> dict[str, float]:
    residuals = tuple(a - p for a, p in zip(actual, predicted, strict=True))
    mean = math.fsum(actual) / len(actual)
    ss_total = math.fsum((value - mean) ** 2 for value in actual)
    ss_error = math.fsum(value * value for value in residuals)
    return {
        "mae": math.fsum(abs(value) for value in residuals) / len(residuals),
        "rmse": math.sqrt(ss_error / len(residuals)),
        "r_squared": 0.0 if ss_total == 0.0 else 1.0 - ss_error / ss_total,
    }


def _incremental_fit(
    initial: tuple[float, ...], added: tuple[float, ...], target: tuple[float, ...]
) -> tuple[tuple[float, ...], tuple[float, ...]]:
    """Return initial-only and initial-plus-added orthogonalized predictions."""
    initial_prediction = _single_feature_fit(initial, target)
    added_given_initial = tuple(
        value - predicted
        for value, predicted in zip(added, _single_feature_fit(initial, added), strict=True)
    )
    target_residual = tuple(
        value - predicted for value, predicted in zip(target, initial_prediction, strict=True)
    )
    denominator = math.fsum(value * value for value in added_given_initial)
    coefficient = (
        0.0
        if denominator == 0.0
        else math.fsum(x * y for x, y in zip(added_given_initial, target_residual, strict=True))
        / denominator
    )
    combined = tuple(
        prediction + coefficient * residual
        for prediction, residual in zip(initial_prediction, added_given_initial, strict=True)
    )
    return initial_prediction, combined


def circularity_diagnostics(csv_path: str | Path) -> dict[str, object]:
    """Quantify stock persistence and initial-state dependence in a saved dataset."""
    with Path(csv_path).open(encoding="utf-8", newline="") as handle:
        rows = tuple(csv.DictReader(handle))
    stock_rows = tuple(
        row for row in rows if int(float(row["simulation_horizon_months"])) in {60, 120}
    )
    baseline_rows = tuple(row for row in stock_rows if row["policy_id"] == "baseline")
    initial_soc = tuple(float(row["baseline_soc_t_c_ha"]) for row in stock_rows)
    final_soc = tuple(float(row["final_total_soc_t_c_ha"]) for row in stock_rows)
    protected = tuple(float(row["final_protected_soc_proxy_t_c_ha"]) for row in stock_rows)
    clay = tuple(float(row["clay_percent"]) for row in stock_rows)
    baseline_initial = tuple(float(row["baseline_soc_t_c_ha"]) for row in baseline_rows)
    baseline_final = tuple(float(row["final_total_soc_t_c_ha"]) for row in baseline_rows)
    baseline_protected = tuple(
        float(row["final_protected_soc_proxy_t_c_ha"]) for row in baseline_rows
    )
    final_prediction = _single_feature_fit(baseline_initial, baseline_final)
    baseline_clay = tuple(float(row["clay_percent"]) for row in baseline_rows)
    protected_prediction, protected_initial_plus_clay = _incremental_fit(
        baseline_initial, baseline_clay, baseline_protected
    )
    # Clay's incremental diagnostic is the correlation with residual protected stock
    # after the initial-SOC-only fit. It is descriptive, not a causal attribution.
    protected_residual = tuple(
        actual - predicted
        for actual, predicted in zip(baseline_protected, protected_prediction, strict=True)
    )
    intervention_rows = tuple(row for row in stock_rows if row["policy_id"] != "baseline")
    effect_columns = (
        "delta_final_total_soc_t_c_ha",
        "delta_final_protected_soc_proxy_t_c_ha",
        "delta_cumulative_respiration_t_c_ha",
    )
    zero_effect_performance = {
        column: _metrics(
            tuple(float(row[column]) for row in intervention_rows),
            tuple(0.0 for _ in intervention_rows),
        )
        for column in effect_columns
    }
    yield_rows = tuple(
        row
        for row in rows
        if int(float(row["simulation_horizon_months"])) == 24 and row["policy_id"] != "baseline"
    )
    zero_effect_performance["delta_crop_yield_t_dm_ha"] = _metrics(
        tuple(float(row["delta_crop_yield_t_dm_ha"]) for row in yield_rows),
        tuple(0.0 for _ in yield_rows),
    )
    return {
        "version": "0.9.5",
        "source": str(csv_path),
        "row_count": len(stock_rows),
        "baseline_row_count": len(baseline_rows),
        "final_stock_correlation_with_initial_stock": pearson(initial_soc, final_soc),
        "protected_proxy_correlation_with_initial_soc": pearson(initial_soc, protected),
        "protected_proxy_correlation_with_clay": pearson(clay, protected),
        "protected_proxy_residual_correlation_with_clay_beyond_initial_soc": pearson(
            baseline_clay, protected_residual
        ),
        "initial_soc_only_final_stock_performance": _metrics(baseline_final, final_prediction),
        "initial_soc_only_protected_proxy_performance": _metrics(
            baseline_protected, protected_prediction
        ),
        "initial_soc_plus_clay_protected_proxy_performance": _metrics(
            baseline_protected, protected_initial_plus_clay
        ),
        "incremental_r_squared_from_clay_beyond_initial_soc": (
            _metrics(baseline_protected, protected_initial_plus_clay)["r_squared"]
            - _metrics(baseline_protected, protected_prediction)["r_squared"]
        ),
        "baseline_only_zero_effect_performance": zero_effect_performance,
        "interpretation": (
            "High stock performance is persistence-dominated. Incremental intervention skill "
            "must be assessed only on paired effects beyond the initial state."
        ),
    }
