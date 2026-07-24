"""Phase 6 scenario-direction regressions; these are not empirical validation."""

from __future__ import annotations

from pathlib import Path

from soil_simulator.domain.management import ManagementSimulationResult
from soil_simulator.io.configuration import load_management_scenarios, load_model_parameters
from soil_simulator.simulator.management import compare_management_scenarios

ROOT = Path(__file__).parents[2]
PARAMETERS = load_model_parameters(ROOT / "config" / "model_defaults.yaml")
SCENARIOS = load_management_scenarios(ROOT / "config" / "scenarios" / "management_scenarios.yaml")


def _results() -> dict[str, ManagementSimulationResult]:
    return {
        result.policy_id: result
        for result in compare_management_scenarios(SCENARIOS, PARAMETERS).results
    }


def _soil_carbon(result: ManagementSimulationResult) -> float:
    state = result.final_state
    return state.dpm_c + state.rpm_c + state.microbial_c + state.protected_soc_c + state.iom_c


def test_intensive_tillage_can_reduce_amf_biomass() -> None:
    results = _results()
    assert results["conventional_tillage"].steps[2].final_state.amf_live_c < (
        results["no_till"].steps[2].final_state.amf_live_c
    )


def test_cover_crop_can_increase_plant_derived_carbon_inputs_without_guaranteed_yield_gain() -> (
    None
):
    results = _results()
    cover = results["cover_crop"]
    baseline = results["baseline"]
    assert cover.cumulative_cover_crop_carbon_input_t_c_ha > 0.0
    assert cover.cumulative_grain_yield_t_dm_ha <= baseline.cumulative_grain_yield_t_dm_ha


def test_phosphorus_can_relieve_limitation_while_lowering_amf_allocation() -> None:
    results = _results()
    phosphorus = results["phosphorus"].steps[2].amf_step
    baseline = results["baseline"].steps[2].amf_step
    assert phosphorus.stress.phosphorus > baseline.stress.phosphorus
    assert phosphorus.effective_amf_allocation_fraction < baseline.effective_amf_allocation_fraction


def test_manure_can_raise_soil_carbon_with_cost_and_emissions() -> None:
    results = _results()
    manure = results["farmyard_manure"]
    assert _soil_carbon(manure) > _soil_carbon(results["baseline"])
    assert manure.cumulative_cost_gbp_ha > 0.0
    assert manure.cumulative_emissions_proxy_kg_co2e_ha > 0.0


def test_no_intervention_is_universally_optimal_across_reported_outcomes() -> None:
    results = _results()
    highest_yield = max(results.values(), key=lambda result: result.cumulative_grain_yield_t_dm_ha)
    highest_soil_carbon = max(results.values(), key=_soil_carbon)
    lowest_cost = min(results.values(), key=lambda result: result.cumulative_cost_gbp_ha)
    assert highest_yield.policy_id == "phosphorus"
    assert highest_soil_carbon.policy_id == "farmyard_manure"
    assert lowest_cost.policy_id == "baseline"
