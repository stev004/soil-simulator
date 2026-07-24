"""Integrated Phase 6 intervention, accounting, ordering, and replay tests."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from soil_simulator.domain.management import (
    ManagementPolicy,
    ManagementScenarioSet,
    ManagementSimulationResult,
)
from soil_simulator.io.configuration import load_management_scenarios, load_model_parameters
from soil_simulator.simulator.management import (
    compare_management_scenarios,
    run_management_policy,
)

ROOT = Path(__file__).parents[2]
PARAMETERS = load_model_parameters(ROOT / "config" / "model_defaults.yaml")
SCENARIOS = load_management_scenarios(ROOT / "config" / "scenarios" / "management_scenarios.yaml")


def _results() -> dict[str, ManagementSimulationResult]:
    comparison = compare_management_scenarios(SCENARIOS, PARAMETERS)
    return {result.policy_id: result for result in comparison.results}


def test_each_predefined_intervention_runs_independently_and_balances() -> None:
    results = _results()
    assert set(results) == {
        "baseline",
        "conventional_tillage",
        "reduced_tillage",
        "no_till",
        "cover_crop",
        "phosphorus",
        "farmyard_manure",
    }
    for result in results.values():
        assert all(step.carbon_balance.within_tolerance for step in result.steps)
        assert all(step.phosphorus_balance.within_tolerance for step in result.steps)
        assert result.final_state.month_index == 24
        assert result.configuration_hash
        assert result.schedule_hash


def test_tillage_changes_amf_and_carbon_turnover_by_configured_intensity() -> None:
    results = _results()
    conventional = results["conventional_tillage"].steps[2]
    reduced = results["reduced_tillage"].steps[2]
    no_till = results["no_till"].steps[2]
    assert conventional.tillage_amf_mortality_t_c_ha > reduced.tillage_amf_mortality_t_c_ha
    assert reduced.tillage_amf_mortality_t_c_ha > no_till.tillage_amf_mortality_t_c_ha
    assert conventional.amf_step.carbon_core.respiration_t_c_ha > (
        no_till.amf_step.carbon_core.respiration_t_c_ha
    )
    assert conventional.amf_step.final_state.amf_live_c < no_till.amf_step.final_state.amf_live_c


def test_cover_crop_biomass_phosphorus_and_termination_residue_routing() -> None:
    cover = _results()["cover_crop"]
    establishment = cover.steps[8]
    termination = cover.steps[13]
    assert establishment.final_management_state.cover_crop_active
    assert establishment.cover_crop_gross_carbon_t_c_ha > 0.0
    assert establishment.cover_crop_phosphorus_uptake_kg_p_ha > 0.0
    assert establishment.final_management_state.cover_root_c_t_ha > 0.0
    assert termination.cover_crop_residue_return_t_c_ha > 0.0
    assert termination.cover_crop_phosphorus_return_kg_p_ha > 0.0
    assert not termination.final_management_state.cover_crop_active
    assert termination.final_state.dpm_c > termination.amf_step.final_state.dpm_c
    assert termination.final_state.rpm_c > termination.amf_step.final_state.rpm_c


def test_phosphorus_application_adds_once_then_is_depleted_by_uptake() -> None:
    phosphorus = _results()["phosphorus"]
    application = phosphorus.steps[2]
    assert application.phosphorus_application_kg_p_ha == 20.0
    input_records = [
        record
        for record in application.phosphorus_fluxes
        if record.process == "external_available_phosphorus_input"
    ]
    assert len(input_records) == 1
    assert input_records[0].amount_kg_p_ha == 20.0
    assert application.final_state.available_p_kg_ha < (
        application.initial_state.available_p_kg_ha + 20.0
    )
    assert application.amf_step.total_plant_phosphorus_received_kg_p_ha > 0.0


def test_manure_routes_carbon_and_phosphorus_post_decomposition() -> None:
    manure = _results()["farmyard_manure"]
    application = manure.steps[9]
    assert application.manure_carbon_input_t_c_ha == 1.0
    assert application.manure_phosphorus_input_kg_p_ha == 5.0
    assert application.final_state.dpm_c == pytest.approx(
        application.amf_step.final_state.dpm_c + 0.49
    )
    assert application.final_state.rpm_c == pytest.approx(
        application.amf_step.final_state.rpm_c + 0.49
    )
    assert application.final_state.protected_soc_c == pytest.approx(
        application.amf_step.final_state.protected_soc_c + 0.02
    )
    assert application.final_state.available_p_kg_ha == pytest.approx(
        application.amf_step.final_state.available_p_kg_ha + 5.0
    )


def test_event_cost_and_emissions_totals_are_additive_and_non_mechanistic() -> None:
    results = _results()
    conventional = results["conventional_tillage"]
    assert conventional.cumulative_cost_gbp_ha == 140.0
    assert conventional.cumulative_emissions_proxy_kg_co2e_ha == 50.0
    assert results["baseline"].cumulative_cost_gbp_ha == 0.0
    assert results["baseline"].cumulative_emissions_proxy_kg_co2e_ha == 0.0


def test_execution_order_is_recorded_when_events_share_a_month() -> None:
    p = SCENARIOS.policies[5].events[0].model_copy(update={"simulation_month": 2})
    tillage = SCENARIOS.policies[2].events[0].model_copy(update={"simulation_month": 2})
    manure = SCENARIOS.policies[6].events[0].model_copy(update={"simulation_month": 2})
    policy = ManagementPolicy(
        policy_id="same-month",
        name="same-month",
        events=(manure, tillage, p),
        classification="scenario_assumption",
        provenance="integration test",
    )
    scenario = SCENARIOS.model_copy(update={"policies": (policy,)})
    result = run_management_policy(scenario, policy, PARAMETERS)
    assert [applied.event.event_type for applied in result.steps[2].applied_events] == [
        "phosphorus_application",
        "tillage",
        "farmyard_manure",
    ]


def test_deterministic_twenty_year_management_replay_is_identical() -> None:
    policy = SCENARIOS.policies[4]
    scenario = SCENARIOS.model_copy(
        update={"monthly_steps": SCENARIOS.monthly_steps * 10, "policies": (policy,)}
    )
    # Revalidate the copied horizon and schedule rather than relying on unchecked model_copy.
    scenario = ManagementScenarioSet.model_validate(scenario.model_dump(mode="python"))
    first = run_management_policy(scenario, policy, PARAMETERS)
    second = run_management_policy(scenario, policy, PARAMETERS)
    assert first == second
    assert first.model_dump_json() == second.model_dump_json()
    assert first.final_state.month_index == 240
    assert abs(first.cumulative_carbon_residual_t_c_ha) <= 1.0e-9
    assert abs(first.cumulative_phosphorus_residual_kg_p_ha) <= 1.0e-9


def test_management_flux_records_and_results_are_immutable() -> None:
    result = _results()["farmyard_manure"]
    record = next(record for record in result.steps[9].carbon_fluxes if "manure" in record.process)
    with pytest.raises(ValidationError):
        record.__setattr__("amount_t_c_ha", 0.0)
    with pytest.raises(ValidationError):
        result.__setattr__("cumulative_cost_gbp_ha", 0.0)
