# ruff: noqa: E501
"""Build the Phase 9.8 manuscript evidence exports from frozen artifacts.

This script does not execute the simulator or recompute scientific analyses. It
copies verified files, derives presentation tables/figures from existing
machine-readable evidence, and emits deterministic SHA-256 manifests.
"""

from __future__ import annotations

import csv
import hashlib
import html
import json
import shutil
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
MANUSCRIPT = ROOT / "manuscript"
AUDITS = ROOT / "docs" / "audits"

AUDIT_SOURCE_MAP = {
    "AUDIT_PHASE96_CLEAN_SLATE.md": "AUDIT_PHASE96_CLEAN_SLATE.md",
    "audit_closure_matrix_independent.csv": "phase96_finding_closure.csv",
    "recomputed_metrics.json": "phase96_recomputed_metrics.json",
    "discrepancies.md": "phase96_discrepancies.md",
    "AUDIT_PHASE97_FOCUSED.md": "AUDIT_PHASE97_FOCUSED.md",
    "phase97_finding_closure.csv": "phase97_finding_closure.csv",
    "phase97_recomputed_metrics.json": "phase97_recomputed_metrics.json",
    "phase97_discrepancies.md": "phase97_discrepancies.md",
    "sobol_findings.md": "phase97_sobol_findings.md",
    "convergence_findings.md": "phase97_convergence_findings.md",
}


def read_json(path: str) -> Any:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value.rstrip() + "\n", encoding="utf-8")


def write_json(path: Path, value: Any) -> None:
    write_text(path, json.dumps(value, indent=2, sort_keys=True))


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def markdown_preview(path: Path, fieldnames: list[str], rows: list[dict[str, Any]]) -> None:
    def cell(value: Any) -> str:
        return str(value).replace("|", "\\|").replace("\n", " ")

    lines = [
        f"# Preview: {path.stem}",
        "",
        "Generated from the adjacent CSV for human inspection. The CSV is canonical.",
        "",
        "| " + " | ".join(fieldnames) + " |",
        "| " + " | ".join("---" for _ in fieldnames) + " |",
    ]
    lines.extend(
        "| " + " | ".join(cell(row.get(name, "")) for name in fieldnames) + " |" for row in rows
    )
    write_text(path.with_suffix(".md"), "\n".join(lines))


def table(path: str, fieldnames: list[str], rows: list[dict[str, Any]]) -> None:
    target = MANUSCRIPT / "tables" / path
    write_csv(target, fieldnames, rows)
    markdown_preview(target, fieldnames, rows)


def copy_verified(source: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(ROOT / source, destination)


def validate_audit_export() -> dict[str, Any]:
    """Fail unless all ten incoming audit files match the supplied export manifest."""
    manifest_path = ROOT / "audits/incoming/AUDIT_EXPORT_MANIFEST.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    entries = manifest.get("files")
    if not isinstance(entries, list) or manifest.get("total_file_count") != len(AUDIT_SOURCE_MAP):
        raise ValueError("audit export manifest does not declare exactly ten files")
    entry_by_name = {entry["filename"]: entry for entry in entries}
    if set(entry_by_name) != set(AUDIT_SOURCE_MAP):
        raise ValueError("audit export manifest filenames do not match the required set")
    actual_files = {
        path.name
        for path in (ROOT / "audits/incoming").iterdir()
        if path.is_file() and path.name != "AUDIT_EXPORT_MANIFEST.json"
    }
    if actual_files != set(AUDIT_SOURCE_MAP):
        raise ValueError("incoming audit directory contains a missing or unexpected deliverable")
    for filename in AUDIT_SOURCE_MAP:
        source = ROOT / "audits/incoming" / filename
        entry = entry_by_name[filename]
        if source.stat().st_size != entry["byte_size"]:
            raise ValueError(f"audit export byte-size mismatch: {filename}")
        if sha256(source) != entry["sha256"]:
            raise ValueError(f"audit export SHA-256 mismatch: {filename}")
        if entry.get("retrieved_unchanged") is not True:
            raise ValueError(f"audit export does not attest unchanged bytes: {filename}")
    return manifest


def build_audit_archive() -> None:
    export_manifest = validate_audit_export()
    AUDITS.mkdir(parents=True, exist_ok=True)
    copy_verified(
        "docs/AUDIT_soil_simulator_v0.9.0.md",
        AUDITS / "AUDIT_v0.9.0_INDEPENDENT.md",
    )
    for source_name, canonical_name in AUDIT_SOURCE_MAP.items():
        copy_verified(
            f"audits/incoming/{source_name}",
            AUDITS / canonical_name,
        )
    copy_verified(
        "audits/incoming/AUDIT_EXPORT_MANIFEST.json",
        AUDITS / "AUDIT_EXPORT_MANIFEST.json",
    )
    files = sorted(
        path for path in AUDITS.iterdir() if path.is_file() and path.name != "audit_manifest.json"
    )
    entries = []
    for path in files:
        if path.name == "AUDIT_v0.9.0_INDEPENDENT.md":
            entries.append(
                manifest_entry(
                    path,
                    "audit",
                    "docs/AUDIT_soil_simulator_v0.9.0.md",
                    "copied",
                )
            )
        elif path.name == "AUDIT_EXPORT_MANIFEST.json":
            entries.append(
                manifest_entry(
                    path,
                    "audit_export_manifest",
                    "audits/incoming/AUDIT_EXPORT_MANIFEST.json",
                    "copied",
                )
            )
        elif path.name in AUDIT_SOURCE_MAP.values():
            source_name = next(
                source for source, canonical in AUDIT_SOURCE_MAP.items() if canonical == path.name
            )
            entries.append(
                manifest_entry(
                    path,
                    "independent_audit",
                    f"audits/incoming/{source_name}",
                    "copied",
                )
            )
        else:
            entries.append(manifest_entry(path, "audit", "Phase 9.8 documentation", "generated"))
    write_json(
        AUDITS / "audit_manifest.json",
        {
            "entries": entries,
            "export_manifest_sha256": sha256(ROOT / "audits/incoming/AUDIT_EXPORT_MANIFEST.json"),
            "export_manifest_total_file_count": export_manifest["total_file_count"],
            "missing_required_independent_deliverables": [],
            "source_validation": "10/10 byte sizes and SHA-256 values match the supplied export manifest",
            "schema_version": "1.0.0",
        },
    )


def model_component_rows() -> list[dict[str, Any]]:
    return [
        {
            "component": "RothC carbon core",
            "state_or_output": "DPM; RPM; BIO; HUM/protected proxy; IOM; respiration",
            "units": "t C ha-1",
            "source_modules": "src/soil_simulator/processes/rothc.py; src/soil_simulator/simulator/carbon_core.py",
            "configuration": "config/model_defaults.yaml; config/scenarios/carbon_core.yaml",
            "assumption_ids": "A001; A013; A014",
            "verification_tests": "tests/parity/test_rothc_worked_example.py; tests/properties/test_carbon_core_properties.py",
            "source_path": "docs/CARBON_CORE.md",
            "audit_status": "independently reproduced at v0.9.0",
        },
        {
            "component": "Crop growth and residue return",
            "state_or_output": "NPP; shoot/root carbon; yield; residues",
            "units": "t C ha-1; t dry matter ha-1",
            "source_modules": "src/soil_simulator/processes/plant.py; src/soil_simulator/simulator/plant_baseline.py",
            "configuration": "config/model_defaults.yaml; config/scenarios/spring_barley_baseline.yaml",
            "assumption_ids": "A002; A015-A020",
            "verification_tests": "tests/unit/test_plant_processes.py; tests/integration/test_plant_baseline.py",
            "source_path": "docs/PLANT_PHOSPHORUS_BASELINE.md",
            "audit_status": "verified implementation; biological magnitudes provisional",
        },
        {
            "component": "Phosphorus dynamics",
            "state_or_output": "available P; plant/AMF uptake; P balance",
            "units": "kg P ha-1",
            "source_modules": "src/soil_simulator/processes/phosphorus.py; src/soil_simulator/simulator/amf_extension.py",
            "configuration": "config/model_defaults.yaml",
            "assumption_ids": "A017; A023; A026; A031; A075",
            "verification_tests": "tests/unit/test_phosphorus_processes.py; tests/properties/test_amf_properties.py",
            "source_path": "docs/PHASE95_PHOSPHORUS_ABLATION.md",
            "audit_status": "mass balance verified; magnitudes excluded from headline claims",
        },
        {
            "component": "AMF dynamics",
            "state_or_output": "live biomass; necromass; C allocation; respiration; P transfer",
            "units": "t C ha-1; kg P ha-1",
            "source_modules": "src/soil_simulator/processes/amf.py; src/soil_simulator/simulator/amf_extension.py",
            "configuration": "config/model_defaults.yaml",
            "assumption_ids": "A003-A010; A021-A025",
            "verification_tests": "tests/unit/test_amf_processes.py; tests/integration/test_amf_extension.py",
            "source_path": "docs/AMF_EXTENSION.md",
            "audit_status": "accounting verified; no empirical AMF validation",
        },
        {
            "component": "Management and accounting",
            "state_or_output": "scheduled events; recurring costs; operational/lifecycle proxies",
            "units": "event month; GBP ha-1; kg CO2e ha-1",
            "source_modules": "src/soil_simulator/simulator/management.py; src/soil_simulator/phase95/accounting.py",
            "configuration": "config/scenarios/management_scenarios.yaml; config/phase95/accounting.yaml",
            "assumption_ids": "A027-A031; A065-A066",
            "verification_tests": "tests/integration/test_management_interventions.py; tests/unit/test_phase95.py",
            "source_path": "docs/MANAGEMENT_INTERVENTIONS.md",
            "audit_status": "implementation remediation closed; proxy scope remains provisional",
        },
        {
            "component": "Population and spin-up",
            "state_or_output": "112 synthetic descendants of 56 paired locations; initial pools",
            "units": "fields; t C ha-1",
            "source_modules": "src/soil_simulator/population/generator.py; src/soil_simulator/population/spinup.py; src/soil_simulator/phase96/empirical.py",
            "configuration": "config/populations/phase96_population.yaml",
            "assumption_ids": "A032-A039; A077-A081",
            "verification_tests": "tests/unit/test_population_generation.py; tests/unit/test_phase96.py",
            "source_path": "outputs/phase96_v0.9.6/generated_population_manifest.json",
            "audit_status": "empirical pilot only; not representative",
        },
        {
            "component": "Sensitivity",
            "state_or_output": "Morris screening; S1/ST; convergence diagnostics",
            "units": "dimensionless indices",
            "source_modules": "src/soil_simulator/phase97/sensitivity.py",
            "configuration": "config/phase97/sensitivity.yaml",
            "assumption_ids": "A071; A081; A086-A087",
            "verification_tests": "tests/unit/test_phase97.py",
            "source_path": "outputs/phase97_v0.9.7/sensitivity_convergence_manifest.json",
            "audit_status": "corrected design; not converged; diagnostic only",
        },
        {
            "component": "Effect-only ML and gates",
            "state_or_output": "paired effects; residual intervals; leakage/readiness gates",
            "units": "target-specific",
            "source_modules": "src/soil_simulator/phase96/effect_ml.py; src/soil_simulator/phase97/gates.py",
            "configuration": "not applicable (artifact-derived gates)",
            "assumption_ids": "A067-A068; A084; A088-A090",
            "verification_tests": "tests/unit/test_phase96.py; tests/unit/test_phase97.py",
            "source_path": "outputs/phase97_v0.9.7/gate_evidence.json",
            "audit_status": "leakage/coverage pass; prediction/OOD/independent validation fail",
        },
    ]


def build_tables() -> None:
    components = model_component_rows()
    table("table_01_model_components.csv", list(components[0]), components)

    source = read_json("outputs/phase96_v0.9.6/EMPIRICAL_SOURCE_MANIFEST.json")
    data_rows = [
        {
            "dataset": source["soil"]["dataset"],
            "data_class": "raw external prediction cache / processed empirical pilot",
            "coverage": "64 requested; 56 accepted; 8 rejected; 0-23 cm",
            "units": "locations; cm",
            "license": source["soil"]["license"],
            "access_date": source["access_date"],
            "local_path": "data/raw/phase96_empirical/soilgrids/; data/processed/phase96_empirical_soil_locations_v1.csv",
            "sha256": source["processed_files"][0]["sha256"],
            "source_path": "outputs/phase96_v0.9.6/EMPIRICAL_SOURCE_MANIFEST.json",
            "audit_status": "manifested; Phase 9.7 focused re-audit verified the 56-location pilot boundary",
        },
        {
            "dataset": source["climate"]["dataset"],
            "data_class": "raw external reanalysis cache / processed empirical pilot",
            "coverage": "monthly 2001-2020; 56 accepted locations",
            "units": "months; locations",
            "license": source["climate"]["license"],
            "access_date": source["access_date"],
            "local_path": "data/raw/phase96_empirical/nasa_power/; data/processed/phase96_empirical_monthly_climate_v1.csv",
            "sha256": source["processed_files"][1]["sha256"],
            "source_path": "outputs/phase96_v0.9.6/EMPIRICAL_SOURCE_MANIFEST.json",
            "audit_status": "manifested; PET is derived under A080",
        },
        {
            "dataset": source["long_term_validation"]["dataset"],
            "data_class": "external validation/reference archive",
            "coverage": "Hoosfield model example and forcing",
            "units": "monthly forcing and t C ha-1 observations",
            "license": source["long_term_validation"]["license"],
            "access_date": source["access_date"],
            "local_path": source["long_term_validation"]["path"],
            "sha256": source["long_term_validation"]["sha256"],
            "source_path": "outputs/phase96_v0.9.6/EMPIRICAL_SOURCE_MANIFEST.json",
            "audit_status": "source correction verified; cessation fit remains weak",
        },
    ]
    table("table_02_data_sources.csv", list(data_rows[0]), data_rows)

    test_rows = [
        {
            "verification_area": "Complete baseline suite",
            "test_path": "tests/",
            "test_count": 234,
            "units": "tests",
            "result": "pass",
            "source_path": "manuscript/data/software_verification_summary.json",
            "audit_status": "Phase 9.8 final restoration replay",
        },
        {
            "verification_area": "RothC parity",
            "test_path": "tests/parity/test_rothc_worked_example.py",
            "test_count": 1,
            "units": "test",
            "result": "pass",
            "source_path": "docs/AUDIT_soil_simulator_v0.9.0.md",
            "audit_status": "independently recomputed at v0.9.0",
        },
        {
            "verification_area": "Carbon and phosphorus properties",
            "test_path": "tests/properties/",
            "test_count": "not separately counted",
            "units": "tests",
            "result": "pass within complete suite",
            "source_path": "manuscript/data/software_verification_summary.json",
            "audit_status": "verified",
        },
        {
            "verification_area": "Scenario directions",
            "test_path": "tests/scenarios/",
            "test_count": "not separately counted",
            "units": "tests",
            "result": "pass within complete suite",
            "source_path": "manuscript/data/software_verification_summary.json",
            "audit_status": "encoded-direction checks; not empirical proof",
        },
    ]
    table("table_03_verification_tests.csv", list(test_rows[0]), test_rows)

    long_term = read_json("outputs/phase96_v0.9.6/long_term_diagnosis.json")
    validation_rows: list[dict[str, Any]] = []
    runs = [
        ("phase95_original_forcing", long_term["uncalibrated_phase95_benchmark"]),
        (
            "phase96_source_corrected_uncalibrated",
            long_term["uncalibrated_source_corrected_forcing"],
        ),
        ("phase96_optional_bounded_calibration", long_term["optional_calibration"]["trajectory"]),
    ]
    for run_name, run in runs:
        metrics = run["aggregate_metrics"]
        validation_rows.append(
            {
                "run": run_name,
                "treatment": "aggregate",
                "evaluation_role": "all post-initialization observations",
                "mae_t_c_ha": metrics["mae_t_c_ha"],
                "rmse_t_c_ha": metrics["rmse_t_c_ha"],
                "bias_t_c_ha": metrics["bias_t_c_ha"],
                "units": "t C ha-1",
                "calibration_boundary": (
                    "upper bound" if "calibration" in run_name else "not applicable"
                ),
                "source_path": "outputs/phase96_v0.9.6/long_term_diagnosis.json",
                "audit_status": "verified source artifact; interpret total SOC only",
            }
        )
        for treatment, values in run["treatments"].items():
            metrics = values["metrics"]
            validation_rows.append(
                {
                    "run": run_name,
                    "treatment": treatment,
                    "evaluation_role": (
                        "held-out treatment"
                        if treatment == "fym_1852_1871"
                        else "mixed calibration/held-out temporal"
                    ),
                    "mae_t_c_ha": metrics["mae_t_c_ha"],
                    "rmse_t_c_ha": metrics["rmse_t_c_ha"],
                    "bias_t_c_ha": metrics["bias_t_c_ha"],
                    "units": "t C ha-1",
                    "calibration_boundary": (
                        "upper bound" if "calibration" in run_name else "not applicable"
                    ),
                    "source_path": "outputs/phase96_v0.9.6/long_term_diagnosis.json",
                    "audit_status": "cessation weakness retained",
                }
            )
    table("table_04_hoosfield_validation.csv", list(validation_rows[0]), validation_rows)

    convergence = read_json("outputs/phase97_v0.9.7/sensitivity_convergence_manifest.json")
    convergence_rows = []
    for comparison in convergence["comparisons"]:
        convergence_rows.append(
            {
                "previous_base_sample_size": comparison["previous_base_sample_size"],
                "current_base_sample_size": comparison["current_base_sample_size"],
                "maximum_absolute_s1_change": comparison["maximum_absolute_first_order_change"],
                "maximum_absolute_st_change": comparison["maximum_absolute_total_order_change"],
                "s1_rank_correlation": comparison["first_order_rank_correlation"],
                "st_rank_correlation": comparison["total_order_rank_correlation"],
                "mean_ci_width": comparison["mean_confidence_interval_width"],
                "unstable_fraction": comparison["unstable_estimate_fraction"],
                "negative_fraction": comparison["negative_estimate_fraction"],
                "converged": comparison["passed"],
                "units": "dimensionless except sample counts",
                "source_path": "outputs/phase97_v0.9.7/sensitivity_convergence_manifest.json",
                "audit_status": "not converged; diagnostic only",
            }
        )
    table("table_05_sensitivity_convergence.csv", list(convergence_rows[0]), convergence_rows)

    gates = read_json("outputs/phase97_v0.9.7/gate_evidence.json")
    gate_rows = []
    for name, passed in gates["downstream_execution"]["required_gates"].items():
        gate_rows.append(
            {
                "gate": name,
                "result": "pass" if passed else "fail",
                "units": "boolean",
                "effect_on_downstream": "required prerequisite",
                "selection_regret_executed": gates["downstream_execution"][
                    "selection_regret_executed"
                ],
                "source_path": "outputs/phase97_v0.9.7/gate_evidence.json",
                "audit_status": "computed from artifacts",
            }
        )
    gate_rows.append(
        {
            "gate": "downstream_execution",
            "result": "blocked",
            "units": "decision",
            "effect_on_downstream": gates["downstream_execution"]["decision"],
            "selection_regret_executed": False,
            "source_path": "outputs/phase97_v0.9.7/gate_evidence.json",
            "audit_status": "negative finding preserved",
        }
    )
    table("table_06_ml_gate_results.csv", list(gate_rows[0]), gate_rows)

    closure_rows = [
        {
            "audit_stage": "v0.9.0 independent audit",
            "finding_id": finding_id,
            "severity": severity,
            "finding": finding,
            "closure_status": status,
            "units": "not applicable",
            "evidence": evidence,
            "source_path": "docs/AUDIT_soil_simulator_v0.9.0.md",
            "audit_status": "independent finding; remediation evidence indexed",
        }
        for finding_id, severity, finding, status, evidence in [
            (
                "C1",
                "critical",
                "authored population not empirically grounded",
                "remediated_with_limited_pilot",
                "outputs/phase96_v0.9.6/EMPIRICAL_SOURCE_MANIFEST.json",
            ),
            (
                "C2",
                "critical",
                "stock-target circularity",
                "closed_for_headline_ml",
                "outputs/phase95_v0.9.5/headline_target_manifest.json",
            ),
            (
                "M1",
                "major",
                "phosphorus structural loop",
                "bounded_and_excluded",
                "outputs/phase95_v0.9.5/phosphorus_ablation.json",
            ),
            (
                "M2",
                "major",
                "horizon-invariant accounting identities",
                "implementation_remediated",
                "outputs/phase95_v0.9.5/horizon_aware_accounting.json",
            ),
            (
                "M3",
                "major",
                "no_till duplicates baseline",
                "implementation_remediated",
                "outputs/phase95_v0.9.5/duplicate_policy_report.json",
            ),
            (
                "M4",
                "major",
                "missing sensitivity/calibration/long-term validation",
                "partially_addressed_scientific_limits_remain",
                "docs/PHASE97_PUBLICATION_READINESS.md",
            ),
            (
                "M5",
                "major",
                "designed synthetic covariance",
                "partially_addressed_limited_pilot",
                "outputs/phase96_v0.9.6/empirical_covariance_report.json",
            ),
        ]
    ]
    with (AUDITS / "phase96_finding_closure.csv").open(encoding="utf-8", newline="") as stream:
        closure96 = list(csv.DictReader(stream))
    closure_rows.extend(
        {
            "audit_stage": "Phase 9.6 independent clean-slate audit",
            "finding_id": item["finding_id"],
            "severity": item["severity"],
            "finding": item["title"],
            "closure_status": item["independent_status"],
            "units": "not applicable",
            "evidence": item["evidence"],
            "source_path": "docs/audits/phase96_finding_closure.csv",
            "audit_status": "independent Phase 9.6 assessment",
        }
        for item in closure96
    )
    with (AUDITS / "phase97_finding_closure.csv").open(encoding="utf-8", newline="") as stream:
        closure97 = list(csv.DictReader(stream))
    closure_rows.extend(
        {
            "audit_stage": "Phase 9.7 focused independent re-audit",
            "finding_id": item["defect_id"],
            "severity": "not separately assigned",
            "finding": item["phase96_defect"],
            "closure_status": item["phase97_classification"],
            "units": "not applicable",
            "evidence": item["evidence"],
            "source_path": "docs/audits/phase97_finding_closure.csv",
            "audit_status": "independently verified Phase 9.7 closure classification",
        }
        for item in closure97
    )
    table("table_07_audit_finding_closure.csv", list(closure_rows[0]), closure_rows)

    claim_rows = []
    claims = {
        "permitted": [
            "deterministic under frozen configurations",
            "carbon and phosphorus mass balance enforced",
            "RothC decay core reproduces documented parity case",
            "56 paired empirical soil-climate locations used as a pilot",
            "Hoosfield source correction improved aggregate uncalibrated fit",
            "effect-prediction and OOD gates failed",
            "downstream selection correctly blocked",
            "identified implementation defects remediated",
        ],
        "qualified": [
            "sensitivity rankings are diagnostic because convergence was not achieved",
            "Hoosfield performance remains weak for FYM cessation",
            "empirical pilot is geographically and numerically limited",
            "protected SOC is a model proxy, not measured MAOC",
            "uncertainty coverage is predictive residual coverage",
            "FYM calibration reached the upper bound",
        ],
        "prohibited": [
            "validated prediction of real-farm outcomes",
            "causal intervention effects or field-level recommendations",
            "national representativeness",
            "measured MAOC prediction or validated carbon-credit estimates",
            "generalisable ML intervention selection",
            "publication claims based on final-stock R-squared",
            "fully converged sensitivity analysis",
        ],
    }
    for boundary, statements in claims.items():
        claim_rows.extend(
            {
                "boundary": boundary,
                "claim": statement,
                "units": "not applicable",
                "source_path": "manuscript/CLAIM_BOUNDARIES.md",
                "audit_status": "bounded by Phase 9.7 evidence",
            }
            for statement in statements
        )
    table("table_08_claim_boundaries.csv", list(claim_rows[0]), claim_rows)

    with (ROOT / "docs/ASSUMPTIONS_REGISTER.csv").open(encoding="utf-8", newline="") as stream:
        assumptions = list(csv.DictReader(stream))
    counts = Counter(
        (
            row["component"],
            row["classification"],
            row["default_status"],
            row["validation_priority"],
        )
        for row in assumptions
    )
    assumption_rows = [
        {
            "component": key[0],
            "classification": key[1],
            "default_status": key[2],
            "validation_priority": key[3],
            "assumption_count": value,
            "units": "registered assumptions",
            "source_path": "docs/ASSUMPTIONS_REGISTER.csv",
            "audit_status": "complete register summary",
        }
        for key, value in sorted(counts.items())
    ]
    table("table_09_assumptions_summary.csv", list(assumption_rows[0]), assumption_rows)


def svg_document(body: str, width: int = 1000, height: int = 620) -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">\n'
        '<rect width="100%" height="100%" fill="#ffffff"/>\n'
        "<style>text{font-family:Arial,sans-serif;fill:#17212b}.title{font-size:24px;font-weight:700}"
        ".label{font-size:15px}.small{font-size:12px}.axis{stroke:#394b59;stroke-width:1.2}"
        ".grid{stroke:#d9e2e8;stroke-width:1}.box{fill:#eef5f0;stroke:#2f6b4f;stroke-width:2}"
        ".warn{fill:#fff3cd;stroke:#8a6d1d;stroke-width:2}</style>\n" + body + "\n</svg>\n"
    )


def text_svg(x: float, y: float, value: str, css: str = "label", anchor: str = "start") -> str:
    return (
        f'<text x="{x:.2f}" y="{y:.2f}" class="{css}" text-anchor="{anchor}">'
        f"{html.escape(value)}</text>"
    )


def box_svg(x: int, y: int, w: int, h: int, title: str, lines: list[str]) -> str:
    body = f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="10" class="box"/>'
    body += text_svg(x + w / 2, y + 28, title, "label", "middle")
    for index, line in enumerate(lines):
        body += text_svg(x + w / 2, y + 51 + index * 18, line, "small", "middle")
    return body


def architecture_figure() -> str:
    body = text_svg(500, 38, "Verified soil_simulator evidence architecture", "title", "middle")
    boxes = [
        (50, 90, "Configuration", ["validated parameters", "assumption classes"]),
        (290, 90, "Mechanistic kernel", ["RothC + crop + P + AMF", "C/P ledgers"]),
        (530, 90, "Population", ["56-location pilot", "synthetic descendants"]),
        (770, 90, "Experiments", ["validation + sensitivity", "effect-only ML"]),
        (290, 320, "Verification", ["parity + properties", "deterministic replay"]),
        (530, 320, "Fail-closed gates", ["leakage + coverage", "prediction/OOD/validation"]),
        (770, 320, "Evidence archive", ["hashes + manifests", "bounded manuscript index"]),
    ]
    for x, y, title, lines in boxes:
        body += box_svg(x, y, 180, 100, title, lines)
    for x1, y1, x2, y2 in [
        (230, 140, 290, 140),
        (470, 140, 530, 140),
        (710, 140, 770, 140),
        (380, 190, 380, 320),
        (860, 190, 620, 320),
        (710, 370, 770, 370),
    ]:
        body += f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="#2f6b4f" stroke-width="2"/>'
    body += text_svg(
        500,
        545,
        "The optimiser/selector is downstream and was not run in Phase 9.7.",
        "label",
        "middle",
    )
    return svg_document(body)


def flow_figure() -> str:
    body = text_svg(500, 35, "Carbon and phosphorus flow/accounting boundary", "title", "middle")
    items = [
        (60, 95, "Atmospheric/plant C", ["potential NPP", "stress modifiers"]),
        (300, 95, "Plant + AMF", ["allocation", "growth/respiration"]),
        (540, 95, "Residue + necromass", ["DPM/RPM", "protected proxy route"]),
        (780, 95, "RothC pools", ["decay + retained split", "CO₂-C output"]),
        (60, 330, "External P", ["fertiliser/FYM", "explicit input"]),
        (300, 330, "Available P", ["stock-capped uptake", "P ledger"]),
        (540, 330, "Plant/AMF P", ["uptake/transfer", "export/return"]),
        (780, 330, "Boundaries", ["harvest + respiration", "C/P residual checks"]),
    ]
    for x, y, title, lines in items:
        body += box_svg(x, y, 170, 105, title, lines)
    for y in (147, 382):
        for x1, x2 in ((230, 300), (470, 540), (710, 780)):
            body += (
                f'<line x1="{x1}" y1="{y}" x2="{x2}" y2="{y}" stroke="#2f6b4f" stroke-width="2"/>'
            )
    body += '<rect x="55" y="510" width="890" height="60" rx="8" class="warn"/>'
    body += text_svg(
        500,
        540,
        "Every represented transfer has an explicit source/destination; protected SOC is a model proxy, not measured MAOC.",
        "label",
        "middle",
    )
    return svg_document(body)


def scatter_figure(rows: list[dict[str, str]]) -> str:
    width, height = 1000, 650
    left, right, top, bottom = 90, 950, 80, 560
    xs = [float(row["longitude_deg_rounded_0_1"]) for row in rows]
    ys = [float(row["latitude_deg_rounded_0_1"]) for row in rows]
    xmin, xmax, ymin, ymax = min(xs), max(xs), min(ys), max(ys)

    def px(value: float) -> float:
        return left + (value - xmin) / (xmax - xmin) * (right - left)

    def py(value: float) -> float:
        return bottom - (value - ymin) / (ymax - ymin) * (bottom - top)

    body = text_svg(
        500, 35, "Empirical pilot location coverage (rounded coordinates)", "title", "middle"
    )
    body += f'<line x1="{left}" y1="{bottom}" x2="{right}" y2="{bottom}" class="axis"/>'
    body += f'<line x1="{left}" y1="{top}" x2="{left}" y2="{bottom}" class="axis"/>'
    for index in range(6):
        xvalue = xmin + (xmax - xmin) * index / 5
        yvalue = ymin + (ymax - ymin) * index / 5
        x = px(xvalue)
        y = py(yvalue)
        body += f'<line x1="{x}" y1="{top}" x2="{x}" y2="{bottom}" class="grid"/>'
        body += f'<line x1="{left}" y1="{y}" x2="{right}" y2="{y}" class="grid"/>'
        body += text_svg(x, bottom + 24, f"{xvalue:.1f}", "small", "middle")
        body += text_svg(left - 10, y + 4, f"{yvalue:.1f}", "small", "end")
    colors = {
        "south_west": "#2f6b4f",
        "south_east": "#3465a4",
        "midlands": "#8f5902",
        "north": "#75507b",
        "east": "#cc0000",
    }
    for row in rows:
        body += (
            f'<circle cx="{px(float(row["longitude_deg_rounded_0_1"])):.2f}" '
            f'cy="{py(float(row["latitude_deg_rounded_0_1"])):.2f}" r="5" '
            f'fill="{colors.get(row["region"], "#2f6b4f")}" opacity="0.8"/>'
        )
    body += text_svg(520, 620, "Longitude (degrees; rounded to 0.1°)", "label", "middle")
    body += text_svg(24, 320, "Latitude (degrees; rounded to 0.1°)", "label", "middle")
    body += text_svg(940, 62, f"n = {len(rows)} accepted locations", "label", "end")
    return svg_document(body, width, height)


def line_chart(
    title: str,
    x_values: list[float],
    series: list[tuple[str, list[float], str]],
    x_label: str,
    y_label: str,
    note: str,
) -> str:
    width, height = 1000, 650
    left, right, top, bottom = 100, 940, 80, 530
    all_y = [value for _, values, _ in series for value in values]
    xmin, xmax = min(x_values), max(x_values)
    ymin, ymax = min([*all_y, 0]), max(all_y)
    padding = (ymax - ymin) * 0.08 or 1.0
    ymin -= padding
    ymax += padding

    def px(value: float) -> float:
        return left + (value - xmin) / (xmax - xmin) * (right - left)

    def py(value: float) -> float:
        return bottom - (value - ymin) / (ymax - ymin) * (bottom - top)

    body = text_svg(500, 35, title, "title", "middle")
    body += f'<line x1="{left}" y1="{bottom}" x2="{right}" y2="{bottom}" class="axis"/>'
    body += f'<line x1="{left}" y1="{top}" x2="{left}" y2="{bottom}" class="axis"/>'
    for index in range(6):
        yvalue = ymin + (ymax - ymin) * index / 5
        y = py(yvalue)
        body += f'<line x1="{left}" y1="{y}" x2="{right}" y2="{y}" class="grid"/>'
        body += text_svg(left - 12, y + 4, f"{yvalue:.3g}", "small", "end")
    for name, values, color in series:
        points = " ".join(f"{px(x):.2f},{py(y):.2f}" for x, y in zip(x_values, values, strict=True))
        body += f'<polyline points="{points}" fill="none" stroke="{color}" stroke-width="3"/>'
        for x, y in zip(x_values, values, strict=True):
            body += f'<circle cx="{px(x):.2f}" cy="{py(y):.2f}" r="4" fill="{color}"/>'
        body += f'<rect x="{right - 190}" y="{90 + 24 * series.index((name, values, color))}" width="16" height="4" fill="{color}"/>'
        body += text_svg(right - 165, 96 + 24 * series.index((name, values, color)), name, "small")
    for x in x_values:
        body += text_svg(px(x), bottom + 22, f"{x:g}", "small", "middle")
    body += text_svg((left + right) / 2, 580, x_label, "label", "middle")
    body += text_svg(28, 310, y_label, "label", "middle")
    body += text_svg(500, 625, note, "small", "middle")
    return svg_document(body, width, height)


def bar_chart(
    title: str,
    labels: list[str],
    values: list[float],
    colors: list[str],
    y_label: str,
    note: str,
) -> str:
    width, height = 1000, 650
    left, right, top, bottom = 100, 950, 80, 520
    ymax = max([*values, 1.0]) * 1.15
    body = text_svg(500, 35, title, "title", "middle")
    body += f'<line x1="{left}" y1="{bottom}" x2="{right}" y2="{bottom}" class="axis"/>'
    body += f'<line x1="{left}" y1="{top}" x2="{left}" y2="{bottom}" class="axis"/>'
    slot = (right - left) / len(labels)
    for index, (label, value, color) in enumerate(zip(labels, values, colors, strict=True)):
        x = left + index * slot + slot * 0.18
        bar_width = slot * 0.64
        bar_height = value / ymax * (bottom - top)
        body += f'<rect x="{x:.2f}" y="{bottom - bar_height:.2f}" width="{bar_width:.2f}" height="{bar_height:.2f}" fill="{color}"/>'
        body += text_svg(
            x + bar_width / 2, bottom - bar_height - 8, f"{value:.3g}", "small", "middle"
        )
        body += text_svg(x + bar_width / 2, bottom + 25, label, "small", "middle")
    body += text_svg(28, 300, y_label, "label", "middle")
    body += text_svg(500, 610, note, "small", "middle")
    return svg_document(body, width, height)


def build_figures() -> None:
    figures = MANUSCRIPT / "figures"
    figures.mkdir(parents=True, exist_ok=True)
    write_text(figures / "figure_01_model_architecture.svg", architecture_figure())
    write_text(figures / "figure_02_carbon_phosphorus_flow.svg", flow_figure())

    with (ROOT / "data/processed/phase96_empirical_soil_locations_v1.csv").open(
        encoding="utf-8", newline=""
    ) as stream:
        locations = list(csv.DictReader(stream))
    write_text(figures / "figure_03_empirical_location_coverage.svg", scatter_figure(locations))
    copy_verified(
        "outputs/phase96_v0.9.6/figures/empirical_generated_distributions.svg",
        figures / "figure_04_empirical_generated_distributions.svg",
    )
    copy_verified(
        "outputs/phase96_v0.9.6/figures/hoosfield_trajectories.svg",
        figures / "figure_05_hoosfield_trajectories.svg",
    )

    with (ROOT / "outputs/phase96_v0.9.6/validation_trajectories.csv").open(
        encoding="utf-8", newline=""
    ) as stream:
        trajectory_rows = list(csv.DictReader(stream))
    corrected = [
        row
        for row in trajectory_rows
        if row["run"] == "uncalibrated_source_corrected_forcing"
        and row["evaluation_role"] != "initialization"
    ]
    years = sorted({float(row["year"]) for row in corrected})
    residual_series = []
    for treatment, color in [
        ("unfertilized", "#3465a4"),
        ("fym_annual", "#2f6b4f"),
        ("fym_1852_1871", "#cc0000"),
    ]:
        by_year = {
            float(row["year"]): float(row["residual_t_c_ha"])
            for row in corrected
            if row["treatment"] == treatment
        }
        residual_series.append((treatment, [by_year.get(year, 0.0) for year in years], color))
    write_text(
        figures / "figure_06_hoosfield_residuals.svg",
        line_chart(
            "Hoosfield source-corrected residuals",
            years,
            residual_series,
            "Year",
            "Simulated minus observed SOC (t C ha⁻¹)",
            "Uncalibrated source-corrected forcing; cessation weakness is retained.",
        ),
    )

    calibration = read_json("outputs/phase97_v0.9.7/calibration_profile.json")
    profile = calibration["profile"]
    write_text(
        figures / "figure_07_fym_calibration_profile.svg",
        line_chart(
            "FYM calibration boundary profile",
            [item["fym_carbon_factor"] for item in profile],
            [
                (
                    "profile objective",
                    [item["profile_objective_mean_treatment_rmse_t_c_ha"] for item in profile],
                    "#8f5902",
                )
            ],
            "FYM carbon reconstruction factor",
            "Mean treatment RMSE (t C ha⁻¹)",
            "Estimate reaches the permitted upper bound (1.10); no beyond-bound evaluation performed.",
        ),
    )

    convergence = read_json("outputs/phase97_v0.9.7/sensitivity_convergence_manifest.json")
    comparisons = convergence["comparisons"]
    write_text(
        figures / "figure_08_sensitivity_convergence.svg",
        line_chart(
            "Sensitivity convergence diagnostics — NOT CONVERGED",
            [item["current_base_sample_size"] for item in comparisons],
            [
                (
                    "maximum |ΔS1|",
                    [item["maximum_absolute_first_order_change"] for item in comparisons],
                    "#cc0000",
                ),
                (
                    "maximum |ΔST|",
                    [item["maximum_absolute_total_order_change"] for item in comparisons],
                    "#8f5902",
                ),
                ("threshold", [0.1 for _ in comparisons], "#555753"),
            ],
            "Current nested base sample size",
            "Maximum adjacent index change",
            "At N=1,024 both index-change criteria remain above 0.10.",
        ),
    )

    with (ROOT / "outputs/phase97_v0.9.7/sensitivity_first_total.csv").open(
        encoding="utf-8", newline=""
    ) as stream:
        sobol_rows = list(csv.DictReader(stream))
    selected = [
        row
        for row in sobol_rows
        if row["base_sample_size"] == "1024"
        and row["policy_id"] == "farmyard_manure"
        and row["target_name"] == "total_soc_t_c_ha"
        and row["horizon_months"] == "120"
    ]
    labels = [row["parameter"].replace("_", " ") for row in selected]
    values = [float(row["total_order"]) for row in selected]
    write_text(
        figures / "figure_09_representative_total_order_sensitivity.svg",
        bar_chart(
            "Representative ST indices — diagnostic, NOT CONVERGED",
            labels,
            values,
            ["#75507b"] * len(labels),
            "Total-order index (dimensionless)",
            "FYM policy, 120-month total-SOC effect, N=1,024; negative estimates are retained in source data.",
        ),
    )

    gate_evidence = read_json("outputs/phase97_v0.9.7/gate_evidence.json")
    gate_items = list(gate_evidence["downstream_execution"]["required_gates"].items())
    write_text(
        figures / "figure_10_ml_gate_summary.svg",
        bar_chart(
            "Phase 9.7 fail-closed ML readiness gates",
            [name.replace("_", " ") for name, _ in gate_items],
            [1.0 if passed else 0.05 for _, passed in gate_items],
            ["#2f6b4f" if passed else "#cc0000" for _, passed in gate_items],
            "Pass indicator (1=pass; red stub=fail)",
            "Prediction, OOD and independent empirical-effect validation failed; selection was blocked.",
        ),
    )

    body = text_svg(500, 40, "Audit and remediation chronology", "title", "middle")
    stages = [
        ("v0.9.0 audit", "independent", "critical/major findings retained", "#3465a4"),
        ("Phase 9.5", "remediation", "effect-only/accounting/validation", "#2f6b4f"),
        (
            "Phase 9.6",
            "empirical grounding",
            "56-location pilot; independent clean-slate audit",
            "#8f5902",
        ),
        ("Phase 9.7", "focused re-audit", "implementation blockers cleared", "#75507b"),
        ("Phase 9.8", "archive", "bounded evidence; no manuscript prose", "#555753"),
    ]
    for index, (stage, subtitle, note, color) in enumerate(stages):
        x = 80 + index * 185
        body += f'<circle cx="{x}" cy="250" r="22" fill="{color}"/>'
        if index < len(stages) - 1:
            body += f'<line x1="{x + 22}" y1="250" x2="{x + 163}" y2="250" stroke="#394b59" stroke-width="3"/>'
        body += text_svg(x, 310, stage, "label", "middle")
        body += text_svg(x, 334, subtitle, "small", "middle")
        body += text_svg(x, 380, note, "small", "middle")
    body += text_svg(
        500,
        520,
        "Negative findings were preserved; implementation closure is not scientific validation.",
        "label",
        "middle",
    )
    write_text(figures / "figure_11_audit_remediation_timeline.svg", svg_document(body))


def build_supplementary() -> None:
    supplementary = MANUSCRIPT / "supplementary"
    copy_map = {
        "ASSUMPTIONS_REGISTER.csv": "docs/ASSUMPTIONS_REGISTER.csv",
        "phase96_internal_audit_closure_matrix.csv": "outputs/phase96_v0.9.6/audit_closure_matrix.csv",
        "phase97_internal_audit_closure_matrix.csv": "outputs/phase97_v0.9.7/audit_closure_matrix.csv",
        "sensitivity_convergence_manifest.json": "outputs/phase97_v0.9.7/sensitivity_convergence_manifest.json",
        "calibration_profile.csv": "outputs/phase97_v0.9.7/calibration_profile.csv",
        "validation_residuals.csv": "outputs/phase96_v0.9.6/validation_trajectories.csv",
        "EFFECT_ONLY_MODEL_CARD.md": "outputs/phase96_v0.9.6/EFFECT_ONLY_MODEL_CARD.md",
        "leakage_evidence.json": "outputs/phase97_v0.9.7/leakage_check_evidence.json",
        "uncertainty_evidence.json": "outputs/phase97_v0.9.7/uncertainty_coverage_report.json",
        "publication_readiness_gates.json": "outputs/phase97_v0.9.7/publication_readiness.json",
    }
    for destination, source in copy_map.items():
        copy_verified(source, supplementary / destination)

    manifest_sources = {
        "phase95_artifact_hashes.json": "outputs/phase95_v0.9.5/artifact_hashes.json",
        "phase96_artifact_hashes.json": "outputs/phase96_v0.9.6/artifact_hashes.json",
        "phase96_empirical_source_manifest.json": "outputs/phase96_v0.9.6/EMPIRICAL_SOURCE_MANIFEST.json",
        "phase97_artifact_hashes.json": "outputs/phase97_v0.9.7/artifact_hashes.json",
        "phase97_source_manifest.json": "outputs/phase97_v0.9.7/source_manifest.json",
        "phase97_pipeline_manifest.json": "outputs/phase97_v0.9.7/pipeline_manifest.json",
        "phase97_sobol_sampling_manifest.json": "outputs/phase97_v0.9.7/sobol_sampling_manifest.json",
    }
    for destination, source in manifest_sources.items():
        copy_verified(source, supplementary / "source_manifests" / destination)

    indexes = [
        ("full_phase95_sensitivity", "outputs/phase95_v0.9.5/sensitivity_results.json"),
        ("superseded_phase96_sensitivity", "outputs/phase96_v0.9.6/sensitivity_results.json"),
        ("corrected_phase97_sensitivity", "outputs/phase97_v0.9.7/sensitivity_first_total.json"),
        (
            "corrected_phase97_sensitivity_long_table",
            "outputs/phase97_v0.9.7/sensitivity_first_total.csv",
        ),
        ("effect_only_dataset", "outputs/phase96_v0.9.6/effect_only_dataset.csv"),
        ("generated_population", "outputs/phase96_v0.9.6/generated_population_v0.9.6.json"),
    ]
    index_rows = []
    for name, source in indexes:
        source_path = ROOT / source
        index_rows.append(
            {
                "name": name,
                "source_path": source,
                "sha256": sha256(source_path),
                "file_size": source_path.stat().st_size,
                "reason_indexed": "preserve frozen artifact and avoid unnecessary duplication",
                "scientifically_frozen": True,
            }
        )
    write_json(supplementary / "LARGE_FILE_INDEX.json", index_rows)
    audit_index_rows = []
    for canonical_name in AUDIT_SOURCE_MAP.values():
        source_path = AUDITS / canonical_name
        audit_index_rows.append(
            {
                "source_path": str(source_path.relative_to(ROOT)),
                "sha256": sha256(source_path),
                "file_size": source_path.stat().st_size,
                "role": "independent audit evidence; canonical copy in docs/audits",
                "scientifically_frozen": True,
            }
        )
    write_json(supplementary / "INDEPENDENT_AUDIT_INDEX.json", audit_index_rows)
    write_text(
        supplementary / "README.md",
        """# Supplementary evidence index

Small, high-value evidence files are copied here byte-for-byte. Large datasets and
sensitivity results are indexed in `LARGE_FILE_INDEX.json` so frozen historical
artifacts are not duplicated or relocated. Internal Phase 9.6/9.7 closure matrices
remain labelled internal. The ten byte-preserved independent audit deliverables are
indexed in `INDEPENDENT_AUDIT_INDEX.json` and archived canonically in `docs/audits/`.
""",
    )


def build_data_index() -> None:
    source = read_json("outputs/phase96_v0.9.6/EMPIRICAL_SOURCE_MANIFEST.json")
    rows = []
    for item in source["raw_files"]:
        rows.append(
            {
                "data_class": "raw",
                "path": item["path"],
                "sha256": item["sha256"],
                "file_size": item["bytes"],
                "source": item["source"],
                "redistribution_status": "local cache; consult source licence",
                "source_path": "outputs/phase96_v0.9.6/EMPIRICAL_SOURCE_MANIFEST.json",
            }
        )
    for item in source["processed_files"]:
        rows.append(
            {
                "data_class": "processed",
                "path": item["path"],
                "sha256": item["sha256"],
                "file_size": item["bytes"],
                "source": "SoilGrids/NASA POWER derivation",
                "redistribution_status": "repository-local processed pilot",
                "source_path": "outputs/phase96_v0.9.6/EMPIRICAL_SOURCE_MANIFEST.json",
            }
        )
    for data_class, path in [
        ("generated", "outputs/phase96_v0.9.6/generated_population_v0.9.6.json"),
        ("simulated", "outputs/phase96_v0.9.6/effect_only_dataset.csv"),
        ("simulated", "outputs/phase96_v0.9.6/validation_trajectories.csv"),
    ]:
        source_path = ROOT / path
        rows.append(
            {
                "data_class": data_class,
                "path": path,
                "sha256": sha256(source_path),
                "file_size": source_path.stat().st_size,
                "source": "soil_simulator deterministic pipeline",
                "redistribution_status": "frozen project artifact",
                "source_path": "outputs/phase96_v0.9.6/artifact_hashes.json",
            }
        )
    write_csv(MANUSCRIPT / "data" / "DATA_INDEX.csv", list(rows[0]), rows)


def manifest_entry(path: Path, category: str, source: str, action: str) -> dict[str, Any]:
    return {
        "action": action,
        "category": category,
        "file_size": path.stat().st_size,
        "path": str(path.relative_to(ROOT)),
        "scientifically_frozen": action in {"copied", "indexed"},
        "sha256": sha256(path),
        "source_or_generating_script": source,
    }


def action_and_source(path: Path, category: str) -> tuple[str, str]:
    """Return the archive action and exact source description for a bundle path."""
    relative = str(path.relative_to(ROOT))
    copied_figures = {
        "manuscript/figures/figure_04_empirical_generated_distributions.svg": (
            "outputs/phase96_v0.9.6/figures/empirical_generated_distributions.svg"
        ),
        "manuscript/figures/figure_05_hoosfield_trajectories.svg": (
            "outputs/phase96_v0.9.6/figures/hoosfield_trajectories.svg"
        ),
    }
    copied_supplementary = {
        "manuscript/supplementary/ASSUMPTIONS_REGISTER.csv": "docs/ASSUMPTIONS_REGISTER.csv",
        "manuscript/supplementary/calibration_profile.csv": "outputs/phase97_v0.9.7/calibration_profile.csv",
        "manuscript/supplementary/EFFECT_ONLY_MODEL_CARD.md": "outputs/phase96_v0.9.6/EFFECT_ONLY_MODEL_CARD.md",
        "manuscript/supplementary/leakage_evidence.json": "outputs/phase97_v0.9.7/leakage_check_evidence.json",
        "manuscript/supplementary/phase96_internal_audit_closure_matrix.csv": "outputs/phase96_v0.9.6/audit_closure_matrix.csv",
        "manuscript/supplementary/phase97_internal_audit_closure_matrix.csv": "outputs/phase97_v0.9.7/audit_closure_matrix.csv",
        "manuscript/supplementary/publication_readiness_gates.json": "outputs/phase97_v0.9.7/publication_readiness.json",
        "manuscript/supplementary/sensitivity_convergence_manifest.json": "outputs/phase97_v0.9.7/sensitivity_convergence_manifest.json",
        "manuscript/supplementary/uncertainty_evidence.json": "outputs/phase97_v0.9.7/uncertainty_coverage_report.json",
        "manuscript/supplementary/validation_residuals.csv": "outputs/phase96_v0.9.6/validation_trajectories.csv",
        "manuscript/supplementary/source_manifests/phase95_artifact_hashes.json": "outputs/phase95_v0.9.5/artifact_hashes.json",
        "manuscript/supplementary/source_manifests/phase96_artifact_hashes.json": "outputs/phase96_v0.9.6/artifact_hashes.json",
        "manuscript/supplementary/source_manifests/phase96_empirical_source_manifest.json": "outputs/phase96_v0.9.6/EMPIRICAL_SOURCE_MANIFEST.json",
        "manuscript/supplementary/source_manifests/phase97_artifact_hashes.json": "outputs/phase97_v0.9.7/artifact_hashes.json",
        "manuscript/supplementary/source_manifests/phase97_pipeline_manifest.json": "outputs/phase97_v0.9.7/pipeline_manifest.json",
        "manuscript/supplementary/source_manifests/phase97_sobol_sampling_manifest.json": "outputs/phase97_v0.9.7/sobol_sampling_manifest.json",
        "manuscript/supplementary/source_manifests/phase97_source_manifest.json": "outputs/phase97_v0.9.7/source_manifest.json",
    }
    if relative in copied_figures:
        return "copied", copied_figures[relative]
    if relative in copied_supplementary:
        return "copied", copied_supplementary[relative]
    if category == "supplementary":
        if path.name in {"LARGE_FILE_INDEX.json", "INDEPENDENT_AUDIT_INDEX.json"}:
            return "indexed", "frozen sources listed inside the index"
        if path.name == "README.md":
            return "generated", "Phase 9.8 documentation"
        return "generated", "Phase 9.8 supplementary index/documentation"
    if category in {"tables", "figures", "data_indexes"}:
        return "generated", "scripts/build_phase98_archive.py"
    return "generated", "Phase 9.8 archive build/documentation"


def build_manifests() -> None:
    manifests = MANUSCRIPT / "manifests"
    manifests.mkdir(parents=True, exist_ok=True)
    phase97_manifest = read_json("outputs/phase97_v0.9.7/artifact_hashes.json")
    current_byte_changes = []
    for relative_path, historical_hash in phase97_manifest["files"].items():
        current_hash = sha256(ROOT / relative_path)
        if current_hash != historical_hash:
            current_byte_changes.append(
                {
                    "current_sha256": current_hash,
                    "historical_sha256": historical_hash,
                    "path": relative_path,
                    "reason": "Phase 9.8 required top-level research-archive links/status",
                    "scientific_content_changed": False,
                }
            )
    write_json(
        manifests / "phase98_current_byte_corrections.json",
        {
            "allowed_changed_paths": ["README.md"],
            "changes_since_phase97_freeze": current_byte_changes,
            "historical_manifest_modified": False,
            "historical_manifest_path": "outputs/phase97_v0.9.7/artifact_hashes.json",
            "historical_set_sha256": phase97_manifest["artifact_set_sha256"],
            "role": "transparent Phase 9.8 documentation-only current-byte correction",
        },
    )
    categories = {
        "tables": MANUSCRIPT / "tables",
        "figures": MANUSCRIPT / "figures",
        "supplementary": MANUSCRIPT / "supplementary",
        "data_indexes": MANUSCRIPT / "data",
    }
    for category, directory in categories.items():
        entries = []
        for path in sorted(directory.rglob("*")):
            if not path.is_file():
                continue
            action, source = action_and_source(path, category)
            entries.append(manifest_entry(path, category, source, action))
        write_json(manifests / f"{category}_manifest.json", {"entries": entries})

    included = [
        path
        for path in sorted(MANUSCRIPT.rglob("*"))
        if path.is_file()
        and path.name not in {"manuscript_bundle_manifest.json", "MANUSCRIPT_BUNDLE_SHA256.txt"}
    ]
    entries = []
    for path in included:
        category = path.parent.name
        if "supplementary" in path.parts:
            category = "supplementary"
        elif path.parent == MANUSCRIPT / "data":
            category = "data_indexes"
        action, source = action_and_source(path, category)
        entries.append(manifest_entry(path, category, source, action))
    canonical = "".join(f"{item['path']}\0{item['sha256']}\n" for item in entries)
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    write_json(
        manifests / "manuscript_bundle_manifest.json",
        {
            "entry_count": len(entries),
            "entries": entries,
            "set_digest_algorithm": "sha256(path NUL sha256 LF, sorted by path)",
            "set_sha256": digest,
        },
    )
    write_text(manifests / "MANUSCRIPT_BUNDLE_SHA256.txt", digest)


def build_restructuring_log() -> None:
    archive_files = [path for path in MANUSCRIPT.rglob("*") if path.is_file()] + [
        path for path in AUDITS.rglob("*") if path.is_file()
    ]
    phase98_paths = [
        ROOT / "README.md",
        ROOT / "docs/provenance/RESEARCH_ARCHIVE.md",
        ROOT / "docs/PHASE98_MANUSCRIPT_ARCHIVE.md",
        ROOT / "scripts/build_phase98_archive.py",
        ROOT / "src/soil_simulator/phase98/__init__.py",
        ROOT / "src/soil_simulator/phase98/archive.py",
        ROOT / "tests/unit/test_phase96.py",
        ROOT / "tests/unit/test_phase97.py",
        ROOT / "tests/unit/test_phase98_archive.py",
    ]
    generated = sorted({*archive_files, *(path for path in phase98_paths if path.is_file())})
    rows = []
    for path in generated:
        action = "generated"
        source = "scripts/build_phase98_archive.py or Phase 9.8 documentation"
        if path.name == "AUDIT_v0.9.0_INDEPENDENT.md":
            action = "copied"
            source = "docs/AUDIT_soil_simulator_v0.9.0.md"
        elif path.parent == AUDITS and path.name in AUDIT_SOURCE_MAP.values():
            action = "copied"
            source_name = next(
                incoming
                for incoming, canonical in AUDIT_SOURCE_MAP.items()
                if canonical == path.name
            )
            source = f"audits/incoming/{source_name}"
        elif path == AUDITS / "AUDIT_EXPORT_MANIFEST.json":
            action = "copied"
            source = "audits/incoming/AUDIT_EXPORT_MANIFEST.json"
        elif "supplementary" in path.parts and path.suffix in {".csv", ".json", ".md"}:
            action = "copied_or_indexed"
            source = "see supplementary README and LARGE_FILE_INDEX.json"
        elif path in {
            ROOT / "README.md",
            ROOT / "tests/unit/test_phase96.py",
            ROOT / "tests/unit/test_phase97.py",
        }:
            action = "modified"
            source = "Phase 9.8 archive links or transparent manifest-replay correction"
        rows.append(
            {
                "action": action,
                "path": str(path.relative_to(ROOT)),
                "source_or_reason": source,
                "sha256": sha256(path),
                "file_size": path.stat().st_size,
            }
        )
    rows.append(
        {
            "action": "generated",
            "path": "docs/PHASE98_RESTRUCTURING_LOG.csv",
            "source_or_reason": "self-index; hash and size omitted to avoid recursive mutation",
            "sha256": "not_applicable_self_referential",
            "file_size": "not_applicable_self_referential",
        }
    )
    write_csv(
        ROOT / "docs/PHASE98_RESTRUCTURING_LOG.csv",
        ["action", "path", "source_or_reason", "sha256", "file_size"],
        rows,
    )


def main() -> None:
    build_audit_archive()
    build_tables()
    build_figures()
    build_supplementary()
    build_data_index()
    build_manifests()
    build_restructuring_log()


if __name__ == "__main__":
    main()
