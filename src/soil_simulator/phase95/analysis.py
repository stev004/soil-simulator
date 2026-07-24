"""Phosphorus-loop ablations and simulator response extraction for Phase 9.5."""

from __future__ import annotations

import math
from collections.abc import Mapping

from soil_simulator.domain.management import (
    ManagementPolicy,
    ManagementScenarioSet,
    ManagementSimulationResult,
)
from soil_simulator.domain.models import ModelParameters
from soil_simulator.domain.population import (
    PopulationGenerationConfig,
    SyntheticField,
    SyntheticPopulation,
)
from soil_simulator.phase95.accounting import AccountingSchedule, accrue_accounting
from soil_simulator.phase95.policies import scenario_with_phase95_policies
from soil_simulator.population.batch import _scenario_for_field, parameters_for_field
from soil_simulator.simulator.management import run_management_policy


def _scenario(
    field: SyntheticField,
    template: ManagementScenarioSet,
    population_config: PopulationGenerationConfig,
    horizon: int,
    *,
    interval_months: int = 12,
    phosphorus_amount: float | None = None,
) -> ManagementScenarioSet:
    legacy = _scenario_for_field(field, template, population_config, horizon)
    return scenario_with_phase95_policies(
        legacy,
        horizon,
        interval_months=interval_months,
        phosphorus_amount_kg_p_ha=phosphorus_amount,
    )


def _policy(scenario: ManagementScenarioSet, policy_id: str) -> ManagementPolicy:
    return next(policy for policy in scenario.policies if policy.policy_id == policy_id)


def _trajectory_summary(
    result: ManagementSimulationResult, horizon_months: int | None = None
) -> dict[str, float]:
    steps = result.steps if horizon_months is None else result.steps[:horizon_months]
    if not steps:
        raise ValueError("trajectory summary requires at least one month")
    final_state = steps[-1].final_state
    return {
        "npp_t_c_ha": math.fsum(step.amf_step.gross_realised_plant_carbon_t_c_ha for step in steps),
        "residue_carbon_t_c_ha": math.fsum(
            step.amf_step.residue_to_dpm_t_c_ha
            + step.amf_step.residue_to_rpm_t_c_ha
            + step.cover_crop_residue_return_t_c_ha
            for step in steps
        ),
        "respiration_t_c_ha": math.fsum(step.carbon_balance.respiration_t_c_ha for step in steps),
        "total_soc_t_c_ha": math.fsum(
            (
                final_state.dpm_c,
                final_state.rpm_c,
                final_state.microbial_c,
                final_state.protected_soc_c,
                final_state.iom_c,
            )
        ),
        "protected_soc_proxy_t_c_ha": final_state.protected_soc_c,
        "yield_t_dm_ha": final_state.cumulative_yield_t_dm_ha,
        "max_carbon_residual_t_c_ha": max(
            abs(step.carbon_balance.residual_t_c_ha) for step in steps
        ),
        "max_phosphorus_residual_kg_p_ha": max(
            abs(step.phosphorus_balance.residual_kg_p_ha) for step in steps
        ),
    }


def _difference(outcome: Mapping[str, float], baseline: Mapping[str, float]) -> dict[str, float]:
    return {
        key: value - baseline[key] for key, value in outcome.items() if not key.startswith("max_")
    }


def _alternative_p_parameters(parameters: ModelParameters) -> ModelParameters:
    values = parameters.model_dump(mode="python", by_alias=True)
    values["plant"]["direct_p_uptake_half_saturation"]["default"] = 40.0
    values["amf"]["p_uptake_km"]["default"] = 40.0
    values["amf"]["allocation_p_half_saturation"]["default"] = 40.0
    return ModelParameters.model_validate(values)


def _mean_rows(rows: list[dict[str, float]]) -> dict[str, float]:
    return {key: math.fsum(row[key] for row in rows) / len(rows) for key in rows[0]}


def phosphorus_ablation(
    population: SyntheticPopulation,
    template: ManagementScenarioSet,
    parameters: ModelParameters,
    population_config: PopulationGenerationConfig,
    accounting: AccountingSchedule,
) -> dict[str, object]:
    """Quantify the full P-stress -> NPP -> residue -> SOC structural pathway."""
    variants: dict[str, dict[str, object]] = {}
    for horizon in (24, 60, 120):
        current_rows: list[dict[str, float]] = []
        capped_rows: list[dict[str, float]] = []
        alternative_rows: list[dict[str, float]] = []
        baseline_rows: list[dict[str, float]] = []
        for field in population.fields:
            field_parameters = parameters_for_field(field, parameters)
            scenario = _scenario(field, template, population_config, horizon)
            baseline = _trajectory_summary(
                run_management_policy(scenario, _policy(scenario, "baseline"), field_parameters)
            )
            current = _trajectory_summary(
                run_management_policy(scenario, _policy(scenario, "phosphorus"), field_parameters)
            )
            capped_scenario = _scenario(
                field,
                template,
                population_config,
                horizon,
                phosphorus_amount=5.0,
            )
            capped = _trajectory_summary(
                run_management_policy(
                    capped_scenario,
                    _policy(capped_scenario, "phosphorus"),
                    field_parameters,
                )
            )
            alternative_parameters = parameters_for_field(
                field, _alternative_p_parameters(parameters)
            )
            alternative_baseline = _trajectory_summary(
                run_management_policy(
                    scenario,
                    _policy(scenario, "baseline"),
                    alternative_parameters,
                )
            )
            alternative = _trajectory_summary(
                run_management_policy(
                    scenario, _policy(scenario, "phosphorus"), alternative_parameters
                )
            )
            baseline_rows.append(baseline)
            current_rows.append(_difference(current, baseline))
            capped_rows.append(_difference(capped, baseline))
            alternative_rows.append(_difference(alternative, alternative_baseline))
        accounting_totals = accrue_accounting(accounting, "phosphorus", horizon)
        variants[str(horizon)] = {
            "no_phosphorus_intervention": _mean_rows(baseline_rows),
            "phosphorus_current_plant_growth_response_effect": _mean_rows(current_rows),
            "phosphorus_capped_response_effect": _mean_rows(capped_rows),
            "phosphorus_alternative_plausible_parameters_effect": _mean_rows(alternative_rows),
            "horizon_aware_accounting": accounting_totals.model_dump(mode="json"),
            "capped_response_definition": (
                "5 kg P ha-1 per scheduled event versus the current 20 kg P ha-1; this bounds "
                "the response without changing or recalibrating the plant-growth equation"
            ),
            "alternative_parameters": {
                "direct_p_uptake_half_saturation_kg_p_ha": 40.0,
                "amf_p_uptake_km_kg_p_ha": 40.0,
                "allocation_p_half_saturation_kg_p_ha": 40.0,
            },
        }
    ranking_rows: dict[str, list[float]] = {}
    for field in population.fields:
        scenario = _scenario(field, template, population_config, 120)
        field_parameters = parameters_for_field(field, parameters)
        baseline = _trajectory_summary(
            run_management_policy(scenario, _policy(scenario, "baseline"), field_parameters)
        )
        for policy in scenario.policies:
            outcome = _trajectory_summary(run_management_policy(scenario, policy, field_parameters))
            effect = _difference(outcome, baseline)
            ranking_rows.setdefault(policy.policy_id, []).append(
                effect["total_soc_t_c_ha"] + effect["protected_soc_proxy_t_c_ha"]
            )
    ranking_pairs = sorted(
        (
            (policy_id, math.fsum(values) / len(values))
            for policy_id, values in ranking_rows.items()
        ),
        key=lambda row: row[1],
        reverse=True,
    )
    ranking = tuple(
        {"policy_id": policy_id, "mean_carbon_priority_proxy": score}
        for policy_id, score in ranking_pairs
    )
    without_phosphorus = tuple(row for row in ranking if row["policy_id"] != "phosphorus")
    return {
        "version": "0.9.5",
        "population_hash": population.manifest.population_hash,
        "field_count": len(population.fields),
        "variants_by_horizon": variants,
        "policy_ranking_with_phosphorus": ranking,
        "policy_ranking_excluding_phosphorus": without_phosphorus,
        "phosphorus_excluded_from_headline_carbon_conclusion": True,
        "magnitude_status": "unresolved_no_defensible_calibration_dataset",
        "claim_boundary": (
            "Ablations quantify current simulator structure only. They are not causal or field "
            "estimates and no response was tuned to obtain a preferred ranking."
        ),
    }


def apply_sensitivity_values(
    parameters: ModelParameters, values: Mapping[str, float]
) -> ModelParameters:
    """Apply registered sensitivity values to a copied validated configuration."""
    raw = parameters.model_dump(mode="python", by_alias=True)
    mapping = {
        "amf_allocation": ("amf", "photosynthate_allocation_fraction"),
        "amf_cue": ("amf", "carbon_use_efficiency"),
        "amf_turnover": ("amf", "turnover_per_month"),
        "necromass_stabilisation": ("amf", "necromass_stabilisation_fraction"),
        "phosphorus_uptake_vmax": ("amf", "p_uptake_vmax"),
        "phosphorus_half_saturation": ("amf", "p_uptake_km"),
        "tillage_amf_mortality": (
            "management",
            "tillage",
            "conventional",
            "amf_pulse_mortality",
        ),
        "tillage_decomposition_multiplier": (
            "management",
            "tillage",
            "conventional",
            "decomposition_multiplier",
        ),
        "cover_crop_npp": ("management", "cover_crop", "monthly_potential_npp_t_c_ha"),
        "cover_crop_root_fraction": (
            "management",
            "cover_crop",
            "root_allocation_fraction",
        ),
        "fym_phosphorus_content": (
            "management",
            "farmyard_manure",
            "phosphorus_content_kg_p_per_t_c",
        ),
    }
    for name, path in mapping.items():
        if name not in values:
            continue
        target = raw
        for component in path[:-1]:
            target = target[component]
        target[path[-1]]["default"] = values[name]
    if "amf_turnover" in values:
        maximum_tillage_multiplier = max(
            parameters.management.tillage.conventional.amf_turnover_multiplier.default,
            parameters.management.tillage.reduced.amf_turnover_multiplier.default,
            parameters.management.tillage.no_till.amf_turnover_multiplier.default,
        )
        raw["amf"]["turnover_per_month"]["max"] = max(
            raw["amf"]["turnover_per_month"]["max"],
            values["amf_turnover"] * maximum_tillage_multiplier,
        )
    if "necromass_stabilisation" in values:
        stabilisation = values["necromass_stabilisation"]
        remainder = 1.0 - stabilisation
        ratio = parameters.rothc.crop_dpm_rpm_ratio
        raw["amf"]["necromass_to_dpm_fraction"]["default"] = remainder * ratio / (1.0 + ratio)
        raw["amf"]["necromass_to_rpm_fraction"]["default"] = remainder / (1.0 + ratio)
    return ModelParameters.model_validate(raw)


def sensitivity_evaluator(
    field: SyntheticField,
    template: ManagementScenarioSet,
    parameters: ModelParameters,
    population_config: PopulationGenerationConfig,
    values: Mapping[str, float],
) -> dict[str, float]:
    """Return paired effects by policy, target and horizon for one parameter draw."""
    interval = max(1, round(values.get("schedule_interval_months", 12.0)))
    sampled = apply_sensitivity_values(parameters_for_field(field, parameters), values)
    scenario = _scenario(
        field,
        template,
        population_config,
        120,
        interval_months=interval,
    )
    trajectories = {
        policy.policy_id: run_management_policy(scenario, policy, sampled)
        for policy in scenario.policies
    }
    outputs: dict[str, float] = {}
    for horizon in (24, 60, 120):
        baseline = _trajectory_summary(trajectories["baseline"], horizon)
        for policy_id, trajectory in trajectories.items():
            if policy_id == "baseline":
                continue
            effects = _difference(_trajectory_summary(trajectory, horizon), baseline)
            targets = (
                ("yield_t_dm_ha",)
                if horizon == 24
                else (
                    "npp_t_c_ha",
                    "residue_carbon_t_c_ha",
                    "respiration_t_c_ha",
                    "total_soc_t_c_ha",
                    "protected_soc_proxy_t_c_ha",
                )
            )
            for target in targets:
                outputs[f"{policy_id}|{target}|{horizon}"] = effects[target]
    return outputs
