"""Command-line access to configuration and deterministic simulator baselines."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import cast

from soil_simulator.io.configuration import (
    ConfigLoadError,
    load_carbon_core_scenario,
    load_management_scenarios,
    load_model_parameters,
    load_plant_scenario,
)
from soil_simulator.io.ml_configuration import load_ml_benchmark_config
from soil_simulator.io.phase9_configuration import load_phase9_benchmark_config
from soil_simulator.io.phase86_configuration import load_phase86_benchmark_config
from soil_simulator.io.population_configuration import load_population_config
from soil_simulator.ml.dataset import build_ml_dataset, load_saved_batch, load_saved_population
from soil_simulator.ml.phase86 import run_phase86_benchmark
from soil_simulator.ml.pipeline import run_benchmark
from soil_simulator.population.adapters import DatasetAdapterError, VersionedLocalYamlAdapter
from soil_simulator.population.batch import run_population_batch
from soil_simulator.population.foundation import expand_synthetic_foundation
from soil_simulator.population.generator import generate_population
from soil_simulator.population.reporting import (
    batch_summary,
    batch_summary_table,
    population_summary,
    population_summary_table,
)
from soil_simulator.selection.artifacts import FrozenArtifactError, load_frozen_phase86_bundle
from soil_simulator.selection.benchmark import run_phase9_benchmark
from soil_simulator.simulator.amf_extension import run_amf_extension
from soil_simulator.simulator.carbon_core import run_carbon_core
from soil_simulator.simulator.errors import CarbonCoreError
from soil_simulator.simulator.management import compare_management_scenarios

DEFAULT_CONFIG_PATH = Path("config/model_defaults.yaml")
DEFAULT_CARBON_CORE_SCENARIO_PATH = Path("config/scenarios/carbon_core.yaml")
DEFAULT_PLANT_SCENARIO_PATH = Path("config/scenarios/spring_barley_baseline.yaml")
DEFAULT_MANAGEMENT_SCENARIO_PATH = Path("config/scenarios/management_scenarios.yaml")
DEFAULT_POPULATION_CONFIG_PATH = Path("config/populations/phase7_population.yaml")
DEFAULT_POPULATION_DATASET_PATH = Path("data/processed/phase7_empirical_seed_fixture_v1.yaml")
DEFAULT_ML_CONFIG_PATH = Path("config/ml/phase8_benchmark.yaml")
DEFAULT_PHASE85_POPULATION_CONFIG_PATH = Path("config/populations/phase85_population.yaml")
DEFAULT_ML_OUTPUT_DIR = Path("outputs/phase85_v0.8.5")
DEFAULT_PHASE86_ML_CONFIG_PATH = Path("config/ml/phase86_benchmark.yaml")
DEFAULT_PHASE86_POPULATION_CONFIG_PATH = Path("config/populations/phase86_population.yaml")
DEFAULT_PHASE86_OUTPUT_DIR = Path("outputs/phase86_v0.8.6")
DEFAULT_PHASE9_CONFIG_PATH = Path("config/selection/phase9_benchmark.yaml")
DEFAULT_PHASE9_OUTPUT_DIR = Path("outputs/phase9_v0.9.0")


def build_parser() -> argparse.ArgumentParser:
    """Build the Soil Simulator CLI parser."""
    parser = argparse.ArgumentParser(
        prog="soil-simulator",
        description="Validate contracts and run the deterministic Soil Simulator carbon core.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command, help_text in (
        ("validate-config", "validate model configuration and print its stable hash"),
        ("show-model-info", "show model metadata and the current implementation boundary"),
    ):
        subparser = subparsers.add_parser(command, help=help_text)
        subparser.add_argument(
            "config",
            nargs="?",
            type=Path,
            default=DEFAULT_CONFIG_PATH,
            help=f"configuration YAML (default: {DEFAULT_CONFIG_PATH})",
        )
    run_parser = subparsers.add_parser(
        "run-carbon-core",
        help="run the predefined deterministic Phase 3 RothC-style scenario",
    )
    run_parser.add_argument(
        "scenario",
        nargs="?",
        type=Path,
        default=DEFAULT_CARBON_CORE_SCENARIO_PATH,
        help=f"scenario YAML (default: {DEFAULT_CARBON_CORE_SCENARIO_PATH})",
    )
    run_parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_CONFIG_PATH,
        help=f"configuration YAML (default: {DEFAULT_CONFIG_PATH})",
    )
    plant_parser = subparsers.add_parser(
        "run-spring-barley",
        help="run the deterministic Phase 5 spring-barley/AMF/P scenario",
    )
    plant_parser.add_argument(
        "scenario",
        nargs="?",
        type=Path,
        default=DEFAULT_PLANT_SCENARIO_PATH,
        help=f"scenario YAML (default: {DEFAULT_PLANT_SCENARIO_PATH})",
    )
    plant_parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_CONFIG_PATH,
        help=f"configuration YAML (default: {DEFAULT_CONFIG_PATH})",
    )
    management_parser = subparsers.add_parser(
        "compare-management",
        help="run and compare the predefined deterministic Phase 6 management scenarios",
    )
    management_parser.add_argument(
        "scenario",
        nargs="?",
        type=Path,
        default=DEFAULT_MANAGEMENT_SCENARIO_PATH,
        help=f"scenario YAML (default: {DEFAULT_MANAGEMENT_SCENARIO_PATH})",
    )
    management_parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_CONFIG_PATH,
        help=f"configuration YAML (default: {DEFAULT_CONFIG_PATH})",
    )
    for command, help_text, run_batch in (
        (
            "generate-population",
            "generate and summarise a reproducible Phase 7 synthetic population",
            False,
        ),
        (
            "run-population-batch",
            "run eligible Phase 6 policies across a Phase 7 population",
            True,
        ),
    ):
        population_parser = subparsers.add_parser(command, help=help_text)
        population_parser.add_argument(
            "population_config",
            nargs="?",
            type=Path,
            default=DEFAULT_POPULATION_CONFIG_PATH,
            help=f"population configuration YAML (default: {DEFAULT_POPULATION_CONFIG_PATH})",
        )
        population_parser.add_argument(
            "--dataset",
            type=Path,
            default=DEFAULT_POPULATION_DATASET_PATH,
            help=f"versioned local seed dataset (default: {DEFAULT_POPULATION_DATASET_PATH})",
        )
        population_parser.add_argument(
            "--config",
            type=Path,
            default=DEFAULT_CONFIG_PATH,
            help=f"model configuration YAML (default: {DEFAULT_CONFIG_PATH})",
        )
        population_parser.add_argument(
            "--count",
            type=int,
            default=None,
            help="accepted field count (default: population configuration value)",
        )
        population_parser.add_argument(
            "--seed",
            type=int,
            default=None,
            help="generation seed override",
        )
        population_parser.add_argument(
            "--json-output",
            type=Path,
            default=None,
            help="optional path for complete JSON output; stdout remains a human-readable table",
        )
        if run_batch:
            population_parser.add_argument(
                "--scenario",
                type=Path,
                default=DEFAULT_MANAGEMENT_SCENARIO_PATH,
                help=f"Phase 6 policy scenario YAML (default: {DEFAULT_MANAGEMENT_SCENARIO_PATH})",
            )
    ml_parser = subparsers.add_parser(
        "benchmark-intervention-ml",
        help="run Phase 8.5 diagnostics from saved field and multi-horizon batch artifacts",
    )
    ml_parser.add_argument(
        "population_json", type=Path, help="saved JSON containing Phase 7 fields"
    )
    ml_parser.add_argument(
        "batch_json", type=Path, help="saved JSON containing Phase 6 batch outcomes"
    )
    ml_parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_CONFIG_PATH,
        help=f"model configuration for provenance validation (default: {DEFAULT_CONFIG_PATH})",
    )
    ml_parser.add_argument(
        "--ml-config",
        type=Path,
        default=DEFAULT_ML_CONFIG_PATH,
        help=f"Phase 8.5 benchmark configuration (default: {DEFAULT_ML_CONFIG_PATH})",
    )
    ml_parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_ML_OUTPUT_DIR,
        help=f"versioned artifact directory (default: {DEFAULT_ML_OUTPUT_DIR})",
    )
    ml_parser.add_argument(
        "--json-output",
        type=Path,
        default=None,
        help="optional additional path for the complete evaluation JSON",
    )
    phase85_parser = subparsers.add_parser(
        "run-phase85-benchmark",
        help="generate expanded synthetic groups, run 24/60/120-month batches, and benchmark",
    )
    phase85_parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_CONFIG_PATH,
        help=f"model configuration (default: {DEFAULT_CONFIG_PATH})",
    )
    phase85_parser.add_argument(
        "--dataset",
        type=Path,
        default=DEFAULT_POPULATION_DATASET_PATH,
        help=f"ten-template synthetic fixture (default: {DEFAULT_POPULATION_DATASET_PATH})",
    )
    phase85_parser.add_argument(
        "--population-config",
        type=Path,
        default=DEFAULT_PHASE85_POPULATION_CONFIG_PATH,
        help=(
            "Phase 8.5 population configuration "
            f"(default: {DEFAULT_PHASE85_POPULATION_CONFIG_PATH})"
        ),
    )
    phase85_parser.add_argument(
        "--scenario",
        type=Path,
        default=DEFAULT_MANAGEMENT_SCENARIO_PATH,
        help=f"Phase 6 policy scenario YAML (default: {DEFAULT_MANAGEMENT_SCENARIO_PATH})",
    )
    phase85_parser.add_argument(
        "--ml-config",
        type=Path,
        default=DEFAULT_ML_CONFIG_PATH,
        help=f"Phase 8.5 ML configuration (default: {DEFAULT_ML_CONFIG_PATH})",
    )
    phase85_parser.add_argument(
        "--count",
        type=int,
        default=None,
        help="field count; must include every one of the 50 groups (default: config value)",
    )
    phase85_parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_ML_OUTPUT_DIR,
        help=f"versioned artifact directory (default: {DEFAULT_ML_OUTPUT_DIR})",
    )
    phase85_parser.add_argument(
        "--json-output",
        type=Path,
        default=None,
        help="optional additional path for the complete evaluation JSON",
    )
    phase86_parser = subparsers.add_parser(
        "run-phase86-benchmark",
        help=(
            "run repeated synthetic populations, freeze decisions, then evaluate a new "
            "final population"
        ),
    )
    phase86_parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    phase86_parser.add_argument("--dataset", type=Path, default=DEFAULT_POPULATION_DATASET_PATH)
    phase86_parser.add_argument(
        "--population-config", type=Path, default=DEFAULT_PHASE86_POPULATION_CONFIG_PATH
    )
    phase86_parser.add_argument("--scenario", type=Path, default=DEFAULT_MANAGEMENT_SCENARIO_PATH)
    phase86_parser.add_argument("--ml-config", type=Path, default=DEFAULT_PHASE86_ML_CONFIG_PATH)
    phase86_parser.add_argument("--output-dir", type=Path, default=DEFAULT_PHASE86_OUTPUT_DIR)
    phase86_parser.add_argument("--json-output", type=Path, default=None)
    phase9_parser = subparsers.add_parser(
        "run-phase9-benchmark",
        help=(
            "run the offline synthetic Phase 9 selection, abstention and oracle-regret "
            "benchmark using exact frozen Phase 8.6 observable artifacts"
        ),
    )
    phase9_parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    phase9_parser.add_argument("--dataset", type=Path, default=DEFAULT_POPULATION_DATASET_PATH)
    phase9_parser.add_argument(
        "--population-config", type=Path, default=DEFAULT_PHASE86_POPULATION_CONFIG_PATH
    )
    phase9_parser.add_argument("--scenario", type=Path, default=DEFAULT_MANAGEMENT_SCENARIO_PATH)
    phase9_parser.add_argument("--phase9-config", type=Path, default=DEFAULT_PHASE9_CONFIG_PATH)
    phase9_parser.add_argument(
        "--phase86-config", type=Path, default=DEFAULT_PHASE86_ML_CONFIG_PATH
    )
    phase9_parser.add_argument("--phase86-artifacts", type=Path, default=DEFAULT_PHASE86_OUTPUT_DIR)
    phase9_parser.add_argument("--output-dir", type=Path, default=DEFAULT_PHASE9_OUTPUT_DIR)
    phase9_parser.add_argument("--json-output", type=Path, default=None)
    return parser


def _show_model_info(parameters_json: dict[str, object]) -> None:
    print(json.dumps(parameters_json, sort_keys=True))


def _write_json(path: Path, payload: object) -> None:
    """Write deterministic, finite JSON only when explicitly requested."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, allow_nan=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main(argv: Sequence[str] | None = None) -> int:
    """Run the CLI and return a process exit code."""
    args = build_parser().parse_args(argv)
    command = cast(str, args.command)
    config_path = cast(Path, args.config)
    try:
        parameters = load_model_parameters(config_path)
    except ConfigLoadError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    if command == "validate-config":
        print(
            json.dumps(
                {
                    "configuration_hash": parameters.stable_hash(),
                    "model": parameters.model.name,
                    "status": "valid",
                    "version": parameters.model.version,
                },
                sort_keys=True,
            )
        )
        return 0

    if command == "show-model-info":
        _show_model_info(
            {
                "carbon_unit": parameters.model.carbon_unit,
                "horizon_years": parameters.model.horizon_years,
                "implementation_status": (
                    "Phase 9 offline synthetic intervention-selection and oracle-regret benchmark "
                    "across independent population, weather, and latent-biological seeds; "
                    "protected_soc remains a model proxy, not measured MAOC"
                ),
                "name": parameters.model.name,
                "scientific_claim_boundary": (
                    "synthetic success is not field validation or evidence of real-world causality"
                ),
                "soil_depth_cm": parameters.model.soil_depth_cm,
                "timestep_months": parameters.model.timestep_months,
                "version": parameters.model.version,
            }
        )
        return 0

    if command == "run-phase86-benchmark":
        try:
            phase86_config = load_phase86_benchmark_config(cast(Path, args.ml_config))
            population_config = load_population_config(cast(Path, args.population_config))
            base_dataset = VersionedLocalYamlAdapter().load(cast(Path, args.dataset))
            template = load_management_scenarios(cast(Path, args.scenario))
            report, table = run_phase86_benchmark(
                base_dataset=base_dataset,
                population_config=population_config,
                parameters=parameters,
                scenario=template,
                config=phase86_config,
                output_dir=cast(Path, args.output_dir),
            )
            print(table)
            json_output = cast(Path | None, args.json_output)
            if json_output is not None:
                _write_json(json_output, report)
            return 0
        except (ConfigLoadError, OSError, RuntimeError, ValueError, ArithmeticError) as exc:
            print(str(exc), file=sys.stderr)
            return 2

    if command == "run-phase9-benchmark":
        try:
            phase9_config = load_phase9_benchmark_config(cast(Path, args.phase9_config))
            frozen_bundle = load_frozen_phase86_bundle(
                artifact_dir=cast(Path, args.phase86_artifacts),
                phase86_config_path=cast(Path, args.phase86_config),
                expected=phase9_config.frozen_artifacts,
            )
            population_config = load_population_config(cast(Path, args.population_config))
            base_dataset = VersionedLocalYamlAdapter().load(cast(Path, args.dataset))
            template = load_management_scenarios(cast(Path, args.scenario))
            report, table = run_phase9_benchmark(
                base_dataset=base_dataset,
                population_config=population_config,
                parameters=parameters,
                scenario=template,
                config=phase9_config,
                bundle=frozen_bundle,
                output_dir=cast(Path, args.output_dir),
            )
            print(table)
            json_output = cast(Path | None, args.json_output)
            if json_output is not None:
                _write_json(json_output, report)
            return 0
        except (
            ConfigLoadError,
            DatasetAdapterError,
            FrozenArtifactError,
            OSError,
            RuntimeError,
            ValueError,
            ArithmeticError,
        ) as exc:
            print(str(exc), file=sys.stderr)
            return 2

    if command == "benchmark-intervention-ml":
        try:
            ml_config = load_ml_benchmark_config(cast(Path, args.ml_config))
            population = load_saved_population(cast(Path, args.population_json))
            batch = load_saved_batch(cast(Path, args.batch_json))
            if population.manifest.model_configuration_hash != parameters.stable_hash():
                raise ValueError(
                    "saved population model configuration hash does not match --config"
                )
            rows, manifest = build_ml_dataset(population, batch, ml_config)
            report, table = run_benchmark(rows, manifest, ml_config, cast(Path, args.output_dir))
            print(table)
            json_output = cast(Path | None, args.json_output)
            if json_output is not None:
                _write_json(json_output, report)
            return 0
        except (ConfigLoadError, OSError, RuntimeError, ValueError, ArithmeticError) as exc:
            print(str(exc), file=sys.stderr)
            return 2

    if command == "run-phase85-benchmark":
        try:
            ml_config = load_ml_benchmark_config(cast(Path, args.ml_config))
            population_config = load_population_config(cast(Path, args.population_config))
            base_dataset = VersionedLocalYamlAdapter().load(cast(Path, args.dataset))
            dataset = expand_synthetic_foundation(
                base_dataset,
                group_count=ml_config.foundation_group_count,
                random_seed=ml_config.foundation_seed,
            )
            count = (
                population_config.default_population_size if args.count is None else int(args.count)
            )
            if count < ml_config.foundation_group_count:
                raise ValueError(
                    "field count must be at least the expanded empirical-seed group count"
                )
            population = generate_population(
                dataset=dataset,
                config=population_config,
                parameters=parameters,
                population_size=count,
            )
            template = load_management_scenarios(cast(Path, args.scenario))
            batch = run_population_batch(
                population,
                template,
                parameters,
                population_config,
                horizons_months=ml_config.simulation_horizons_months,
            )
            rows, manifest = build_ml_dataset(population, batch, ml_config)
            output_dir = cast(Path, args.output_dir)
            _write_json(
                output_dir / "saved_population_and_batch.json",
                {
                    "population_manifest": population.manifest.model_dump(mode="json"),
                    "fields": [field.model_dump(mode="json") for field in population.fields],
                    "batch": batch.model_dump(mode="json"),
                },
            )
            report, table = run_benchmark(rows, manifest, ml_config, output_dir)
            print(table)
            json_output = cast(Path | None, args.json_output)
            if json_output is not None:
                _write_json(json_output, report)
            return 0
        except (ConfigLoadError, OSError, RuntimeError, ValueError, ArithmeticError) as exc:
            print(str(exc), file=sys.stderr)
            return 2

    if command in {"generate-population", "run-population-batch"}:
        try:
            population_config = load_population_config(cast(Path, args.population_config))
            dataset = VersionedLocalYamlAdapter().load(cast(Path, args.dataset))
            population = generate_population(
                dataset=dataset,
                config=population_config,
                parameters=parameters,
                population_size=cast(int | None, args.count),
                generation_seed=cast(int | None, args.seed),
            )
            generated_summary = population_summary(population)
            json_output = cast(Path | None, args.json_output)
            if command == "generate-population":
                print(population_summary_table(generated_summary))
                if json_output is not None:
                    _write_json(
                        json_output,
                        {
                            "summary": generated_summary,
                            "manifest": population.manifest.model_dump(mode="json"),
                            "fields": [
                                field.model_dump(mode="json") for field in population.fields
                            ],
                        },
                    )
                return 0
            template = load_management_scenarios(cast(Path, args.scenario))
            batch = run_population_batch(population, template, parameters, population_config)
            intervention_summary = batch_summary(batch)
            print(population_summary_table(generated_summary))
            print()
            print(batch_summary_table(intervention_summary))
            if json_output is not None:
                _write_json(
                    json_output,
                    {
                        "population_summary": generated_summary,
                        "population_manifest": population.manifest.model_dump(mode="json"),
                        "fields": [field.model_dump(mode="json") for field in population.fields],
                        "batch_summary": intervention_summary,
                        "batch": batch.model_dump(mode="json"),
                    },
                )
            return 0
        except (
            CarbonCoreError,
            ConfigLoadError,
            DatasetAdapterError,
            OSError,
            RuntimeError,
            ValueError,
            ArithmeticError,
        ) as exc:
            print(str(exc), file=sys.stderr)
            return 2

    if command == "compare-management":
        scenario_path = cast(Path, args.scenario)
        try:
            management_scenarios = load_management_scenarios(scenario_path)
            comparison = compare_management_scenarios(management_scenarios, parameters)
        except (CarbonCoreError, ConfigLoadError, ValueError, ArithmeticError) as exc:
            print(str(exc), file=sys.stderr)
            return 2
        print(
            json.dumps(
                {
                    "scientific_claim_boundary": comparison.scientific_claim_boundary,
                    "scenario": comparison.scenario_name,
                    "scenario_version": comparison.scenario_version,
                    "policies": [
                        {
                            "policy_id": result.policy_id,
                            "policy_name": result.policy_name,
                            "configuration_hash": result.configuration_hash,
                            "schedule_hash": result.schedule_hash,
                            "intervention_schedule": [
                                {
                                    "event_id": applied.event.event_id,
                                    "event_type": applied.event.event_type,
                                    "simulation_month": applied.simulation_month,
                                    "order_in_month": applied.order_in_month,
                                    "amount": applied.event.amount,
                                    "units": applied.event.units,
                                    "cost_gbp_ha": applied.event.cost_gbp_ha,
                                    "emissions_proxy_kg_co2e_ha": (
                                        applied.event.emissions_proxy_kg_co2e_ha
                                    ),
                                    "source_classification": applied.event.source_classification,
                                    "parameter_provenance": applied.event.parameter_provenance,
                                }
                                for applied in result.applied_events
                            ],
                            "yield_t_dm_ha": result.cumulative_grain_yield_t_dm_ha,
                            "amf": {
                                "final_live_biomass_t_c_ha": result.final_state.amf_live_c,
                                "final_necromass_t_c_ha": result.final_state.amf_necromass_c,
                                "monthly_outcomes": result.amf_outcomes,
                            },
                            "carbon_pools_t_c_ha": {
                                "dpm_c": result.final_state.dpm_c,
                                "rpm_c": result.final_state.rpm_c,
                                "microbial_c": result.final_state.microbial_c,
                                "protected_soc_c": result.final_state.protected_soc_c,
                                "iom_c": result.final_state.iom_c,
                            },
                            "available_phosphorus_kg_p_ha": (result.final_state.available_p_kg_ha),
                            "respiration_t_c_ha": result.cumulative_respiration_t_c_ha,
                            "cost_gbp_ha": result.cumulative_cost_gbp_ha,
                            "emissions_proxy_kg_co2e_ha": (
                                result.cumulative_emissions_proxy_kg_co2e_ha
                            ),
                            "carbon_residual_t_c_ha": (result.cumulative_carbon_residual_t_c_ha),
                            "phosphorus_residual_kg_p_ha": (
                                result.cumulative_phosphorus_residual_kg_p_ha
                            ),
                            "uncertainty": result.uncertainty_status,
                        }
                        for result in comparison.results
                    ],
                },
                sort_keys=True,
            )
        )
        return 0

    if command == "run-spring-barley":
        scenario_path = cast(Path, args.scenario)
        try:
            plant_scenario = load_plant_scenario(scenario_path)
            plant_result = run_amf_extension(
                plant_scenario.initial_state,
                plant_scenario.monthly_steps,
                parameters,
                seed=plant_scenario.seed,
            )
        except (CarbonCoreError, ConfigLoadError, ValueError, ArithmeticError) as exc:
            print(str(exc), file=sys.stderr)
            return 2
        print(
            json.dumps(
                {
                    "configuration_hash": plant_result.configuration_hash,
                    "cumulative": {
                        "amf_phosphorus_acquired_kg_p_ha": (
                            plant_result.cumulative_amf_phosphorus_acquired_kg_p_ha
                        ),
                        "amf_phosphorus_transferred_kg_p_ha": (
                            plant_result.cumulative_amf_phosphorus_transferred_kg_p_ha
                        ),
                        "carbon_mass_balance_residual_t_c_ha": (
                            plant_result.cumulative_carbon_mass_balance.residual_t_c_ha
                        ),
                        "fungal_necromass_routing_t_c_ha": {
                            "dpm_c": plant_result.cumulative_necromass_to_dpm_t_c_ha,
                            "protected_soc_c": (
                                plant_result.cumulative_necromass_to_protected_t_c_ha
                            ),
                            "rpm_c": plant_result.cumulative_necromass_to_rpm_t_c_ha,
                        },
                        "fungal_respiration_t_c_ha": (
                            plant_result.cumulative_fungal_respiration_t_c_ha
                        ),
                        "fungal_turnover_t_c_ha": (plant_result.cumulative_fungal_turnover_t_c_ha),
                        "grain_yield_t_dm_ha": plant_result.cumulative_grain_yield_t_dm_ha,
                        "net_plant_carbon_effect_t_c_ha": (
                            plant_result.cumulative_net_plant_carbon_effect_t_c_ha
                        ),
                        "net_yield_effect_t_dm_ha": (
                            plant_result.cumulative_net_yield_effect_t_dm_ha
                        ),
                        "plant_carbon_allocated_to_amf_t_c_ha": (
                            plant_result.cumulative_plant_to_amf_carbon_t_c_ha
                        ),
                        "phosphorus_mass_balance_residual_kg_p_ha": (
                            plant_result.cumulative_phosphorus_mass_balance.residual_kg_p_ha
                        ),
                        "phosphorus_uptake_kg_p_ha": (
                            plant_result.cumulative_direct_plant_phosphorus_uptake_kg_p_ha
                            + plant_result.cumulative_amf_phosphorus_transferred_kg_p_ha
                        ),
                        "potential_npp_t_c_ha": plant_result.cumulative_potential_npp_t_c_ha,
                        "realised_npp_t_c_ha": (
                            plant_result.cumulative_gross_realised_plant_carbon_t_c_ha
                        ),
                        "residue_to_dpm_t_c_ha": plant_result.cumulative_residue_to_dpm_t_c_ha,
                        "residue_to_rpm_t_c_ha": plant_result.cumulative_residue_to_rpm_t_c_ha,
                    },
                    "final": {
                        "available_phosphorus_kg_p_ha": (
                            plant_result.final_state.available_p_kg_ha
                        ),
                        "fungal_necromass_t_c_ha": (plant_result.final_state.amf_necromass_c),
                        "live_fungal_biomass_t_c_ha": plant_result.final_state.amf_live_c,
                        "root_biomass_t_c_ha": plant_result.final_state.root_c,
                        "shoot_biomass_t_c_ha": plant_result.final_state.plant_c,
                        "soil_carbon_pools_t_c_ha": {
                            "dpm_c": plant_result.final_state.dpm_c,
                            "iom_c": plant_result.final_state.iom_c,
                            "microbial_c": plant_result.final_state.microbial_c,
                            "protected_soc_c": plant_result.final_state.protected_soc_c,
                            "rpm_c": plant_result.final_state.rpm_c,
                        },
                    },
                    "input_timing": parameters.rothc.external_input_timing,
                    "monthly": [
                        {
                            "amf_phosphorus_acquired_kg_p_ha": (
                                step.amf_phosphorus_acquired_kg_p_ha
                            ),
                            "amf_phosphorus_transferred_kg_p_ha": (
                                step.amf_phosphorus_transferred_kg_p_ha
                            ),
                            "available_phosphorus_kg_p_ha": step.final_state.available_p_kg_ha,
                            "carbon_mass_balance_residual_t_c_ha": (
                                step.carbon_mass_balance.residual_t_c_ha
                            ),
                            "grain_yield_t_dm_ha": step.grain_yield_t_dm_ha,
                            "fungal_necromass_routing_t_c_ha": {
                                "dpm_c": step.necromass_to_dpm_t_c_ha,
                                "protected_soc_c": step.necromass_to_protected_t_c_ha,
                                "rpm_c": step.necromass_to_rpm_t_c_ha,
                            },
                            "fungal_respiration_t_c_ha": step.fungal_respiration_t_c_ha,
                            "fungal_turnover_t_c_ha": step.fungal_turnover_t_c_ha,
                            "live_fungal_biomass_t_c_ha": step.final_state.amf_live_c,
                            "month_index": step.initial_state.month_index,
                            "net_plant_carbon_effect_t_c_ha": (step.net_plant_carbon_effect_t_c_ha),
                            "net_yield_effect_t_dm_ha": step.net_yield_effect_t_dm_ha,
                            "phosphorus_mass_balance_residual_kg_p_ha": (
                                step.phosphorus_mass_balance.residual_kg_p_ha
                            ),
                            "phosphorus_uptake_kg_p_ha": (
                                step.total_plant_phosphorus_received_kg_p_ha
                            ),
                            "plant_carbon_allocated_to_amf_t_c_ha": (
                                step.plant_to_amf_carbon_t_c_ha
                            ),
                            "plant_outcome": step.plant_outcome,
                            "potential_npp_t_c_ha": step.potential_npp_t_c_ha,
                            "realised_npp_t_c_ha": (step.gross_realised_plant_carbon_t_c_ha),
                            "residue_to_dpm_t_c_ha": step.residue_to_dpm_t_c_ha,
                            "residue_to_rpm_t_c_ha": step.residue_to_rpm_t_c_ha,
                            "root_biomass_t_c_ha": step.final_state.root_c,
                            "shoot_biomass_t_c_ha": step.final_state.plant_c,
                            "soil_carbon_pools_t_c_ha": {
                                "dpm_c": step.final_state.dpm_c,
                                "iom_c": step.final_state.iom_c,
                                "microbial_c": step.final_state.microbial_c,
                                "protected_soc_c": step.final_state.protected_soc_c,
                                "rpm_c": step.final_state.rpm_c,
                            },
                            "stress_modifiers": step.stress.model_dump(mode="json"),
                        }
                        for step in plant_result.steps
                    ],
                    "provenance": plant_result.provenance,
                    "scenario": plant_scenario.name,
                    "seed": plant_result.seed,
                    "uncertainty": plant_result.uncertainty_status,
                    "units": {
                        "carbon": plant_result.carbon_unit,
                        "phosphorus": plant_result.phosphorus_unit,
                    },
                },
                sort_keys=True,
            )
        )
        return 0

    scenario_path = cast(Path, args.scenario)
    try:
        scenario = load_carbon_core_scenario(scenario_path)
        result = run_carbon_core(
            scenario.initial_state,
            scenario.monthly_steps,
            parameters,
            seed=scenario.seed,
        )
    except (CarbonCoreError, ConfigLoadError, ValueError, ArithmeticError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(
        json.dumps(
            {
                "carbon_unit": result.carbon_unit,
                "external_input_timing": result.external_input_timing,
                "cumulative": {
                    "co2_respiration_t_c_ha": result.cumulative_respiration_t_c_ha,
                    "mass_balance_residual_t_c_ha": (
                        result.cumulative_mass_balance.residual_t_c_ha
                    ),
                    "transfer_to_microbial_t_c_ha": (
                        result.cumulative_transfer_to_microbial_t_c_ha
                    ),
                    "transfer_to_protected_t_c_ha": (
                        result.cumulative_transfer_to_protected_t_c_ha
                    ),
                },
                "final_pools_t_c_ha": {
                    "dpm_c": result.final_state.dpm_c,
                    "iom_c": result.final_state.iom_c,
                    "microbial_c": result.final_state.microbial_c,
                    "protected_soc_c": result.final_state.protected_soc_c,
                    "rpm_c": result.final_state.rpm_c,
                },
                "monthly": [
                    {
                        "co2_respiration_t_c_ha": step.respiration_t_c_ha,
                        "environmental_modifiers": {
                            "combined": step.modifiers.combined,
                            "cover": step.modifiers.cover,
                            "moisture": step.modifiers.moisture,
                            "temperature": step.modifiers.temperature,
                        },
                        "mass_balance_residual_t_c_ha": step.mass_balance.residual_t_c_ha,
                        "month_index": step.initial_state.month_index,
                        "topsoil_moisture_deficit_mm": (step.modifiers.accumulated_tsmd_mm),
                        "transfer_to_microbial_t_c_ha": (step.transfer_to_microbial_t_c_ha),
                        "transfer_to_protected_t_c_ha": (step.transfer_to_protected_t_c_ha),
                    }
                    for step in result.steps
                ],
                "provenance": result.provenance,
                "scenario": scenario.name,
                "seed": result.seed,
                "uncertainty": result.uncertainty_status,
            },
            sort_keys=True,
        )
    )
    return 0
