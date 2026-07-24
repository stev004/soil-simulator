"""Property-based Phase 6 stock-safety and intervention-balance tests."""

from __future__ import annotations

from pathlib import Path

from hypothesis import given, settings
from hypothesis import strategies as st

from soil_simulator.domain.management import ManagementPolicy, ManagementScenarioSet
from soil_simulator.io.configuration import load_management_scenarios, load_model_parameters
from soil_simulator.simulator.management import run_management_policy

ROOT = Path(__file__).parents[2]
PARAMETERS = load_model_parameters(ROOT / "config" / "model_defaults.yaml")
SCENARIOS = load_management_scenarios(ROOT / "config" / "scenarios" / "management_scenarios.yaml")


@given(
    phosphorus_amount=st.floats(
        min_value=0.0, max_value=60.0, allow_nan=False, allow_infinity=False
    ),
    manure_carbon=st.floats(min_value=0.0, max_value=3.0, allow_nan=False, allow_infinity=False),
)
@settings(max_examples=20, deadline=None)
def test_valid_management_inputs_preserve_non_negative_finite_balanced_states(
    phosphorus_amount: float, manure_carbon: float
) -> None:
    phosphorus = SCENARIOS.policies[5].events[0].model_copy(update={"amount": phosphorus_amount})
    manure = SCENARIOS.policies[6].events[0].model_copy(update={"amount": manure_carbon})
    policy = ManagementPolicy(
        policy_id="property-inputs",
        name="property-inputs",
        events=(phosphorus, manure),
        classification="scenario_assumption",
        provenance="property test",
    )
    scenario = ManagementScenarioSet.model_validate(
        SCENARIOS.model_copy(update={"policies": (policy,)}).model_dump(mode="python")
    )
    result = run_management_policy(scenario, policy, PARAMETERS)
    for step in result.steps:
        state = step.final_state
        assert (
            min(
                state.plant_c,
                state.root_c,
                state.amf_live_c,
                state.amf_necromass_c,
                state.dpm_c,
                state.rpm_c,
                state.microbial_c,
                state.protected_soc_c,
                state.iom_c,
                state.available_p_kg_ha,
            )
            >= 0.0
        )
        assert step.carbon_balance.within_tolerance
        assert step.phosphorus_balance.within_tolerance
