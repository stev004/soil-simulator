"""Pure utility, constraint, oracle and regret calculations for Phase 9.

Yield uses ``t dry matter ha-1``; SOC quantities use ``t C ha-1``; cost uses
``GBP ha-1``; and the non-mechanistic emissions proxy uses ``kg CO2e ha-1``.
All values are paired intervention-minus-baseline effects except cost and
emissions, whose baseline is zero.  Protected SOC is a model proxy.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass

from soil_simulator.selection.schema import HardConstraints, UtilityProfile

OBJECTIVE_NAMES = (
    "yield_effect",
    "total_soc_effect_5y",
    "total_soc_effect_10y",
    "protected_soc_proxy_effect_5y",
    "protected_soc_proxy_effect_10y",
    "intervention_cost",
    "emissions_proxy",
)


@dataclass(frozen=True)
class OutcomeValues:
    """One policy's five benefits and two accounting burdens."""

    yield_effect: float
    total_soc_effect_5y: float
    total_soc_effect_10y: float
    protected_soc_proxy_effect_5y: float
    protected_soc_proxy_effect_10y: float
    intervention_cost: float
    emissions_proxy: float

    def as_dict(self) -> dict[str, float]:
        """Return named finite objective values."""
        values = {
            "yield_effect": self.yield_effect,
            "total_soc_effect_5y": self.total_soc_effect_5y,
            "total_soc_effect_10y": self.total_soc_effect_10y,
            "protected_soc_proxy_effect_5y": self.protected_soc_proxy_effect_5y,
            "protected_soc_proxy_effect_10y": self.protected_soc_proxy_effect_10y,
            "intervention_cost": self.intervention_cost,
            "emissions_proxy": self.emissions_proxy,
        }
        if any(not math.isfinite(value) for value in values.values()):
            raise ValueError("outcome values must be finite")
        return values


@dataclass(frozen=True)
class OutcomeInterval:
    """Point and synthetic predictive limits; costs are known policy metadata."""

    point: OutcomeValues
    lower: OutcomeValues
    upper: OutcomeValues


@dataclass(frozen=True)
class NormalisationStat:
    """Training/validation-only mean and population SD for one objective."""

    mean: float
    scale: float
    unit: str
    fitted_partition: str = "phase9_train_and_validation_only"


@dataclass(frozen=True)
class NormalisationContract:
    """Frozen objective scaling fitted before untouched evaluation."""

    stats: dict[str, NormalisationStat]
    fitted_row_ids_hash: str

    def stable_hash(self) -> str:
        """Return a semantic artifact hash."""
        payload = {
            "stats": {
                name: {
                    "mean": value.mean,
                    "scale": value.scale,
                    "unit": value.unit,
                    "fitted_partition": value.fitted_partition,
                }
                for name, value in sorted(self.stats.items())
            },
            "fitted_row_ids_hash": self.fitted_row_ids_hash,
        }
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode()).hexdigest()


@dataclass(frozen=True)
class ConstraintDecision:
    """Auditable feasibility result for one policy."""

    feasible: bool
    violations: tuple[str, ...]


@dataclass(frozen=True)
class OracleDecision:
    """True feasible simulator policy selected only after predictions are fixed."""

    policy_id: str | None
    utility: float | None
    feasible_policies: tuple[str, ...]


@dataclass(frozen=True)
class RegretValues:
    """Utility and raw-objective gaps from the true feasible oracle."""

    utility_regret: float
    normalised_regret: float
    yield_regret: float
    total_soc_regret_5y: float
    total_soc_regret_10y: float
    protected_soc_proxy_regret_5y: float
    protected_soc_proxy_regret_10y: float


def fit_normalisation(
    rows: tuple[tuple[str, OutcomeValues], ...],
) -> NormalisationContract:
    """Fit means and SDs from explicitly supplied training/validation outcomes only."""
    if not rows:
        raise ValueError("normalisation requires training/validation outcomes")
    units = {
        "yield_effect": "t dry matter ha-1 versus paired baseline",
        "total_soc_effect_5y": "t C ha-1 versus paired baseline",
        "total_soc_effect_10y": "t C ha-1 versus paired baseline",
        "protected_soc_proxy_effect_5y": "t C ha-1 versus paired baseline proxy",
        "protected_soc_proxy_effect_10y": "t C ha-1 versus paired baseline proxy",
        "intervention_cost": "GBP ha-1",
        "emissions_proxy": "kg CO2e ha-1 non-mechanistic proxy",
    }
    stats: dict[str, NormalisationStat] = {}
    dictionaries = tuple(value.as_dict() for _, value in rows)
    for name in OBJECTIVE_NAMES:
        values = tuple(item[name] for item in dictionaries)
        mean = math.fsum(values) / len(values)
        variance = math.fsum((value - mean) ** 2 for value in values) / len(values)
        scale = math.sqrt(variance)
        stats[name] = NormalisationStat(
            mean=mean,
            scale=scale if scale > 1.0e-12 else 1.0,
            unit=units[name],
        )
    row_ids = json.dumps(sorted(row_id for row_id, _ in rows), separators=(",", ":"))
    return NormalisationContract(
        stats=stats,
        fitted_row_ids_hash=hashlib.sha256(row_ids.encode()).hexdigest(),
    )


def utility(
    values: OutcomeValues,
    profile: UtilityProfile,
    normalisation: NormalisationContract,
) -> float:
    """Calculate the transparent weighted utility for one scenario profile."""
    raw = values.as_dict()

    def z(name: str) -> float:
        stat = normalisation.stats[name]
        return (raw[name] - stat.mean) / stat.scale

    horizon_5y, horizon_10y = profile.carbon_horizon_weights
    total_soc = horizon_5y * z("total_soc_effect_5y") + horizon_10y * z("total_soc_effect_10y")
    protected = horizon_5y * z("protected_soc_proxy_effect_5y") + horizon_10y * z(
        "protected_soc_proxy_effect_10y"
    )
    weights = profile.weights
    return (
        weights.yield_effect * z("yield_effect")
        + weights.total_soc_effect * total_soc
        + weights.protected_soc_proxy_effect * protected
        - weights.intervention_cost * z("intervention_cost")
        - weights.emissions_proxy * z("emissions_proxy")
    )


def utility_interval(
    values: OutcomeInterval,
    profile: UtilityProfile,
    normalisation: NormalisationContract,
) -> tuple[float, float]:
    """Propagate frozen marginal residual limits conservatively into utility."""
    return (
        utility(values.lower, profile, normalisation),
        utility(values.upper, profile, normalisation),
    )


def constraints_allow(
    values: OutcomeValues,
    constraints: HardConstraints,
    *,
    eligible: bool,
    applicable: bool,
) -> ConstraintDecision:
    """Apply hard thresholds without clipping or replacing a failed policy."""
    violations: list[str] = []
    if not eligible:
        violations.append("intervention_ineligible")
    if not applicable:
        violations.append("outside_applicability_domain")
    if values.yield_effect < -constraints.maximum_yield_loss_t_dm_ha:
        violations.append("maximum_yield_loss")
    if values.intervention_cost > constraints.maximum_cost_gbp_ha:
        violations.append("maximum_cost")
    if values.emissions_proxy > constraints.maximum_emissions_proxy_kg_co2e_ha:
        violations.append("maximum_emissions_proxy")
    horizon_5y_carbon = values.total_soc_effect_5y
    horizon_10y_carbon = values.total_soc_effect_10y
    if min(horizon_5y_carbon, horizon_10y_carbon) < constraints.minimum_total_soc_benefit_t_c_ha:
        violations.append("minimum_total_soc_benefit")
    return ConstraintDecision(feasible=not violations, violations=tuple(violations))


def exhaustive_oracle(
    outcomes: dict[str, OutcomeValues],
    eligible_policies: set[str],
    profile: UtilityProfile,
    normalisation: NormalisationContract,
) -> OracleDecision:
    """Choose the true best feasible policy for post-selection evaluation only."""
    feasible = tuple(
        policy
        for policy in sorted(outcomes)
        if constraints_allow(
            outcomes[policy],
            profile.constraints,
            eligible=policy in eligible_policies,
            applicable=True,
        ).feasible
    )
    if not feasible:
        return OracleDecision(policy_id=None, utility=None, feasible_policies=())
    scored = {policy: utility(outcomes[policy], profile, normalisation) for policy in feasible}
    winner = min(feasible, key=lambda policy: (-scored[policy], policy))
    return OracleDecision(policy_id=winner, utility=scored[winner], feasible_policies=feasible)


def calculate_regret(
    *,
    selected_policy: str | None,
    abstention_evaluation_policy: str,
    oracle: OracleDecision,
    outcomes: dict[str, OutcomeValues],
    profile: UtilityProfile,
    normalisation: NormalisationContract,
) -> RegretValues | None:
    """Calculate non-negative utility regret and signed raw objective gaps."""
    if oracle.policy_id is None or oracle.utility is None:
        return None
    evaluated = selected_policy if selected_policy is not None else abstention_evaluation_policy
    if evaluated not in outcomes:
        raise ValueError("selected/evaluation policy has no revealed simulator outcome")
    chosen = outcomes[evaluated]
    truth = outcomes[oracle.policy_id]
    chosen_utility = utility(chosen, profile, normalisation)
    utility_regret = max(0.0, oracle.utility - chosen_utility)
    feasible_utilities = [
        utility(outcomes[policy], profile, normalisation) for policy in oracle.feasible_policies
    ]
    denominator = oracle.utility - min(feasible_utilities)
    normalised = utility_regret / denominator if denominator > 1.0e-12 else 0.0
    return RegretValues(
        utility_regret=utility_regret,
        normalised_regret=max(0.0, min(1.0, normalised)),
        yield_regret=truth.yield_effect - chosen.yield_effect,
        total_soc_regret_5y=truth.total_soc_effect_5y - chosen.total_soc_effect_5y,
        total_soc_regret_10y=truth.total_soc_effect_10y - chosen.total_soc_effect_10y,
        protected_soc_proxy_regret_5y=(
            truth.protected_soc_proxy_effect_5y - chosen.protected_soc_proxy_effect_5y
        ),
        protected_soc_proxy_regret_10y=(
            truth.protected_soc_proxy_effect_10y - chosen.protected_soc_proxy_effect_10y
        ),
    )


def is_catastrophic_failure(
    regret: RegretValues | None,
    actual_constraints: ConstraintDecision,
    threshold: float,
) -> bool:
    """Classify a predeclared catastrophic failure transparently.

    A result is catastrophic when the normalised oracle regret is at least the
    configured threshold or the revealed action violates any hard constraint.
    """
    return bool(actual_constraints.violations) or (
        regret is not None and regret.normalised_regret >= threshold
    )
