"""Horizon-aware scheduled-event cost and emissions accounting.

Accounting is external to biological carbon and phosphorus balances.  Costs
use ``GBP ha-1`` and emissions use ``kg CO2e ha-1``.  Operational and lifecycle
components are kept separate; all current values remain provisional scenario
assumptions rather than regional farm budgets or complete LCAs.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Annotated, Literal

import yaml
from pydantic import Field, model_validator

from soil_simulator.domain.models import ContractModel, NonNegativeFloat, NonNegativeInt


class AccountingEvent(ContractModel):
    """One repeatable accounting event with explicit timing and provenance."""

    event_id: Annotated[str, Field(min_length=1)]
    policy_id: Annotated[str, Field(min_length=1)]
    event_type: Annotated[str, Field(min_length=1)]
    first_month: NonNegativeInt
    repeat_every_months: Annotated[int, Field(gt=0)]
    pair_id: str | None = None
    cost_gbp_ha: NonNegativeFloat
    operational_emissions_kg_co2e_ha: NonNegativeFloat
    lifecycle_emissions_kg_co2e_ha: NonNegativeFloat
    lifecycle_boundary: Literal["partial", "unsupported"]
    classification: Literal["scenario_assumption"] = "scenario_assumption"
    provenance: Annotated[str, Field(min_length=1)]


class AccountingSchedule(ContractModel):
    """Validated Phase 9.5 recurring-event accounting specification."""

    version: Literal["0.9.5"]
    events: Annotated[tuple[AccountingEvent, ...], Field(min_length=1)]
    units: dict[str, str]
    claim_boundary: Annotated[str, Field(min_length=1)]

    @model_validator(mode="after")
    def validate_unique_events(self) -> AccountingSchedule:
        ids = [event.event_id for event in self.events]
        if len(ids) != len(set(ids)):
            raise ValueError("accounting event_id values must be unique")
        pairs: dict[tuple[str, str], int] = {}
        for event in self.events:
            if event.pair_id is not None:
                key = (event.policy_id, event.pair_id)
                pairs[key] = pairs.get(key, 0) + 1
        if any(count != 2 for count in pairs.values()):
            raise ValueError("paired accounting schedules require exactly two event templates")
        return self

    def stable_hash(self) -> str:
        """Return a deterministic semantic SHA-256 for the validated schedule."""
        payload = json.dumps(
            self.model_dump(mode="json"),
            allow_nan=False,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )
        return hashlib.sha256(payload.encode()).hexdigest()


class AccruedAccountingEvent(ContractModel):
    """One event that occurs inside a requested simulation horizon."""

    event_id: str
    policy_id: str
    event_type: str
    simulation_month: NonNegativeInt
    cost_gbp_ha: NonNegativeFloat
    operational_emissions_kg_co2e_ha: NonNegativeFloat
    lifecycle_emissions_kg_co2e_ha: NonNegativeFloat
    provenance: str


class AccountingTotals(ContractModel):
    """Horizon-specific totals computed directly from scheduled events."""

    policy_id: str
    horizon_months: Annotated[int, Field(gt=0)]
    event_count: NonNegativeInt
    events: tuple[AccruedAccountingEvent, ...]
    cost_gbp_ha: NonNegativeFloat
    operational_emissions_kg_co2e_ha: NonNegativeFloat
    lifecycle_emissions_kg_co2e_ha: NonNegativeFloat
    total_emissions_kg_co2e_ha: NonNegativeFloat
    units: dict[str, str]
    uncertainty_status: Literal["provisional_not_regional_budget_or_complete_lca"] = (
        "provisional_not_regional_budget_or_complete_lca"
    )


def load_accounting_schedule(path: str | Path) -> AccountingSchedule:
    """Load a strict local YAML schedule; never perform network I/O."""
    raw: object = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    return AccountingSchedule.model_validate(raw)


def _occurrences(event: AccountingEvent, horizon_months: int) -> tuple[int, ...]:
    return tuple(range(event.first_month, horizon_months, event.repeat_every_months))


def accrue_accounting(
    schedule: AccountingSchedule, policy_id: str, horizon_months: int
) -> AccountingTotals:
    """Accrue only events that occur before ``horizon_months``.

    Paired events such as cover establishment/termination accrue only for
    complete pairs inside the horizon.  This mirrors the biological schedule
    contract, which forbids an unclosed cover-crop state.
    """
    if horizon_months < 1:
        raise ValueError("horizon_months must be positive")
    templates = tuple(event for event in schedule.events if event.policy_id == policy_id)
    if policy_id == "baseline":
        templates = ()
    accrued: list[AccruedAccountingEvent] = []
    pair_ids: set[str] = set()
    for event in templates:
        if event.pair_id is not None:
            pair_ids.add(event.pair_id)
    valid_pair_cycles: dict[str, set[int]] = {}
    for pair_id in pair_ids:
        first_events = sorted(
            (event for event in templates if event.pair_id == pair_id),
            key=lambda item: item.first_month,
        )
        if len(first_events) != 2:
            raise ValueError(f"pair {pair_id!r} must have exactly two templates")
        left, right = first_events
        offsets = (left.first_month, right.first_month)
        cycle_count = max(horizon_months // left.repeat_every_months + 2, 2)
        valid_pair_cycles[pair_id] = {
            cycle
            for cycle in range(cycle_count)
            if all(offset + cycle * left.repeat_every_months < horizon_months for offset in offsets)
        }
    for event in templates:
        for month in _occurrences(event, horizon_months):
            if event.pair_id is not None:
                cycle = (month - event.first_month) // event.repeat_every_months
                if cycle not in valid_pair_cycles[event.pair_id]:
                    continue
            accrued.append(
                AccruedAccountingEvent(
                    event_id=f"{event.event_id}-m{month:03d}",
                    policy_id=policy_id,
                    event_type=event.event_type,
                    simulation_month=month,
                    cost_gbp_ha=event.cost_gbp_ha,
                    operational_emissions_kg_co2e_ha=(event.operational_emissions_kg_co2e_ha),
                    lifecycle_emissions_kg_co2e_ha=event.lifecycle_emissions_kg_co2e_ha,
                    provenance=event.provenance,
                )
            )
    events = tuple(sorted(accrued, key=lambda item: (item.simulation_month, item.event_id)))
    cost = sum(event.cost_gbp_ha for event in events)
    operational = sum(event.operational_emissions_kg_co2e_ha for event in events)
    lifecycle = sum(event.lifecycle_emissions_kg_co2e_ha for event in events)
    return AccountingTotals(
        policy_id=policy_id,
        horizon_months=horizon_months,
        event_count=len(events),
        events=events,
        cost_gbp_ha=cost,
        operational_emissions_kg_co2e_ha=operational,
        lifecycle_emissions_kg_co2e_ha=lifecycle,
        total_emissions_kg_co2e_ha=operational + lifecycle,
        units=schedule.units,
    )
