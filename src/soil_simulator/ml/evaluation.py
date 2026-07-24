"""Metrics, residual diagnostics, and group-aware intervals for Phase 8.5."""

from __future__ import annotations

import math
import statistics
from collections.abc import Callable

from soil_simulator.ml.schema import TARGETS, MlRow


def target_matrix(
    rows: tuple[MlRow, ...], target_names: tuple[str, ...] = TARGETS
) -> tuple[tuple[float, ...], ...]:
    """Extract targets in an explicit stable order."""
    return tuple(tuple(row.targets[name] for name in target_names) for row in rows)


def policy_vector(rows: tuple[MlRow, ...]) -> tuple[str, ...]:
    """Extract policy identifiers for the policy-mean baseline."""
    return tuple(row.policy_id for row in rows)


def _percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = fraction * (len(ordered) - 1)
    lower = math.floor(position)
    upper = math.ceil(position)
    weight = position - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def regression_metrics(
    actual: tuple[tuple[float, ...], ...],
    predicted: tuple[tuple[float, ...], ...],
    target_names: tuple[str, ...] = TARGETS,
) -> dict[str, dict[str, float | None]]:
    """Calculate held-out errors and scale them by natural outcome variation."""
    if not actual or len(actual) != len(predicted):
        raise ValueError("metric inputs are empty or misaligned")
    result: dict[str, dict[str, float | None]] = {}
    for index, name in enumerate(target_names):
        observed = [row[index] for row in actual]
        estimates = [row[index] for row in predicted]
        errors = [estimate - value for estimate, value in zip(estimates, observed, strict=True)]
        mae = math.fsum(abs(error) for error in errors) / len(errors)
        rmse = math.sqrt(math.fsum(error * error for error in errors) / len(errors))
        mean = math.fsum(observed) / len(observed)
        total = math.fsum((value - mean) ** 2 for value in observed)
        residual = math.fsum(error * error for error in errors)
        variation = math.sqrt(total / len(observed))
        result[name] = {
            "mae": mae,
            "rmse": rmse,
            "r_squared": None if total <= 0.0 else 1.0 - residual / total,
            "natural_field_to_field_sd": variation,
            "mae_relative_to_natural_variation": None if variation <= 0.0 else mae / variation,
            "sample_count": float(len(observed)),
        }
    return result


def mean_normalised_rmse(metrics: dict[str, dict[str, float | None]]) -> float:
    """Return a scale-independent validation score across all explicit targets."""
    values: list[float] = []
    for item in metrics.values():
        variation = item["natural_field_to_field_sd"]
        rmse = item["rmse"]
        if isinstance(variation, float) and variation > 0.0 and isinstance(rmse, float):
            values.append(rmse / variation)
    if not values:
        raise ValueError("no varying validation target is available")
    return math.fsum(values) / len(values)


def grouped_metrics(
    rows: tuple[MlRow, ...],
    actual: tuple[tuple[float, ...], ...],
    predicted: tuple[tuple[float, ...], ...],
    key: Callable[[MlRow], str],
) -> dict[str, dict[str, dict[str, float | None]]]:
    """Calculate the same honest metrics within a policy or field subgroup."""
    groups: dict[str, list[int]] = {}
    for index, row in enumerate(rows):
        groups.setdefault(key(row), []).append(index)
    return {
        group: regression_metrics(
            tuple(actual[index] for index in indices),
            tuple(predicted[index] for index in indices),
        )
        for group, indices in sorted(groups.items())
    }


def residual_diagnostics(
    actual: tuple[tuple[float, ...], ...],
    predicted: tuple[tuple[float, ...], ...],
    target_names: tuple[str, ...] = TARGETS,
) -> dict[str, dict[str, float]]:
    """Summarise held-out signed residual distributions without hiding tails."""
    diagnostics: dict[str, dict[str, float]] = {}
    for index, name in enumerate(target_names):
        residuals = [pred[index] - obs[index] for pred, obs in zip(predicted, actual, strict=True)]
        diagnostics[name] = {
            "mean_residual": statistics.fmean(residuals),
            "residual_sd": statistics.pstdev(residuals),
            "median_residual": statistics.median(residuals),
            "p05_residual": _percentile(residuals, 0.05),
            "p95_residual": _percentile(residuals, 0.95),
            "maximum_absolute_residual": max(abs(value) for value in residuals),
        }
    return diagnostics


def fit_conformal_half_widths(
    actual: tuple[tuple[float, ...], ...],
    predicted: tuple[tuple[float, ...], ...],
    alpha: float,
    target_names: tuple[str, ...] = TARGETS,
) -> dict[str, float]:
    """Fit finite-sample split-conformal absolute-residual half-widths."""
    if not 0.0 < alpha < 1.0 or not actual or len(actual) != len(predicted):
        raise ValueError("invalid conformal calibration inputs")
    sample_count = len(actual)
    rank = min(sample_count, math.ceil((sample_count + 1) * (1.0 - alpha)))
    result: dict[str, float] = {}
    for index, name in enumerate(target_names):
        residuals = sorted(
            abs(pred[index] - obs[index]) for pred, obs in zip(predicted, actual, strict=True)
        )
        result[name] = residuals[rank - 1]
    return result


def fit_group_conformal_half_widths(
    rows: tuple[MlRow, ...],
    actual: tuple[tuple[float, ...], ...],
    predicted: tuple[tuple[float, ...], ...],
    alpha: float,
    minimum_groups: int,
    target_names: tuple[str, ...] = TARGETS,
) -> tuple[dict[str, float], dict[str, object]]:
    """Calibrate constant widths from validation-group residual quantiles only.

    Each empirical-seed group contributes one within-group residual quantile.
    A finite-sample conformal rank is then applied across groups so large groups
    cannot dominate calibration.  If too few groups are available, widths are
    still reported but the calibration claim explicitly abstains.
    """
    if len(rows) != len(actual) or len(rows) != len(predicted) or not rows:
        raise ValueError("group-aware calibration inputs are empty or misaligned")
    groups: dict[str, list[int]] = {}
    for index, row in enumerate(rows):
        groups.setdefault(row.empirical_seed_id, []).append(index)
    group_count = len(groups)
    if group_count < 2:
        raise ValueError("group-aware calibration requires at least two empirical-seed groups")
    group_rank = min(group_count, math.ceil((group_count + 1) * (1.0 - alpha)))
    widths: dict[str, float] = {}
    group_quantiles: dict[str, dict[str, float]] = {}
    for target_index, name in enumerate(target_names):
        values: list[tuple[str, float]] = []
        for group, indices in sorted(groups.items()):
            residuals = sorted(
                abs(predicted[index][target_index] - actual[index][target_index])
                for index in indices
            )
            within_rank = min(len(residuals), math.ceil((len(residuals) + 1) * (1.0 - alpha)))
            values.append((group, residuals[within_rank - 1]))
        ordered = sorted(value for _, value in values)
        widths[name] = ordered[group_rank - 1]
        group_quantiles[name] = dict(values)
    sufficient = group_count >= minimum_groups
    return widths, {
        "calibration_group_count": group_count,
        "minimum_groups_for_claim": minimum_groups,
        "calibration_claim_supported": sufficient,
        "claim": (
            "group-aware synthetic validation coverage may be assessed"
            if sufficient
            else "abstain: insufficient independent validation groups for a calibration claim"
        ),
        "group_residual_quantiles": group_quantiles,
    }


def grouped_interval_diagnostics(
    rows: tuple[MlRow, ...],
    actual: tuple[tuple[float, ...], ...],
    predicted: tuple[tuple[float, ...], ...],
    half_widths: dict[str, float],
    key: Callable[[MlRow], str],
    minimum_rows: int,
    target_names: tuple[str, ...] = TARGETS,
) -> dict[str, object]:
    """Report interval coverage by subgroup and abstain for small groups."""
    groups: dict[str, list[int]] = {}
    for index, row in enumerate(rows):
        groups.setdefault(key(row), []).append(index)
    result: dict[str, object] = {}
    for group, indices in sorted(groups.items()):
        diagnostics = interval_diagnostics(
            tuple(actual[index] for index in indices),
            tuple(predicted[index] for index in indices),
            half_widths,
            target_names,
        )
        result[group] = {
            "row_count": len(indices),
            "coverage_claim_supported": len(indices) >= minimum_rows,
            "claim": (
                "synthetic subgroup coverage reported"
                if len(indices) >= minimum_rows
                else "abstain: insufficient subgroup rows for a calibration claim"
            ),
            "targets": diagnostics,
        }
    return result


def interval_diagnostics(
    actual: tuple[tuple[float, ...], ...],
    predicted: tuple[tuple[float, ...], ...],
    half_widths: dict[str, float],
    target_names: tuple[str, ...] = TARGETS,
) -> dict[str, dict[str, float]]:
    """Measure held-out marginal coverage and constant interval width."""
    if not actual or len(actual) != len(predicted):
        raise ValueError("invalid interval evaluation inputs")
    result: dict[str, dict[str, float]] = {}
    for index, name in enumerate(target_names):
        half_width = half_widths[name]
        covered = math.fsum(
            1.0 if pred[index] - half_width <= obs[index] <= pred[index] + half_width else 0.0
            for pred, obs in zip(predicted, actual, strict=True)
        )
        result[name] = {
            "coverage": covered / len(actual),
            "mean_interval_width": 2.0 * half_width,
            "sample_count": float(len(actual)),
        }
    return result


def paired_effect_metrics(
    metrics: dict[str, dict[str, float | None]],
) -> dict[str, dict[str, float | None]]:
    """Select the intervention-minus-baseline target errors explicitly."""
    return {name: value for name, value in metrics.items() if name.startswith("delta_")}


def pearson_correlation(left: list[float], right: list[float]) -> float | None:
    """Return Pearson correlation for an engineered-correlation audit."""
    if len(left) != len(right) or len(left) < 2:
        raise ValueError("correlation inputs are misaligned")
    left_mean = statistics.fmean(left)
    right_mean = statistics.fmean(right)
    numerator = math.fsum(
        (x - left_mean) * (y - right_mean) for x, y in zip(left, right, strict=True)
    )
    left_ss = math.fsum((x - left_mean) ** 2 for x in left)
    right_ss = math.fsum((y - right_mean) ** 2 for y in right)
    denominator = math.sqrt(left_ss * right_ss)
    return None if denominator <= 0.0 else numerator / denominator
