"""Deterministic Phase 9.5 scientific-remediation artifact pipeline."""

from __future__ import annotations

import csv
import hashlib
import json
import math
import random
from collections import Counter
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, cast

from soil_simulator.io.configuration import (
    load_management_scenarios,
    load_model_parameters,
)
from soil_simulator.io.population_configuration import load_population_config
from soil_simulator.ml.dataset import load_saved_population
from soil_simulator.phase95.accounting import accrue_accounting, load_accounting_schedule
from soil_simulator.phase95.analysis import phosphorus_ablation, sensitivity_evaluator
from soil_simulator.phase95.baseline import verify_frozen_baseline
from soil_simulator.phase95.empirical import location_group_leakage
from soil_simulator.phase95.long_term_validation import run_hoosfield_validation
from soil_simulator.phase95.policies import duplicate_policy_report
from soil_simulator.phase95.readiness import publication_readiness
from soil_simulator.phase95.reporting import (
    circularity_diagnostics,
    headline_target_manifest,
)
from soil_simulator.phase95.sensitivity import (
    SensitivityParameter,
    load_sensitivity_specification,
    morris_screen,
    rank_stability,
    sobol_indices,
)

OUTPUT_DIRECTORY = "outputs/phase95_v0.9.5"


def _write_json(path: Path, value: object) -> None:
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def _write_csv(path: Path, rows: Sequence[Mapping[str, object]]) -> None:
    if not rows:
        raise ValueError(f"cannot write empty CSV {path}")
    columns = tuple(rows[0])
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="raise")
        writer.writeheader()
        writer.writerows(rows)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _accounting_artifacts(root: Path) -> tuple[dict[str, object], list[dict[str, object]]]:
    schedule = load_accounting_schedule(root / "config/phase95/accounting.yaml")
    records: list[dict[str, object]] = []
    policies = (
        "baseline",
        "conventional_tillage",
        "reduced_tillage",
        "cover_crop",
        "phosphorus",
        "farmyard_manure",
    )
    results: dict[str, object] = {}
    for horizon in (24, 60, 120):
        by_policy: dict[str, object] = {}
        for policy in policies:
            total = accrue_accounting(schedule, policy, horizon)
            by_policy[policy] = total.model_dump(mode="json")
            records.append(
                {
                    "policy_id": policy,
                    "horizon_months": horizon,
                    "event_count": total.event_count,
                    "cost_gbp_ha": total.cost_gbp_ha,
                    "operational_emissions_kg_co2e_ha": (total.operational_emissions_kg_co2e_ha),
                    "lifecycle_emissions_kg_co2e_ha": (total.lifecycle_emissions_kg_co2e_ha),
                    "total_emissions_kg_co2e_ha": total.total_emissions_kg_co2e_ha,
                    "status": total.uncertainty_status,
                }
            )
        results[str(horizon)] = by_policy
    return {
        "version": "0.9.5",
        "schedule_hash": schedule.stable_hash(),
        "horizons": results,
        "mass_balance_boundary": (
            "All accounting totals are external to biological carbon and phosphorus ledgers."
        ),
        "claim_boundary": schedule.claim_boundary,
    }, records


def _phosphorus_csv(result: Mapping[str, object]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    variants = cast(dict[str, dict[str, object]], result["variants_by_horizon"])
    for horizon, by_variant in sorted(variants.items(), key=lambda item: int(item[0])):
        for variant, payload in by_variant.items():
            if not variant.endswith("_effect") and variant != "no_phosphorus_intervention":
                continue
            for target, value in cast(dict[str, float], payload).items():
                rows.append(
                    {
                        "horizon_months": int(horizon),
                        "variant": variant,
                        "target": target,
                        "value": value,
                    }
                )
        accounting = cast(dict[str, object], by_variant["horizon_aware_accounting"])
        for target in (
            "cost_gbp_ha",
            "operational_emissions_kg_co2e_ha",
            "lifecycle_emissions_kg_co2e_ha",
            "total_emissions_kg_co2e_ha",
        ):
            rows.append(
                {
                    "horizon_months": int(horizon),
                    "variant": "phosphorus_horizon_aware_accounting",
                    "target": target,
                    "value": accounting[target],
                }
            )
    return rows


def _screen_scores(
    screen: Mapping[str, Mapping[str, Mapping[str, float]]],
    parameters: tuple[SensitivityParameter, ...],
) -> dict[str, float]:
    scores = {parameter.name: 0.0 for parameter in parameters}
    usable_outputs = 0
    for by_parameter in screen.values():
        maximum = max(metric["mu_star"] for metric in by_parameter.values())
        if maximum <= 0.0:
            continue
        usable_outputs += 1
        for name, metric in by_parameter.items():
            scores[name] += metric["mu_star"] / maximum
    divisor = max(usable_outputs, 1)
    return {name: score / divisor for name, score in scores.items()}


def _sobol_rank_stability(full: Mapping[str, object], partial: Mapping[str, object]) -> float:
    full_outputs = cast(dict[str, dict[str, object]], full["outputs"])
    partial_outputs = cast(dict[str, dict[str, object]], partial["outputs"])
    agreements: list[float] = []
    for output, full_result in full_outputs.items():
        partial_result = partial_outputs[output]
        full_indices = cast(dict[str, dict[str, float | None]], full_result["indices"])
        partial_indices = cast(dict[str, dict[str, float | None]], partial_result["indices"])
        full_rank = tuple(
            sorted(
                full_indices,
                key=lambda name: float(full_indices[name]["total_order"] or 0.0),
                reverse=True,
            )
        )
        partial_rank = tuple(
            sorted(
                partial_indices,
                key=lambda name: float(partial_indices[name]["total_order"] or 0.0),
                reverse=True,
            )
        )
        agreements.append(
            math.fsum(a == b for a, b in zip(full_rank, partial_rank, strict=True)) / len(full_rank)
        )
    return math.fsum(agreements) / len(agreements)


def _ranking_uncertainty(
    parameters: tuple[SensitivityParameter, ...],
    evaluator: Any,
    *,
    draws: int,
    seed: int,
) -> dict[str, object]:
    rng = random.Random(seed)
    with_phosphorus: Counter[str] = Counter()
    without_phosphorus: Counter[str] = Counter()
    for _ in range(draws):
        values = {parameter.name: parameter.transform(rng.random()) for parameter in parameters}
        outcomes = evaluator(values)
        policies = {
            key.split("|", 1)[0] for key in outcomes if key.endswith("|total_soc_t_c_ha|120")
        }
        policy_scores = {
            policy: float(outcomes[f"{policy}|total_soc_t_c_ha|120"])
            + float(outcomes[f"{policy}|protected_soc_proxy_t_c_ha|120"])
            for policy in policies
        }
        with_phosphorus[max(policies, key=policy_scores.__getitem__)] += 1
        remaining = policies - {"phosphorus"}
        without_phosphorus[max(remaining, key=policy_scores.__getitem__)] += 1
    return {
        "draws": draws,
        "seed": seed,
        "winner_frequency_with_phosphorus": {
            key: value / draws for key, value in sorted(with_phosphorus.items())
        },
        "winner_frequency_excluding_phosphorus": {
            key: value / draws for key, value in sorted(without_phosphorus.items())
        },
        "stable_with_phosphorus": len(with_phosphorus) == 1,
        "stable_excluding_phosphorus": len(without_phosphorus) == 1,
    }


def _sensitivity_artifacts(
    root: Path, field: object
) -> tuple[dict[str, object], list[dict[str, object]]]:
    specification = load_sensitivity_specification(root / "config/phase95/sensitivity.yaml")
    parameters = load_model_parameters(root / "config/model_defaults.yaml")
    population_config = load_population_config(root / "config/populations/phase86_population.yaml")
    template = load_management_scenarios(root / "config/scenarios/management_scenarios.yaml")

    def evaluator(values: Mapping[str, float]) -> Mapping[str, float]:
        return sensitivity_evaluator(
            cast(Any, field), template, parameters, population_config, values
        )

    screen = morris_screen(
        specification.parameters,
        evaluator,
        trajectories=specification.morris_trajectories,
        levels=specification.morris_levels,
        seed=specification.seed,
    )
    partial_screen = morris_screen(
        specification.parameters,
        evaluator,
        trajectories=specification.morris_trajectories // 2,
        levels=specification.morris_levels,
        seed=specification.seed,
    )
    scores = _screen_scores(screen, specification.parameters)
    selected_names = tuple(
        name
        for name, _ in sorted(scores.items(), key=lambda item: item[1], reverse=True)[
            : specification.sobol_parameter_count
        ]
    )
    selected = tuple(
        parameter for parameter in specification.parameters if parameter.name in selected_names
    )
    sobol = sobol_indices(
        selected,
        evaluator,
        sample_size=specification.sobol_base_sample_size,
        seed=specification.seed + 1,
    )
    partial_sobol = sobol_indices(
        selected,
        evaluator,
        sample_size=specification.sobol_base_sample_size // 2,
        seed=specification.seed + 1,
    )
    morris_stability = {
        output: rank_stability(by_parameter, partial_screen[output])
        for output, by_parameter in screen.items()
    }
    ranking = _ranking_uncertainty(
        specification.parameters,
        evaluator,
        draws=24,
        seed=specification.seed + 2,
    )
    result: dict[str, object] = {
        "version": "0.9.5",
        "method": "Morris screening followed by Saltelli/Sobol",
        "seed_manifest": {
            "morris_seed": specification.seed,
            "sobol_seed": specification.seed + 1,
            "ranking_seed": specification.seed + 2,
        },
        "parameters": [parameter.__dict__ for parameter in specification.parameters],
        "morris": screen,
        "morris_aggregate_scores": scores,
        "sobol_selected_parameters": selected_names,
        "sobol": sobol,
        "convergence": {
            "morris_half_vs_full_rank_agreement_by_output": morris_stability,
            "morris_mean_rank_agreement": math.fsum(morris_stability.values())
            / len(morris_stability),
            "sobol_half_vs_full_mean_rank_agreement": _sobol_rank_stability(sobol, partial_sobol),
        },
        "policy_ranking_uncertainty": ranking,
        "population_covariance_sensitivity": {
            "status": "not_run",
            "reason": (
                "The required empirical pilot was unavailable, so observable covariance "
                "parameters could not be re-estimated or defensibly propagated."
            ),
        },
        "scope": (
            "Global parameter uncertainty on one archived synthetic field across all six "
            "Phase 9.5 policies and paired effect targets; not population uncertainty."
        ),
        "complete_for_publication_gate": False,
    }
    rows: list[dict[str, object]] = []
    for output, by_parameter in screen.items():
        policy, target, horizon = output.split("|")
        for parameter, metric in by_parameter.items():
            rows.append(
                {
                    "method": "morris",
                    "policy_id": policy,
                    "target": target,
                    "horizon_months": int(horizon),
                    "parameter": parameter,
                    "first_order": "",
                    "total_order": "",
                    "interaction_remainder": "",
                    "mu_star": metric["mu_star"],
                    "sigma": metric["sigma"],
                }
            )
    sobol_outputs = cast(dict[str, dict[str, object]], sobol["outputs"])
    for output, output_result in sobol_outputs.items():
        policy, target, horizon = output.split("|")
        indices = cast(dict[str, dict[str, float | None]], output_result["indices"])
        for parameter, sobol_metric in indices.items():
            rows.append(
                {
                    "method": "sobol",
                    "policy_id": policy,
                    "target": target,
                    "horizon_months": int(horizon),
                    "parameter": parameter,
                    "first_order": sobol_metric["first_order"],
                    "total_order": sobol_metric["total_order"],
                    "interaction_remainder": sobol_metric["interaction_remainder"],
                    "mu_star": "",
                    "sigma": "",
                }
            )
    return result, rows


def _validation_rows(result: Mapping[str, object]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    treatments = cast(dict[str, dict[str, object]], result["treatments"])
    for treatment, payload in treatments.items():
        for point in cast(tuple[dict[str, object], ...], payload["trajectory"]):
            rows.append({"treatment": treatment, **point})
    return rows


def _trajectory_svg(rows: Sequence[Mapping[str, object]]) -> str:
    width, height = 900, 520
    left, right, top, bottom = 80, 30, 45, 70
    plot_width = width - left - right
    plot_height = height - top - bottom
    years = [int(str(row["year"])) for row in rows]
    values = [
        float(str(row[key]))
        for row in rows
        for key in ("observed_soc_t_c_ha", "simulated_soc_t_c_ha")
    ]
    minimum = min(values) - 5.0
    maximum = max(values) + 5.0

    def x(year: int) -> float:
        return float(left + (year - min(years)) / (max(years) - min(years)) * plot_width)

    def y(value: float) -> float:
        return top + (maximum - value) / (maximum - minimum) * plot_height

    colours = {
        "unfertilized": "#2f6b3c",
        "fym_annual": "#9c4a1a",
        "fym_1852_1871": "#4267a8",
    }
    lines = [
        (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" '
            f'height="{height}" viewBox="0 0 {width} {height}">'
        ),
        '<rect width="100%" height="100%" fill="white"/>',
        (
            '<text x="450" y="25" text-anchor="middle" font-family="sans-serif" '
            'font-size="18">Hoosfield SOC: observed (solid) and uncalibrated simulated '
            "(dashed)</text>"
        ),
        (
            f'<line x1="{left}" y1="{top + plot_height}" '
            f'x2="{left + plot_width}" y2="{top + plot_height}" stroke="black"/>'
        ),
        (f'<line x1="{left}" y1="{top}" x2="{left}" y2="{top + plot_height}" stroke="black"/>'),
    ]
    treatments = sorted({str(row["treatment"]) for row in rows})
    for treatment_index, treatment in enumerate(treatments):
        subset = sorted(
            (row for row in rows if row["treatment"] == treatment),
            key=lambda row: int(str(row["year"])),
        )
        observed = " ".join(
            f"{x(int(str(row['year']))):.1f},{y(float(str(row['observed_soc_t_c_ha']))):.1f}"
            for row in subset
        )
        simulated = " ".join(
            f"{x(int(str(row['year']))):.1f},{y(float(str(row['simulated_soc_t_c_ha']))):.1f}"
            for row in subset
        )
        colour = colours[treatment]
        lines.extend(
            (
                (f'<polyline points="{observed}" fill="none" stroke="{colour}" stroke-width="3"/>'),
                (
                    f'<polyline points="{simulated}" fill="none" stroke="{colour}" '
                    'stroke-width="2" stroke-dasharray="7 5"/>'
                ),
                (
                    f'<text x="{left + 15 + treatment_index * 245}" y="{height - 24}" '
                    f'font-family="sans-serif" font-size="13" fill="{colour}">'
                    f"{treatment}</text>"
                ),
            )
        )
    for tick in (1860, 1900, 1940, 1980):
        lines.append(
            f'<text x="{x(tick):.1f}" y="{top + plot_height + 24}" '
            f'text-anchor="middle" font-family="sans-serif" font-size="12">{tick}</text>'
        )
    middle = top + plot_height / 2
    lines.append(
        f'<text x="18" y="{middle:.1f}" transform="rotate(-90 18 {middle:.1f})" '
        'text-anchor="middle" font-family="sans-serif" font-size="13">'
        "SOC (t C ha-1, 0-23 cm)</text>"
    )
    lines.append("</svg>\n")
    return "\n".join(lines)


def _blocked_manifests(
    root: Path, population: object
) -> tuple[dict[str, object], dict[str, object]]:
    local_fixture = root / "data/processed/phase7_empirical_seed_fixture_v1.yaml"
    empirical = {
        "version": "0.9.5",
        "status": "blocked",
        "source_assessment_date": "2026-07-21",
        "minimum_required_locations": 50,
        "completed_empirical_locations": 0,
        "coordinates_stored": False,
        "immutable_fixture_created": False,
        "required_extraction_contract": {
            "coordinate_resolution": "coarsened non-sensitive grid-cell centroids",
            "soil_depth": "0-23 cm target with documented source-depth harmonisation",
            "soil_variables": [
                "clay_percent",
                "silt_percent",
                "sand_percent",
                "soc_t_c_ha",
                "bulk_density_g_cm3",
                "ph",
            ],
            "climate_variables": [
                "monthly_mean_temperature_c",
                "monthly_precipitation_mm",
                "monthly_potential_evapotranspiration_mm",
            ],
            "units_required_in_fixture": True,
            "grouping": "empirical location or region",
        },
        "sources_evaluated": [
            {
                "name": "SoilGrids",
                "version": "SoilGrids 2.0 documentation available on assessment date",
                "url": "https://docs.isric.org/globaldata/soilgrids/",
                "status": "not_reliably_extractable",
                "reason": (
                    "official point REST API is paused; no immutable 50-point extraction "
                    "was available"
                ),
            },
            {
                "name": "LUCAS 2018 topsoil",
                "version": "JRC LUCAS 2018 topsoil data portal on assessment date",
                "url": "https://esdac.jrc.ec.europa.eu/content/lucas-2018-topsoil-data",
                "status": "access_requires_registration",
                "reason": "no authenticated, version-pinned extraction was available",
            },
            {
                "name": "ERA5-Land monthly averaged data",
                "version": "Copernicus CDS ERA5-Land monthly averaged data",
                "url": (
                    "https://cds.climate.copernicus.eu/datasets/reanalysis-era5-land-monthly-means"
                ),
                "status": "documented_but_not_paired",
                "reason": "climate data alone cannot satisfy the paired soil-climate pilot",
            },
        ],
        "existing_fixture": {
            "path": str(local_fixture.relative_to(root)),
            "sha256": _sha256(local_fixture),
            "classification": "hand_authored_synthetic_demonstration_seed_fixture",
        },
        "prohibition": (
            "The existing ten-seed fixture and Phase 8.6 expansion remain synthetic and are "
            "not relabelled as empirical."
        ),
    }
    revised_population = {
        "version": "0.9.5",
        "status": "not_generated_due_empirical_pilot_blocker",
        "field_count": 0,
        "population_hash": None,
        "covariance_reestimation": "not_performed_insufficient_real_pilot_data",
        "archived_synthetic_diagnostic_input": {
            "population_hash": cast(Any, population).manifest.population_hash,
            "field_count": len(cast(Any, population).fields),
            "classification": "archived_non_representative_synthetic_methodology",
            "group_leakage_check": location_group_leakage(cast(Any, population)),
        },
        "downstream_consequence": (
            "No new population, ML training, applicability benchmark, oracle, or regret result "
            "is reported as a Phase 9.5 result."
        ),
    }
    return empirical, revised_population


def _hash_artifacts(output_dir: Path) -> dict[str, object]:
    files = {
        path.relative_to(output_dir).as_posix(): _sha256(path)
        for path in sorted(output_dir.rglob("*"))
        if path.is_file() and path.name != "artifact_hashes.json"
    }
    payload = json.dumps(files, sort_keys=True, separators=(",", ":"))
    return {
        "version": "0.9.5",
        "directory": str(output_dir),
        "files": files,
        "artifact_set_sha256": hashlib.sha256(payload.encode()).hexdigest(),
    }


def run_phase95_pipeline(
    repository_root: str | Path, output_dir: str | Path | None = None
) -> dict[str, object]:
    """Regenerate all Phase 9.5 machine-readable evidence without network access."""
    root = Path(repository_root).resolve()
    destination = root / OUTPUT_DIRECTORY if output_dir is None else Path(output_dir).resolve()
    destination.mkdir(parents=True, exist_ok=True)

    parameters = load_model_parameters(root / "config/model_defaults.yaml")
    template = load_management_scenarios(root / "config/scenarios/management_scenarios.yaml")
    population_config = load_population_config(root / "config/populations/phase86_population.yaml")
    population = load_saved_population(
        root / "outputs/phase86_v0.8.6/frozen_final_population_and_batch.json"
    )
    diagnostic_population = population.model_copy(update={"fields": population.fields[:5]})

    baseline = verify_frozen_baseline(root, root / "config/phase95/frozen_v090_sha256.json")
    targets = headline_target_manifest()
    circularity = circularity_diagnostics(
        root / "outputs/phase86_v0.8.6/frozen_final_dataset_v0.8.6.csv"
    )
    duplicates = duplicate_policy_report(template, parameters)
    accounting, accounting_rows = _accounting_artifacts(root)
    phosphorus = phosphorus_ablation(
        diagnostic_population,
        template,
        parameters,
        population_config,
        load_accounting_schedule(root / "config/phase95/accounting.yaml"),
    )
    sensitivity, sensitivity_rows = _sensitivity_artifacts(root, population.fields[0])
    validation = run_hoosfield_validation(
        root / "data/validation/hoosfield_soc_1852_1998_v1.csv", parameters
    )
    validation["local_fixture_sha256"] = _sha256(
        root / "data/validation/hoosfield_soc_1852_1998_v1.csv"
    )
    validation_rows = _validation_rows(validation)
    empirical, revised_population = _blocked_manifests(root, population)
    readiness = publication_readiness(
        {
            "stock_target_circularity_removed_from_headlines": True,
            "deterministic_accounting_removed_from_ml": True,
            "duplicate_no_till_resolved": True,
            "phosphorus_dominance_bounded_calibrated_or_excluded": True,
            "global_sensitivity_complete": False,
            "multi_decade_soc_validation_reported": True,
            "population_empirically_grounded_or_explicitly_synthetic": True,
            "results_and_limitations_reproducible": True,
            "negative_findings_visible": True,
        }
    )
    readiness["blocker_detail"] = {
        "global_sensitivity_complete": (
            "Mechanistic and schedule uncertainty was analysed, but observable population "
            "covariance could not be propagated without the blocked empirical pilot."
        ),
        "empirical_pilot": (
            "A reliable versioned 50-location paired soil-climate extraction remains required "
            "before population covariance and downstream ML/regret reruns."
        ),
        "audit_document": (
            "docs/AUDIT_soil_simulator_v0.9.0.md was requested but is absent from this checkout."
        ),
    }

    outputs = {
        "baseline_preservation.json": baseline,
        "headline_target_manifest.json": targets,
        "circularity_diagnostics.json": circularity,
        "duplicate_policy_report.json": duplicates,
        "horizon_aware_accounting.json": accounting,
        "phosphorus_ablation.json": phosphorus,
        "sensitivity_results.json": sensitivity,
        "long_term_validation.json": validation,
        "EMPIRICAL_PILOT_DATA_MANIFEST.json": empirical,
        "REVISED_POPULATION_MANIFEST.json": revised_population,
        "publication_readiness.json": readiness,
        "seed_manifest.json": {
            "version": "0.9.5",
            "sensitivity": sensitivity["seed_manifest"],
            "hoosfield_carbon_core_seed": 9501852,
            "phosphorus_diagnostic_population_hash": population.manifest.population_hash,
            "phosphorus_diagnostic_field_ids": [
                field.field.field_id for field in diagnostic_population.fields
            ],
        },
    }
    for filename, value in outputs.items():
        _write_json(destination / filename, value)
    _write_csv(destination / "horizon_aware_accounting.csv", accounting_rows)
    _write_csv(destination / "phosphorus_ablation.csv", _phosphorus_csv(phosphorus))
    _write_csv(destination / "sensitivity_results.csv", sensitivity_rows)
    _write_csv(destination / "long_term_validation.csv", validation_rows)
    (destination / "hoosfield_soc_trajectories.svg").write_text(
        _trajectory_svg(validation_rows), encoding="utf-8"
    )
    _write_json(destination / "artifact_hashes.json", _hash_artifacts(destination))
    return {
        "output_directory": str(destination),
        "baseline_preserved": baseline["passed"],
        "publication_ready": readiness["passed"],
        "next_task": readiness["exact_next_task"],
    }


def main() -> None:
    """Run from a source checkout with the repository as current directory."""
    print(json.dumps(run_phase95_pipeline(Path.cwd()), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
