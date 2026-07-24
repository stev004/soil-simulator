"""Phase 9.5 policy deduplication and recurring biological schedules."""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from datetime import date

from soil_simulator.domain.enums import ManagementEventType
from soil_simulator.domain.management import (
    ManagementPolicy,
    ManagementScenarioSet,
    ManagementSimulationResult,
    event_simulation_month,
)
from soil_simulator.domain.models import ManagementEvent, ModelParameters
from soil_simulator.simulator.management import run_management_policy

PHASE95_POLICY_IDS: tuple[str, ...] = (
    "baseline",
    "conventional_tillage",
    "reduced_tillage",
    "cover_crop",
    "phosphorus",
    "farmyard_manure",
)


def _copy_event(event: ManagementEvent, month: int, suffix: int) -> ManagementEvent:
    values = event.model_dump(mode="python")
    values.update(
        event_id=f"phase95-{event.event_id}-{suffix:02d}",
        event_date=None,
        simulation_month=month,
        provenance=f"{event.provenance} Phase 9.5 explicit recurring schedule.",
    )
    return ManagementEvent.model_validate(values)


def recurring_policy(
    policy: ManagementPolicy,
    horizon_months: int,
    *,
    start_date: date,
    interval_months: int = 12,
    phosphorus_amount_kg_p_ha: float | None = None,
) -> ManagementPolicy:
    """Expand the first explicit policy cycle to a complete horizon.

    Cover events are emitted only as complete establishment/termination pairs.
    All other interventions recur from their first configured event.  Historical
    Phase 6 policy objects remain unchanged.
    """
    if horizon_months < 1 or interval_months < 1:
        raise ValueError("horizon and interval must be positive")
    if policy.policy_id == "baseline":
        return policy.model_copy(update={"events": ()})
    by_type: dict[ManagementEventType, list[ManagementEvent]] = defaultdict(list)
    for event in policy.events:
        by_type[event.event_type].append(event)
    prototypes = {
        kind: min(
            events,
            key=lambda item: event_simulation_month(item, start_date),
        )
        for kind, events in by_type.items()
    }
    events: list[ManagementEvent] = []
    if {
        ManagementEventType.COVER_CROP_ESTABLISHMENT,
        ManagementEventType.COVER_CROP_TERMINATION,
    }.issubset(prototypes):
        establish = prototypes[ManagementEventType.COVER_CROP_ESTABLISHMENT]
        terminate = prototypes[ManagementEventType.COVER_CROP_TERMINATION]
        start = event_simulation_month(establish, start_date)
        end = event_simulation_month(terminate, start_date)
        if end <= start:
            raise ValueError("cover prototypes require ordered simulation months")
        cycle = 0
        while end + cycle * interval_months < horizon_months:
            events.append(_copy_event(establish, start + cycle * interval_months, cycle))
            events.append(_copy_event(terminate, end + cycle * interval_months, cycle))
            cycle += 1
    else:
        for prototype in prototypes.values():
            first = event_simulation_month(prototype, start_date)
            cycle = 0
            month = first
            while month < horizon_months:
                copied = _copy_event(prototype, month, cycle)
                if (
                    phosphorus_amount_kg_p_ha is not None
                    and copied.event_type is ManagementEventType.PHOSPHORUS_APPLICATION
                ):
                    copied = copied.model_copy(update={"amount": phosphorus_amount_kg_p_ha})
                events.append(copied)
                cycle += 1
                month = first + cycle * interval_months
    return policy.model_copy(update={"events": tuple(events)})


def phase95_policy_set(
    policies: tuple[ManagementPolicy, ...],
    horizon_months: int,
    *,
    start_date: date,
    interval_months: int = 12,
    phosphorus_amount_kg_p_ha: float | None = None,
) -> tuple[ManagementPolicy, ...]:
    """Return the six honest Phase 9.5 policies with recurring schedules."""
    by_id = {policy.policy_id: policy for policy in policies}
    missing = set(PHASE95_POLICY_IDS) - set(by_id)
    if missing:
        raise ValueError(f"missing Phase 9.5 policies: {sorted(missing)}")
    return tuple(
        recurring_policy(
            by_id[policy_id],
            horizon_months,
            start_date=start_date,
            interval_months=interval_months,
            phosphorus_amount_kg_p_ha=phosphorus_amount_kg_p_ha,
        )
        for policy_id in PHASE95_POLICY_IDS
    )


def _biological_digest(result: ManagementSimulationResult) -> str:
    data = result.model_dump(mode="json")
    data.pop("policy_id")
    data.pop("policy_name")
    data.pop("schedule_hash")
    data.pop("cumulative_cost_gbp_ha")
    data.pop("cumulative_emissions_proxy_kg_co2e_ha")
    data.pop("provenance")
    data.pop("applied_events")
    for step in data["steps"]:
        step.pop("applied_events")
        step.pop("cost_gbp_ha")
        step.pop("emissions_proxy_kg_co2e_ha")
    payload = json.dumps(data, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(payload.encode()).hexdigest()


def duplicate_policy_report(
    scenario: ManagementScenarioSet, parameters: ModelParameters
) -> dict[str, object]:
    """Detect exact biological duplicates under a common deterministic scenario."""
    digests = {
        policy.policy_id: _biological_digest(run_management_policy(scenario, policy, parameters))
        for policy in scenario.policies
    }
    groups: dict[str, list[str]] = defaultdict(list)
    for policy_id, digest in digests.items():
        groups[digest].append(policy_id)
    duplicates = tuple(tuple(sorted(group)) for group in groups.values() if len(group) > 1)
    return {
        "version": "0.9.5",
        "biological_digests": digests,
        "duplicate_groups": duplicates,
        "resolution": "remove no_till from Phase 9.5 benchmark policy set",
        "phase95_policy_ids": PHASE95_POLICY_IDS,
        "passed": "no_till" not in PHASE95_POLICY_IDS,
    }


def scenario_with_phase95_policies(
    scenario: ManagementScenarioSet,
    horizon_months: int,
    *,
    interval_months: int = 12,
    phosphorus_amount_kg_p_ha: float | None = None,
) -> ManagementScenarioSet:
    """Replace policies with validated Phase 9.5 schedules, leaving forcing unchanged."""
    values = scenario.model_dump(mode="python")
    values.update(
        version="0.9.5",
        monthly_steps=scenario.monthly_steps[:horizon_months],
        policies=phase95_policy_set(
            scenario.policies,
            horizon_months,
            start_date=scenario.start_date,
            interval_months=interval_months,
            phosphorus_amount_kg_p_ha=phosphorus_amount_kg_p_ha,
        ),
        provenance=(f"{scenario.provenance}; Phase 9.5 horizon-aware schedules; no_till removed"),
    )
    return ManagementScenarioSet.model_validate(values)
