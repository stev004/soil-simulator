"""Small dependency-free statistical summaries for Phase 9.6 artifacts."""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence

from soil_simulator.phase96.values import as_float


def covariance_matrix(
    records: Sequence[Mapping[str, object]], variables: Sequence[str]
) -> dict[str, dict[str, float]]:
    """Return the unbiased sample covariance matrix for named numeric variables."""
    if len(records) < 2:
        raise ValueError("covariance requires at least two records")
    values = {name: [as_float(record[name]) for record in records] for name in variables}
    means = {name: math.fsum(column) / len(column) for name, column in values.items()}
    return {
        first: {
            second: math.fsum(
                (left - means[first]) * (right - means[second])
                for left, right in zip(values[first], values[second], strict=True)
            )
            / (len(records) - 1)
            for second in variables
        }
        for first in variables
    }


def correlation_matrix(
    records: Sequence[Mapping[str, object]], variables: Sequence[str]
) -> dict[str, dict[str, float]]:
    """Return a named Pearson correlation matrix with explicit zero-variance failure."""
    covariance = covariance_matrix(records, variables)
    deviations = {name: math.sqrt(covariance[name][name]) for name in variables}
    zero = [name for name, deviation in deviations.items() if deviation == 0.0]
    if zero:
        raise ValueError(f"correlation variables have zero variance: {zero}")
    return {
        first: {
            second: covariance[first][second] / (deviations[first] * deviations[second])
            for second in variables
        }
        for first in variables
    }


def distributions(
    records: Sequence[Mapping[str, object]], variables: Sequence[str]
) -> dict[str, dict[str, float]]:
    """Return deterministic empirical range and quantile summaries."""
    if not records:
        raise ValueError("distribution report requires records")
    result: dict[str, dict[str, float]] = {}
    for name in variables:
        values = sorted(as_float(record[name]) for record in records)

        def quantile(probability: float, ordered: list[float] = values) -> float:
            position = probability * (len(ordered) - 1)
            lower = math.floor(position)
            upper = math.ceil(position)
            weight = position - lower
            return ordered[lower] * (1.0 - weight) + ordered[upper] * weight

        result[name] = {
            "minimum": values[0],
            "q05": quantile(0.05),
            "median": quantile(0.50),
            "mean": math.fsum(values) / len(values),
            "q95": quantile(0.95),
            "maximum": values[-1],
        }
    return result


def _jacobi_eigenvalues(matrix: list[list[float]]) -> tuple[list[float], list[list[float]]]:
    """Return eigenpairs for a small real symmetric matrix using Jacobi rotations."""
    size = len(matrix)
    work = [row[:] for row in matrix]
    vectors = [[1.0 if row == column else 0.0 for column in range(size)] for row in range(size)]
    for _ in range(100 * size * size):
        first, second = max(
            ((i, j) for i in range(size) for j in range(i + 1, size)),
            key=lambda pair: abs(work[pair[0]][pair[1]]),
        )
        if abs(work[first][second]) < 1.0e-12:
            break
        angle = 0.5 * math.atan2(
            2.0 * work[first][second], work[second][second] - work[first][first]
        )
        cosine, sine = math.cos(angle), math.sin(angle)
        for index in range(size):
            if index not in (first, second):
                left, right = work[index][first], work[index][second]
                work[index][first] = work[first][index] = cosine * left - sine * right
                work[index][second] = work[second][index] = sine * left + cosine * right
        diagonal_first, diagonal_second = work[first][first], work[second][second]
        off_diagonal = work[first][second]
        work[first][first] = (
            cosine * cosine * diagonal_first
            - 2.0 * sine * cosine * off_diagonal
            + sine * sine * diagonal_second
        )
        work[second][second] = (
            sine * sine * diagonal_first
            + 2.0 * sine * cosine * off_diagonal
            + cosine * cosine * diagonal_second
        )
        work[first][second] = work[second][first] = 0.0
        for index in range(size):
            left, right = vectors[index][first], vectors[index][second]
            vectors[index][first] = cosine * left - sine * right
            vectors[index][second] = sine * left + cosine * right
    eigenpairs = sorted(
        (
            (work[index][index], [vectors[row][index] for row in range(size)])
            for index in range(size)
        ),
        key=lambda pair: pair[0],
        reverse=True,
    )
    return [pair[0] for pair in eigenpairs], [pair[1] for pair in eigenpairs]


def pca_report(
    empirical: Sequence[Mapping[str, object]],
    generated: Sequence[Mapping[str, object]],
    variables: Sequence[str],
) -> dict[str, object]:
    """Fit PCA on empirical observables and report generated score-range coverage."""
    if len(empirical) < 2 or not generated:
        raise ValueError("PCA coverage requires empirical and generated records")
    means = {
        name: math.fsum(as_float(record[name]) for record in empirical) / len(empirical)
        for name in variables
    }
    covariance = covariance_matrix(empirical, variables)
    scales = {name: math.sqrt(covariance[name][name]) for name in variables}
    if any(value == 0.0 for value in scales.values()):
        raise ValueError("PCA variables must have non-zero empirical variance")
    correlation = [
        [covariance[first][second] / (scales[first] * scales[second]) for second in variables]
        for first in variables
    ]
    eigenvalues, eigenvectors = _jacobi_eigenvalues(correlation)
    total = math.fsum(max(value, 0.0) for value in eigenvalues)

    def scores(records: Sequence[Mapping[str, object]], vector: list[float]) -> list[float]:
        return [
            math.fsum(
                ((as_float(record[name]) - means[name]) / scales[name]) * coefficient
                for name, coefficient in zip(variables, vector, strict=True)
            )
            for record in records
        ]

    components: list[dict[str, object]] = []
    for index, (eigenvalue, vector) in enumerate(zip(eigenvalues, eigenvectors, strict=True)):
        empirical_scores = scores(empirical, vector)
        generated_scores = scores(generated, vector)
        lower, upper = min(empirical_scores), max(empirical_scores)
        inside = sum(lower <= value <= upper for value in generated_scores) / len(generated_scores)
        components.append(
            {
                "component": index + 1,
                "explained_variance_fraction": max(eigenvalue, 0.0) / total,
                "empirical_score_range": [lower, upper],
                "generated_score_range": [min(generated_scores), max(generated_scores)],
                "generated_fraction_inside_empirical_range": inside,
                "loadings": {name: value for name, value in zip(variables, vector, strict=True)},
            }
        )
    return {
        "fit_population": "empirical_locations",
        "variables": list(variables),
        "components": components,
    }
