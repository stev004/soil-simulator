"""Deterministic Phase 7 descriptive summaries and plain-text CLI tables."""

from __future__ import annotations

import math
import statistics
from collections import Counter, defaultdict
from collections.abc import Iterable

from soil_simulator.domain.population import PopulationBatchResult, SyntheticPopulation


def _quantile(values: tuple[float, ...], probability: float) -> float:
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * probability
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    fraction = position - lower
    return ordered[lower] * (1.0 - fraction) + ordered[upper] * fraction


def _describe(values: Iterable[float]) -> dict[str, float]:
    collected = tuple(values)
    if not collected:
        return {name: 0.0 for name in ("min", "p05", "mean", "median", "p95", "max")}
    return {
        "min": min(collected),
        "p05": _quantile(collected, 0.05),
        "mean": statistics.fmean(collected),
        "median": statistics.median(collected),
        "p95": _quantile(collected, 0.95),
        "max": max(collected),
    }


def _correlation(left: tuple[float, ...], right: tuple[float, ...]) -> float:
    if len(left) != len(right) or len(left) < 2:
        return 0.0
    left_mean = statistics.fmean(left)
    right_mean = statistics.fmean(right)
    numerator = math.fsum(
        (left_value - left_mean) * (right_value - right_mean)
        for left_value, right_value in zip(left, right, strict=True)
    )
    left_scale = math.sqrt(math.fsum((value - left_mean) ** 2 for value in left))
    right_scale = math.sqrt(math.fsum((value - right_mean) ** 2 for value in right))
    if left_scale == 0.0 or right_scale == 0.0:
        return 0.0
    return numerator / (left_scale * right_scale)


def population_summary(population: SyntheticPopulation) -> dict[str, object]:
    """Summarise distributions, correlations, groups, QC and reproducibility."""
    fields = population.fields
    variables: dict[str, tuple[float, ...]] = {
        "clay_percent": tuple(field.field.clay_percent for field in fields),
        "sand_percent": tuple(field.field.sand_percent for field in fields),
        "silt_percent": tuple(field.field.silt_percent for field in fields),
        "ph": tuple(field.field.ph for field in fields),
        "soc_t_c_ha": tuple(field.field.baseline_soc_t_c_ha for field in fields),
        "bulk_density_g_cm3": tuple(field.field.bulk_density_g_cm3 for field in fields),
        "available_p_kg_ha": tuple(field.initial_state.available_p_kg_ha for field in fields),
        "amf_live_c_t_ha": tuple(field.initial_state.amf_live_c for field in fields),
        "mean_temperature_c": tuple(
            statistics.fmean(month.mean_air_temperature_c for month in field.weather)
            for field in fields
        ),
        "annual_rainfall_mm": tuple(
            math.fsum(month.precipitation_mm for month in field.weather)
            / len(field.weather_year_ids)
            for field in fields
        ),
        "annual_evapotranspiration_mm": tuple(
            math.fsum(month.potential_evapotranspiration_mm for month in field.weather)
            / len(field.weather_year_ids)
            for field in fields
        ),
    }
    pairs = (
        ("clay_percent", "soc_t_c_ha"),
        ("clay_percent", "bulk_density_g_cm3"),
        ("soc_t_c_ha", "bulk_density_g_cm3"),
        ("soc_t_c_ha", "amf_live_c_t_ha"),
        ("available_p_kg_ha", "amf_live_c_t_ha"),
        ("annual_rainfall_mm", "annual_evapotranspiration_mm"),
    )
    rejection_counts = Counter(
        reason for rejection in population.manifest.rejections for reason in rejection.reasons
    )
    return {
        "accepted_count": population.manifest.accepted_count,
        "rejected_count": population.manifest.rejected_count,
        "rejection_reasons": dict(sorted(rejection_counts.items())),
        "population_hash": population.manifest.population_hash,
        "configuration_hash": population.manifest.configuration_hash,
        "dataset": {
            "name": population.manifest.dataset_name,
            "version": population.manifest.dataset_version,
            "adapter": population.manifest.adapter_name,
            "adapter_version": population.manifest.adapter_version,
        },
        "distributions": {name: _describe(values) for name, values in variables.items()},
        "correlations": {
            f"{left}__{right}": _correlation(variables[left], variables[right])
            for left, right in pairs
        },
        "archetype_counts": dict(sorted(Counter(field.archetype for field in fields).items())),
        "split_counts": dict(
            sorted(Counter(field.population_split.value for field in fields).items())
        ),
        "empirical_seed_counts": dict(
            sorted(Counter(field.empirical_seed_id for field in fields).items())
        ),
        "spinup": {
            "all_converged": all(field.spinup.converged for field in fields),
            "maximum_years": max((field.spinup.years_run for field in fields), default=0),
            "maximum_relative_cycle_change": max(
                (field.spinup.relative_cycle_change for field in fields), default=0.0
            ),
        },
        "scientific_claim_boundary": "synthetic success is not field validation or causal evidence",
    }


def batch_summary(batch: PopulationBatchResult) -> dict[str, object]:
    """Summarise policy outcomes and paired intervention-minus-baseline differences."""
    grouped: dict[str, list[object]] = defaultdict(list)
    for result in batch.results:
        grouped[result.policy_id].append(result)
    policy_summaries: dict[str, dict[str, object]] = {}
    baseline_by_field = {
        result.field_id: result for result in batch.results if result.policy_id == "baseline"
    }
    for policy_id, raw_results in sorted(grouped.items()):
        results = [result for result in batch.results if result.policy_id == policy_id]
        protected_differences = tuple(
            result.final_protected_soc_proxy_t_c_ha
            - baseline_by_field[result.field_id].final_protected_soc_proxy_t_c_ha
            for result in results
            if result.field_id in baseline_by_field and policy_id != "baseline"
        )
        yield_differences = tuple(
            result.yield_t_dm_ha - baseline_by_field[result.field_id].yield_t_dm_ha
            for result in results
            if result.field_id in baseline_by_field and policy_id != "baseline"
        )
        policy_summaries[policy_id] = {
            "trajectory_count": len(raw_results),
            "yield_t_dm_ha": _describe(result.yield_t_dm_ha for result in results),
            "final_total_soc_t_c_ha": _describe(
                result.final_total_soc_t_c_ha for result in results
            ),
            "final_protected_soc_proxy_t_c_ha": _describe(
                result.final_protected_soc_proxy_t_c_ha for result in results
            ),
            "cost_gbp_ha": _describe(result.cost_gbp_ha for result in results),
            "paired_protected_soc_difference_t_c_ha": _describe(protected_differences),
            "paired_yield_difference_t_dm_ha": _describe(yield_differences),
        }
    return {
        "population_hash": batch.population_hash,
        "scenario_version": batch.scenario_version,
        "trajectory_count": len(batch.results),
        "simulator_failure_count": len(batch.failures),
        "failures": [failure.model_dump(mode="json") for failure in batch.failures],
        "maximum_carbon_residual_t_c_ha": batch.maximum_carbon_residual_t_c_ha,
        "maximum_phosphorus_residual_kg_p_ha": (batch.maximum_phosphorus_residual_kg_p_ha),
        "policies": policy_summaries,
        "scientific_claim_boundary": (
            "synthetic intervention comparisons are model implications, not recommendations"
        ),
    }


def _table(headers: tuple[str, ...], rows: Iterable[tuple[str, ...]]) -> str:
    collected = [headers, *rows]
    widths = [max(len(row[index]) for row in collected) for index in range(len(headers))]
    separator = "-+-".join("-" * width for width in widths)
    lines = [
        " | ".join(value.ljust(widths[index]) for index, value in enumerate(headers)),
        separator,
    ]
    lines.extend(
        " | ".join(value.ljust(widths[index]) for index, value in enumerate(row))
        for row in collected[1:]
    )
    return "\n".join(lines)


def population_summary_table(summary: dict[str, object]) -> str:
    """Render a compact human-readable population summary."""
    distributions = summary["distributions"]
    assert isinstance(distributions, dict)
    distribution_rows: list[tuple[str, ...]] = []
    for name, raw in distributions.items():
        assert isinstance(name, str) and isinstance(raw, dict)
        distribution_rows.append(
            (
                name,
                f"{float(raw['min']):.4g}",
                f"{float(raw['mean']):.4g}",
                f"{float(raw['median']):.4g}",
                f"{float(raw['max']):.4g}",
            )
        )
    counts = (
        f"Accepted {summary['accepted_count']} | Rejected {summary['rejected_count']} | "
        f"Hash {summary['population_hash']}"
    )
    return "\n\n".join(
        (
            counts,
            _table(("Variable", "Min", "Mean", "Median", "Max"), distribution_rows),
            f"Archetypes: {summary['archetype_counts']}",
            f"Splits: {summary['split_counts']}",
            f"Correlations: {summary['correlations']}",
            str(summary["scientific_claim_boundary"]),
        )
    )


def batch_summary_table(summary: dict[str, object]) -> str:
    """Render compact intervention comparison rows without ranking policies."""
    policies = summary["policies"]
    assert isinstance(policies, dict)
    rows: list[tuple[str, ...]] = []
    for policy_id, raw in policies.items():
        assert isinstance(policy_id, str) and isinstance(raw, dict)
        yield_summary = raw["yield_t_dm_ha"]
        protected = raw["paired_protected_soc_difference_t_c_ha"]
        cost = raw["cost_gbp_ha"]
        assert isinstance(yield_summary, dict)
        assert isinstance(protected, dict)
        assert isinstance(cost, dict)
        rows.append(
            (
                policy_id,
                str(raw["trajectory_count"]),
                f"{float(yield_summary['mean']):.4g}",
                f"{float(protected['mean']):+.4g}",
                f"{float(cost['mean']):.4g}",
            )
        )
    maximum_carbon = summary["maximum_carbon_residual_t_c_ha"]
    maximum_phosphorus = summary["maximum_phosphorus_residual_kg_p_ha"]
    assert isinstance(maximum_carbon, (int, float))
    assert isinstance(maximum_phosphorus, (int, float))
    header = (
        f"Trajectories {summary['trajectory_count']} | Failures "
        f"{summary['simulator_failure_count']} | Max C residual "
        f"{maximum_carbon:.3e} | Max P residual {maximum_phosphorus:.3e}"
    )
    return "\n\n".join(
        (
            header,
            _table(("Policy", "N", "Mean yield", "Delta protected", "Mean cost"), rows),
            str(summary["scientific_claim_boundary"]),
        )
    )
