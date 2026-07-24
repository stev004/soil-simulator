"""Leakage-resistant policy selectors for the Phase 9 offline benchmark."""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass

from soil_simulator.ml.schema import MlRow
from soil_simulator.selection.artifacts import (
    FrozenArtifactError,
    FrozenPhase86Bundle,
    observable_applicability_reasons,
    predict_frozen_task,
)
from soil_simulator.selection.core import (
    NormalisationContract,
    OutcomeInterval,
    OutcomeValues,
    constraints_allow,
    utility,
    utility_interval,
)
from soil_simulator.selection.schema import PHASE9_POLICIES, UtilityProfile


@dataclass(frozen=True)
class SelectionDecision:
    """A policy or explicit abstention, with no revealed simulator outcomes."""

    method: str
    selected_policy: str | None
    abstained: bool
    reason: str | None
    predicted_utility: float | None
    applicable: bool


@dataclass(frozen=True)
class FrozenPolicyPredictions:
    """Observable-only policy predictions and mandatory abstention reasons."""

    intervals: dict[str, OutcomeInterval]
    rejection_reasons: dict[str, tuple[str, ...]]


def deterministic_random_policy(
    *, field_id: str, profile_id: str, eligible_policies: set[str], random_seed: int
) -> str | None:
    """Choose a replayable random eligible policy without reading outcomes."""
    choices = tuple(policy for policy in PHASE9_POLICIES if policy in eligible_policies)
    if not choices:
        return None
    digest = hashlib.sha256(f"{random_seed}|{field_id}|{profile_id}".encode()).digest()
    return choices[int.from_bytes(digest[:8], "big") % len(choices)]


def build_frozen_policy_predictions(
    *,
    rows_by_policy_horizon: dict[tuple[str, int], MlRow],
    eligible_policies: set[str],
    accounting: dict[str, tuple[float, float]],
    bundle: FrozenPhase86Bundle,
) -> FrozenPolicyPredictions:
    """Score only observable rows and preserve every applicability failure."""
    intervals: dict[str, OutcomeInterval] = {}
    rejected: dict[str, tuple[str, ...]] = {}
    tasks = (
        "delta_crop_yield_t_dm_ha@24",
        "delta_final_total_soc_t_c_ha@60",
        "delta_final_total_soc_t_c_ha@120",
        "delta_final_protected_soc_proxy_t_c_ha@60",
        "delta_final_protected_soc_proxy_t_c_ha@120",
    )
    for policy in PHASE9_POLICIES:
        reasons: list[str] = []
        if policy not in eligible_policies:
            reasons.append("intervention_ineligible")
        task_rows: dict[str, MlRow] = {}
        for task in tasks:
            _, horizon_raw = task.rsplit("@", maxsplit=1)
            row = rows_by_policy_horizon.get((policy, int(horizon_raw)))
            if row is None:
                reasons.append(f"missing_required_observations:{task}")
                continue
            task_rows[task] = row
            reasons.extend(observable_applicability_reasons(row, task=task, bundle=bundle))
        if reasons:
            rejected[policy] = tuple(sorted(set(reasons)))
            continue
        predictions: dict[str, tuple[float, float]] = {}
        try:
            for task, row in task_rows.items():
                predictions[task] = predict_frozen_task(row, task=task, bundle=bundle)
        except FrozenArtifactError as exc:
            rejected[policy] = (f"frozen_prediction_unavailable:{exc}",)
            continue
        cost, emissions = accounting[policy]
        point = OutcomeValues(
            yield_effect=predictions[tasks[0]][0],
            total_soc_effect_5y=predictions[tasks[1]][0],
            total_soc_effect_10y=predictions[tasks[2]][0],
            protected_soc_proxy_effect_5y=predictions[tasks[3]][0],
            protected_soc_proxy_effect_10y=predictions[tasks[4]][0],
            intervention_cost=cost,
            emissions_proxy=emissions,
        )
        lower = OutcomeValues(
            yield_effect=point.yield_effect - predictions[tasks[0]][1],
            total_soc_effect_5y=point.total_soc_effect_5y - predictions[tasks[1]][1],
            total_soc_effect_10y=point.total_soc_effect_10y - predictions[tasks[2]][1],
            protected_soc_proxy_effect_5y=(
                point.protected_soc_proxy_effect_5y - predictions[tasks[3]][1]
            ),
            protected_soc_proxy_effect_10y=(
                point.protected_soc_proxy_effect_10y - predictions[tasks[4]][1]
            ),
            intervention_cost=cost,
            emissions_proxy=emissions,
        )
        upper = OutcomeValues(
            yield_effect=point.yield_effect + predictions[tasks[0]][1],
            total_soc_effect_5y=point.total_soc_effect_5y + predictions[tasks[1]][1],
            total_soc_effect_10y=point.total_soc_effect_10y + predictions[tasks[2]][1],
            protected_soc_proxy_effect_5y=(
                point.protected_soc_proxy_effect_5y + predictions[tasks[3]][1]
            ),
            protected_soc_proxy_effect_10y=(
                point.protected_soc_proxy_effect_10y + predictions[tasks[4]][1]
            ),
            intervention_cost=cost,
            emissions_proxy=emissions,
        )
        intervals[policy] = OutcomeInterval(point=point, lower=lower, upper=upper)
    return FrozenPolicyPredictions(intervals=intervals, rejection_reasons=rejected)


def _abstain(method: str, reason: str, *, applicable: bool) -> SelectionDecision:
    return SelectionDecision(
        method=method,
        selected_policy=None,
        abstained=True,
        reason=reason,
        predicted_utility=None,
        applicable=applicable,
    )


def select_from_estimates(
    *,
    method: str,
    estimates: dict[str, OutcomeValues],
    eligible_policies: set[str],
    profile: UtilityProfile,
    normalisation: NormalisationContract,
) -> SelectionDecision:
    """Select with training-only policy means or another point-estimate baseline."""
    feasible = tuple(
        policy
        for policy in PHASE9_POLICIES
        if policy in estimates
        and constraints_allow(
            estimates[policy],
            profile.constraints,
            eligible=policy in eligible_policies,
            applicable=True,
        ).feasible
    )
    if not feasible:
        return _abstain(method, "no_policy_satisfies_predicted_constraints", applicable=True)
    scores = {policy: utility(estimates[policy], profile, normalisation) for policy in feasible}
    winner = min(feasible, key=lambda policy: (-scores[policy], policy))
    return SelectionDecision(method, winner, False, None, scores[winner], True)


def select_observable_ml(
    *,
    method: str,
    predictions: FrozenPolicyPredictions,
    eligible_policies: set[str],
    profile: UtilityProfile,
    normalisation: NormalisationContract,
    overlap_tolerance: float,
    improvement_margin: float,
) -> SelectionDecision:
    """Select by point or lower-confidence-bound score with explicit abstention."""
    if not predictions.intervals:
        reasons = sorted(
            {reason for values in predictions.rejection_reasons.values() for reason in values}
        )
        return _abstain(
            method, "mandatory_applicability_abstention:" + ",".join(reasons), applicable=False
        )
    conservative = method != "observable_ml"
    feasible: list[str] = []
    bounds: dict[str, tuple[float, float]] = {}
    point_scores: dict[str, float] = {}
    for policy, interval in predictions.intervals.items():
        constrained = interval.lower if conservative else interval.point
        if constraints_allow(
            constrained,
            profile.constraints,
            eligible=policy in eligible_policies,
            applicable=True,
        ).feasible:
            feasible.append(policy)
            bounds[policy] = utility_interval(interval, profile, normalisation)
            point_scores[policy] = utility(interval.point, profile, normalisation)
    if not feasible:
        return _abstain(method, "no_policy_satisfies_predicted_constraints", applicable=True)
    score = {
        policy: bounds[policy][0] if conservative else point_scores[policy] for policy in feasible
    }
    winner = min(feasible, key=lambda policy: (-score[policy], policy))
    if method == "uncertainty_overlap_abstain" and len(feasible) > 1:
        alternatives = tuple(policy for policy in feasible if policy != winner)
        best_alternative_upper = max(bounds[policy][1] for policy in alternatives)
        if bounds[winner][0] <= best_alternative_upper + overlap_tolerance:
            return _abstain(method, "material_policy_ranking_overlap", applicable=True)
    if method == "uncertainty_baseline_abstain" and winner != "baseline":
        baseline = predictions.intervals.get("baseline")
        if baseline is None:
            return _abstain(method, "baseline_uncertainty_unavailable", applicable=False)
        baseline_upper = utility_interval(baseline, profile, normalisation)[1]
        if bounds[winner][0] <= baseline_upper + improvement_margin:
            return _abstain(method, "no_confident_improvement_over_baseline", applicable=True)
    return SelectionDecision(method, winner, False, None, score[winner], True)


def transparent_rule_policy(*, row: MlRow, eligible_policies: set[str]) -> str:
    """Apply a fixed observable-only benchmark rule, not agronomic guidance."""
    phosphorus_status = str(row.features.get("initial_phosphorus_status", ""))
    tillage = float(row.features.get("management_history_tillage_intensity", math.nan))
    historical_cover = float(row.features.get("management_history_cover_crop_indicator", math.nan))
    if phosphorus_status == "low" and "phosphorus" in eligible_policies:
        return "phosphorus"
    if math.isfinite(tillage) and tillage >= 1.5 and "reduced_tillage" in eligible_policies:
        return "reduced_tillage"
    if (
        math.isfinite(historical_cover)
        and historical_cover < 0.5
        and "cover_crop" in eligible_policies
    ):
        return "cover_crop"
    return "baseline"
