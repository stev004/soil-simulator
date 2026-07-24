"""CLI tests for configuration and deterministic carbon-core commands."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from soil_simulator.cli import main

CONFIG_PATH = Path(__file__).parents[2] / "config" / "model_defaults.yaml"


def test_validate_config_command(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["validate-config", str(CONFIG_PATH)]) == 0
    captured = capsys.readouterr()
    output = json.loads(captured.out)
    assert output["status"] == "valid"
    assert len(output["configuration_hash"]) == 64


def test_show_model_info_states_phase_8_boundary(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["show-model-info", str(CONFIG_PATH)]) == 0
    captured = capsys.readouterr()
    output = json.loads(captured.out)
    assert (
        "Phase 9 offline synthetic intervention-selection and oracle-regret benchmark"
        in output["implementation_status"]
    )
    assert "latent-biological seeds" in output["implementation_status"]
    assert "not measured MAOC" in output["implementation_status"]
    assert "not field validation" in output["scientific_claim_boundary"]


def test_validate_config_returns_nonzero_for_missing_file(
    capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    assert main(["validate-config", str(tmp_path / "missing.yaml")]) == 2
    captured = capsys.readouterr()
    assert "could not read configuration" in captured.err


def test_run_carbon_core_prints_required_summary(capsys: pytest.CaptureFixture[str]) -> None:
    scenario_path = CONFIG_PATH.parent / "scenarios" / "carbon_core.yaml"
    assert main(["run-carbon-core", str(scenario_path), "--config", str(CONFIG_PATH)]) == 0
    captured = capsys.readouterr()
    output = json.loads(captured.out)
    assert set(output["final_pools_t_c_ha"]) == {
        "dpm_c",
        "rpm_c",
        "microbial_c",
        "protected_soc_c",
        "iom_c",
    }
    assert output["cumulative"]["co2_respiration_t_c_ha"] > 0.0
    assert output["cumulative"]["transfer_to_microbial_t_c_ha"] > 0.0
    assert output["cumulative"]["transfer_to_protected_t_c_ha"] > 0.0
    assert abs(output["cumulative"]["mass_balance_residual_t_c_ha"]) <= 1.0e-9
    assert all("environmental_modifiers" in month for month in output["monthly"])
    assert all("mass_balance_residual_t_c_ha" in month for month in output["monthly"])
    assert output["uncertainty"] == "not_quantified_in_phase_3"


def test_run_spring_barley_prints_phase_5_amf_diagnostics(
    capsys: pytest.CaptureFixture[str],
) -> None:
    scenario_path = CONFIG_PATH.parent / "scenarios" / "spring_barley_baseline.yaml"
    assert main(["run-spring-barley", str(scenario_path), "--config", str(CONFIG_PATH)]) == 0
    output = json.loads(capsys.readouterr().out)
    assert output["cumulative"]["potential_npp_t_c_ha"] == 6.0
    assert output["cumulative"]["realised_npp_t_c_ha"] > 0.0
    assert output["cumulative"]["phosphorus_uptake_kg_p_ha"] > 0.0
    assert output["cumulative"]["grain_yield_t_dm_ha"] > 0.0
    assert output["cumulative"]["residue_to_dpm_t_c_ha"] > 0.0
    assert output["cumulative"]["residue_to_rpm_t_c_ha"] > 0.0
    assert output["cumulative"]["plant_carbon_allocated_to_amf_t_c_ha"] > 0.0
    assert output["cumulative"]["fungal_respiration_t_c_ha"] > 0.0
    assert output["cumulative"]["fungal_turnover_t_c_ha"] > 0.0
    assert output["cumulative"]["amf_phosphorus_acquired_kg_p_ha"] > 0.0
    assert set(output["cumulative"]["fungal_necromass_routing_t_c_ha"]) == {
        "dpm_c",
        "rpm_c",
        "protected_soc_c",
    }
    assert "net_plant_carbon_effect_t_c_ha" in output["cumulative"]
    assert "net_yield_effect_t_dm_ha" in output["cumulative"]
    assert output["final"]["live_fungal_biomass_t_c_ha"] >= 0.0
    assert abs(output["cumulative"]["carbon_mass_balance_residual_t_c_ha"]) <= 1.0e-9
    assert abs(output["cumulative"]["phosphorus_mass_balance_residual_kg_p_ha"]) <= 1.0e-9
    assert len(output["configuration_hash"]) == 64
    assert all("stress_modifiers" in month for month in output["monthly"])
    assert all("soil_carbon_pools_t_c_ha" in month for month in output["monthly"])
    assert all("plant_outcome" in month for month in output["monthly"])


def test_compare_management_prints_required_phase_6_outputs(
    capsys: pytest.CaptureFixture[str],
) -> None:
    scenario_path = CONFIG_PATH.parent / "scenarios" / "management_scenarios.yaml"
    assert main(["compare-management", str(scenario_path), "--config", str(CONFIG_PATH)]) == 0
    output = json.loads(capsys.readouterr().out)
    assert len(output["policies"]) >= 5
    assert "not field validation" in output["scientific_claim_boundary"]
    for policy in output["policies"]:
        assert "intervention_schedule" in policy
        assert "yield_t_dm_ha" in policy
        assert "amf" in policy
        assert "carbon_pools_t_c_ha" in policy
        assert "available_phosphorus_kg_p_ha" in policy
        assert "respiration_t_c_ha" in policy
        assert "cost_gbp_ha" in policy
        assert "emissions_proxy_kg_co2e_ha" in policy
        assert abs(policy["carbon_residual_t_c_ha"]) <= 1.0e-9
        assert abs(policy["phosphorus_residual_kg_p_ha"]) <= 1.0e-9
