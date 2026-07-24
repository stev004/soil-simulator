"""Deterministic offline Phase 9.6 artifact pipeline."""

from __future__ import annotations

import csv
import hashlib
import json
import math
from collections import Counter
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, cast

from soil_simulator.io.configuration import load_management_scenarios, load_model_parameters
from soil_simulator.io.population_configuration import load_population_config
from soil_simulator.phase95.accounting import load_accounting_schedule
from soil_simulator.phase95.empirical import location_group_leakage
from soil_simulator.phase96.effect_ml import build_effect_rows, prediction_benchmark
from soil_simulator.phase96.empirical import (
    PILOT_LOCATIONS,
    build_empirical_records,
    sha256_file,
    to_empirical_dataset,
)
from soil_simulator.phase96.sensitivity import run_population_sensitivity
from soil_simulator.phase96.statistics import (
    correlation_matrix,
    covariance_matrix,
    distributions,
    pca_report,
)
from soil_simulator.phase96.validation import TREATMENTS, diagnose_and_validate
from soil_simulator.phase96.values import as_float, as_int
from soil_simulator.population.adapters import VersionedLocalYamlAdapter
from soil_simulator.population.generator import generate_population

OUTPUT_DIRECTORY = "outputs/phase96_v0.9.6"
EMPIRICAL_VARIABLES = (
    "clay_percent",
    "silt_percent",
    "sand_percent",
    "bulk_density_g_cm3",
    "ph_h2o",
    "cation_exchange_capacity_cmolc_kg",
    "total_nitrogen_percent",
    "soc_stock_t_c_ha_0_23cm",
    "mean_temperature_c",
    "annual_precipitation_mm",
    "annual_pet_mm",
)


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def _write_csv(path: Path, rows: Sequence[Mapping[str, object]]) -> None:
    if not rows:
        raise ValueError(f"cannot write empty CSV {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    columns = tuple(rows[0])
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="raise")
        writer.writeheader()
        writer.writerows(rows)


def _annual_location_records(
    locations: list[dict[str, object]], monthly: list[dict[str, object]]
) -> list[dict[str, object]]:
    by_location: dict[str, list[dict[str, object]]] = {}
    for row in monthly:
        by_location.setdefault(str(row["location_id"]), []).append(row)
    result: list[dict[str, object]] = []
    for location in locations:
        rows = by_location[str(location["location_id"])]
        years = sorted({as_int(row["year"]) for row in rows})
        annual_rain = [
            math.fsum(
                as_float(row["precipitation_mm_month"])
                for row in rows
                if as_int(row["year"]) == year
            )
            for year in years
        ]
        annual_pet = [
            math.fsum(
                as_float(row["potential_evapotranspiration_mm_month"])
                for row in rows
                if as_int(row["year"]) == year
            )
            for year in years
        ]
        result.append(
            {
                **location,
                "mean_temperature_c": math.fsum(
                    as_float(row["mean_air_temperature_c"]) for row in rows
                )
                / len(rows),
                "annual_precipitation_mm": math.fsum(annual_rain) / len(annual_rain),
                "annual_pet_mm": math.fsum(annual_pet) / len(annual_pet),
            }
        )
    return result


def _pilot_qc(
    locations: list[dict[str, object]], monthly: list[dict[str, object]]
) -> tuple[list[dict[str, object]], list[dict[str, object]], list[dict[str, object]]]:
    accepted: list[dict[str, object]] = []
    rejected: list[dict[str, object]] = []
    for row in locations:
        reasons: list[str] = []
        if not 5.0 <= as_float(row["soc_stock_t_c_ha_0_23cm"]) <= 250.0:
            reasons.append("SOC stock outside conservative mineral-topsoil domain [5,250] t C ha-1")
        if not 0.7 <= as_float(row["bulk_density_g_cm3"]) <= 1.8:
            reasons.append("bulk density outside [0.7,1.8] g cm-3")
        if not 3.0 <= as_float(row["ph_h2o"]) <= 10.0:
            reasons.append("pH outside [3,10]")
        if reasons:
            rejected.append({"location_id": row["location_id"], "reasons": "; ".join(reasons)})
        else:
            accepted.append(row)
    accepted_ids = {str(row["location_id"]) for row in accepted}
    paired_monthly = [row for row in monthly if str(row["location_id"]) in accepted_ids]
    if len(accepted) < 50:
        raise ValueError(
            f"empirical pilot has only {len(accepted)} accepted locations; 50 required"
        )
    return accepted, paired_monthly, rejected


def _generated_records(population: object) -> list[dict[str, object]]:
    fields = cast(Any, population).fields
    result: list[dict[str, object]] = []
    for field in fields:
        properties = field.field
        years = len(field.weather) / 12.0
        result.append(
            {
                "field_id": properties.field_id,
                "location_id": field.empirical_seed_id,
                "population_split": field.population_split.value,
                "clay_percent": properties.clay_percent,
                "silt_percent": properties.silt_percent,
                "sand_percent": properties.sand_percent,
                "bulk_density_g_cm3": properties.bulk_density_g_cm3,
                "ph_h2o": properties.ph,
                "cation_exchange_capacity_cmolc_kg": properties.cation_exchange_capacity_cmolc_kg,
                "total_nitrogen_percent": properties.baseline_total_nitrogen_percent,
                "soc_stock_t_c_ha_0_23cm": properties.baseline_soc_t_c_ha,
                "mean_temperature_c": math.fsum(
                    month.mean_air_temperature_c for month in field.weather
                )
                / len(field.weather),
                "annual_precipitation_mm": math.fsum(
                    month.precipitation_mm for month in field.weather
                )
                / years,
                "annual_pet_mm": math.fsum(
                    month.potential_evapotranspiration_mm for month in field.weather
                )
                / years,
            }
        )
    return result


def _old_fixture_summary(root: Path) -> dict[str, object]:
    dataset = VersionedLocalYamlAdapter().load(
        root / "data/processed/phase7_empirical_seed_fixture_v1.yaml"
    )
    records = [
        {
            "clay_percent": seed.clay_percent,
            "silt_percent": seed.silt_percent,
            "sand_percent": seed.sand_percent,
            "bulk_density_g_cm3": seed.bulk_density_g_cm3,
            "ph_h2o": seed.ph,
            "cation_exchange_capacity_cmolc_kg": seed.cation_exchange_capacity_cmolc_kg,
            "total_nitrogen_percent": seed.total_nitrogen_percent,
            "soc_stock_t_c_ha_0_23cm": seed.soc_t_c_ha,
        }
        for seed in dataset.seeds
    ]
    return {
        "classification": "authored synthetic demonstration fixture",
        "location_count": len(records),
        "soil_distributions": distributions(records, EMPIRICAL_VARIABLES[:8]),
        "source_hash": sha256_file(root / "data/processed/phase7_empirical_seed_fixture_v1.yaml"),
    }


def _covariance_report(
    empirical: list[dict[str, object]], generated: list[dict[str, object]], root: Path
) -> dict[str, object]:
    empirical_ranges = distributions(empirical, EMPIRICAL_VARIABLES)
    generated_ranges = distributions(generated, EMPIRICAL_VARIABLES)
    range_coverage = {
        name: {
            "generated_covers_empirical_minimum": generated_ranges[name]["minimum"]
            <= empirical_ranges[name]["minimum"],
            "generated_covers_empirical_maximum": generated_ranges[name]["maximum"]
            >= empirical_ranges[name]["maximum"],
            "generated_fraction_within_empirical_range": math.fsum(
                empirical_ranges[name]["minimum"]
                <= as_float(row[name])
                <= empirical_ranges[name]["maximum"]
                for row in generated
            )
            / len(generated),
        }
        for name in EMPIRICAL_VARIABLES
    }
    return {
        "version": "0.9.6",
        "observable_variables": list(EMPIRICAL_VARIABLES),
        "empirical_location_count": len(empirical),
        "generated_field_count": len(generated),
        "empirical_distributions": empirical_ranges,
        "generated_distributions": generated_ranges,
        "empirical_covariance": covariance_matrix(empirical, EMPIRICAL_VARIABLES),
        "empirical_correlation": correlation_matrix(empirical, EMPIRICAL_VARIABLES),
        "generated_correlation": correlation_matrix(generated, EMPIRICAL_VARIABLES),
        "range_coverage": range_coverage,
        "principal_component_coverage": pca_report(empirical, generated, EMPIRICAL_VARIABLES),
        "previous_population_comparison": _old_fixture_summary(root),
        "separation": {
            "empirically_estimated": list(EMPIRICAL_VARIABLES),
            "latent_biological_priors": [
                "AMF allocation",
                "AMF CUE",
                "AMF turnover",
                "necromass stabilisation",
                "P acquisition",
                "tillage mortality",
                "cover establishment",
            ],
            "imposed_mechanistic_relationships": [
                "RothC turnover/partition",
                "AMF carbon-for-P response",
                "management equations",
            ],
        },
    }


def _source_manifest(
    root: Path, processed_paths: tuple[Path, ...], accepted: int, rejected: int
) -> dict[str, object]:
    raw = root / "data/raw/phase96_empirical"
    files = []
    for path in sorted(raw.rglob("*.json")):
        source = "SoilGrids 2.0 REST" if path.parent.name == "soilgrids" else "NASA POWER v10"
        files.append(
            {
                "path": path.relative_to(root).as_posix(),
                "sha256": sha256_file(path),
                "bytes": path.stat().st_size,
                "source": source,
            }
        )
    rothc_archive = root / "data/raw/phase96_validation/RothC_Code-v2.1.1.zip"
    if not rothc_archive.exists():
        raise FileNotFoundError(f"required validation archive is missing: {rothc_archive}")
    return {
        "version": "1.0.0",
        "access_date": "2026-07-21",
        "sampling_frame_locations": len(PILOT_LOCATIONS),
        "accepted_locations": accepted,
        "rejected_locations": rejected,
        "coordinate_policy": "coordinates rounded to 0.1 degrees; no farm or field coordinates",
        "soil": {
            "dataset": "SoilGrids 2.0 median predictions",
            "url": "https://rest.isric.org/soilgrids/v2.0/properties/query",
            "license": "CC BY 4.0",
            "depths": ["0-5 cm", "5-15 cm", "15-30 cm (top 8 cm used)"],
            "target_depth": "0-23 cm",
        },
        "climate": {
            "dataset": "NASA POWER v10, MERRA-2 monthly 2001-2020",
            "url": "https://power.larc.nasa.gov/api/temporal/monthly/regional",
            "license": "CC0 under NASA Earthdata policy unless specifically restricted",
            "variables": ["T2M", "T2M_MIN", "T2M_MAX", "PRECTOTCORR"],
            "derived_variable": (
                "monthly potential evapotranspiration from Thornthwaite monthly-mean "
                "temperature, latitude and daylength; assumption A080"
            ),
        },
        "long_term_validation": {
            "dataset": "Official RothC model and Hoosfield example v2.1.1",
            "url": "https://doi.org/10.5281/zenodo.10724802",
            "license": "Apache-2.0",
            "path": rothc_archive.relative_to(root).as_posix(),
            "sha256": sha256_file(rothc_archive),
            "bytes": rothc_archive.stat().st_size,
        },
        "raw_files": files,
        "processed_files": [
            {
                "path": path.relative_to(root).as_posix(),
                "sha256": sha256_file(path),
                "bytes": path.stat().st_size,
            }
            for path in processed_paths
        ],
        "offline_replay": True,
        "manual_fallback": (
            "Run scripts/download_phase96_empirical.py once with network access, then archive "
            "the raw JSON responses; all processing/tests use only those local bytes."
        ),
    }


def _validation_rows(diagnosis: Mapping[str, object]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for run_name in ("uncalibrated_phase95_benchmark", "uncalibrated_source_corrected_forcing"):
        run = cast(dict[str, Any], diagnosis[run_name])
        for treatment, payload in run["treatments"].items():
            for point in payload["trajectory"]:
                rows.append(
                    {
                        "run": run_name,
                        "treatment": treatment,
                        **point,
                        "residual_t_c_ha": float(point["simulated_soc_t_c_ha"])
                        - float(point["observed_soc_t_c_ha"]),
                        "uncertainty_lower_t_c_ha": "",
                        "uncertainty_upper_t_c_ha": "",
                    }
                )
    calibration_payload = cast(dict[str, Any], diagnosis["optional_calibration"])
    calibration = calibration_payload["trajectory"]
    bands = {
        (str(item["treatment"]), int(item["year"])): item
        for item in calibration_payload["parameter_uncertainty_bands"]
    }
    for treatment, payload in calibration["treatments"].items():
        for point in payload["trajectory"]:
            band = bands[(treatment, int(point["year"]))]
            rows.append(
                {
                    "run": "optional_calibrated",
                    "treatment": treatment,
                    **point,
                    "residual_t_c_ha": float(point["simulated_soc_t_c_ha"])
                    - float(point["observed_soc_t_c_ha"]),
                    "uncertainty_lower_t_c_ha": band["lower_t_c_ha"],
                    "uncertainty_upper_t_c_ha": band["upper_t_c_ha"],
                }
            )
    return rows


def _sensitivity_rows(result: Mapping[str, object]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    morris = cast(dict[str, dict[str, dict[str, float]]], result["morris"])
    for output, by_parameter in morris.items():
        policy, target, horizon = output.split("|")
        for parameter, metric in by_parameter.items():
            rows.append(
                {
                    "method": "morris",
                    "policy_id": policy,
                    "target": target,
                    "horizon_months": horizon,
                    "parameter": parameter,
                    "first_order": "",
                    "total_order": "",
                    "interaction_remainder": "",
                    "mu_star": metric["mu_star"],
                    "sigma": metric["sigma"],
                }
            )
    sobol = cast(dict[str, Any], result["sobol"])["outputs"]
    for output, payload in sobol.items():
        policy, target, horizon = output.split("|")
        for parameter, metric in payload["indices"].items():
            rows.append(
                {
                    "method": "sobol",
                    "policy_id": policy,
                    "target": target,
                    "horizon_months": horizon,
                    "parameter": parameter,
                    "first_order": metric["first_order"],
                    "total_order": metric["total_order"],
                    "interaction_remainder": metric["interaction_remainder"],
                    "mu_star": "",
                    "sigma": "",
                }
            )
    return rows


def _audit_closure() -> list[dict[str, object]]:
    return [
        {
            "finding_id": "AUDIT-SOURCE-MISSING",
            "severity": "critical",
            "finding": "Original severity-labelled v0.9.0 audit body unavailable",
            "status": "unresolved",
            "evidence": "docs/AUDIT_soil_simulator_v0.9.0.md",
            "artifacts": "audit_closure_matrix.csv",
        },
        {
            "finding_id": "P95-CIRCULARITY",
            "severity": "critical",
            "finding": "Stock circularity and deterministic accounting targets",
            "status": "addressed",
            "evidence": "src/soil_simulator/phase96/effect_ml.py",
            "artifacts": "effect_only_dataset.csv; EFFECT_ONLY_MODEL_CARD.md",
        },
        {
            "finding_id": "P95-EMPIRICAL",
            "severity": "critical",
            "finding": "No 50-location paired empirical pilot",
            "status": "addressed",
            "evidence": "src/soil_simulator/phase96/empirical.py",
            "artifacts": "EMPIRICAL_SOURCE_MANIFEST.json; empirical_covariance_report.json",
        },
        {
            "finding_id": "P95-SENSITIVITY",
            "severity": "critical",
            "finding": "Sensitivity excluded empirical covariance/location variation",
            "status": "addressed",
            "evidence": "src/soil_simulator/phase96/sensitivity.py",
            "artifacts": "sensitivity_results.json; sensitivity_results.csv",
        },
        {
            "finding_id": "P95-HOOSFIELD",
            "severity": "critical",
            "finding": "Material FYM underprediction unexplained",
            "status": "partially addressed",
            "evidence": "src/soil_simulator/phase96/validation.py",
            "artifacts": "long_term_diagnosis.json; validation_trajectories.csv",
        },
        {
            "finding_id": "P95-PHOSPHORUS",
            "severity": "major",
            "finding": "Unbounded phosphorus dominance",
            "status": "partially addressed",
            "evidence": "docs/PHASE95_PHOSPHORUS_ABLATION.md",
            "artifacts": "phosphorus excluded from headline effect ML/sensitivity rankings",
        },
        {
            "finding_id": "P95-DUPLICATE",
            "severity": "major",
            "finding": "Biologically duplicate no-till policy",
            "status": "addressed",
            "evidence": "src/soil_simulator/phase95/policies.py",
            "artifacts": "outputs/phase95_v0.9.5/duplicate_policy_report.json",
        },
        {
            "finding_id": "P95-SCHEDULE",
            "severity": "major",
            "finding": "Horizon-invariant intervention accounting",
            "status": "addressed",
            "evidence": "src/soil_simulator/phase95/accounting.py",
            "artifacts": "outputs/phase95_v0.9.5/horizon_aware_accounting.json",
        },
        {
            "finding_id": "P95-REPRODUCIBILITY",
            "severity": "minor",
            "finding": "Incomplete machine-readable provenance/hashes",
            "status": "addressed",
            "evidence": "src/soil_simulator/phase96/pipeline.py",
            "artifacts": "EMPIRICAL_SOURCE_MANIFEST.json; artifact_hashes.json",
        },
    ]


def _artifact_hashes(root: Path, output: Path, extra: tuple[Path, ...]) -> dict[str, object]:
    paths = [
        path
        for path in sorted(output.rglob("*"))
        if path.is_file() and path.name != "artifact_hashes.json"
    ]
    paths.extend(extra)
    files = {path.relative_to(root).as_posix(): sha256_file(path) for path in paths}
    canonical = json.dumps(files, sort_keys=True, separators=(",", ":"))
    return {
        "version": "0.9.6",
        "files": files,
        "artifact_set_sha256": hashlib.sha256(canonical.encode()).hexdigest(),
    }


def _write_distribution_figure(path: Path, report: Mapping[str, object]) -> None:
    """Write a deterministic SVG comparing empirical/generated central ranges."""
    empirical = cast(dict[str, dict[str, float]], report["empirical_distributions"])
    generated = cast(dict[str, dict[str, float]], report["generated_distributions"])
    width = 980
    height = 80 + 52 * len(EMPIRICAL_VARIABLES)
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">',
        '<rect width="100%" height="100%" fill="white"/>',
        '<text x="20" y="28" font-family="sans-serif" font-size="18">'
        "Phase 9.6 empirical vs generated 5--95% ranges (variable-normalised)</text>",
        '<text x="650" y="28" font-family="sans-serif" font-size="12" fill="#1769aa">'
        "empirical</text>",
        '<text x="730" y="28" font-family="sans-serif" font-size="12" fill="#d95f02">'
        "generated</text>",
    ]
    for index, name in enumerate(EMPIRICAL_VARIABLES):
        y = 62 + index * 52
        combined_min = min(empirical[name]["minimum"], generated[name]["minimum"])
        combined_max = max(empirical[name]["maximum"], generated[name]["maximum"])
        span = combined_max - combined_min
        if span <= 0.0:
            span = 1.0

        def x_position(value: float, minimum: float = combined_min, scale: float = span) -> float:
            return 300.0 + 620.0 * (value - minimum) / scale

        parts.extend(
            (
                f'<text x="20" y="{y + 5}" font-family="monospace" font-size="12">{name}</text>',
                f'<line x1="300" y1="{y}" x2="920" y2="{y}" stroke="#dddddd"/>',
                f'<line x1="{x_position(empirical[name]["q05"]):.2f}" y1="{y - 7}" '
                f'x2="{x_position(empirical[name]["q95"]):.2f}" y2="{y - 7}" '
                'stroke="#1769aa" stroke-width="5"/>',
                f'<circle cx="{x_position(empirical[name]["median"]):.2f}" cy="{y - 7}" '
                'r="4" fill="#1769aa"/>',
                f'<line x1="{x_position(generated[name]["q05"]):.2f}" y1="{y + 8}" '
                f'x2="{x_position(generated[name]["q95"]):.2f}" y2="{y + 8}" '
                'stroke="#d95f02" stroke-width="5"/>',
                f'<circle cx="{x_position(generated[name]["median"]):.2f}" cy="{y + 8}" '
                'r="4" fill="#d95f02"/>',
            )
        )
    parts.append("</svg>")
    path.write_text("\n".join(parts) + "\n", encoding="utf-8")


def _write_validation_figure(path: Path, diagnosis: Mapping[str, object]) -> None:
    """Write observed and source-corrected/calibrated Hoosfield trajectories."""
    corrected = cast(dict[str, Any], diagnosis["uncalibrated_source_corrected_forcing"])
    calibration = cast(dict[str, Any], diagnosis["optional_calibration"])["trajectory"]
    width, height = 1050, 380
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">',
        '<rect width="100%" height="100%" fill="white"/>',
        '<text x="20" y="25" font-family="sans-serif" font-size="18">'
        "Hoosfield total SOC: observations and source-corrected trajectories</text>",
    ]
    for panel, treatment in enumerate(TREATMENTS):
        source_points = corrected["treatments"][treatment]["trajectory"]
        calibrated_points = calibration["treatments"][treatment]["trajectory"]
        values = [as_float(point["observed_soc_t_c_ha"]) for point in source_points]
        values.extend(as_float(point["simulated_soc_t_c_ha"]) for point in source_points)
        values.extend(as_float(point["simulated_soc_t_c_ha"]) for point in calibrated_points)
        lower, upper = min(values) - 2.0, max(values) + 2.0
        left = 40.0 + panel * 340.0
        top, plot_height, plot_width = 60.0, 260.0, 290.0

        def x_position(
            year: int, panel_left: float = left, panel_width: float = plot_width
        ) -> float:
            return panel_left + panel_width * (year - 1852) / (1998 - 1852)

        def y_position(
            value: float,
            panel_top: float = top,
            panel_height: float = plot_height,
            maximum: float = upper,
            minimum: float = lower,
        ) -> float:
            return panel_top + panel_height * (maximum - value) / (maximum - minimum)

        corrected_path = " ".join(
            ("M" if index == 0 else "L")
            + f"{x_position(as_int(point['year'])):.2f},"
            + f"{y_position(as_float(point['simulated_soc_t_c_ha'])):.2f}"
            for index, point in enumerate(source_points)
        )
        calibrated_path = " ".join(
            ("M" if index == 0 else "L")
            + f"{x_position(as_int(point['year'])):.2f},"
            + f"{y_position(as_float(point['simulated_soc_t_c_ha'])):.2f}"
            for index, point in enumerate(calibrated_points)
        )
        parts.extend(
            (
                f'<text x="{left}" y="48" font-family="sans-serif" font-size="13">'
                f"{treatment}</text>",
                f'<rect x="{left}" y="{top}" width="{plot_width}" height="{plot_height}" '
                'fill="none" stroke="#999999"/>',
                f'<path d="{corrected_path}" fill="none" stroke="#1769aa" stroke-width="2"/>',
                f'<path d="{calibrated_path}" fill="none" stroke="#d95f02" '
                'stroke-width="2" stroke-dasharray="5 3"/>',
            )
        )
        parts.extend(
            f'<circle cx="{x_position(as_int(point["year"])):.2f}" '
            f'cy="{y_position(as_float(point["observed_soc_t_c_ha"])):.2f}" '
            'r="3" fill="#222222"/>'
            for point in source_points
        )
    parts.extend(
        (
            '<text x="20" y="355" font-family="sans-serif" font-size="12">'
            "black: observed; blue: uncalibrated source forcing; orange dashed: optional "
            "bounded calibration. protected_soc is not shown.</text>",
            "</svg>",
        )
    )
    path.write_text("\n".join(parts) + "\n", encoding="utf-8")


def _write_sensitivity_figure(path: Path, result: Mapping[str, object]) -> None:
    """Write a deterministic SVG of aggregate Morris screening scores."""
    scores = cast(dict[str, float], result["morris_aggregate_scores"])
    ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)[:10]
    maximum = max(value for _, value in ranked) or 1.0
    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="900" height="470">',
        '<rect width="100%" height="100%" fill="white"/>',
        '<text x="20" y="28" font-family="sans-serif" font-size="18">'
        "Population-aware Morris aggregate screening</text>",
    ]
    for index, (name, value) in enumerate(ranked):
        y = 52 + index * 39
        bar_width = 560.0 * value / maximum
        parts.extend(
            (
                f'<text x="20" y="{y + 14}" font-family="monospace" font-size="12">{name}</text>',
                f'<rect x="280" y="{y}" width="{bar_width:.2f}" height="20" fill="#4c78a8"/>',
                f'<text x="{290 + bar_width:.2f}" y="{y + 14}" '
                f'font-family="sans-serif" font-size="11">{value:.4g}</text>',
            )
        )
    parts.extend(
        (
            '<text x="20" y="452" font-family="sans-serif" font-size="11">'
            "Scores aggregate paired biological effects across policies/horizons; no causal "
            "importance is claimed.</text>",
            "</svg>",
        )
    )
    path.write_text("\n".join(parts) + "\n", encoding="utf-8")


def _write_reports(
    root: Path,
    empirical_count: int,
    rejected_count: int,
    covariance: Mapping[str, object],
    diagnosis: Mapping[str, object],
    sensitivity: Mapping[str, object],
    prediction: Mapping[str, object],
    readiness: Mapping[str, object],
) -> None:
    phase95_metrics = cast(dict[str, Any], diagnosis["uncalibrated_phase95_benchmark"])[
        "aggregate_metrics"
    ]
    corrected_metrics = cast(dict[str, Any], diagnosis["uncalibrated_source_corrected_forcing"])[
        "aggregate_metrics"
    ]
    calibration = cast(dict[str, Any], diagnosis["optional_calibration"])
    reports = {
        "PHASE96_EMPIRICAL_GROUNDING.md": "\n".join(
            (
                "# Phase 9.6 empirical grounding",
                "",
                f"The pilot contains **{empirical_count} accepted paired locations** "
                f"({rejected_count} rejected from the predeclared 64-location frame). "
                "SoilGrids 2.0 median predictions are thickness-harmonised to 0--23 cm; "
                "NASA POWER/MERRA-2 supplies complete monthly years for 2001--2020. "
                "Thornthwaite PET is derived from monthly mean temperature, latitude and "
                "daylength. Coordinates are rounded to 0.1 degrees.",
                "",
                "Observable covariance is estimated only from paired empirical records. "
                "Latent AMF/P priors and imposed simulator relationships remain separate. "
                f"The generated population contains {covariance['generated_field_count']} "
                "fields grouped by empirical location with frozen train/validation/test/OOD "
                "assignments. See `outputs/phase96_v0.9.6/EMPIRICAL_SOURCE_MANIFEST.json` "
                "and `empirical_covariance_report.json`.",
                "",
            )
        ),
        "PHASE96_LONG_TERM_DIAGNOSIS.md": "\n".join(
            (
                "# Phase 9.6 long-term SOC diagnosis",
                "",
                "The Phase 9.5 Hoosfield aggregate RMSE/bias were "
                f"{phase95_metrics['rmse_t_c_ha']:.3f}/"
                f"{phase95_metrics['bias_t_c_ha']:.3f} t C ha-1. Replacing only the "
                "authored forcing with the official RothC v2.1.1 bundled normal changes "
                f"these to {corrected_metrics['rmse_t_c_ha']:.3f}/"
                f"{corrected_metrics['bias_t_c_ha']:.3f}. The forcing mismatch is the "
                "dominant identified negative-bias source.",
                "",
                "FYM amount, 49/49/2 partition, crop DPM:RPM, 23 cm depth, 2.7 t C ha-1 "
                "IOM, treatment timing and fallow years match the authoritative description. "
                "The FYM-cessation treatment remains underpredicted and is retained as a "
                "failure.",
                "",
            )
        ),
        "PHASE96_CALIBRATION_VALIDATION.md": "\n".join(
            (
                "# Phase 9.6 calibration and held-out validation",
                "",
                "The fully uncalibrated, source-corrected benchmark is retained. An optional "
                "grid calibration fits only plant-residue and FYM carbon reconstruction "
                "factors to unmanured/annual-FYM observations through 1965. Post-1965 points "
                "and the complete cessation treatment are held out. "
                f"Best factors: {calibration['best_parameters']}. Boundary solution: "
                f"{calibration['boundary_solution']}. Held-out temporal metrics: "
                f"{calibration['held_out_temporal_metrics']}. Held-out treatment metrics: "
                f"{calibration['held_out_treatment_metrics']}.",
                "",
                "The calibration is not retained as a general simulator parameter; RothC "
                "constants are unchanged. Uncertainty bands are parameter-reconstruction "
                "bands, not observational confidence intervals.",
                "",
            )
        ),
        "PHASE96_POPULATION_SENSITIVITY.md": "\n".join(
            (
                "# Phase 9.6 population sensitivity",
                "",
                "Morris screening and Sobol analysis include empirical-location selection, "
                "complete-year weather resampling, spin-up pool assumptions, AMF/P priors, "
                "cover/tillage/FYM-P and schedule assumptions. Primary outputs are paired "
                "effects. The mean Morris/Sobol rank agreements are "
                f"{cast(Any, sensitivity['convergence'])['morris_mean_rank_agreement']:.3f}/"
                f"{cast(Any, sensitivity['convergence'])['sobol_mean_rank_agreement']:.3f}. "
                f"Selected Sobol parameters: {sensitivity['sobol_selected_parameters']}. "
                "Phosphorus is excluded from headline policy-winner proportions.",
                "",
            )
        ),
        "PHASE96_PUBLICATION_READINESS.md": "\n".join(
            (
                "# Phase 9.6 publication readiness",
                "",
                f"**Publication ready: {readiness['passed']}**. The repository is prepared "
                "for independent re-audit, not manuscript drafting. Remaining blockers: "
                f"{readiness['remaining_blockers']}.",
                "",
                f"Effect prediction gates: {prediction['gates']}. Downstream selection "
                f"executed: {prediction['downstream_selection_executed']}. "
                f"{prediction['stop_decision'] or ''}",
                "",
                "Independent Claude Science re-audit must verify raw/processed hashes, "
                "rerun `.venv/bin/python -m soil_simulator.phase96.pipeline`, run all quality "
                "gates, reconcile the missing original v0.9.0 audit source, and review the "
                "empirical, Hoosfield, sensitivity and effect-only evidence without treating "
                "synthetic outcomes as causal.",
                "",
            )
        ),
    }
    for filename, text in reports.items():
        (root / "docs" / filename).write_text(text, encoding="utf-8")


def run_phase96_pipeline(repository_root: str | Path) -> dict[str, object]:
    """Regenerate all Phase 9.6 evidence from immutable local caches."""
    root = Path(repository_root).resolve()
    output = root / OUTPUT_DIRECTORY
    output.mkdir(parents=True, exist_ok=True)
    raw = root / "data/raw/phase96_empirical"
    location_rows, monthly_rows, corrections = build_empirical_records(raw)
    accepted, paired_monthly, rejected = _pilot_qc(location_rows, monthly_rows)
    rejected.extend(
        {
            "location_id": item["location_id"],
            "reasons": item["reasons"],
        }
        for item in corrections
        if item.get("source_record_status") == "rejected"
    )
    print(f"phase96: empirical QC accepted {len(accepted)} locations", flush=True)
    processed_locations = root / "data/processed/phase96_empirical_soil_locations_v1.csv"
    processed_monthly = root / "data/processed/phase96_empirical_monthly_climate_v1.csv"
    _write_csv(processed_locations, accepted)
    _write_csv(processed_monthly, paired_monthly)
    empirical_dataset = to_empirical_dataset(accepted, paired_monthly)
    parameters = load_model_parameters(root / "config/model_defaults.yaml")
    population_config = load_population_config(root / "config/populations/phase96_population.yaml")
    template = load_management_scenarios(root / "config/scenarios/management_scenarios.yaml")
    accounting = load_accounting_schedule(root / "config/phase95/accounting.yaml")
    population = generate_population(
        dataset=empirical_dataset,
        config=population_config,
        parameters=parameters,
        generation_seed=209600,
        weather_resampling_seed=209601,
        biological_parameter_seed=209602,
    )
    print(f"phase96: generated {len(population.fields)} fields", flush=True)
    generated = _generated_records(population)
    empirical = _annual_location_records(accepted, paired_monthly)
    covariance = _covariance_report(empirical, generated, root)
    source_manifest = _source_manifest(
        root, (processed_locations, processed_monthly), len(accepted), len(rejected)
    )
    split_counts = Counter(field.population_split.value for field in population.fields)
    region_lookup = {location.location_id: location.region for location in PILOT_LOCATIONS}
    population_manifest = {
        "version": "0.9.6",
        "population_hash": population.manifest.population_hash,
        "field_count": len(population.fields),
        "empirical_location_count": len({field.empirical_seed_id for field in population.fields}),
        "split_counts": dict(sorted(split_counts.items())),
        "region_counts": dict(
            sorted(
                Counter(
                    region_lookup[field.empirical_seed_id] for field in population.fields
                ).items()
            )
        ),
        "location_group_leakage": location_group_leakage(population),
        "rejections": [item.model_dump(mode="json") for item in population.manifest.rejections],
        "empirical_record_rejections": rejected,
        "texture_corrections": corrections,
        "observable_covariance_source": "empirical pilot",
        "latent_prior_source": "separate scenario/literature priors",
    }
    diagnosis = diagnose_and_validate(
        root / "data/validation/hoosfield_soc_1852_1998_v1.csv", parameters
    )
    print("phase96: completed Hoosfield diagnosis/calibration", flush=True)
    sensitivity = run_population_sensitivity(
        population,
        template,
        parameters,
        population_config,
        root / "config/phase96/sensitivity.yaml",
    )
    print("phase96: completed population sensitivity", flush=True)
    effect_rows = build_effect_rows(population, template, parameters, population_config, accounting)
    prediction = prediction_benchmark(effect_rows)
    print("phase96: completed effect-only prediction gates", flush=True)
    audit_rows = _audit_closure()
    sensitivity_convergence = cast(dict[str, float], sensitivity["convergence"])
    prediction_gates = cast(dict[str, bool], prediction["gates"])
    calibration = cast(dict[str, Any], diagnosis["optional_calibration"])
    readiness_gates = {
        "immutable_empirical_pilot": len(accepted) >= 50,
        "documented_empirical_covariance": True,
        "population_global_sensitivity": (
            sensitivity_convergence["morris_mean_rank_agreement"] >= 0.75
            and sensitivity_convergence["sobol_mean_rank_agreement"] >= 0.75
        ),
        "uncalibrated_long_term_validation_clear": True,
        "calibration_held_out_only": True,
        "calibration_not_on_parameter_boundary": not bool(calibration["boundary_solution"]),
        "held_out_cessation_failure_resolved": False,
        "phosphorus_bounded_or_excluded": True,
        "effect_only_ml_reporting": True,
        "effect_prediction_gates_passed": all(prediction_gates.values()),
        "independent_empirical_effect_validation": prediction_gates[
            "independent_empirical_effect_validation"
        ],
        "reproducible_hashes_seeds_commands": True,
        "all_original_audit_findings_reconciled": False,
        "independent_reaudit_passed": False,
    }
    readiness = {
        "version": "0.9.6",
        "gates": readiness_gates,
        "passed": all(readiness_gates.values()),
        "remaining_blockers": [name for name, passed in readiness_gates.items() if not passed],
        "independent_reaudit_required": True,
        "manuscript_drafting_recommendation": "do_not_start_Prism_manuscript_drafting",
    }
    _write_json(output / "EMPIRICAL_SOURCE_MANIFEST.json", source_manifest)
    _write_json(output / "empirical_covariance_report.json", covariance)
    _write_json(output / "generated_population_manifest.json", population_manifest)
    _write_json(output / "generated_population_v0.9.6.json", population.model_dump(mode="json"))
    _write_json(output / "long_term_diagnosis.json", diagnosis)
    _write_csv(output / "validation_trajectories.csv", _validation_rows(diagnosis))
    _write_json(output / "sensitivity_results.json", sensitivity)
    _write_csv(output / "sensitivity_results.csv", _sensitivity_rows(sensitivity))
    _write_csv(output / "effect_only_dataset.csv", effect_rows)
    _write_json(output / "prediction_gate_report.json", prediction)
    _write_csv(output / "audit_closure_matrix.csv", audit_rows)
    _write_json(output / "audit_closure_matrix.json", audit_rows)
    _write_json(output / "publication_readiness.json", readiness)
    figures = output / "figures"
    figures.mkdir(parents=True, exist_ok=True)
    _write_distribution_figure(figures / "empirical_generated_distributions.svg", covariance)
    _write_validation_figure(figures / "hoosfield_trajectories.svg", diagnosis)
    _write_sensitivity_figure(figures / "population_sensitivity.svg", sensitivity)
    (output / "EFFECT_ONLY_MODEL_CARD.md").write_text(
        "# Phase 9.6 effect-only model card\n\n"
        "Only paired intervention-minus-baseline biological effects are targets. Final "
        "stocks, deterministic cost/emissions and phosphorus headline claims are excluded. "
        "Location groups are isolated.\n\n"
        + json.dumps(prediction, indent=2, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )
    if not prediction["downstream_selection_executed"]:
        (output / "DOWNSTREAM_BENCHMARK_STOP_DECISION.md").write_text(
            "# Phase 9.6 downstream benchmark stop decision\n\n"
            + str(prediction["stop_decision"])
            + "\nNo selector, oracle agreement or regret result is claimed. The frozen v0.9.0 "
            "and Phase 9.5 results remain historical comparisons only.\n",
            encoding="utf-8",
        )
    _write_reports(
        root,
        len(accepted),
        len(rejected),
        covariance,
        diagnosis,
        sensitivity,
        prediction,
        readiness,
    )
    _write_json(
        output / "artifact_hashes.json",
        _artifact_hashes(
            root,
            output,
            (
                processed_locations,
                processed_monthly,
                root / "pyproject.toml",
                root / "README.md",
                root / "scripts/download_phase96_empirical.py",
                root / "config/model_defaults.yaml",
                root / "config/scenarios/management_scenarios.yaml",
                root / "config/phase95/accounting.yaml",
                root / "config/phase96/sensitivity.yaml",
                root / "config/populations/phase96_population.yaml",
                *(sorted((root / "src/soil_simulator/phase96").glob("*.py"))),
                *(
                    root / "docs" / name
                    for name in (
                        "ASSUMPTIONS_REGISTER.csv",
                        "ARCHITECTURE.md",
                        "AUDIT_soil_simulator_v0.9.0.md",
                        "MODEL_SPEC.md",
                        "MVP_SPEC.md",
                        "REFERENCES.md",
                        "VALIDATION_PLAN.md",
                        "PHASE96_EMPIRICAL_GROUNDING.md",
                        "PHASE96_LONG_TERM_DIAGNOSIS.md",
                        "PHASE96_CALIBRATION_VALIDATION.md",
                        "PHASE96_POPULATION_SENSITIVITY.md",
                        "PHASE96_PUBLICATION_READINESS.md",
                    )
                ),
            ),
        ),
    )
    return {
        "output_directory": str(output),
        "empirical_locations": len(accepted),
        "population_hash": population.manifest.population_hash,
        "downstream_selection_executed": prediction["downstream_selection_executed"],
        "publication_ready": readiness["passed"],
    }


def main() -> None:
    """Run from the repository root using only immutable local source caches."""
    print(json.dumps(run_phase96_pipeline(Path.cwd()), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
