"""Deterministic Morris screening and Saltelli/Sobol estimators.

The implementation is dependency-light so tests remain offline.  Parameter
transforms cover the complete registered ranges; no range is silently narrowed.
First-order and total-order indices are reported when output variance is nonzero.
"""

from __future__ import annotations

import math
import random
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

import yaml


@dataclass(frozen=True)
class SensitivityParameter:
    """One fully bounded parameter distribution from the assumptions registry."""

    name: str
    minimum: float
    maximum: float
    distribution: str
    classification: str
    source: str

    def transform(self, quantile: float) -> float:
        """Map a unit quantile to the declared full-range distribution."""
        q = min(1.0, max(0.0, quantile))
        if self.distribution == "uniform":
            scaled = q
        elif self.distribution == "uniform_discrete":
            value = round(self.minimum + q * (self.maximum - self.minimum))
            return float(value)
        elif self.distribution == "log_uniform":
            if self.minimum <= 0.0:
                raise ValueError("log-uniform parameters require a positive minimum")
            return math.exp(math.log(self.minimum) + q * math.log(self.maximum / self.minimum))
        elif self.distribution.startswith("triangular_"):
            mode = float(self.distribution.split("_", 1)[1])
            fraction = (mode - self.minimum) / (self.maximum - self.minimum)
            if q < fraction:
                return self.minimum + math.sqrt(
                    q * (self.maximum - self.minimum) * (mode - self.minimum)
                )
            return self.maximum - math.sqrt(
                (1.0 - q) * (self.maximum - self.minimum) * (self.maximum - mode)
            )
        elif self.distribution.startswith("beta_scaled_"):
            _, _, alpha_text, beta_text = self.distribution.split("_")
            scaled = _inverse_integer_beta(q, int(alpha_text), int(beta_text))
        else:
            raise ValueError(f"unsupported sensitivity distribution {self.distribution!r}")
        return self.minimum + scaled * (self.maximum - self.minimum)


def _integer_beta_cdf(value: float, alpha: int, beta: int) -> float:
    n = alpha + beta - 1
    return math.fsum(
        math.comb(n, j) * value**j * (1.0 - value) ** (n - j) for j in range(alpha, n + 1)
    )


def _inverse_integer_beta(quantile: float, alpha: int, beta: int) -> float:
    if quantile <= 0.0:
        return 0.0
    if quantile >= 1.0:
        return 1.0
    lower = 0.0
    upper = 1.0
    for _ in range(60):
        midpoint = (lower + upper) / 2.0
        if _integer_beta_cdf(midpoint, alpha, beta) < quantile:
            lower = midpoint
        else:
            upper = midpoint
    return (lower + upper) / 2.0


VectorEvaluator = Callable[[Mapping[str, float]], Mapping[str, float]]


@dataclass(frozen=True)
class SensitivitySpecification:
    """Validated execution settings and full-range parameter declarations."""

    version: str
    seed: int
    morris_trajectories: int
    morris_levels: int
    sobol_base_sample_size: int
    sobol_parameter_count: int
    parameters: tuple[SensitivityParameter, ...]


def load_sensitivity_specification(path: str | Path) -> SensitivitySpecification:
    """Load and minimally validate the offline Phase 9.5 YAML specification."""
    raw = cast(dict[str, Any], yaml.safe_load(Path(path).read_text(encoding="utf-8")))
    parameters = tuple(
        SensitivityParameter(
            name=str(item["name"]),
            minimum=float(item["minimum"]),
            maximum=float(item["maximum"]),
            distribution=str(item["distribution"]),
            classification=str(item["classification"]),
            source=str(item["source"]),
        )
        for item in cast(list[dict[str, Any]], raw["parameters"])
    )
    if len({parameter.name for parameter in parameters}) != len(parameters):
        raise ValueError("sensitivity parameter names must be unique")
    if any(parameter.maximum <= parameter.minimum for parameter in parameters):
        raise ValueError("sensitivity parameter maximum must exceed minimum")
    specification = SensitivitySpecification(
        version=str(raw["version"]),
        seed=int(raw["seed"]),
        morris_trajectories=int(raw["morris_trajectories"]),
        morris_levels=int(raw["morris_levels"]),
        sobol_base_sample_size=int(raw["sobol_base_sample_size"]),
        sobol_parameter_count=int(raw["sobol_parameter_count"]),
        parameters=parameters,
    )
    if specification.version != "0.9.5":
        raise ValueError("Phase 9.5 sensitivity version must be 0.9.5")
    return specification


def _summarise_effects(effects: list[float]) -> dict[str, float]:
    absolute = tuple(abs(value) for value in effects)
    mean = math.fsum(effects) / len(effects)
    return {
        "mu": mean,
        "mu_star": math.fsum(absolute) / len(absolute),
        "sigma": math.sqrt(math.fsum((value - mean) ** 2 for value in effects) / len(effects)),
    }


def morris_screen(
    parameters: tuple[SensitivityParameter, ...],
    evaluator: VectorEvaluator,
    *,
    trajectories: int,
    levels: int,
    seed: int,
) -> dict[str, dict[str, dict[str, float]]]:
    """Return elementary-effect summaries by output and parameter."""
    if trajectories < 2 or levels < 4:
        raise ValueError("Morris screening requires >=2 trajectories and >=4 levels")
    rng = random.Random(seed)
    delta = 1.0 / (levels - 1)
    effects: dict[str, dict[str, list[float]]] = {}
    for _ in range(trajectories):
        point = {
            parameter.name: rng.randrange(levels - 1) / (levels - 1) for parameter in parameters
        }
        order = list(parameters)
        rng.shuffle(order)
        current_values = {
            parameter.name: parameter.transform(point[parameter.name]) for parameter in parameters
        }
        current = evaluator(current_values)
        for parameter in order:
            next_point = dict(point)
            next_point[parameter.name] += delta
            next_values = {item.name: item.transform(next_point[item.name]) for item in parameters}
            following = evaluator(next_values)
            for output, value in current.items():
                # Divide by unit-hypercube distance, not physical units, so
                # parameter rankings compare effects over their declared ranges.
                normalised = (following[output] - value) / delta
                effects.setdefault(output, {}).setdefault(parameter.name, []).append(normalised)
            point = next_point
            current_values = next_values
            current = following
    return {
        output: {name: _summarise_effects(values) for name, values in by_parameter.items()}
        for output, by_parameter in effects.items()
    }


def _variance(values: tuple[float, ...]) -> float:
    mean = math.fsum(values) / len(values)
    return math.fsum((value - mean) ** 2 for value in values) / len(values)


def sobol_indices(
    parameters: tuple[SensitivityParameter, ...],
    evaluator: VectorEvaluator,
    *,
    sample_size: int,
    seed: int,
) -> dict[str, object]:
    """Estimate first/total-order Saltelli indices and convergence diagnostics."""
    if sample_size < 16:
        raise ValueError("Sobol analysis requires at least 16 base samples")
    rng = random.Random(seed)
    matrix_a = tuple(tuple(rng.random() for _ in parameters) for _ in range(sample_size))
    matrix_b = tuple(tuple(rng.random() for _ in parameters) for _ in range(sample_size))

    def transformed(row: tuple[float, ...]) -> dict[str, float]:
        return {
            parameter.name: parameter.transform(value)
            for parameter, value in zip(parameters, row, strict=True)
        }

    evaluations_a = tuple(evaluator(transformed(row)) for row in matrix_a)
    evaluations_b = tuple(evaluator(transformed(row)) for row in matrix_b)
    outputs = tuple(evaluations_a[0])
    hybrid_evaluations: dict[str, tuple[Mapping[str, float], ...]] = {}
    for index, parameter in enumerate(parameters):
        hybrids = tuple(
            tuple(
                value_b if position == index else value_a
                for position, (value_a, value_b) in enumerate(zip(row_a, row_b, strict=True))
            )
            for row_a, row_b in zip(matrix_a, matrix_b, strict=True)
        )
        hybrid_evaluations[parameter.name] = tuple(evaluator(transformed(row)) for row in hybrids)
    result: dict[str, object] = {}
    for output in outputs:
        values_a = tuple(item[output] for item in evaluations_a)
        values_b = tuple(item[output] for item in evaluations_b)
        variance = _variance(values_a + values_b)
        indices: dict[str, dict[str, float | None]] = {}
        for parameter in parameters:
            values_ab = tuple(
                evaluation[output] for evaluation in hybrid_evaluations[parameter.name]
            )
            if variance == 0.0:
                first = None
                total = None
            else:
                first = math.fsum(
                    b * (ab - a) for a, b, ab in zip(values_a, values_b, values_ab, strict=True)
                ) / (sample_size * variance)
                total = math.fsum(
                    (a - ab) ** 2 for a, ab in zip(values_a, values_ab, strict=True)
                ) / (2.0 * sample_size * variance)
            indices[parameter.name] = {
                "first_order": first,
                "total_order": total,
                "interaction_remainder": (
                    None if first is None or total is None else total - first
                ),
            }
        result[output] = {"variance": variance, "indices": indices}
    return {
        "sample_size": sample_size,
        "seed": seed,
        "outputs": result,
        "evaluation_count": sample_size * (len(parameters) + 2),
    }


def rank_stability(
    full: Mapping[str, Mapping[str, float]],
    partial: Mapping[str, Mapping[str, float]],
) -> float:
    """Return exact top-to-bottom ranking agreement fraction."""
    full_rank = tuple(sorted(full, key=lambda name: full[name]["mu_star"], reverse=True))
    partial_rank = tuple(sorted(partial, key=lambda name: partial[name]["mu_star"], reverse=True))
    return math.fsum(a == b for a, b in zip(full_rank, partial_rank, strict=True)) / len(full_rank)
