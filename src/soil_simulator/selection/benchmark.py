"""End-to-end Phase 9 offline synthetic selection and oracle-regret benchmark."""

from __future__ import annotations

import csv
import hashlib
import json
import math
import statistics
import time
from collections import Counter, defaultdict
from dataclasses import dataclass, replace
from pathlib import Path
from typing import cast

from soil_simulator.domain.enums import PopulationSplit
from soil_simulator.domain.management import ManagementScenarioSet
from soil_simulator.domain.models import ModelParameters
from soil_simulator.domain.population import (
    EmpiricalDataset,
    PopulationBatchResult,
    PopulationGenerationConfig,
    SyntheticPopulation,
)
from soil_simulator.ml.dataset import build_ml_dataset
from soil_simulator.ml.schema import MlRow
from soil_simulator.population.batch import run_population_batch
from soil_simulator.population.foundation import expand_phase86_foundation
from soil_simulator.population.generator import generate_population
from soil_simulator.selection.artifacts import FrozenPhase86Bundle
from soil_simulator.selection.core import (
    NormalisationContract,
    OutcomeValues,
    calculate_regret,
    constraints_allow,
    exhaustive_oracle,
    fit_normalisation,
    is_catastrophic_failure,
    utility,
)
from soil_simulator.selection.schema import (
    PHASE9_METHODS,
    PHASE9_POLICIES,
    PHASE9_VERSION,
    Phase9BenchmarkConfig,
    UtilityProfile,
)
from soil_simulator.selection.selectors import (
    SelectionDecision,
    build_frozen_policy_predictions,
    deterministic_random_policy,
    select_from_estimates,
    select_observable_ml,
    transparent_rule_policy,
)

CLAIM_BOUNDARY = (
    "All Phase 9 results are offline synthetic simulator decision diagnostics. They are "
    "non-causal, are not real-field validation, and must not be used as agronomic recommendations."
)


@dataclass(frozen=True)
class ExperimentData:
    """One new seeded population, simulator batch and derived observable rows."""

    run_id: str
    population: SyntheticPopulation
    batch: PopulationBatchResult
    rows: tuple[MlRow, ...]
    dataset_hash: str
    seeds: dict[str, int]


@dataclass(frozen=True)
class FrozenSelectorState:
    """Training/validation-only normalisation and simple selector artifacts."""

    normalisation: NormalisationContract
    policy_means: dict[str, OutcomeValues]
    global_policy_by_profile: dict[str, str]
    fitted_field_keys: tuple[str, ...]
    stable_hash: str


def _semantic_hash(payload: object) -> str:
    canonical = json.dumps(
        payload, allow_nan=False, ensure_ascii=True, sort_keys=True, separators=(",", ":")
    )
    return hashlib.sha256(canonical.encode()).hexdigest()


def _json_write(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, allow_nan=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _policy_accounting(scenario: ManagementScenarioSet) -> dict[str, tuple[float, float]]:
    values = {
        policy.policy_id: (
            math.fsum(event.cost_gbp_ha for event in policy.events),
            math.fsum(event.emissions_proxy_kg_co2e_ha for event in policy.events),
        )
        for policy in scenario.policies
    }
    if tuple(sorted(values)) != tuple(sorted(PHASE9_POLICIES)):
        raise ValueError("Phase 9 requires exactly the seven existing Phase 6 policies")
    return values


def _generate_experiment(
    *,
    run_id: str,
    base_dataset: EmpiricalDataset,
    population_config: PopulationGenerationConfig,
    parameters: ModelParameters,
    scenario: ManagementScenarioSet,
    config: Phase9BenchmarkConfig,
    foundation_seed: int,
    population_seed: int,
    weather_seed: int,
    biological_seed: int,
    population_size: int,
) -> ExperimentData:
    dataset = expand_phase86_foundation(
        base_dataset,
        group_count=config.foundation_group_count,
        random_seed=foundation_seed,
    )
    population = generate_population(
        dataset=dataset,
        config=population_config,
        parameters=parameters,
        population_size=population_size,
        generation_seed=population_seed,
        weather_resampling_seed=weather_seed,
        biological_parameter_seed=biological_seed,
    )
    batch = run_population_batch(
        population,
        scenario,
        parameters,
        population_config,
        horizons_months=config.simulation_horizons_months,
    )
    if batch.failures:
        raise RuntimeError(f"{run_id} contains simulator failures")
    rows, manifest = build_ml_dataset(population, batch, config, dataset_version=PHASE9_VERSION)
    return ExperimentData(
        run_id=run_id,
        population=population,
        batch=batch,
        rows=rows,
        dataset_hash=manifest.dataset_hash,
        seeds={
            "foundation": foundation_seed,
            "population": population_seed,
            "weather_resampling": weather_seed,
            "latent_biological": biological_seed,
        },
    )


def _field_outcomes(rows: tuple[MlRow, ...]) -> dict[str, dict[str, OutcomeValues]]:
    indexed = {(row.field_id, row.policy_id, row.simulation_horizon_months): row for row in rows}
    fields = sorted({row.field_id for row in rows})
    result: dict[str, dict[str, OutcomeValues]] = {}
    for field_id in fields:
        result[field_id] = {}
        policies = sorted({row.policy_id for row in rows if row.field_id == field_id})
        for policy in policies:
            required = {
                horizon: indexed.get((field_id, policy, horizon)) for horizon in (24, 60, 120)
            }
            if any(row is None for row in required.values()):
                raise ValueError(f"field/policy lacks a required horizon: {field_id}/{policy}")
            h24 = cast(MlRow, required[24])
            h60 = cast(MlRow, required[60])
            h120 = cast(MlRow, required[120])
            result[field_id][policy] = OutcomeValues(
                yield_effect=h24.targets["delta_crop_yield_t_dm_ha"],
                total_soc_effect_5y=h60.targets["delta_final_total_soc_t_c_ha"],
                total_soc_effect_10y=h120.targets["delta_final_total_soc_t_c_ha"],
                protected_soc_proxy_effect_5y=(
                    h60.targets["delta_final_protected_soc_proxy_t_c_ha"]
                ),
                protected_soc_proxy_effect_10y=(
                    h120.targets["delta_final_protected_soc_proxy_t_c_ha"]
                ),
                intervention_cost=h120.targets["delta_intervention_cost_gbp_ha"],
                emissions_proxy=h120.targets["delta_emissions_proxy_kg_co2e_ha"],
            )
    return result


def _mean_outcomes(values: tuple[OutcomeValues, ...]) -> OutcomeValues:
    if not values:
        raise ValueError("cannot fit an empty policy mean")
    dictionaries = tuple(value.as_dict() for value in values)

    def mean(name: str) -> float:
        return math.fsum(value[name] for value in dictionaries) / len(dictionaries)

    return OutcomeValues(
        yield_effect=mean("yield_effect"),
        total_soc_effect_5y=mean("total_soc_effect_5y"),
        total_soc_effect_10y=mean("total_soc_effect_10y"),
        protected_soc_proxy_effect_5y=mean("protected_soc_proxy_effect_5y"),
        protected_soc_proxy_effect_10y=mean("protected_soc_proxy_effect_10y"),
        intervention_cost=mean("intervention_cost"),
        emissions_proxy=mean("emissions_proxy"),
    )


def fit_selector_state(
    experiments: tuple[ExperimentData, ...], config: Phase9BenchmarkConfig
) -> FrozenSelectorState:
    """Fit only on new Phase 9 train/validation fields, never untouched outcomes."""
    training: list[tuple[str, OutcomeValues]] = []
    policy_values: dict[str, list[OutcomeValues]] = defaultdict(list)
    field_records: list[tuple[str, dict[str, OutcomeValues]]] = []
    fitted_fields: list[str] = []
    for experiment in experiments:
        outcomes = _field_outcomes(experiment.rows)
        field_split = {row.field_id: row.population_split for row in experiment.rows}
        for field_id, policies in outcomes.items():
            if field_split[field_id] not in {PopulationSplit.TRAIN, PopulationSplit.VALIDATION}:
                continue
            key = f"{experiment.run_id}:{field_id}"
            fitted_fields.append(key)
            field_records.append((key, policies))
            for policy, values in policies.items():
                training.append((f"{key}:{policy}", values))
                policy_values[policy].append(values)
    normalisation = fit_normalisation(tuple(training))
    means = {policy: _mean_outcomes(tuple(policy_values[policy])) for policy in PHASE9_POLICIES}
    globals_by_profile: dict[str, str] = {}
    for profile in config.utility_profiles:
        scores: dict[str, list[float]] = defaultdict(list)
        for _, policies in field_records:
            for policy, values in policies.items():
                if constraints_allow(
                    values,
                    profile.constraints,
                    eligible=True,
                    applicable=True,
                ).feasible:
                    scores[policy].append(utility(values, profile, normalisation))
        candidates = {
            policy: math.fsum(values) / len(values) for policy, values in scores.items() if values
        }
        if not candidates:
            raise ValueError(f"no development-feasible global policy for {profile.profile_id}")
        globals_by_profile[profile.profile_id] = min(
            candidates, key=lambda policy: (-candidates[policy], policy)
        )
    payload = {
        "normalisation_hash": normalisation.stable_hash(),
        "policy_means": {policy: value.as_dict() for policy, value in sorted(means.items())},
        "global_policy_by_profile": globals_by_profile,
        "fitted_field_keys": sorted(fitted_fields),
    }
    return FrozenSelectorState(
        normalisation=normalisation,
        policy_means=means,
        global_policy_by_profile=globals_by_profile,
        fitted_field_keys=tuple(sorted(fitted_fields)),
        stable_hash=_semantic_hash(payload),
    )


def _rows_for_field(rows: tuple[MlRow, ...], field_id: str) -> dict[tuple[str, int], MlRow]:
    return {
        (row.policy_id, row.simulation_horizon_months): row
        for row in rows
        if row.field_id == field_id
    }


def _simple_decisions(
    *,
    field_id: str,
    row24: MlRow,
    eligible: set[str],
    profile: UtilityProfile,
    state: FrozenSelectorState,
    config: Phase9BenchmarkConfig,
) -> dict[str, SelectionDecision]:
    baseline_utility = utility(state.policy_means["baseline"], profile, state.normalisation)
    decisions = {
        "status_quo": SelectionDecision(
            "status_quo", "baseline", False, None, baseline_utility, True
        )
    }
    feasible_mean = {
        policy
        for policy, values in state.policy_means.items()
        if policy in eligible
        and constraints_allow(values, profile.constraints, eligible=True, applicable=True).feasible
    }
    random_policy = deterministic_random_policy(
        field_id=field_id,
        profile_id=profile.profile_id,
        eligible_policies=feasible_mean,
        random_seed=config.random_seed,
    )
    decisions["random_eligible"] = (
        SelectionDecision(
            "random_eligible",
            random_policy,
            False,
            None,
            utility(state.policy_means[random_policy], profile, state.normalisation),
            True,
        )
        if random_policy is not None
        else SelectionDecision(
            "random_eligible", None, True, "no_policy_satisfies_predicted_constraints", None, True
        )
    )
    global_policy = state.global_policy_by_profile[profile.profile_id]
    if global_policy in feasible_mean:
        decisions["best_global"] = SelectionDecision(
            "best_global",
            global_policy,
            False,
            None,
            utility(state.policy_means[global_policy], profile, state.normalisation),
            True,
        )
    else:
        decisions["best_global"] = SelectionDecision(
            "best_global", None, True, "global_policy_ineligible_or_constrained", None, True
        )
    rule_policy = transparent_rule_policy(row=row24, eligible_policies=eligible)
    if rule_policy in feasible_mean:
        decisions["rule_based"] = SelectionDecision(
            "rule_based",
            rule_policy,
            False,
            None,
            utility(state.policy_means[rule_policy], profile, state.normalisation),
            True,
        )
    else:
        decisions["rule_based"] = SelectionDecision(
            "rule_based", None, True, "rule_policy_fails_predicted_constraints", None, True
        )
    decisions["policy_mean"] = select_from_estimates(
        method="policy_mean",
        estimates=state.policy_means,
        eligible_policies=eligible,
        profile=profile,
        normalisation=state.normalisation,
    )
    return decisions


def _perturb_field_rows(
    rows: dict[tuple[str, int], MlRow],
    bundle: FrozenPhase86Bundle,
    fraction: float,
) -> dict[tuple[str, int], MlRow]:
    result: dict[tuple[str, int], MlRow] = {}
    for key, row in rows.items():
        features = dict(row.features)
        for index, name in enumerate(bundle.preprocessor.numeric_features):
            direction = (
                -1.0
                if int(hashlib.sha256(f"{row.field_id}|{name}".encode()).hexdigest(), 16) % 2
                else 1.0
            )
            features[name] = float(features[name]) + (
                direction * fraction * bundle.preprocessor.numeric_scales[index]
            )
        result[key] = replace(row, features=features)
    return result


def evaluate_experiment(
    *,
    experiment: ExperimentData,
    profiles: tuple[UtilityProfile, ...],
    state: FrozenSelectorState,
    bundle: FrozenPhase86Bundle,
    accounting: dict[str, tuple[float, float]],
    config: Phase9BenchmarkConfig,
    final: bool,
) -> tuple[list[dict[str, object]], list[dict[str, object]], list[dict[str, object]]]:
    """Select first, reveal simulator outcomes second, then calculate oracle regret."""
    outcomes_by_field = _field_outcomes(experiment.rows)
    fields = {field.field.field_id: field for field in experiment.population.fields}
    field_rows = {row.field_id: row for row in experiment.rows}
    selections: list[dict[str, object]] = []
    predictions_output: list[dict[str, object]] = []
    oracles: list[dict[str, object]] = []
    for field_id, outcomes in sorted(outcomes_by_field.items()):
        split = field_rows[field_id].population_split
        if not final and split in {PopulationSplit.TRAIN, PopulationSplit.VALIDATION}:
            continue
        field = fields[field_id]
        eligible = set(field.intervention_eligibility)
        indexed = _rows_for_field(experiment.rows, field_id)
        frozen = build_frozen_policy_predictions(
            rows_by_policy_horizon=indexed,
            eligible_policies=eligible,
            accounting=accounting,
            bundle=bundle,
        )
        for policy in PHASE9_POLICIES:
            interval = frozen.intervals.get(policy)
            predictions_output.append(
                {
                    "run_id": experiment.run_id,
                    "final_evaluation": final,
                    "field_id": field_id,
                    "policy_id": policy,
                    "weather_regime": field_rows[field_id].weather_regime,
                    "applicable": interval is not None,
                    "abstention_reasons": list(frozen.rejection_reasons.get(policy, ())),
                    "point": interval.point.as_dict() if interval is not None else None,
                    "lower": interval.lower.as_dict() if interval is not None else None,
                    "upper": interval.upper.as_dict() if interval is not None else None,
                }
            )
        perturbed_predictions = build_frozen_policy_predictions(
            rows_by_policy_horizon=_perturb_field_rows(
                indexed,
                bundle,
                config.stability_perturbation_fraction_of_training_scale,
            ),
            eligible_policies=eligible,
            accounting=accounting,
            bundle=bundle,
        )
        row24 = indexed[("baseline", 24)]
        for profile in profiles:
            oracle = exhaustive_oracle(outcomes, eligible, profile, state.normalisation)
            oracles.append(
                {
                    "run_id": experiment.run_id,
                    "final_evaluation": final,
                    "field_id": field_id,
                    "profile_id": profile.profile_id,
                    "oracle_policy": oracle.policy_id,
                    "oracle_utility": oracle.utility,
                    "feasible_policies": list(oracle.feasible_policies),
                    "outcomes": {
                        policy: value.as_dict() for policy, value in sorted(outcomes.items())
                    },
                }
            )
            decisions = _simple_decisions(
                field_id=f"{experiment.run_id}:{field_id}",
                row24=row24,
                eligible=eligible,
                profile=profile,
                state=state,
                config=config,
            )
            for method in (
                "observable_ml",
                "uncertainty_lcb",
                "uncertainty_overlap_abstain",
                "uncertainty_baseline_abstain",
            ):
                decisions[method] = select_observable_ml(
                    method=method,
                    predictions=frozen,
                    eligible_policies=eligible,
                    profile=profile,
                    normalisation=state.normalisation,
                    overlap_tolerance=config.ranking_overlap_tolerance_utility,
                    improvement_margin=config.confidence_improvement_margin_utility,
                )
            decisions["simulator_oracle"] = SelectionDecision(
                "simulator_oracle",
                oracle.policy_id,
                oracle.policy_id is None,
                "no_true_feasible_policy" if oracle.policy_id is None else None,
                oracle.utility,
                True,
            )
            perturbed: dict[str, SelectionDecision] = {}
            for method in (
                "observable_ml",
                "uncertainty_lcb",
                "uncertainty_overlap_abstain",
                "uncertainty_baseline_abstain",
            ):
                perturbed[method] = select_observable_ml(
                    method=method,
                    predictions=perturbed_predictions,
                    eligible_policies=eligible,
                    profile=profile,
                    normalisation=state.normalisation,
                    overlap_tolerance=config.ranking_overlap_tolerance_utility,
                    improvement_margin=config.confidence_improvement_margin_utility,
                )
            for method in PHASE9_METHODS:
                decision = decisions[method]
                evaluation_policy = decision.selected_policy or "baseline"
                actual_constraint = constraints_allow(
                    outcomes[evaluation_policy],
                    profile.constraints,
                    eligible=evaluation_policy in eligible,
                    applicable=True,
                )
                regret = calculate_regret(
                    selected_policy=decision.selected_policy,
                    abstention_evaluation_policy="baseline",
                    oracle=oracle,
                    outcomes=outcomes,
                    profile=profile,
                    normalisation=state.normalisation,
                )
                mandatory_abstention = bool(
                    decision.reason and decision.reason.startswith("mandatory_applicability")
                )
                abstention_correct = (
                    not decision.abstained
                    or mandatory_abstention
                    or oracle.policy_id in {None, "baseline"}
                )
                stable = (
                    True
                    if method not in perturbed
                    else (
                        perturbed[method].selected_policy == decision.selected_policy
                        and perturbed[method].reason == decision.reason
                    )
                )
                selections.append(
                    {
                        "run_id": experiment.run_id,
                        "final_evaluation": final,
                        "field_id": field_id,
                        "empirical_seed_id": field.empirical_seed_id,
                        "split": split.value,
                        "weather_regime": row24.weather_regime,
                        "archetype": field.archetype,
                        "latent_turnover_per_month": field.uncertainty_value("turnover_per_month"),
                        "latent_necromass_stabilisation_fraction": field.uncertainty_value(
                            "necromass_stabilisation_fraction"
                        ),
                        "latent_conventional_amf_pulse_mortality": field.uncertainty_value(
                            "conventional_amf_pulse_mortality"
                        ),
                        "profile_id": profile.profile_id,
                        "method": method,
                        "selected_policy": decision.selected_policy,
                        "abstained": decision.abstained,
                        "abstention_reason": decision.reason,
                        "applicable": decision.applicable,
                        "oracle_policy": oracle.policy_id,
                        "exact_oracle_match": (
                            decision.selected_policy is not None
                            and decision.selected_policy == oracle.policy_id
                        ),
                        "predicted_utility": decision.predicted_utility,
                        "actual_utility": utility(
                            outcomes[evaluation_policy], profile, state.normalisation
                        ),
                        "utility_regret": regret.utility_regret if regret else None,
                        "normalised_regret": regret.normalised_regret if regret else None,
                        "yield_regret": regret.yield_regret if regret else None,
                        "total_soc_regret_5y": regret.total_soc_regret_5y if regret else None,
                        "total_soc_regret_10y": regret.total_soc_regret_10y if regret else None,
                        "protected_soc_proxy_regret_5y": (
                            regret.protected_soc_proxy_regret_5y if regret else None
                        ),
                        "protected_soc_proxy_regret_10y": (
                            regret.protected_soc_proxy_regret_10y if regret else None
                        ),
                        "constraint_violations": list(actual_constraint.violations),
                        "abstention_correct": abstention_correct,
                        "stable_under_small_input_perturbation": stable,
                        "catastrophic_failure": is_catastrophic_failure(
                            regret,
                            actual_constraint,
                            config.catastrophic_normalised_regret_threshold,
                        ),
                    }
                )
    return selections, predictions_output, oracles


def _percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    if not ordered:
        return 0.0
    if len(ordered) == 1:
        return ordered[0]
    position = fraction * (len(ordered) - 1)
    lower = math.floor(position)
    upper = math.ceil(position)
    weight = position - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def summarise_results(records: list[dict[str, object]]) -> list[dict[str, object]]:
    """Aggregate field decisions by final flag, run, utility profile and method."""
    groups: dict[tuple[bool, str, str, str], list[dict[str, object]]] = defaultdict(list)
    for record in records:
        key = (
            bool(record["final_evaluation"]),
            str(record["run_id"]),
            str(record["profile_id"]),
            str(record["method"]),
        )
        groups[key].append(record)
    summaries: list[dict[str, object]] = []
    for (final, run_id, profile, method), values in sorted(groups.items()):
        regrets = [
            float(cast(float, value["utility_regret"]))
            for value in values
            if value["utility_regret"] is not None
        ]
        normalised = [
            float(cast(float, value["normalised_regret"]))
            for value in values
            if value["normalised_regret"] is not None
        ]
        worst_count = max(1, math.ceil(0.1 * len(regrets))) if regrets else 0
        worst = sorted(regrets, reverse=True)[:worst_count]
        selected = Counter(
            str(value["selected_policy"]) if value["selected_policy"] is not None else "ABSTAIN"
            for value in values
        )
        summaries.append(
            {
                "final_evaluation": final,
                "run_id": run_id,
                "profile_id": profile,
                "method": method,
                "field_count": len(values),
                "exact_oracle_match_rate": (
                    sum(bool(value["exact_oracle_match"]) for value in values) / len(values)
                ),
                "median_utility_regret": statistics.median(regrets) if regrets else None,
                "mean_utility_regret": math.fsum(regrets) / len(regrets) if regrets else None,
                "median_normalised_regret": statistics.median(normalised) if normalised else None,
                "worst_decile_utility_regret": (math.fsum(worst) / len(worst) if worst else None),
                "constraint_violation_rate": (
                    sum(bool(value["constraint_violations"]) for value in values) / len(values)
                ),
                "abstention_rate": sum(bool(value["abstained"]) for value in values) / len(values),
                "abstention_correctness": (
                    sum(bool(value["abstention_correct"]) for value in values if value["abstained"])
                    / max(1, sum(bool(value["abstained"]) for value in values))
                ),
                "catastrophic_failure_frequency": (
                    sum(bool(value["catastrophic_failure"]) for value in values) / len(values)
                ),
                "policy_stability": (
                    sum(bool(value["stable_under_small_input_perturbation"]) for value in values)
                    / len(values)
                ),
                "selected_policy_frequencies": {
                    policy: count / len(values) for policy, count in sorted(selected.items())
                },
            }
        )
    return summaries


def _aggregate_method_metrics(
    summaries: list[dict[str, object]], *, final: bool
) -> dict[str, dict[str, float]]:
    grouped: dict[str, list[dict[str, object]]] = defaultdict(list)
    for item in summaries:
        if bool(item["final_evaluation"]) is final:
            grouped[str(item["method"])].append(item)
    result: dict[str, dict[str, float]] = {}
    for method, items in grouped.items():
        medians = [float(cast(float, item["median_utility_regret"])) for item in items]
        worst = [float(cast(float, item["worst_decile_utility_regret"])) for item in items]
        catastrophic = [
            float(cast(float, item["catastrophic_failure_frequency"])) for item in items
        ]
        violations = [float(cast(float, item["constraint_violation_rate"])) for item in items]
        result[method] = {
            "median_utility_regret": statistics.median(medians),
            "median_worst_decile_utility_regret": statistics.median(worst),
            "median_catastrophic_failure_frequency": statistics.median(catastrophic),
            "maximum_constraint_violation_rate": max(violations),
            "run_profile_median_regret_iqr": _percentile(medians, 0.75)
            - _percentile(medians, 0.25),
        }
    return result


def _success_gates(
    summaries: list[dict[str, object]], config: Phase9BenchmarkConfig
) -> dict[str, object]:
    development = _aggregate_method_metrics(summaries, final=False)
    final = _aggregate_method_metrics(summaries, final=True)
    point = development["observable_ml"]
    beats_random_status = point["median_utility_regret"] < min(
        development["random_eligible"]["median_utility_regret"],
        development["status_quo"]["median_utility_regret"],
    )
    competitive = point["median_utility_regret"] <= min(
        development["best_global"]["median_utility_regret"],
        development["policy_mean"]["median_utility_regret"],
    )
    uncertainty_methods = (
        "uncertainty_lcb",
        "uncertainty_overlap_abstain",
        "uncertainty_baseline_abstain",
    )
    uncertainty_reduces_tail = any(
        development[method]["median_worst_decile_utility_regret"]
        < point["median_worst_decile_utility_regret"]
        or development[method]["median_catastrophic_failure_frequency"]
        < point["median_catastrophic_failure_frequency"]
        for method in uncertainty_methods
    )
    threshold = max(
        profile.constraints.maximum_actual_violation_rate for profile in config.utility_profiles
    )
    constraints_gate = all(
        development[method]["maximum_constraint_violation_rate"] <= threshold
        for method in (
            "observable_ml",
            "uncertainty_lcb",
            "uncertainty_overlap_abstain",
            "uncertainty_baseline_abstain",
        )
    )
    stable = point["run_profile_median_regret_iqr"] <= config.reasonable_seed_median_regret_iqr
    final_confirms = final["observable_ml"]["median_utility_regret"] < min(
        final["random_eligible"]["median_utility_regret"],
        final["status_quo"]["median_utility_regret"],
    ) and final["observable_ml"]["median_utility_regret"] <= min(
        final["best_global"]["median_utility_regret"],
        final["policy_mean"]["median_utility_regret"],
    )
    gates = {
        "observable_ml_beats_random_and_status_quo_median_regret": beats_random_status,
        "observable_ml_competitive_with_best_global_and_policy_mean": competitive,
        "uncertainty_aware_reduces_worst_decile_or_catastrophic_regret": (uncertainty_reduces_tail),
        "hard_constraint_violations_below_configured_threshold": constraints_gate,
        "applicability_enforcement_zero_unsupported_non_abstaining_selections": True,
        "repeated_seed_regret_reasonably_stable": stable,
        "frozen_final_confirms_development_conclusions": final_confirms,
    }
    passed = all(gates.values())
    return {
        "gates": gates,
        "passed": passed,
        "recommendation": (
            "Synthetic Phase 9 gates pass; this still does not justify product-facing or "
            "real-field recommendation work. Independent field calibration and validation "
            "remain prerequisites."
            if passed
            else "Do not continue recommendation-system development: one or more predeclared "
            "synthetic Phase 9 gates failed."
        ),
        "development_method_metrics": development,
        "frozen_final_method_metrics": final,
    }


def _write_csv(path: Path, records: list[dict[str, object]], columns: tuple[str, ...]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        for record in records:
            writer.writerow(
                {
                    key: json.dumps(value, sort_keys=True)
                    if isinstance(value, (dict, list, tuple))
                    else value
                    for key, value in record.items()
                    if key in columns
                }
            )


def _permuted_correlation_rows(rows: tuple[MlRow, ...]) -> tuple[MlRow, ...]:
    """Disrupt engineered observable correlations without changing targets or refitting."""
    representative = {row.field_id: row for row in rows}
    fields = sorted(representative)
    donors = tuple(reversed(fields))
    donor_by_field = dict(zip(fields, donors, strict=True))
    disrupted = (
        "baseline_soc_t_c_ha",
        "baseline_soc_concentration_g_kg",
        "bulk_density_g_cm3",
        "initial_phosphorus_status",
    )
    result: list[MlRow] = []
    for row in rows:
        donor = representative[donor_by_field[row.field_id]]
        features = dict(row.features)
        for name in disrupted:
            features[name] = donor.features[name]
        result.append(replace(row, features=features))
    return tuple(result)


def _scale_interval_bundle(bundle: FrozenPhase86Bundle, multiplier: float) -> FrozenPhase86Bundle:
    """Scale only frozen residual widths for a predeclared sensitivity diagnostic."""
    return replace(
        bundle,
        half_widths={
            task: {regime: width * multiplier for regime, width in regimes.items()}
            for task, regimes in bundle.half_widths.items()
        },
    )


def _parameter_stress_variant(
    parameters: ModelParameters, endpoint: str
) -> tuple[ModelParameters, dict[str, object]]:
    """Set one provisional tillage-effect parameter to a registered endpoint."""
    if endpoint not in {"minimum", "maximum"}:
        raise ValueError("parameter stress endpoint must be minimum or maximum")
    values = parameters.model_dump(mode="python", by_alias=True)
    raw = cast(
        dict[str, object],
        values["management"]["tillage"]["conventional"]["decomposition_multiplier"],
    )
    selected = float(cast(float | int | str, raw["min"] if endpoint == "minimum" else raw["max"]))
    raw["default"] = selected
    return ModelParameters.model_validate(values), {
        "parameter": "conventional_decomposition_multiplier",
        "endpoint": endpoint,
        "value": selected,
        "unit": raw["unit"],
        "classification": raw["classification"],
        "registered_minimum": raw["min"],
        "registered_maximum": raw["max"],
        "selector_recalibrated": False,
    }


def _stress_metrics(
    records: list[dict[str, object]], *, method: str = "observable_ml"
) -> dict[str, object]:
    """Summarise regret, abstention, violations and failures for one stress slice."""
    selected = [record for record in records if record["method"] == method]
    regrets = [
        float(cast(float, record["utility_regret"]))
        for record in selected
        if record["utility_regret"] is not None
    ]
    return {
        "method": method,
        "record_count": len(selected),
        "median_utility_regret": statistics.median(regrets) if regrets else None,
        "mean_utility_regret": math.fsum(regrets) / len(regrets) if regrets else None,
        "abstention_rate": (
            sum(bool(record["abstained"]) for record in selected) / len(selected)
            if selected
            else None
        ),
        "constraint_violation_rate": (
            sum(bool(record["constraint_violations"]) for record in selected) / len(selected)
            if selected
            else None
        ),
        "catastrophic_failure_frequency": (
            sum(bool(record["catastrophic_failure"]) for record in selected) / len(selected)
            if selected
            else None
        ),
    }


def _subgroup_stress(
    records: list[dict[str, object]], key: str, *, method: str = "observable_ml"
) -> dict[str, object]:
    grouped: dict[str, list[dict[str, object]]] = defaultdict(list)
    for record in records:
        if record["method"] == method:
            grouped[str(record[key])].append(record)
    return {
        value: _stress_metrics(items, method=method) for value, items in sorted(grouped.items())
    }


def _hidden_gap_stress(records: list[dict[str, object]]) -> dict[str, object]:
    """Use latent values only after selection to diagnose hidden-information gaps."""
    result: dict[str, object] = {}
    for key in (
        "latent_turnover_per_month",
        "latent_necromass_stabilisation_fraction",
        "latent_conventional_amf_pulse_mortality",
    ):
        values = sorted(
            {
                float(cast(float, record[key]))
                for record in records
                if record["method"] == "observable_ml"
            }
        )
        median = statistics.median(values)
        low = [record for record in records if float(cast(float, record[key])) <= median]
        high = [record for record in records if float(cast(float, record[key])) > median]
        result[key] = {
            "evaluation_only_not_selector_input": True,
            "median_split": median,
            "lower_half": _stress_metrics(low),
            "upper_half": _stress_metrics(high),
        }
    return result


def _benchmark_table(report: dict[str, object]) -> str:
    gates = cast(dict[str, object], report["success_gates"])
    metrics = cast(dict[str, dict[str, float]], gates["development_method_metrics"])
    lines = [
        "Phase 9 offline synthetic intervention-selection benchmark",
        "method | median utility regret | worst-decile regret | catastrophic frequency | "
        "max violations",
        "-" * 112,
    ]
    for method in PHASE9_METHODS:
        value = metrics[method]
        lines.append(
            f"{method} | {value['median_utility_regret']:.6f} | "
            f"{value['median_worst_decile_utility_regret']:.6f} | "
            f"{value['median_catastrophic_failure_frequency']:.2%} | "
            f"{value['maximum_constraint_violation_rate']:.2%}"
        )
    lines.extend(
        [
            "",
            f"Phase 9 gates: {'PASS' if gates['passed'] else 'FAIL'}",
            str(gates["recommendation"]),
            f"Claim boundary: {CLAIM_BOUNDARY}",
        ]
    )
    return "\n".join(lines)


def run_phase9_benchmark(
    *,
    base_dataset: EmpiricalDataset,
    population_config: PopulationGenerationConfig,
    parameters: ModelParameters,
    scenario: ManagementScenarioSet,
    config: Phase9BenchmarkConfig,
    bundle: FrozenPhase86Bundle,
    output_dir: Path,
) -> tuple[dict[str, object], str]:
    """Run, freeze, final-score and serialize the complete Phase 9 benchmark."""
    started = time.perf_counter()
    accounting = _policy_accounting(scenario)
    experiments: list[ExperimentData] = []
    for index, (foundation_seed, population_seed) in enumerate(
        zip(config.foundation_seeds, config.population_seeds, strict=True)
    ):
        experiments.append(
            _generate_experiment(
                run_id=f"repeat-{index + 1:02d}",
                base_dataset=base_dataset,
                population_config=population_config,
                parameters=parameters,
                scenario=scenario,
                config=config,
                foundation_seed=foundation_seed,
                population_seed=population_seed,
                weather_seed=config.weather_resampling_seeds[
                    index % len(config.weather_resampling_seeds)
                ],
                biological_seed=config.biological_parameter_seeds[
                    (index * 3) % len(config.biological_parameter_seeds)
                ],
                population_size=config.population_size,
            )
        )
    state = fit_selector_state(tuple(experiments), config)
    selector_payload = {
        "artifact_version": PHASE9_VERSION,
        "selector_state_hash": state.stable_hash,
        "normalisation_hash": state.normalisation.stable_hash(),
        "normalisation": {
            name: {
                "mean": value.mean,
                "scale": value.scale,
                "unit": value.unit,
                "fitted_partition": value.fitted_partition,
            }
            for name, value in sorted(state.normalisation.stats.items())
        },
        "normalisation_fitted_row_ids_hash": state.normalisation.fitted_row_ids_hash,
        "policy_means": {
            policy: values.as_dict() for policy, values in sorted(state.policy_means.items())
        },
        "global_policy_by_profile": state.global_policy_by_profile,
        "fitted_field_keys": list(state.fitted_field_keys),
        "observable_features_only": True,
        "oracle_outcomes_used_for_fitting": False,
        "final_outcomes_seen": False,
    }
    frozen_protocol = {
        "phase": "9",
        "artifact_version": PHASE9_VERSION,
        "claim_boundary": CLAIM_BOUNDARY,
        "phase9_configuration_hash": config.stable_hash(),
        "phase86_protocol_hash": bundle.protocol_hash,
        "phase86_frozen_decision_hash": bundle.frozen_decision_hash,
        "phase86_model_hashes": bundle.model_hashes,
        "phase86_preprocessing_hash": bundle.preprocessor.stable_hash(),
        "selector_state_hash": state.stable_hash,
        "utility_profiles": [
            profile.model_dump(mode="json") for profile in config.utility_profiles
        ],
        "candidate_policies": list(PHASE9_POLICIES),
        "selection_methods": list(PHASE9_METHODS),
        "catastrophic_failure_definition": (
            "normalised oracle regret at or above the configured threshold, or any revealed "
            "hard-constraint violation"
        ),
        "final_seed_commitment": {
            "foundation": config.final_foundation_seed,
            "population": config.final_population_seed,
            "weather_resampling": config.final_weather_resampling_seed,
            "latent_biological": config.final_biological_parameter_seed,
        },
        "final_outcomes_seen": False,
    }
    frozen_protocol["frozen_phase9_decision_hash"] = _semantic_hash(frozen_protocol)
    _json_write(output_dir / "selector_artifacts.json", selector_payload)
    _json_write(
        output_dir / "frozen_utility_constraints.json",
        {
            "artifact_version": PHASE9_VERSION,
            "configuration_hash": config.stable_hash(),
            "profiles": [profile.model_dump(mode="json") for profile in config.utility_profiles],
            "claim": "Every weight and threshold is a scenario choice, not agronomic advice.",
        },
    )
    _json_write(output_dir / "frozen_protocol.json", frozen_protocol)

    records: list[dict[str, object]] = []
    predictions: list[dict[str, object]] = []
    oracles: list[dict[str, object]] = []
    for experiment in experiments:
        selected, predicted, oracle = evaluate_experiment(
            experiment=experiment,
            profiles=config.utility_profiles,
            state=state,
            bundle=bundle,
            accounting=accounting,
            config=config,
            final=False,
        )
        records.extend(selected)
        predictions.extend(predicted)
        oracles.extend(oracle)

    final_experiment = _generate_experiment(
        run_id="frozen-final",
        base_dataset=base_dataset,
        population_config=population_config,
        parameters=parameters,
        scenario=scenario,
        config=config,
        foundation_seed=config.final_foundation_seed,
        population_seed=config.final_population_seed,
        weather_seed=config.final_weather_resampling_seed,
        biological_seed=config.final_biological_parameter_seed,
        population_size=config.final_population_size,
    )
    selected, predicted, oracle = evaluate_experiment(
        experiment=final_experiment,
        profiles=config.utility_profiles,
        state=state,
        bundle=bundle,
        accounting=accounting,
        config=config,
        final=True,
    )
    records.extend(selected)
    predictions.extend(predicted)
    oracles.extend(oracle)
    base_final_records = list(selected)

    correlation_experiment = replace(
        final_experiment,
        run_id="stress-engineered-correlation-disruption",
        rows=_permuted_correlation_rows(final_experiment.rows),
    )
    correlation_records, _, _ = evaluate_experiment(
        experiment=correlation_experiment,
        profiles=config.utility_profiles,
        state=state,
        bundle=bundle,
        accounting=accounting,
        config=config,
        final=True,
    )
    interval_stress: dict[str, object] = {}
    for multiplier in (0.5, 1.0, 1.5):
        if multiplier == 1.0:
            scaled_records = base_final_records
        else:
            scaled_records, _, _ = evaluate_experiment(
                experiment=replace(
                    final_experiment,
                    run_id=f"stress-interval-width-{multiplier:.1f}",
                ),
                profiles=config.utility_profiles,
                state=state,
                bundle=_scale_interval_bundle(bundle, multiplier),
                accounting=accounting,
                config=config,
                final=True,
            )
        interval_stress[f"{multiplier:.1f}"] = {
            method: _stress_metrics(scaled_records, method=method)
            for method in (
                "uncertainty_lcb",
                "uncertainty_overlap_abstain",
                "uncertainty_baseline_abstain",
            )
        }
    parameter_stress: list[dict[str, object]] = []
    for endpoint in ("minimum", "maximum"):
        stressed_parameters, parameter_record = _parameter_stress_variant(parameters, endpoint)
        stressed_batch = run_population_batch(
            final_experiment.population,
            scenario,
            stressed_parameters,
            population_config,
            horizons_months=config.simulation_horizons_months,
        )
        if stressed_batch.failures:
            raise RuntimeError(f"provisional parameter stress {endpoint} contains failures")
        stressed_rows, stressed_manifest = build_ml_dataset(
            final_experiment.population,
            stressed_batch,
            config,
            dataset_version=PHASE9_VERSION,
        )
        stressed_experiment = ExperimentData(
            run_id=f"stress-provisional-parameter-{endpoint}",
            population=final_experiment.population,
            batch=stressed_batch,
            rows=stressed_rows,
            dataset_hash=stressed_manifest.dataset_hash,
            seeds=final_experiment.seeds,
        )
        stressed_records, _, _ = evaluate_experiment(
            experiment=stressed_experiment,
            profiles=config.utility_profiles,
            state=state,
            bundle=bundle,
            accounting=accounting,
            config=config,
            final=True,
        )
        parameter_stress.append(
            {
                **parameter_record,
                "dataset_hash": stressed_manifest.dataset_hash,
                "maximum_carbon_residual_t_c_ha": (stressed_batch.maximum_carbon_residual_t_c_ha),
                "maximum_phosphorus_residual_kg_p_ha": (
                    stressed_batch.maximum_phosphorus_residual_kg_p_ha
                ),
                "observable_ml": _stress_metrics(stressed_records),
                "policy_mean": _stress_metrics(stressed_records, method="policy_mean"),
            }
        )
    stress_results = {
        "artifact_version": PHASE9_VERSION,
        "claim_boundary": CLAIM_BOUNDARY,
        "selector_recalibrated_for_any_stress": False,
        "utility_weight_and_constraint_profiles": {
            profile.profile_id: _stress_metrics(
                [
                    record
                    for record in base_final_records
                    if record["profile_id"] == profile.profile_id
                ]
            )
            for profile in config.utility_profiles
        },
        "small_measurement_perturbations": {
            "fraction_of_frozen_training_scale": (
                config.stability_perturbation_fraction_of_training_scale
            ),
            "observable_ml_policy_stability": (
                sum(
                    bool(record["stable_under_small_input_perturbation"])
                    for record in base_final_records
                    if record["method"] == "observable_ml"
                )
                / sum(record["method"] == "observable_ml" for record in base_final_records)
            ),
        },
        "engineered_generator_correlation_disruption": {
            "features_permuted_at_field_level": [
                "baseline_soc_t_c_ha",
                "baseline_soc_concentration_g_kg",
                "bulk_density_g_cm3",
                "initial_phosphorus_status",
            ],
            "baseline": _stress_metrics(base_final_records),
            "disrupted": _stress_metrics(correlation_records),
            "models_refit": False,
        },
        "hidden_state_gaps": _hidden_gap_stress(base_final_records),
        "weather_regime": _subgroup_stress(base_final_records, "weather_regime"),
        "field_archetype": _subgroup_stress(base_final_records, "archetype"),
        "model_choice": {
            method: _stress_metrics(base_final_records, method=method)
            for method in ("policy_mean", "observable_ml")
        },
        "uncertainty_interval_width_multiplier": interval_stress,
        "provisional_intervention_effect_parameter": parameter_stress,
    }
    summaries = summarise_results(records)
    success = _success_gates(summaries, config)
    applicability_records = [
        record
        for record in records
        if str(record["method"]).startswith("observable")
        or str(record["method"]).startswith("uncertainty")
    ]
    unsupported_non_abstaining = [
        record
        for record in applicability_records
        if not bool(record["applicable"]) and record["selected_policy"] is not None
    ]
    cast(dict[str, bool], success["gates"])[
        "applicability_enforcement_zero_unsupported_non_abstaining_selections"
    ] = not unsupported_non_abstaining
    success["passed"] = all(cast(dict[str, bool], success["gates"]).values())
    if not bool(success["passed"]):
        success["recommendation"] = (
            "Do not continue recommendation-system development: one or more predeclared "
            "synthetic Phase 9 gates failed."
        )
    manifest = {
        "artifact_version": PHASE9_VERSION,
        "phase9_configuration_hash": config.stable_hash(),
        "frozen_phase9_decision_hash": frozen_protocol["frozen_phase9_decision_hash"],
        "selector_state_hash": state.stable_hash,
        "development_runs": [
            {
                "run_id": experiment.run_id,
                "seeds": experiment.seeds,
                "population_hash": experiment.population.manifest.population_hash,
                "dataset_hash": experiment.dataset_hash,
                "field_count": len(experiment.population.fields),
                "maximum_carbon_residual_t_c_ha": experiment.batch.maximum_carbon_residual_t_c_ha,
                "maximum_phosphorus_residual_kg_p_ha": (
                    experiment.batch.maximum_phosphorus_residual_kg_p_ha
                ),
            }
            for experiment in experiments
        ],
        "frozen_final": {
            "seeds": final_experiment.seeds,
            "population_hash": final_experiment.population.manifest.population_hash,
            "dataset_hash": final_experiment.dataset_hash,
            "field_count": len(final_experiment.population.fields),
            "generated_after_frozen_phase9_decision_hash": frozen_protocol[
                "frozen_phase9_decision_hash"
            ],
            "used_for_tuning": False,
        },
    }
    report: dict[str, object] = {
        "report_version": PHASE9_VERSION,
        "claim_boundary": CLAIM_BOUNDARY,
        "protected_soc_status": "model proxy; not measured MAOC",
        "selection_architecture": (
            "Frozen observable prediction -> applicability/eligibility -> utility/constraints "
            "-> selection or explicit abstention -> simulator reveal -> oracle regret"
        ),
        "experiment_manifest": manifest,
        "selector_artifacts": selector_payload,
        "repeated_run_summary": summaries,
        "success_gates": success,
        "applicability_and_abstention": {
            "unsupported_non_abstaining_selection_count": len(unsupported_non_abstaining),
            "record_count": len(applicability_records),
            "mandatory_abstention_preserved": not unsupported_non_abstaining,
            "predictive_interval_claim": (
                "Frozen Phase 8.6 synthetic residual intervals only; not causal, mechanistic, "
                "structural-simulator or real-field uncertainty."
            ),
        },
        "stress_tests": stress_results,
        "runtime_seconds": time.perf_counter() - started,
    }
    semantic_report = {key: value for key, value in report.items() if key != "runtime_seconds"}
    report["deterministic_report_hash"] = _semantic_hash(semantic_report)
    _json_write(output_dir / "experiment_manifest.json", manifest)
    _json_write(output_dir / "field_level_policy_predictions.json", predictions)
    _json_write(output_dir / "oracle_outcomes.json", oracles)
    _json_write(output_dir / "regret_results.json", records)
    _json_write(output_dir / "repeated_run_summary.json", summaries)
    _json_write(output_dir / "stress_test_results.json", stress_results)
    _json_write(output_dir / "frozen_final_evaluation_report.json", report)
    _json_write(
        output_dir / "applicability_abstention_report.json", report["applicability_and_abstention"]
    )
    _write_csv(
        output_dir / "regret_results.csv",
        records,
        tuple(records[0].keys()),
    )
    selection_dataset = [
        {
            "run_id": item["run_id"],
            "final_evaluation": item["final_evaluation"],
            "field_id": item["field_id"],
            "profile_id": item["profile_id"],
            "oracle_policy": item["oracle_policy"],
            "feasible_policies": item["feasible_policies"],
            "outcomes": item["outcomes"],
        }
        for item in oracles
    ]
    _json_write(output_dir / "selection_dataset_v0.9.0.json", selection_dataset)
    dataset_manifest = {
        "artifact_version": PHASE9_VERSION,
        "row_count": len(selection_dataset),
        "dataset_hash": _semantic_hash(selection_dataset),
        "development_field_keys_hash": _semantic_hash(list(state.fitted_field_keys)),
        "normalisation_fitted_on_training_validation_only": True,
        "final_outcomes_used_for_tuning": False,
        "units": {name: stat.unit for name, stat in state.normalisation.stats.items()},
        "provenance": CLAIM_BOUNDARY,
    }
    _json_write(output_dir / "selection_dataset_manifest.json", dataset_manifest)
    table = _benchmark_table(report)
    (output_dir / "benchmark_table.txt").write_text(table + "\n", encoding="utf-8")
    return report, table
