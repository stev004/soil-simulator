"""Genuine Sobol/Saltelli-compatible sampling and convergence evidence.

The sampler uses SciPy's maintained scrambled Sobol engine.  One ``2D``
unit-cube design is split into A and B matrices; A_B(i) hybrids provide the
Saltelli/Jansen first- and total-order estimators.  Negative estimates are
retained because they diagnose finite-sample estimator noise.
"""

from __future__ import annotations

import hashlib
import json
import math
import multiprocessing
import time
from collections.abc import Callable, Mapping, Sequence
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from importlib import import_module
from itertools import pairwise
from pathlib import Path
from typing import Any, cast

import yaml

from soil_simulator.phase95.sensitivity import SensitivityParameter
from soil_simulator.phase96.values import as_float, as_int

# NumPy/SciPy are loaded dynamically because their current upstream type stubs
# require a newer mypy target than this Python >=3.11 project. Runtime versions
# and exact design hashes are still recorded in every sampling manifest.
np: Any = import_module("numpy")
qmc: Any = import_module("scipy.stats.qmc")
rankdata: Any = import_module("scipy.stats").rankdata
scipy_version = str(import_module("scipy").__version__)

VectorEvaluator = Callable[[Mapping[str, float]], Mapping[str, float]]


@dataclass(frozen=True)
class ConvergenceRule:
    """Predeclared numerical convergence thresholds for Sobol estimates."""

    maximum_absolute_index_change: float
    minimum_rank_correlation: float
    maximum_mean_confidence_interval_width: float
    maximum_unstable_fraction: float


@dataclass(frozen=True)
class SobolSettings:
    """Validated Phase 9.7 Sobol design settings."""

    seed: int
    base_sample_sizes: tuple[int, ...]
    bootstrap_replicates: int
    confidence_level: float
    evaluation_workers: int
    selected_parameter_names: tuple[str, ...]
    convergence_rule: ConvergenceRule


def _power_of_two(value: int) -> bool:
    return value > 0 and value & (value - 1) == 0


def load_phase97_settings(path: str | Path) -> SobolSettings:
    """Load and validate the power-of-two Phase 9.7 convergence design."""
    raw = cast(dict[str, Any], yaml.safe_load(Path(path).read_text(encoding="utf-8")))
    if raw.get("version") != "0.9.7":
        raise ValueError("Phase 9.7 sensitivity settings must use version 0.9.7")
    sizes = tuple(as_int(value) for value in cast(list[object], raw["base_sample_sizes"]))
    if not sizes or tuple(sorted(set(sizes))) != sizes or any(not _power_of_two(n) for n in sizes):
        raise ValueError("Sobol base sample sizes must be unique increasing powers of two")
    if sizes[0] < 128:
        raise ValueError("Phase 9.7 Sobol convergence must start at 128 base samples or more")
    bootstrap_replicates = int(raw["bootstrap_replicates"])
    if bootstrap_replicates < 100:
        raise ValueError("at least 100 bootstrap replicates are required")
    confidence_level = float(raw["confidence_level"])
    if not 0.5 < confidence_level < 1.0:
        raise ValueError("confidence level must lie between 0.5 and 1.0")
    rule_raw = cast(dict[str, object], raw["convergence_rule"])
    return SobolSettings(
        seed=int(raw["seed"]),
        base_sample_sizes=sizes,
        bootstrap_replicates=bootstrap_replicates,
        confidence_level=confidence_level,
        evaluation_workers=as_int(raw.get("evaluation_workers", 1)),
        selected_parameter_names=tuple(
            str(value) for value in cast(list[object], raw["selected_parameters"])
        ),
        convergence_rule=ConvergenceRule(
            maximum_absolute_index_change=as_float(rule_raw["maximum_absolute_index_change"]),
            minimum_rank_correlation=as_float(rule_raw["minimum_rank_correlation"]),
            maximum_mean_confidence_interval_width=float(
                as_float(rule_raw["maximum_mean_confidence_interval_width"])
            ),
            maximum_unstable_fraction=as_float(rule_raw["maximum_unstable_fraction"]),
        ),
    )


_PROCESS_EVALUATOR: VectorEvaluator | None = None
_PROCESS_PARAMETERS: Sequence[SensitivityParameter] = ()
_PROCESS_RETAINED_OUTPUT: Callable[[str], bool] | None = None


def _process_evaluate(row: tuple[float, ...]) -> dict[str, float]:
    """Evaluate one unit row in a forked deterministic worker."""
    if _PROCESS_EVALUATOR is None or _PROCESS_RETAINED_OUTPUT is None:
        raise RuntimeError("parallel Sobol evaluator was not initialised")
    raw = _PROCESS_EVALUATOR(transform_unit_row(_PROCESS_PARAMETERS, row))
    return {name: float(value) for name, value in raw.items() if _PROCESS_RETAINED_OUTPUT(name)}


def sobol_unit_matrices(dimension: int, base_sample_size: int, seed: int) -> tuple[Any, Any, str]:
    """Return scrambled Sobol A/B matrices and their exact float-byte hash."""
    if dimension < 1:
        raise ValueError("Sobol dimension must be positive")
    if not _power_of_two(base_sample_size):
        raise ValueError("Sobol base sample size must be a power of two")
    engine = qmc.Sobol(d=2 * dimension, scramble=True, seed=seed)
    design = engine.random_base2(int(math.log2(base_sample_size)))
    matrix_a = design[:, :dimension]
    matrix_b = design[:, dimension:]
    digest = hashlib.sha256(design.astype("<f8", copy=False).tobytes()).hexdigest()
    return matrix_a, matrix_b, digest


def transform_unit_row(
    parameters: Sequence[SensitivityParameter], row: Sequence[float]
) -> dict[str, float]:
    """Transform one unit-cube row through the configured distributions."""
    if len(parameters) != len(row):
        raise ValueError("parameter and unit-row dimensions differ")
    return {
        parameter.name: parameter.transform(float(value))
        for parameter, value in zip(parameters, row, strict=True)
    }


def _variance(values_a: np.ndarray, values_b: np.ndarray) -> float:
    return float(np.var(np.concatenate((values_a, values_b)), ddof=0))


def _one_estimate(
    values_a: np.ndarray, values_b: np.ndarray, values_ab: np.ndarray
) -> tuple[float | None, float | None]:
    variance = _variance(values_a, values_b)
    if variance == 0.0:
        return None, None
    first = float(np.mean(values_b * (values_ab - values_a)) / variance)
    total = float(np.mean((values_a - values_ab) ** 2) / (2.0 * variance))
    return first, total


def _percentile_interval(values: np.ndarray, confidence_level: float) -> tuple[float, float]:
    tail = (1.0 - confidence_level) / 2.0
    lower, upper = np.quantile(values, (tail, 1.0 - tail), method="linear")
    return float(lower), float(upper)


def estimate_indices(
    evaluations_a: Sequence[Mapping[str, float]],
    evaluations_b: Sequence[Mapping[str, float]],
    hybrid_evaluations: Mapping[str, Sequence[Mapping[str, float]]],
    *,
    parameter_names: Sequence[str],
    bootstrap_replicates: int,
    confidence_level: float,
    bootstrap_seed: int,
) -> dict[str, object]:
    """Estimate S1/ST with deterministic bootstrap confidence intervals."""
    if not evaluations_a or len(evaluations_a) != len(evaluations_b):
        raise ValueError("Sobol A/B evaluations must be non-empty and aligned")
    sample_size = len(evaluations_a)
    outputs = tuple(evaluations_a[0])
    rng = np.random.default_rng(bootstrap_seed)
    resamples = rng.integers(0, sample_size, size=(bootstrap_replicates, sample_size))
    result: dict[str, object] = {}
    for output in outputs:
        values_a = np.asarray([item[output] for item in evaluations_a], dtype=float)
        values_b = np.asarray([item[output] for item in evaluations_b], dtype=float)
        variance = _variance(values_a, values_b)
        indices: dict[str, object] = {}
        for parameter_name in parameter_names:
            values_ab = np.asarray(
                [item[output] for item in hybrid_evaluations[parameter_name]], dtype=float
            )
            first, total = _one_estimate(values_a, values_b, values_ab)
            if first is None or total is None:
                first_ci: tuple[float, float] | None = None
                total_ci: tuple[float, float] | None = None
            else:
                bootstrap_first = np.empty(bootstrap_replicates, dtype=float)
                bootstrap_total = np.empty(bootstrap_replicates, dtype=float)
                for index, selected in enumerate(resamples):
                    boot_first, boot_total = _one_estimate(
                        values_a[selected], values_b[selected], values_ab[selected]
                    )
                    bootstrap_first[index] = math.nan if boot_first is None else boot_first
                    bootstrap_total[index] = math.nan if boot_total is None else boot_total
                first_ci = _percentile_interval(
                    bootstrap_first[np.isfinite(bootstrap_first)], confidence_level
                )
                total_ci = _percentile_interval(
                    bootstrap_total[np.isfinite(bootstrap_total)], confidence_level
                )
            indices[parameter_name] = {
                "first_order": first,
                "first_order_confidence_interval": first_ci,
                "total_order": total,
                "total_order_confidence_interval": total_ci,
                "first_order_negative": first is not None and first < 0.0,
                "total_order_negative": total is not None and total < 0.0,
                "interaction_remainder": (
                    None if first is None or total is None else total - first
                ),
            }
        result[output] = {"variance": variance, "indices": indices}
    return {
        "base_sample_size": sample_size,
        "estimator": {
            "first_order": "Saltelli 2010 covariance estimator",
            "total_order": "Jansen 1999 squared-difference estimator",
            "variance": "population variance of concatenated A and B evaluations",
            "negative_estimates": "retained without clipping",
        },
        "bootstrap_replicates": bootstrap_replicates,
        "confidence_level": confidence_level,
        "outputs": result,
    }


def _spearman(left: Sequence[float], right: Sequence[float]) -> float:
    if len(left) != len(right) or not left:
        raise ValueError("rank vectors must be non-empty and aligned")
    left_rank = rankdata(np.asarray(left, dtype=float), method="average")
    right_rank = rankdata(np.asarray(right, dtype=float), method="average")
    if np.std(left_rank) == 0.0 or np.std(right_rank) == 0.0:
        return 1.0 if np.array_equal(left_rank, right_rank) else 0.0
    return float(np.corrcoef(left_rank, right_rank)[0, 1])


def convergence_diagnostics(
    estimates: Mapping[int, Mapping[str, object]], rule: ConvergenceRule
) -> dict[str, object]:
    """Compare each nested size to its predecessor under a predeclared rule."""
    sizes = tuple(sorted(estimates))
    comparisons: list[dict[str, object]] = []
    for previous_size, current_size in pairwise(sizes):
        previous_outputs = cast(dict[str, dict[str, object]], estimates[previous_size]["outputs"])
        current_outputs = cast(dict[str, dict[str, object]], estimates[current_size]["outputs"])
        first_previous: list[float] = []
        first_current: list[float] = []
        total_previous: list[float] = []
        total_current: list[float] = []
        ci_widths: list[float] = []
        negative_count = 0
        defined_count = 0
        unstable_count = 0
        for output, payload in current_outputs.items():
            current_indices = cast(dict[str, dict[str, object]], payload["indices"])
            previous_indices = cast(
                dict[str, dict[str, object]], previous_outputs[output]["indices"]
            )
            for name, current in current_indices.items():
                previous = previous_indices[name]
                current_first = current["first_order"]
                current_total = current["total_order"]
                previous_first = previous["first_order"]
                previous_total = previous["total_order"]
                if not all(
                    isinstance(value, (float, int))
                    for value in (
                        current_first,
                        current_total,
                        previous_first,
                        previous_total,
                    )
                ):
                    continue
                cf = as_float(current_first)
                ct = as_float(current_total)
                pf = as_float(previous_first)
                pt = as_float(previous_total)
                first_previous.append(pf)
                first_current.append(cf)
                total_previous.append(pt)
                total_current.append(ct)
                defined_count += 2
                negative_count += int(cf < 0.0) + int(ct < 0.0)
                unstable_count += int(abs(cf - pf) > rule.maximum_absolute_index_change) + int(
                    abs(ct - pt) > rule.maximum_absolute_index_change
                )
                for key in (
                    "first_order_confidence_interval",
                    "total_order_confidence_interval",
                ):
                    interval = current[key]
                    if isinstance(interval, (list, tuple)) and len(interval) == 2:
                        ci_widths.append(float(interval[1]) - float(interval[0]))
        max_first_change = max(
            (abs(a - b) for a, b in zip(first_previous, first_current, strict=True)),
            default=math.inf,
        )
        max_total_change = max(
            (abs(a - b) for a, b in zip(total_previous, total_current, strict=True)),
            default=math.inf,
        )
        first_rank = _spearman(first_previous, first_current) if first_current else 0.0
        total_rank = _spearman(total_previous, total_current) if total_current else 0.0
        mean_width = math.fsum(ci_widths) / len(ci_widths) if ci_widths else math.inf
        unstable_fraction = unstable_count / defined_count if defined_count else 1.0
        negative_fraction = negative_count / defined_count if defined_count else 1.0
        passed = (
            max(max_first_change, max_total_change) <= rule.maximum_absolute_index_change
            and min(first_rank, total_rank) >= rule.minimum_rank_correlation
            and mean_width <= rule.maximum_mean_confidence_interval_width
            and unstable_fraction <= rule.maximum_unstable_fraction
        )
        comparisons.append(
            {
                "previous_base_sample_size": previous_size,
                "current_base_sample_size": current_size,
                "maximum_absolute_first_order_change": max_first_change,
                "maximum_absolute_total_order_change": max_total_change,
                "first_order_rank_correlation": first_rank,
                "total_order_rank_correlation": total_rank,
                "mean_confidence_interval_width": mean_width,
                "unstable_estimate_fraction": unstable_fraction,
                "negative_estimate_fraction": negative_fraction,
                "passed": passed,
            }
        )
    reached = bool(comparisons) and bool(comparisons[-1]["passed"])
    return {
        "predeclared_rule": {
            "maximum_absolute_index_change": rule.maximum_absolute_index_change,
            "minimum_rank_correlation": rule.minimum_rank_correlation,
            "maximum_mean_confidence_interval_width": (rule.maximum_mean_confidence_interval_width),
            "maximum_unstable_fraction": rule.maximum_unstable_fraction,
            "decision_basis": "largest two nested base-sample sizes",
        },
        "comparisons": comparisons,
        "convergence_reached": reached,
        "status": "converged" if reached else "not_converged_results_not_final",
    }


def policy_ranking_stability(
    evaluations_a: Sequence[Mapping[str, float]], base_sample_sizes: Sequence[int]
) -> dict[str, object]:
    """Report policy mean-rank and winner stability across nested designs."""
    if not evaluations_a:
        raise ValueError("policy ranking requires A-matrix evaluations")
    labels: dict[str, set[str]] = {}
    for key in evaluations_a[0]:
        policy, target, horizon = key.split("|", 2)
        labels.setdefault(f"{target}|{horizon}", set()).add(policy)
    final_size = max(base_sample_sizes)
    result: dict[str, object] = {}
    for label, policies_set in sorted(labels.items()):
        policies = tuple(sorted(policies_set))
        target, horizon = label.split("|", 1)
        rankings: dict[int, tuple[str, ...]] = {}
        means_by_size: dict[int, dict[str, float]] = {}
        for size in base_sample_sizes:
            means = {
                policy: math.fsum(
                    row[f"{policy}|{target}|{horizon}"] for row in evaluations_a[:size]
                )
                / size
                for policy in policies
            }
            means_by_size[size] = means
            rankings[size] = tuple(sorted(policies, key=means.__getitem__, reverse=True))
        final_ranking = rankings[final_size]
        result[label] = {
            "mean_effect_by_base_sample_size": {
                str(size): means_by_size[size] for size in base_sample_sizes
            },
            "ranking_by_base_sample_size": {
                str(size): rankings[size] for size in base_sample_sizes
            },
            "rank_correlation_with_largest_design": {
                str(size): _spearman(
                    [rankings[size].index(policy) for policy in policies],
                    [final_ranking.index(policy) for policy in policies],
                )
                for size in base_sample_sizes
            },
            "winner_stable_with_largest_design": {
                str(size): rankings[size][0] == final_ranking[0] for size in base_sample_sizes
            },
        }
    return result


def run_nested_sobol(
    parameters: Sequence[SensitivityParameter],
    evaluator: VectorEvaluator,
    settings: SobolSettings,
    *,
    retained_outputs: Callable[[str], bool],
) -> dict[str, object]:
    """Evaluate one nested scrambled design and calculate all convergence sizes."""
    if tuple(parameter.name for parameter in parameters) != settings.selected_parameter_names:
        raise ValueError("selected sensitivity parameters do not match the predeclared order")
    maximum = max(settings.base_sample_sizes)
    matrix_a, matrix_b, design_hash = sobol_unit_matrices(len(parameters), maximum, settings.seed)

    def evaluate_row(row: Any) -> dict[str, float]:
        raw = evaluator(transform_unit_row(parameters, row))
        return {name: float(value) for name, value in raw.items() if retained_outputs(name)}

    evaluations_a: list[dict[str, float]] = []
    evaluations_b: list[dict[str, float]] = []
    hybrids: dict[str, list[dict[str, float]]] = {parameter.name: [] for parameter in parameters}
    checkpoint_runtime: dict[int, float] = {}
    actual_workers = settings.evaluation_workers
    started = time.perf_counter()
    if settings.evaluation_workers == 1:
        for row_index in range(maximum):
            row_a = matrix_a[row_index]
            row_b = matrix_b[row_index]
            evaluations_a.append(evaluate_row(row_a))
            evaluations_b.append(evaluate_row(row_b))
            for parameter_index, parameter in enumerate(parameters):
                hybrid = row_a.copy()
                hybrid[parameter_index] = row_b[parameter_index]
                hybrids[parameter.name].append(evaluate_row(hybrid))
            completed = row_index + 1
            if completed in settings.base_sample_sizes:
                checkpoint_runtime[completed] = time.perf_counter() - started
    else:
        rows: list[tuple[float, ...]] = []
        for row_index in range(maximum):
            row_a = matrix_a[row_index]
            row_b = matrix_b[row_index]
            rows.extend((tuple(row_a), tuple(row_b)))
            for parameter_index in range(len(parameters)):
                hybrid = row_a.copy()
                hybrid[parameter_index] = row_b[parameter_index]
                rows.append(tuple(hybrid))
        global _PROCESS_EVALUATOR, _PROCESS_PARAMETERS, _PROCESS_RETAINED_OUTPUT
        _PROCESS_EVALUATOR = evaluator
        _PROCESS_PARAMETERS = parameters
        _PROCESS_RETAINED_OUTPUT = retained_outputs
        context = multiprocessing.get_context("fork")
        try:
            with ProcessPoolExecutor(
                max_workers=settings.evaluation_workers, mp_context=context
            ) as executor:
                results = list(executor.map(_process_evaluate, rows, chunksize=8))
        except PermissionError:
            actual_workers = 1
            results = [_process_evaluate(row) for row in rows]
        stride = len(parameters) + 2
        for row_index in range(maximum):
            offset = row_index * stride
            evaluations_a.append(results[offset])
            evaluations_b.append(results[offset + 1])
            for parameter_index, parameter in enumerate(parameters):
                hybrids[parameter.name].append(results[offset + 2 + parameter_index])
        total_runtime = time.perf_counter() - started
        checkpoint_runtime = {
            size: total_runtime * size / maximum for size in settings.base_sample_sizes
        }
    estimates: dict[int, Mapping[str, object]] = {}
    index_runtime: dict[int, float] = {}
    for size in settings.base_sample_sizes:
        index_started = time.perf_counter()
        estimates[size] = estimate_indices(
            evaluations_a[:size],
            evaluations_b[:size],
            {name: rows[:size] for name, rows in hybrids.items()},
            parameter_names=settings.selected_parameter_names,
            bootstrap_replicates=settings.bootstrap_replicates,
            confidence_level=settings.confidence_level,
            bootstrap_seed=settings.seed + size,
        )
        index_runtime[size] = time.perf_counter() - index_started
    convergence = convergence_diagnostics(estimates, settings.convergence_rule)
    sampling_manifest = {
        "sampler": "scipy.stats.qmc.Sobol",
        "scipy_version": scipy_version,
        "scramble": True,
        "seed": settings.seed,
        "dimension": len(parameters),
        "construction": "one 2D Sobol design split column-wise into A and B",
        "base_sample_sizes": settings.base_sample_sizes,
        "evaluation_workers_requested": settings.evaluation_workers,
        "evaluation_workers_actual": actual_workers,
        "largest_design_sha256_float64_le": design_hash,
        "parameter_order": settings.selected_parameter_names,
        "transforms": {
            parameter.name: {
                "distribution": parameter.distribution,
                "minimum": parameter.minimum,
                "maximum": parameter.maximum,
                "classification": parameter.classification,
                "source": parameter.source,
            }
            for parameter in parameters
        },
        "evaluation_count_by_base_sample_size": {
            str(size): size * (len(parameters) + 2) for size in settings.base_sample_sizes
        },
        "cumulative_evaluation_runtime_seconds": {
            str(size): checkpoint_runtime[size] for size in settings.base_sample_sizes
        },
        "index_runtime_seconds": {
            str(size): index_runtime[size] for size in settings.base_sample_sizes
        },
        "uncertainty_separation": {
            "numerical_estimator_noise": (
                "bootstrap confidence intervals, negative estimates and convergence deltas"
            ),
            "biological_and_scenario_uncertainty": (
                "declared input distributions, bounds and source classifications"
            ),
        },
    }
    return {
        "sampling_manifest": sampling_manifest,
        "estimates": {str(size): estimates[size] for size in settings.base_sample_sizes},
        "convergence": convergence,
        "policy_ranking_stability": policy_ranking_stability(
            evaluations_a, settings.base_sample_sizes
        ),
        "result_sha256": hashlib.sha256(
            json.dumps(
                {str(size): estimates[size] for size in settings.base_sample_sizes},
                sort_keys=True,
                separators=(",", ":"),
            ).encode()
        ).hexdigest(),
    }
