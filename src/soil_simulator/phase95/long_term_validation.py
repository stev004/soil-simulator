"""Uncalibrated multi-decade Hoosfield SOC validation.

Observed stocks are the versioned Rothamsted e-RA extraction at 0--23 cm.
Management inputs follow the official February 2024 RothC model description.
No parameter is fitted to the validation observations.
"""

from __future__ import annotations

import csv
import math
from collections import defaultdict
from pathlib import Path

from soil_simulator.domain.carbon import CarbonCoreMonth, CarbonInput, RothCForcing
from soil_simulator.domain.models import FieldState, ModelParameters
from soil_simulator.simulator.carbon_core import run_carbon_core, soil_carbon_total

TREATMENTS = ("unfertilized", "fym_annual", "fym_1852_1871")
FALLOW_YEARS = frozenset({1912, 1933, 1943, 1967})
TEMPERATURE_C = (4.0, 5.0, 8.0, 11.0, 14.0, 17.0, 19.0, 18.0, 15.0, 11.0, 7.0, 5.0)
RAINFALL_MM = (74.0, 59.0, 62.0, 51.0, 52.0, 57.0, 34.0, 55.0, 58.0, 56.0, 75.0, 71.0)
OPEN_PAN_MM = (8.0, 10.0, 27.0, 49.0, 83.0, 99.0, 103.0, 91.0, 69.0, 34.0, 16.0, 8.0)


def _initial_state(total_soc_t_c_ha: float) -> FieldState:
    official_active = (0.1533, 4.4852, 0.6671, 25.8576)
    iom = 2.7
    scale = (total_soc_t_c_ha - iom) / math.fsum(official_active)
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
        iom_c=iom,
        available_p_kg_ha=0.0,
        topsoil_moisture_deficit_mm=0.0,
        crop_development=0.0,
        cumulative_yield_t_dm_ha=0.0,
        aggregate_protection_index=None,
    )


def _plant_inputs(treatment: str, year: int) -> tuple[float, ...]:
    if year in FALLOW_YEARS:
        return (0.0,) * 12
    annual = 1.6
    if treatment == "fym_annual" or (treatment == "fym_1852_1871" and year <= 1876):
        annual = 2.8
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


def _fym_input(treatment: str, year: int, month: int) -> float:
    if treatment == "fym_1852_1871":
        return 3.0 if year <= 1871 and month == 2 else 0.0
    if treatment != "fym_annual":
        return 0.0
    if year == 1931 and month in {2, 11}:
        return 3.0
    application_month = 2 if year <= 1930 else 11
    return 3.0 if month == application_month else 0.0


def _months(treatment: str, start_year: int, end_year: int) -> tuple[CarbonCoreMonth, ...]:
    months: list[CarbonCoreMonth] = []
    for year in range(start_year, end_year + 1):
        plant = _plant_inputs(treatment, year)
        for index in range(12):
            month = index + 1
            plant_c = plant[index]
            fym_c = _fym_input(treatment, year, month)
            dpm = plant_c * 1.44 / 2.44 + fym_c * 0.49
            rpm = plant_c / 2.44 + fym_c * 0.49
            protected = fym_c * 0.02
            covered = year not in FALLOW_YEARS and month in {4, 5, 6, 7}
            months.append(
                CarbonCoreMonth(
                    external_input=CarbonInput(
                        dpm_c=dpm,
                        rpm_c=rpm,
                        protected_soc_c=protected,
                        classification="scenario_assumption",
                        provenance=(
                            "RothC February 2024 Hoosfield treatment input specification; "
                            "not fitted to Phase 9.5 validation observations"
                        ),
                    ),
                    forcing=RothCForcing(
                        mean_air_temperature_c=TEMPERATURE_C[index],
                        precipitation_mm=RAINFALL_MM[index],
                        open_pan_evaporation_mm=OPEN_PAN_MM[index],
                        is_covered=covered,
                        clay_percent=23.4,
                        soil_depth_cm=23.0,
                        provenance=(
                            "Rothamsted monthly water forcing from RothC description; "
                            "temperature is the documented simulator scenario pattern"
                        ),
                    ),
                )
            )
    return tuple(months)


def load_observations(path: str | Path) -> tuple[dict[str, object], ...]:
    """Load the immutable normalized local e-RA extraction."""
    with Path(path).open(encoding="utf-8", newline="") as handle:
        return tuple(dict(row) for row in csv.DictReader(handle))


def _metrics(observed: tuple[float, ...], simulated: tuple[float, ...]) -> dict[str, float]:
    residuals = tuple(s - o for o, s in zip(observed, simulated, strict=True))
    return {
        "mae_t_c_ha": math.fsum(abs(value) for value in residuals) / len(residuals),
        "rmse_t_c_ha": math.sqrt(math.fsum(value * value for value in residuals) / len(residuals)),
        "bias_t_c_ha": math.fsum(residuals) / len(residuals),
    }


def run_hoosfield_validation(
    observation_path: str | Path, parameters: ModelParameters
) -> dict[str, object]:
    """Run uncalibrated 1852--1998 trajectories and score held observations."""
    raw = load_observations(observation_path)
    grouped: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in raw:
        grouped[str(row["treatment"])].append(row)
    results: dict[str, object] = {}
    all_observed: list[float] = []
    all_simulated: list[float] = []
    for treatment in TREATMENTS:
        observations = sorted(grouped[treatment], key=lambda row: int(str(row["year"])))
        initial = float(str(observations[0]["soc_t_c_ha"]))
        simulation = run_carbon_core(
            _initial_state(initial), _months(treatment, 1852, 1998), parameters, seed=9501852
        )
        by_year = {1852: initial}
        for year in range(1852, 1999):
            step_index = (year - 1852 + 1) * 12 - 1
            by_year[year] = soil_carbon_total(simulation.steps[step_index].final_state)
        points = tuple(
            {
                "year": int(str(row["year"])),
                "observed_soc_t_c_ha": float(str(row["soc_t_c_ha"])),
                "simulated_soc_t_c_ha": by_year[int(str(row["year"]))],
                "data_role": row["data_role"],
            }
            for row in observations
        )
        held = tuple(point for point in points if point["data_role"] == "validation")
        observed = tuple(float(str(point["observed_soc_t_c_ha"])) for point in held)
        simulated = tuple(float(str(point["simulated_soc_t_c_ha"])) for point in held)
        all_observed.extend(observed)
        all_simulated.extend(simulated)
        results[treatment] = {
            "metrics": _metrics(observed, simulated),
            "trajectory": points,
            "maximum_monthly_mass_balance_residual_t_c_ha": max(
                abs(step.mass_balance.residual_t_c_ha) for step in simulation.steps
            ),
        }
    return {
        "version": "0.9.5",
        "experiment": "Hoosfield continuous spring barley SOC, 1852-1998",
        "depth_cm": 23,
        "source_version": "e-RA 01-HBSOC1852 v1.0, updated 2021-04-26",
        "source_sha256": "845d0acfecbcac73bdd1f830ceaa6dbb04047a944782a965c81e1ab075e7e76d",
        "calibration": "none; 1852 stocks initialise each trajectory only",
        "run_type": "uncalibrated",
        "aggregate_metrics": _metrics(tuple(all_observed), tuple(all_simulated)),
        "treatments": results,
        "claim_boundary": (
            "This is multi-decade total-SOC validation of the RothC-style core, not AMF or "
            "protected-fraction validation. The one-step parity test remains separate."
        ),
    }
