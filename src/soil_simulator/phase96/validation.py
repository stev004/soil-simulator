"""Hoosfield component attribution, bounded calibration, and held-out validation."""

from __future__ import annotations

import csv
import math
from collections import defaultdict
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from soil_simulator.domain.carbon import CarbonCoreMonth, CarbonInput, RothCForcing
from soil_simulator.domain.models import FieldState, ModelParameters
from soil_simulator.phase96.values import as_float, as_int
from soil_simulator.simulator.carbon_core import run_carbon_core, soil_carbon_total

TREATMENTS = ("unfertilized", "fym_annual", "fym_1852_1871")
FALLOW_YEARS = frozenset({1912, 1933, 1943, 1967})
PHASE95_TEMPERATURE_C = (4.0, 5.0, 8.0, 11.0, 14.0, 17.0, 19.0, 18.0, 15.0, 11.0, 7.0, 5.0)
PHASE95_RAINFALL_MM = (74.0, 59.0, 62.0, 51.0, 52.0, 57.0, 34.0, 55.0, 58.0, 56.0, 75.0, 71.0)
PHASE95_OPEN_PAN_MM = (8.0, 10.0, 27.0, 49.0, 83.0, 99.0, 103.0, 91.0, 69.0, 34.0, 16.0, 8.0)
OFFICIAL_TEMPERATURE_C = (3.73, 3.08, 5.49, 7.4, 10.94, 14.4, 16.28, 16.24, 13.78, 9.51, 6.22, 4.09)
OFFICIAL_RAINFALL_MM = (52.2, 42.9, 35.2, 52.0, 64.9, 46.3, 63.5, 60.6, 58.8, 63.4, 72.5, 60.9)
OFFICIAL_OPEN_PAN_MM = (6.6, 17.3, 40.7, 70.5, 103.5, 117.3, 130.1, 106.9, 61.9, 29.5, 8.8, 3.9)


@dataclass(frozen=True)
class ValidationInputs:
    """Predeclared historical-input reconstruction factors; RothC constants are unchanged."""

    plant_residue_factor: float = 1.0
    fym_carbon_factor: float = 1.0
    initial_iom_t_c_ha: float = 2.7
    forcing: str = "official_v2.1.1_normal"


def _initial_state(total_soc_t_c_ha: float, iom_t_c_ha: float) -> FieldState:
    official_active = (0.1533, 4.4852, 0.6671, 25.8576)
    scale = (total_soc_t_c_ha - iom_t_c_ha) / math.fsum(official_active)
    if scale <= 0.0:
        raise ValueError("initial IOM must be less than total SOC")
    return FieldState(
        month_index=0,
        plant_c=0.0,
        root_c=0.0,
        amf_live_c=0.0,
        amf_necromass_c=0.0,
        dpm_c=official_active[0] * scale,
        rpm_c=official_active[1] * scale,
        microbial_c=official_active[2] * scale,
        protected_soc_c=official_active[3] * scale,
        iom_c=iom_t_c_ha,
        available_p_kg_ha=0.0,
        topsoil_moisture_deficit_mm=0.0,
        crop_development=0.0,
        cumulative_yield_t_dm_ha=0.0,
        aggregate_protection_index=None,
    )


def _forcing(
    inputs: ValidationInputs,
) -> tuple[tuple[float, ...], tuple[float, ...], tuple[float, ...]]:
    if inputs.forcing == "phase95_authored_pattern":
        return PHASE95_TEMPERATURE_C, PHASE95_RAINFALL_MM, PHASE95_OPEN_PAN_MM
    if inputs.forcing == "official_v2.1.1_normal":
        return OFFICIAL_TEMPERATURE_C, OFFICIAL_RAINFALL_MM, OFFICIAL_OPEN_PAN_MM
    raise ValueError(f"unknown validation forcing {inputs.forcing!r}")


def _plant_inputs(treatment: str, year: int, factor: float) -> tuple[float, ...]:
    if year in FALLOW_YEARS:
        return (0.0,) * 12
    annual = 1.6
    if treatment == "fym_annual" or (treatment == "fym_1852_1871" and year <= 1876):
        annual = 2.8
    annual *= factor
    return (
        0.0,
        0.0,
        0.0,
        annual * 0.10,
        annual * 0.20,
        annual * 0.30,
        annual * 0.40,
        0.0,
        0.0,
        0.0,
        0.0,
        0.0,
    )


def _fym_input(treatment: str, year: int, month: int, factor: float) -> float:
    if treatment == "fym_1852_1871":
        return 3.0 * factor if year <= 1871 and month == 2 else 0.0
    if treatment != "fym_annual":
        return 0.0
    if year == 1931 and month in {2, 11}:
        return 3.0 * factor
    application_month = 2 if year <= 1930 else 11
    return 3.0 * factor if month == application_month else 0.0


def _months(treatment: str, inputs: ValidationInputs) -> tuple[CarbonCoreMonth, ...]:
    temperature, rainfall, open_pan = _forcing(inputs)
    months: list[CarbonCoreMonth] = []
    for year in range(1852, 1999):
        plant = _plant_inputs(treatment, year, inputs.plant_residue_factor)
        for index in range(12):
            month = index + 1
            plant_c = plant[index]
            fym_c = _fym_input(treatment, year, month, inputs.fym_carbon_factor)
            months.append(
                CarbonCoreMonth(
                    external_input=CarbonInput(
                        dpm_c=plant_c * 1.44 / 2.44 + fym_c * 0.49,
                        rpm_c=plant_c / 2.44 + fym_c * 0.49,
                        protected_soc_c=fym_c * 0.02,
                        classification="scenario_assumption",
                        provenance=(
                            "RothC February 2024 Hoosfield schedule; reconstruction factors "
                            "are explicit and never alter authoritative turnover constants"
                        ),
                    ),
                    forcing=RothCForcing(
                        mean_air_temperature_c=temperature[index],
                        precipitation_mm=rainfall[index],
                        open_pan_evaporation_mm=open_pan[index],
                        is_covered=year not in FALLOW_YEARS and month in {4, 5, 6, 7},
                        clay_percent=23.4,
                        soil_depth_cm=23.0,
                        provenance=f"Hoosfield forcing={inputs.forcing}",
                    ),
                )
            )
    return tuple(months)


def load_observations(path: str | Path) -> tuple[dict[str, str], ...]:
    """Load the frozen normalized e-RA observations."""
    with Path(path).open(encoding="utf-8", newline="") as handle:
        return tuple(dict(row) for row in csv.DictReader(handle))


def metrics(points: tuple[Mapping[str, object], ...]) -> dict[str, float]:
    """Return MAE, RMSE and signed simulated-minus-observed bias."""
    if not points:
        raise ValueError("validation metrics require at least one point")
    residuals = tuple(
        as_float(point["simulated_soc_t_c_ha"]) - as_float(point["observed_soc_t_c_ha"])
        for point in points
    )
    return {
        "mae_t_c_ha": math.fsum(abs(value) for value in residuals) / len(residuals),
        "rmse_t_c_ha": math.sqrt(math.fsum(value * value for value in residuals) / len(residuals)),
        "bias_t_c_ha": math.fsum(residuals) / len(residuals),
    }


def run_trajectory(
    observations: tuple[dict[str, str], ...],
    parameters: ModelParameters,
    inputs: ValidationInputs,
) -> dict[str, object]:
    """Run all three treatments and retain initial, calibration and held-out roles."""
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in observations:
        grouped[row["treatment"]].append(row)
    treatments: dict[str, object] = {}
    all_points: list[Mapping[str, object]] = []
    for treatment in TREATMENTS:
        source = sorted(grouped[treatment], key=lambda row: int(row["year"]))
        initial = float(source[0]["soc_t_c_ha"])
        simulation = run_carbon_core(
            _initial_state(initial, inputs.initial_iom_t_c_ha),
            _months(treatment, inputs),
            parameters,
            seed=9601852,
        )
        by_year = {
            year: soil_carbon_total(simulation.steps[(year - 1852 + 1) * 12 - 1].final_state)
            for year in range(1852, 1999)
        }
        points: list[dict[str, object]] = []
        for row in source:
            year = int(row["year"])
            role = "initialization"
            if year > 1852:
                if treatment == "fym_1852_1871":
                    role = "held_out_treatment"
                elif year <= 1965:
                    role = "calibration"
                else:
                    role = "held_out_temporal"
            points.append(
                {
                    "treatment": treatment,
                    "year": year,
                    "observed_soc_t_c_ha": float(row["soc_t_c_ha"]),
                    "simulated_soc_t_c_ha": initial if year == 1852 else by_year[year],
                    "evaluation_role": role,
                }
            )
        scored = tuple(point for point in points if point["evaluation_role"] != "initialization")
        all_points.extend(scored)
        treatments[treatment] = {
            "metrics": metrics(scored),
            "trajectory": points,
            "maximum_monthly_mass_balance_residual_t_c_ha": max(
                abs(step.mass_balance.residual_t_c_ha) for step in simulation.steps
            ),
        }
    return {
        "inputs": inputs.__dict__,
        "aggregate_metrics": metrics(tuple(all_points)),
        "treatments": treatments,
    }


def _role_points(result: Mapping[str, object], role: str) -> tuple[Mapping[str, object], ...]:
    treatments = cast(dict[str, dict[str, Any]], result["treatments"])
    return tuple(
        point
        for payload in treatments.values()
        for point in payload["trajectory"]
        if point["evaluation_role"] == role
    )


def calibrate_inputs(
    observations: tuple[dict[str, str], ...], parameters: ModelParameters
) -> dict[str, object]:
    """Fit two bounded input-reconstruction factors without held-out access."""
    candidates: list[dict[str, object]] = []
    for plant_index in range(9):
        plant_factor = 0.80 + plant_index * 0.05
        for fym_index in range(5):
            fym_factor = 0.90 + fym_index * 0.05
            inputs = ValidationInputs(
                plant_residue_factor=plant_factor,
                fym_carbon_factor=fym_factor,
            )
            result = run_trajectory(observations, parameters, inputs)
            calibration_points = _role_points(result, "calibration")
            calibration_by_treatment = {
                treatment: tuple(
                    point for point in calibration_points if point["treatment"] == treatment
                )
                for treatment in ("unfertilized", "fym_annual")
            }
            objective = math.fsum(
                metrics(points)["rmse_t_c_ha"] for points in calibration_by_treatment.values()
            ) / len(calibration_by_treatment)
            candidates.append(
                {
                    "plant_residue_factor": plant_factor,
                    "fym_carbon_factor": fym_factor,
                    "calibration_objective_mean_treatment_rmse_t_c_ha": objective,
                    "result": result,
                }
            )
    best = min(
        candidates,
        key=lambda candidate: as_float(
            candidate["calibration_objective_mean_treatment_rmse_t_c_ha"]
        ),
    )
    minimum = as_float(best["calibration_objective_mean_treatment_rmse_t_c_ha"])
    near = [
        candidate
        for candidate in candidates
        if as_float(candidate["calibration_objective_mean_treatment_rmse_t_c_ha"]) <= minimum * 1.10
    ]
    best_result = best["result"]
    assert isinstance(best_result, dict)
    band_values: dict[tuple[str, int], list[float]] = defaultdict(list)
    for candidate in near:
        result = cast(dict[str, Any], candidate["result"])
        treatments = cast(dict[str, dict[str, Any]], result["treatments"])
        for treatment, payload in treatments.items():
            for point in payload["trajectory"]:
                band_values[(treatment, as_int(point["year"]))].append(
                    as_float(point["simulated_soc_t_c_ha"])
                )
    uncertainty_bands = [
        {
            "treatment": treatment,
            "year": year,
            "lower_t_c_ha": min(values),
            "upper_t_c_ha": max(values),
            "candidate_count": len(values),
            "definition": "range among candidates within 10% of minimum calibration objective",
        }
        for (treatment, year), values in sorted(band_values.items())
    ]
    return {
        "predeclared_parameters": {
            "plant_residue_factor": {"bounds": [0.80, 1.20], "classification": "calibrated"},
            "fym_carbon_factor": {"bounds": [0.90, 1.10], "classification": "calibrated"},
        },
        "calibration_data": "unfertilized and annual-FYM observations through 1965",
        "held_out_data": "post-1965 temporal observations plus entire FYM-cessation treatment",
        "best_parameters": {
            "plant_residue_factor": best["plant_residue_factor"],
            "fym_carbon_factor": best["fym_carbon_factor"],
        },
        "calibration_metrics": metrics(_role_points(best_result, "calibration")),
        "held_out_temporal_metrics": metrics(_role_points(best_result, "held_out_temporal")),
        "held_out_treatment_metrics": metrics(_role_points(best_result, "held_out_treatment")),
        "boundary_solution": (
            as_float(best["plant_residue_factor"]) in {0.80, 1.20}
            or as_float(best["fym_carbon_factor"]) in {0.90, 1.10}
        ),
        "identifiability": {
            "within_10_percent_of_minimum_count": len(near),
            "plant_residue_factor_range": [
                min(as_float(candidate["plant_residue_factor"]) for candidate in near),
                max(as_float(candidate["plant_residue_factor"]) for candidate in near),
            ],
            "fym_carbon_factor_range": [
                min(as_float(candidate["fym_carbon_factor"]) for candidate in near),
                max(as_float(candidate["fym_carbon_factor"]) for candidate in near),
            ],
        },
        "trajectory": best_result,
        "parameter_uncertainty_bands": uncertainty_bands,
        "candidate_summary": [
            {key: value for key, value in candidate.items() if key != "result"}
            for candidate in candidates
        ],
    }


def diagnose_and_validate(
    observation_path: str | Path, parameters: ModelParameters
) -> dict[str, object]:
    """Return the frozen Phase 9.5 benchmark, forcing attribution and calibration experiment."""
    observations = load_observations(observation_path)
    phase95 = run_trajectory(
        observations, parameters, ValidationInputs(forcing="phase95_authored_pattern")
    )
    corrected = run_trajectory(observations, parameters, ValidationInputs())
    calibration = calibrate_inputs(observations, parameters)
    phase95_metrics = cast(dict[str, float], phase95["aggregate_metrics"])
    corrected_metrics = cast(dict[str, float], corrected["aggregate_metrics"])
    base_bias = phase95_metrics["bias_t_c_ha"]
    forcing_bias = corrected_metrics["bias_t_c_ha"]
    return {
        "version": "0.9.6",
        "uncalibrated_phase95_benchmark": phase95,
        "uncalibrated_source_corrected_forcing": corrected,
        "component_attribution": [
            {
                "component": "climate_forcing",
                "phase95_assumption": "authored warmer/lower-evaporation monthly pattern",
                "phase96_evidence": "official RothC v2.1.1 bundled normal",
                "bias_change_t_c_ha": forcing_bias - base_bias,
                "conclusion": "dominant identified source of Phase 9.5 negative bias",
            },
            {
                "component": "FYM quantity and carbon conversion",
                "status": "verified",
                "evidence": "3.0 t C ha-1 schedule matches official February 2024 description",
            },
            {
                "component": "DPM:RPM and FYM partition",
                "status": "verified",
                "evidence": "crop 1.44 and FYM 49/49/2 match authoritative specification",
            },
            {
                "component": "depth, IOM, treatment timing, fallow years and initial pools",
                "status": "verified_with_residual_uncertainty",
                "evidence": "23 cm, 2.7 t C ha-1 IOM and official schedules reproduced explicitly",
            },
            {
                "component": "plant residue inputs",
                "status": "input_reconstruction_uncertainty",
                "evidence": (
                    "official annual totals retained; only bounded factors enter optional "
                    "calibration"
                ),
            },
        ],
        "optional_calibration": calibration,
        "authoritative_constants_changed": False,
        "claim_boundary": (
            "This validates total SOC in the RothC-style core only. It does not validate AMF "
            "dynamics or protected_soc as measured MAOC."
        ),
    }
