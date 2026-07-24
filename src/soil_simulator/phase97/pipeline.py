"""Deterministic Phase 9.7 targeted audit-closure evidence pipeline."""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, cast

from soil_simulator.domain.population import SyntheticField, SyntheticPopulation
from soil_simulator.io.configuration import load_management_scenarios, load_model_parameters
from soil_simulator.io.population_configuration import load_population_config
from soil_simulator.phase95.accounting import load_accounting_schedule
from soil_simulator.phase95.analysis import sensitivity_evaluator
from soil_simulator.phase95.sensitivity import SensitivityParameter
from soil_simulator.phase96.effect_ml import build_effect_rows, prediction_benchmark
from soil_simulator.phase96.sensitivity import _load_specification, _with_weather_and_spinup
from soil_simulator.phase96.validation import diagnose_and_validate
from soil_simulator.phase97.calibration import calibration_boundary_profile
from soil_simulator.phase97.gates import (
    downstream_gate_evidence,
    empirical_location_leakage_evidence,
    independent_effect_validation_evidence,
    load_optional_independent_dataset,
    uncertainty_coverage_evidence,
)
from soil_simulator.phase97.manifests import (
    canonical_set_digest,
    corrected_phase96_manifest,
    sha256_file,
)
from soil_simulator.phase97.sensitivity import load_phase97_settings, run_nested_sobol

OUTPUT_DIRECTORY = "outputs/phase97_v0.9.7"
HEADLINE_POLICIES = frozenset(
    {"conventional_tillage", "reduced_tillage", "cover_crop", "farmyard_manure"}
)
HEADLINE_TARGETS = frozenset(
    {
        "yield_t_dm_ha|24",
        "total_soc_t_c_ha|60",
        "total_soc_t_c_ha|120",
        "protected_soc_proxy_t_c_ha|60",
        "protected_soc_proxy_t_c_ha|120",
        "respiration_t_c_ha|60",
        "respiration_t_c_ha|120",
    }
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
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=tuple(rows[0]), extrasaction="raise")
        writer.writeheader()
        writer.writerows(rows)


def _load_population(path: Path) -> SyntheticPopulation:
    return SyntheticPopulation.model_validate_json(path.read_text(encoding="utf-8"))


def _selected_parameters(
    phase96_specification: Path, selected_names: tuple[str, ...]
) -> tuple[SensitivityParameter, ...]:
    _, all_parameters = _load_specification(phase96_specification)
    by_name = {parameter.name: parameter for parameter in all_parameters}
    missing = [name for name in selected_names if name not in by_name]
    if missing:
        raise ValueError(f"Phase 9.7 selected parameters are missing from Phase 9.6: {missing}")
    return tuple(by_name[name] for name in selected_names)


def _sensitivity_evaluator(
    population: SyntheticPopulation,
    root: Path,
) -> tuple[tuple[SensitivityParameter, ...], Any]:
    settings = load_phase97_settings(root / "config/phase97/sensitivity.yaml")
    selected = _selected_parameters(
        root / "config/phase96/sensitivity.yaml", settings.selected_parameter_names
    )
    parameters = load_model_parameters(root / "config/model_defaults.yaml")
    population_config = load_population_config(root / "config/populations/phase96_population.yaml")
    template = load_management_scenarios(root / "config/scenarios/management_scenarios.yaml")
    by_location: dict[str, list[SyntheticField]] = defaultdict(list)
    for field in population.fields:
        by_location[field.empirical_seed_id].append(field)
    locations = tuple(sorted(by_location))

    def evaluator(values: Mapping[str, float]) -> Mapping[str, float]:
        location_index = min(
            len(locations) - 1, max(0, round(values.get("empirical_location_index", 0.0)))
        )
        candidates = by_location[locations[location_index]]
        replicate = min(
            len(candidates) - 1,
            max(0, round(values.get("weather_resample_index", 0.0))) % len(candidates),
        )
        field = _with_weather_and_spinup(candidates[replicate], values)
        return sensitivity_evaluator(field, template, parameters, population_config, values)

    return selected, evaluator


def _retained_output(name: str) -> bool:
    parts = name.split("|")
    return (
        len(parts) == 3
        and parts[0] in HEADLINE_POLICIES
        and "|".join(parts[1:]) in HEADLINE_TARGETS
    )


def _index_rows(result: Mapping[str, object]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    estimates = cast(dict[str, dict[str, object]], result["estimates"])
    for size, estimate in sorted(estimates.items(), key=lambda item: int(item[0])):
        outputs = cast(dict[str, dict[str, object]], estimate["outputs"])
        for output, payload in sorted(outputs.items()):
            policy, target, horizon = output.split("|")
            indices = cast(dict[str, dict[str, object]], payload["indices"])
            for parameter, values in sorted(indices.items()):
                first_ci = values["first_order_confidence_interval"]
                total_ci = values["total_order_confidence_interval"]
                first_interval = cast(Sequence[object], first_ci) if first_ci is not None else ()
                total_interval = cast(Sequence[object], total_ci) if total_ci is not None else ()
                rows.append(
                    {
                        "base_sample_size": int(size),
                        "policy_id": policy,
                        "target_name": target,
                        "horizon_months": int(horizon),
                        "parameter": parameter,
                        "first_order": values["first_order"],
                        "first_order_ci_lower": first_interval[0] if first_interval else "",
                        "first_order_ci_upper": first_interval[1] if first_interval else "",
                        "total_order": values["total_order"],
                        "total_order_ci_lower": total_interval[0] if total_interval else "",
                        "total_order_ci_upper": total_interval[1] if total_interval else "",
                        "first_order_negative": values["first_order_negative"],
                        "total_order_negative": values["total_order_negative"],
                        "output_variance": payload["variance"],
                    }
                )
    return rows


def _calibration_rows(profile: Mapping[str, object]) -> list[dict[str, object]]:
    raw = profile.get("profile")
    if not isinstance(raw, list):
        raise ValueError("calibration profile is missing")
    return [cast(dict[str, object], row) for row in raw]


def _closure_rows(
    convergence: Mapping[str, object],
    leakage: Mapping[str, object],
    independent: Mapping[str, object],
    coverage: Mapping[str, object],
    calibration: Mapping[str, object],
) -> list[dict[str, object]]:
    return [
        {
            "finding_id": "P97-INTEGRITY",
            "severity": "critical",
            "finding": "Phase 9.6 audit-document hash mismatch",
            "status": "addressed",
            "evidence": "corrected_phase96_artifact_hashes.json",
        },
        {
            "finding_id": "P97-SOBOL",
            "severity": "critical",
            "finding": "pseudorandom matrices mislabeled as Sobol",
            "status": "addressed",
            "evidence": "sobol_sampling_manifest.json; sensitivity_first_total.json",
        },
        {
            "finding_id": "P97-CONVERGENCE",
            "severity": "critical",
            "finding": "insufficient nested self-consistency convergence",
            "status": (
                "addressed_converged"
                if bool(convergence.get("convergence_reached"))
                else "addressed_not_converged_results_not_final"
            ),
            "evidence": "sensitivity_convergence_manifest.json",
        },
        {
            "finding_id": "P97-LEAKAGE-GATE",
            "severity": "critical",
            "finding": "hardcoded empirical-location leakage gate",
            "status": "addressed" if bool(leakage.get("passed")) else "addressed_gate_failed",
            "evidence": "leakage_check_evidence.json",
        },
        {
            "finding_id": "P97-INDEPENDENT-VALIDATION",
            "severity": "critical",
            "finding": "hardcoded independent empirical effect-validation gate",
            "status": (
                "addressed_gate_passed"
                if bool(independent.get("passed"))
                else "addressed_computed_gate_failed"
            ),
            "evidence": "gate_evidence.json",
        },
        {
            "finding_id": "P97-COVERAGE",
            "severity": "major",
            "finding": "over-broad aggregate uncertainty coverage gate",
            "status": "addressed" if bool(coverage.get("passed")) else "addressed_gate_failed",
            "evidence": "uncertainty_coverage_report.json",
        },
        {
            "finding_id": "P97-CALIBRATION-BOUNDARY",
            "severity": "major",
            "finding": "FYM upper-bound solution insufficiently disclosed",
            "status": (
                "addressed_boundary_retained"
                if bool(calibration.get("boundary_constrained"))
                else "addressed"
            ),
            "evidence": "calibration_profile.json; docs/PHASE97_CALIBRATION_BOUNDARY.md",
        },
        {
            "finding_id": "P97-DOCUMENTATION",
            "severity": "major",
            "finding": "overstated empirical, convergence, validation and readiness claims",
            "status": "addressed",
            "evidence": "docs/PHASE97_PUBLICATION_READINESS.md; README.md",
        },
    ]


def _comparison_rows(
    sensitivity: Mapping[str, object],
    leakage: Mapping[str, object],
    coverage: Mapping[str, object],
    independent: Mapping[str, object],
    downstream: Mapping[str, object],
    calibration: Mapping[str, object],
) -> list[dict[str, object]]:
    sampling = cast(dict[str, object], sensitivity["sampling_manifest"])
    convergence = cast(dict[str, object], sensitivity["convergence"])
    return [
        {
            "dimension": "Sobol sampler",
            "phase96": "ordinary pseudorandom A/B matrices",
            "phase97": sampling["sampler"],
            "phase97_status": "corrected",
        },
        {
            "dimension": "Sobol base samples",
            "phase96": "32",
            "phase97": ",".join(
                str(value) for value in cast(Sequence[object], sampling["base_sample_sizes"])
            ),
            "phase97_status": convergence["status"],
        },
        {
            "dimension": "Leakage gate",
            "phase96": "literal true",
            "phase97": str(leakage.get("passed")),
            "phase97_status": "computed from artifacts",
        },
        {
            "dimension": "Uncertainty coverage",
            "phase96": "aggregate 0.80-1.00 acceptance",
            "phase97": str(coverage.get("passed")),
            "phase97_status": "target/regime-specific binomial rule",
        },
        {
            "dimension": "Independent empirical effect validation",
            "phase96": "literal false",
            "phase97": str(independent.get("passed")),
            "phase97_status": str(independent.get("reason")),
        },
        {
            "dimension": "Downstream execution",
            "phase96": "blocked",
            "phase97": str(downstream.get("selection_regret_executed")),
            "phase97_status": str(downstream.get("decision")),
        },
        {
            "dimension": "FYM calibration",
            "phase96": "boundary_solution=True",
            "phase97": (
                f"estimate={calibration.get('estimate')}; "
                f"range={calibration.get('permitted_range')}"
            ),
            "phase97_status": "boundary explicitly profiled; not general calibration success",
        },
    ]


def _source_manifest(root: Path) -> dict[str, object]:
    phase96_source = cast(
        dict[str, object],
        json.loads(
            (root / "outputs/phase96_v0.9.6/EMPIRICAL_SOURCE_MANIFEST.json").read_text(
                encoding="utf-8"
            )
        ),
    )
    source_paths = [
        root / "config/phase96/sensitivity.yaml",
        root / "config/phase97/sensitivity.yaml",
        root / "config/phase97/runtime_reference.json",
        root / "outputs/phase96_v0.9.6/generated_population_v0.9.6.json",
        root / "outputs/phase96_v0.9.6/effect_only_dataset.csv",
        root / "outputs/phase96_v0.9.6/long_term_diagnosis.json",
        *(sorted((root / "src/soil_simulator/phase97").glob("*.py"))),
    ]
    return {
        "version": "0.9.7",
        "offline_replay": True,
        "phase96_empirical_source_manifest_sha256": sha256_file(
            root / "outputs/phase96_v0.9.6/EMPIRICAL_SOURCE_MANIFEST.json"
        ),
        "phase96_raw_and_processed_sources": phase96_source,
        "phase97_pipeline_sources": {
            path.relative_to(root).as_posix(): sha256_file(path) for path in source_paths
        },
        "independent_effect_dataset": "absent; gate fails closed",
    }


def run_phase97_pipeline(
    repository_root: str | Path, output_directory: str | Path = OUTPUT_DIRECTORY
) -> dict[str, object]:
    """Regenerate all Phase 9.7 correction evidence without changing Phase 9.6 outputs."""
    root = Path(repository_root).resolve()
    output = Path(output_directory)
    if not output.is_absolute():
        output = root / output
    output.mkdir(parents=True, exist_ok=True)
    population = _load_population(root / "outputs/phase96_v0.9.6/generated_population_v0.9.6.json")
    settings = load_phase97_settings(root / "config/phase97/sensitivity.yaml")
    selected, evaluator = _sensitivity_evaluator(population, root)
    sensitivity = run_nested_sobol(selected, evaluator, settings, retained_outputs=_retained_output)
    runtime_reference = cast(
        dict[str, object],
        json.loads((root / "config/phase97/runtime_reference.json").read_text(encoding="utf-8")),
    )
    sampling_manifest = cast(dict[str, object], sensitivity["sampling_manifest"])
    sampling_manifest["runtime_reference"] = runtime_reference
    sampling_manifest.pop("cumulative_evaluation_runtime_seconds", None)
    sampling_manifest.pop("index_runtime_seconds", None)
    sampling_manifest["runtime_replay_note"] = (
        "runtime is measured evidence, not a deterministic scientific result; the frozen "
        "single-worker reference is replayed while current wall time is excluded from hashes"
    )

    parameters = load_model_parameters(root / "config/model_defaults.yaml")
    population_config = load_population_config(root / "config/populations/phase96_population.yaml")
    template = load_management_scenarios(root / "config/scenarios/management_scenarios.yaml")
    accounting = load_accounting_schedule(root / "config/phase95/accounting.yaml")
    effect_rows = build_effect_rows(population, template, parameters, population_config, accounting)
    prediction = prediction_benchmark(effect_rows)
    leakage = empirical_location_leakage_evidence(effect_rows)
    records, metadata = load_optional_independent_dataset(
        root / "data/validation/phase97_independent_effect_metadata.json",
        root / "data/validation/phase97_independent_effect_records.json",
    )
    independent = independent_effect_validation_evidence(records, metadata)
    coverage = uncertainty_coverage_evidence(prediction)
    downstream = downstream_gate_evidence(prediction, leakage, independent, coverage)
    diagnosis = diagnose_and_validate(
        root / "data/validation/hoosfield_soc_1852_1998_v1.csv", parameters
    )
    calibration = calibration_boundary_profile(diagnosis)
    corrected = corrected_phase96_manifest(root)
    comparison = _comparison_rows(
        sensitivity, leakage, coverage, independent, downstream, calibration
    )
    closure = _closure_rows(
        cast(dict[str, object], sensitivity["convergence"]),
        leakage,
        independent,
        coverage,
        calibration,
    )
    source_manifest = _source_manifest(root)
    gate_evidence = {
        "version": "0.9.7",
        "prediction": prediction,
        "leakage": leakage,
        "uncertainty_coverage": coverage,
        "independent_empirical_effect_validation": independent,
        "downstream_execution": downstream,
    }
    readiness_gates = {
        "artifact_integrity": True,
        "genuine_sobol_design": True,
        "sensitivity_converged": bool(
            cast(dict[str, object], sensitivity["convergence"])["convergence_reached"]
        ),
        "leakage_checks_passed": bool(leakage["passed"]),
        "prediction_gates_passed": all(
            bool(value)
            for key, value in cast(dict[str, object], prediction["gates"]).items()
            if key
            in {"all_effect_targets_beat_policy_mean", "all_effect_targets_have_acceptable_ood"}
        ),
        "target_specific_uncertainty": bool(coverage["passed"]),
        "independent_empirical_effect_validation": bool(independent["passed"]),
        "calibration_not_boundary_constrained": not bool(calibration["boundary_constrained"]),
        "held_out_cessation_performance_adequate": False,
        "focused_independent_reaudit_passed": False,
    }
    readiness = {
        "version": "0.9.7",
        "passed": all(readiness_gates.values()),
        "gates": readiness_gates,
        "remaining_blockers": [name for name, passed in readiness_gates.items() if not passed],
        "downstream_selection_blocked": not bool(downstream["eligible"]),
        "publication_readiness": {
            "agricultural_prediction_paper": "not_ready",
            "methodological_paper": "potentially_supportable_after_focused_reaudit",
            "software_simulator_paper": "potentially_supportable_after_focused_reaudit",
            "portfolio_case_study": "supported_with_current_claim_boundaries",
        },
        "prism_manuscript_drafting": "do_not_start_before_focused_independent_reaudit",
    }

    _write_json(output / "source_manifest.json", source_manifest)
    _write_json(output / "corrected_phase96_artifact_hashes.json", corrected)
    _write_json(output / "sobol_sampling_manifest.json", sensitivity["sampling_manifest"])
    _write_json(output / "sensitivity_convergence_manifest.json", sensitivity["convergence"])
    _write_json(output / "sensitivity_first_total.json", sensitivity)
    _write_csv(output / "sensitivity_first_total.csv", _index_rows(sensitivity))
    _write_json(output / "gate_evidence.json", gate_evidence)
    _write_json(output / "leakage_check_evidence.json", leakage)
    _write_json(output / "uncertainty_coverage_report.json", coverage)
    _write_json(output / "calibration_profile.json", calibration)
    _write_csv(output / "calibration_profile.csv", _calibration_rows(calibration))
    _write_json(output / "phase96_vs_phase97_comparison.json", comparison)
    _write_csv(output / "phase96_vs_phase97_comparison.csv", comparison)
    _write_json(output / "audit_closure_matrix.json", closure)
    _write_csv(output / "audit_closure_matrix.csv", closure)
    _write_json(output / "publication_readiness.json", readiness)
    pipeline_manifest = {
        "version": "0.9.7",
        "command": ".venv/bin/python -m soil_simulator.phase97.pipeline",
        "output_directory": OUTPUT_DIRECTORY,
        "phase96_outputs_modified": False,
        "historical_v0_9_0_outputs_modified": False,
        "selection_regret_executed": bool(downstream["selection_regret_executed"]),
        "source_manifest_sha256": sha256_file(output / "source_manifest.json"),
        "sampling_manifest_sha256": sha256_file(output / "sobol_sampling_manifest.json"),
        "gate_evidence_sha256": sha256_file(output / "gate_evidence.json"),
    }
    _write_json(output / "pipeline_manifest.json", pipeline_manifest)
    documentation = [
        root / "README.md",
        root / "docs/ASSUMPTIONS_REGISTER.csv",
        root / "docs/AUDIT_soil_simulator_v0.9.0.md",
        root / "docs/PHASE97_AUDIT_CLOSURE.md",
        root / "docs/PHASE97_SENSITIVITY_CORRECTION.md",
        root / "docs/PHASE97_GATE_CORRECTION.md",
        root / "docs/PHASE97_CALIBRATION_BOUNDARY.md",
        root / "docs/PHASE97_PUBLICATION_READINESS.md",
    ]
    artifacts = [
        path
        for path in sorted(output.iterdir())
        if path.is_file() and path.name != "artifact_hashes.json"
    ]
    artifacts.extend(documentation)
    artifacts.extend(
        [
            root / "config/phase97/sensitivity.yaml",
            root / "config/phase97/runtime_reference.json",
            root / "pyproject.toml",
            root / "uv.lock",
            *(sorted((root / "src/soil_simulator/phase97").glob("*.py"))),
        ]
    )
    artifact_files: dict[str, str] = {}
    for path in artifacts:
        logical = (
            f"{OUTPUT_DIRECTORY}/{path.name}"
            if path.parent == output
            else path.relative_to(root).as_posix()
        )
        artifact_files[logical] = sha256_file(path)
    _write_json(
        output / "artifact_hashes.json",
        {
            "version": "0.9.7",
            "files": dict(sorted(artifact_files.items())),
            "artifact_set_sha256": canonical_set_digest(artifact_files),
        },
    )
    return {
        "output_directory": str(output),
        "convergence_reached": cast(dict[str, object], sensitivity["convergence"])[
            "convergence_reached"
        ],
        "leakage_gate": leakage["passed"],
        "independent_validation_gate": independent["passed"],
        "uncertainty_gate": coverage["passed"],
        "downstream_selection_executed": downstream["selection_regret_executed"],
        "publication_ready": readiness["passed"],
    }


def main() -> None:
    """Run the Phase 9.7 offline evidence pipeline from the repository root."""
    print(json.dumps(run_phase97_pipeline(Path.cwd()), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
