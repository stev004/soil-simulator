"""Phase 6 management-event schema and schedule validation tests."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from soil_simulator.domain.management import ManagementScenarioSet, ordered_events
from soil_simulator.domain.models import ManagementEvent
from soil_simulator.io.configuration import load_management_scenarios

ROOT = Path(__file__).parents[2]
SCENARIOS = load_management_scenarios(ROOT / "config" / "scenarios" / "management_scenarios.yaml")


def _phosphorus_event(**updates: object) -> ManagementEvent:
    values: dict[str, object] = {
        "event_id": "p-test",
        "event_type": "phosphorus_application",
        "simulation_month": 2,
        "amount": 10.0,
        "units": "kg_P_ha^-1",
        "cost_gbp_ha": 1.0,
        "emissions_proxy_kg_co2e_ha": 2.0,
        "parameter_provenance": "unit-test provisional input",
        "source_classification": "scenario_assumption",
        "provenance": "unit test",
    }
    values.update(updates)
    return ManagementEvent.model_validate(values)


def test_event_schema_rejects_invalid_timing_units_and_double_timing() -> None:
    with pytest.raises(ValidationError, match="require units"):
        _phosphorus_event(units="t_C_ha^-1")
    with pytest.raises(ValidationError, match="exactly one"):
        _phosphorus_event(simulation_month=None)
    with pytest.raises(ValidationError, match="exactly one"):
        _phosphorus_event(event_date="2026-03-01")


def test_scenario_rejects_out_of_horizon_duplicate_and_conflicting_events() -> None:
    base = SCENARIOS.model_dump(mode="python")
    duplicate = _phosphorus_event()
    base["policies"] = [
        {
            "policy_id": "duplicates",
            "name": "duplicates",
            "events": [duplicate, duplicate.model_copy(update={"event_id": "p-copy"})],
            "classification": "scenario_assumption",
            "provenance": "unit test",
        }
    ]
    with pytest.raises(ValidationError, match="duplicate events"):
        ManagementScenarioSet.model_validate(base)

    out_of_range = _phosphorus_event(simulation_month=len(SCENARIOS.monthly_steps))
    base["policies"][0]["events"] = [out_of_range]
    with pytest.raises(ValidationError, match="outside the horizon"):
        ManagementScenarioSet.model_validate(base)

    tillage = (
        SCENARIOS.policies[1]
        .events[0]
        .model_copy(update={"event_date": None, "simulation_month": 2})
    )
    base["policies"][0]["events"] = [
        tillage,
        SCENARIOS.policies[2].events[0].model_copy(update={"event_id": "second-tillage"}),
    ]
    with pytest.raises(ValidationError, match="one tillage"):
        ManagementScenarioSet.model_validate(base)


def test_same_month_event_order_is_type_then_event_id() -> None:
    phosphorus = _phosphorus_event(simulation_month=2)
    tillage = (
        SCENARIOS.policies[1]
        .events[0]
        .model_copy(update={"event_date": None, "simulation_month": 2})
    )
    manure = SCENARIOS.policies[-1].events[0].model_copy(update={"simulation_month": 2})
    cover = SCENARIOS.policies[4].events[0].model_copy(update={"simulation_month": 2})
    ordered = ordered_events((cover, manure, tillage, phosphorus), SCENARIOS.start_date)
    assert [event.event_type for event in ordered] == [
        "phosphorus_application",
        "tillage",
        "farmyard_manure",
        "cover_crop_establishment",
    ]
