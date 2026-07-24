"""Offline empirical soil--climate harmonisation for Phase 9.6.

SoilGrids median predictions are thickness-harmonised to the model's 0--23 cm
layer. NASA POWER/MERRA-2 monthly values remain grouped as complete source
years. The module performs no network access.
"""

from __future__ import annotations

import calendar
import hashlib
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from soil_simulator.domain.models import VersionedInput
from soil_simulator.domain.population import (
    EmpiricalDataset,
    EmpiricalSeedRecord,
    WeatherYearRecord,
)
from soil_simulator.phase96.values import as_float, as_int

MONTH_NAMES = ("JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC")
DEPTH_WEIGHTS_CM = {"0-5cm": 5.0, "5-15cm": 10.0, "15-30cm": 8.0}
REQUIRED_SOIL_PROPERTIES = ("bdod", "cec", "clay", "nitrogen", "phh2o", "sand", "silt", "soc")
POWER_PARAMETERS = ("T2M", "T2M_MAX", "T2M_MIN", "PRECTOTCORR")


@dataclass(frozen=True)
class PilotLocation:
    """One rounded non-sensitive coordinate in the predeclared GB sampling frame."""

    location_id: str
    region: str
    latitude_deg: float
    longitude_deg: float


PILOT_LOCATIONS = tuple(
    PilotLocation(*row)
    for row in (
        ("gb001", "south_west", 50.4, -4.8),
        ("gb002", "south_west", 50.7, -3.7),
        ("gb003", "south_west", 50.8, -2.3),
        ("gb004", "south_west", 51.1, -2.7),
        ("gb005", "south", 51.2, -1.8),
        ("gb006", "south", 51.1, -1.2),
        ("gb007", "south", 50.9, -0.3),
        ("gb008", "south_east", 51.2, 0.8),
        ("gb009", "south_east", 51.3, -0.5),
        ("gb010", "south", 51.5, -1.0),
        ("gb011", "south", 51.8, -1.3),
        ("gb012", "west_midlands", 51.9, -2.2),
        ("gb013", "west_midlands", 52.1, -2.7),
        ("gb014", "west_midlands", 52.2, -2.2),
        ("gb015", "west_midlands", 52.3, -1.5),
        ("gb016", "east_midlands", 52.3, -0.8),
        ("gb017", "east", 52.0, -0.5),
        ("gb018", "east", 52.3, 0.0),
        ("gb019", "east", 52.2, 0.8),
        ("gb020", "east", 52.7, 1.0),
        ("gb021", "south_east", 51.8, 0.6),
        ("gb022", "south_east", 51.9, -0.2),
        ("gb023", "east_midlands", 52.7, -1.1),
        ("gb024", "east_midlands", 53.0, -1.0),
        ("gb025", "east_midlands", 53.2, -0.3),
        ("gb026", "east_midlands", 53.0, -1.6),
        ("gb027", "west_midlands", 52.7, -2.6),
        ("gb028", "west_midlands", 52.9, -2.0),
        ("gb029", "north_west", 53.1, -2.5),
        ("gb030", "yorkshire", 53.8, -1.2),
        ("gb031", "yorkshire", 53.9, -0.5),
        ("gb032", "yorkshire", 54.2, -1.4),
        ("gb033", "north_west", 53.8, -2.7),
        ("gb034", "north_west", 54.5, -2.8),
        ("gb035", "north_east", 54.7, -1.6),
        ("gb036", "north_east", 55.1, -1.8),
        ("gb037", "wales", 51.8, -4.8),
        ("gb038", "wales", 51.9, -4.2),
        ("gb039", "wales", 52.2, -4.0),
        ("gb040", "wales", 52.3, -3.3),
        ("gb041", "wales", 51.5, -3.4),
        ("gb042", "wales", 51.8, -2.9),
        ("gb043", "wales", 53.1, -3.0),
        ("gb044", "scotland_south", 55.0, -3.6),
        ("gb045", "scotland_south", 55.6, -2.7),
        ("gb046", "scotland_south", 55.6, -4.5),
        ("gb047", "scotland_east", 55.9, -3.3),
        ("gb048", "scotland_east", 56.2, -3.1),
        ("gb049", "scotland_east", 56.6, -2.9),
        ("gb050", "scotland_east", 56.4, -3.5),
        ("gb051", "scotland_north_east", 57.2, -2.2),
        ("gb052", "scotland_north_east", 57.6, -3.3),
        ("gb053", "scotland_north", 57.6, -4.2),
        ("gb054", "scotland_south", 55.7, -3.8),
        ("gb055", "scotland_central", 56.1, -4.0),
        ("gb056", "scotland_north_east", 57.4, -2.8),
        ("gb057", "south_east", 51.0, 0.6),
        ("gb058", "east_midlands", 52.4, -0.2),
        ("gb059", "east", 52.8, 0.2),
        ("gb060", "yorkshire", 53.4, -1.0),
        ("gb061", "yorkshire", 53.5, -0.3),
        ("gb062", "north_west", 54.0, -2.0),
        ("gb063", "north_east", 55.0, -2.5),
        ("gb064", "scotland_east", 56.0, -2.8),
    )
)


def sha256_file(path: str | Path) -> str:
    """Return the byte-level SHA-256 digest of one immutable source or artifact."""
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _load_json(path: Path) -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))


def _soil_layers(response: dict[str, Any]) -> dict[str, dict[str, Any]]:
    layers = response.get("properties", {}).get("layers", [])
    return {str(layer["name"]): cast(dict[str, Any], layer) for layer in layers}


def _depth_values(layer: dict[str, Any]) -> dict[str, float]:
    divisor = float(layer["unit_measure"]["d_factor"])
    result: dict[str, float] = {}
    for depth in cast(list[dict[str, Any]], layer["depths"]):
        raw = depth["values"].get("Q0.5")
        if raw is None:
            raise ValueError(f"missing Q0.5 for {layer['name']} {depth['label']}")
        result[str(depth["label"])] = float(raw) / divisor
    missing = set(DEPTH_WEIGHTS_CM) - set(result)
    if missing:
        raise ValueError(f"missing required depths for {layer['name']}: {sorted(missing)}")
    return result


def _weighted_0_23(values: dict[str, float]) -> float:
    return math.fsum(values[depth] * weight for depth, weight in DEPTH_WEIGHTS_CM.items()) / 23.0


def harmonise_soilgrids(response: dict[str, Any]) -> tuple[dict[str, float], dict[str, object]]:
    """Convert SoilGrids medians to one 0--23 cm model-layer record.

    SOC stock is calculated layer by layer as concentration [g kg-1] times dry
    bulk density [g cm-3] times thickness [cm] times 0.1, yielding t C ha-1.
    """
    layers = _soil_layers(response)
    missing = set(REQUIRED_SOIL_PROPERTIES) - set(layers)
    if missing:
        raise ValueError(f"missing SoilGrids properties: {sorted(missing)}")
    values = {name: _depth_values(layers[name]) for name in REQUIRED_SOIL_PROPERTIES}
    raw_texture = {name: _weighted_0_23(values[name]) for name in ("clay", "silt", "sand")}
    texture_total = math.fsum(raw_texture.values())
    if texture_total <= 0.0:
        raise ValueError("non-positive SoilGrids texture total")
    texture = {name: value * 100.0 / texture_total for name, value in raw_texture.items()}
    soc_stock = math.fsum(
        values["soc"][depth] * values["bdod"][depth] * thickness * 0.1
        for depth, thickness in DEPTH_WEIGHTS_CM.items()
    )
    record = {
        "clay_percent": texture["clay"],
        "silt_percent": texture["silt"],
        "sand_percent": texture["sand"],
        "bulk_density_g_cm3": _weighted_0_23(values["bdod"]),
        "ph_h2o": _weighted_0_23(values["phh2o"]),
        "cation_exchange_capacity_cmolc_kg": _weighted_0_23(values["cec"]),
        "total_nitrogen_percent": _weighted_0_23(values["nitrogen"]) / 10.0,
        "soc_concentration_g_kg": _weighted_0_23(values["soc"]),
        "soc_stock_t_c_ha_0_23cm": soc_stock,
    }
    correction = {
        "rule": "renormalise thickness-weighted independently predicted texture fractions",
        "pre_correction_texture_total_percent": texture_total,
        "absolute_closure_correction_percentage_points": abs(texture_total - 100.0),
        "corrected": not math.isclose(texture_total, 100.0, abs_tol=0.01),
    }
    return record, correction


def thornthwaite_pet_mm_month(
    latitude_deg: float,
    year: int,
    month: int,
    annual_monthly_temperature_c: tuple[float, ...],
) -> float:
    """Return Thornthwaite monthly PET [mm] from monthly mean temperature.

    This avoids misusing monthly absolute T2M_MAX/T2M_MIN extrema as mean
    daily extrema. Negative monthly temperatures contribute zero PET.
    """
    if len(annual_monthly_temperature_c) != 12:
        raise ValueError("Thornthwaite PET requires 12 monthly temperatures")
    heat_index = math.fsum(
        (max(value, 0.0) / 5.0) ** 1.514 for value in annual_monthly_temperature_c
    )
    if heat_index <= 0.0:
        return 0.0
    exponent = 6.75e-7 * heat_index**3 - 7.71e-5 * heat_index**2 + 1.792e-2 * heat_index + 0.49239
    days = calendar.monthrange(year, month)[1]
    day_of_year = sum(calendar.monthrange(year, prior)[1] for prior in range(1, month)) + 15
    declination = 0.409 * math.sin(2.0 * math.pi * day_of_year / 365.0 - 1.39)
    latitude = math.radians(latitude_deg)
    sunset_argument = -math.tan(latitude) * math.tan(declination)
    sunset_angle = math.acos(max(-1.0, min(1.0, sunset_argument)))
    daylight_hours = 24.0 * sunset_angle / math.pi
    temperature = max(annual_monthly_temperature_c[month - 1], 0.0)
    if temperature == 0.0:
        return 0.0
    return (
        16.0
        * (daylight_hours / 12.0)
        * (days / 30.0)
        * math.pow(10.0 * temperature / heat_index, exponent)
    )


def _power_grids(raw_directory: Path) -> dict[str, dict[tuple[float, float], dict[str, float]]]:
    grids: dict[str, dict[tuple[float, float], dict[str, float]]] = {}
    for parameter in POWER_PARAMETERS:
        response = _load_json(raw_directory / "nasa_power" / f"{parameter}.json")
        grid: dict[tuple[float, float], dict[str, float]] = {}
        for feature in cast(list[dict[str, Any]], response["features"]):
            longitude, latitude, *_ = feature["geometry"]["coordinates"]
            values = feature["properties"]["parameter"][parameter]
            grid[(float(latitude), float(longitude))] = {
                str(key): float(value)
                for key, value in values.items()
                if not str(key).endswith("13")
            }
        grids[parameter] = grid
    common = set.intersection(*(set(grid) for grid in grids.values()))
    if not common:
        raise ValueError("NASA POWER parameter grids have no common cells")
    return grids


def _nearest_grid_cell(
    latitude: float, longitude: float, cells: set[tuple[float, float]]
) -> tuple[float, float]:
    return min(cells, key=lambda cell: (cell[0] - latitude) ** 2 + (cell[1] - longitude) ** 2)


def build_empirical_records(
    raw_directory: str | Path,
) -> tuple[list[dict[str, object]], list[dict[str, object]], list[dict[str, object]]]:
    """Build paired soil/location and monthly-climate records entirely offline."""
    raw = Path(raw_directory)
    grids = _power_grids(raw)
    common_cells = set.intersection(*(set(grid) for grid in grids.values()))
    locations: list[dict[str, object]] = []
    monthly: list[dict[str, object]] = []
    corrections: list[dict[str, object]] = []
    for location in PILOT_LOCATIONS:
        try:
            soil, correction = harmonise_soilgrids(
                _load_json(raw / "soilgrids" / f"{location.location_id}.json")
            )
        except ValueError as exc:
            corrections.append(
                {
                    "location_id": location.location_id,
                    "source_record_status": "rejected",
                    "reasons": str(exc),
                }
            )
            continue
        climate_cell = _nearest_grid_cell(
            location.latitude_deg, location.longitude_deg, common_cells
        )
        location_record: dict[str, object] = {
            "location_id": location.location_id,
            "region": location.region,
            "latitude_deg_rounded_0_1": location.latitude_deg,
            "longitude_deg_rounded_0_1": location.longitude_deg,
            "climate_grid_latitude_deg": climate_cell[0],
            "climate_grid_longitude_deg": climate_cell[1],
            "soil_depth_cm": 23.0,
            **soil,
        }
        location_monthly: list[dict[str, object]] = []
        missing_climate_reason: str | None = None
        for year in range(2001, 2021):
            annual_temperatures = tuple(
                grids["T2M"][climate_cell][f"{year:04d}{month:02d}"] for month in range(1, 13)
            )
            for month in range(1, 13):
                key = f"{year:04d}{month:02d}"
                temperature = grids["T2M"][climate_cell][key]
                maximum = grids["T2M_MAX"][climate_cell][key]
                minimum = grids["T2M_MIN"][climate_cell][key]
                precipitation_rate = grids["PRECTOTCORR"][climate_cell][key]
                source_values = (temperature, maximum, minimum, precipitation_rate)
                if any(value <= -900.0 or not math.isfinite(value) for value in source_values):
                    missing_climate_reason = (
                        f"missing NASA POWER value at {location.location_id} {key}"
                    )
                    break
                days = calendar.monthrange(year, month)[1]
                location_monthly.append(
                    {
                        "location_id": location.location_id,
                        "region": location.region,
                        "year": year,
                        "month": month,
                        "mean_air_temperature_c": temperature,
                        "minimum_air_temperature_c": minimum,
                        "maximum_air_temperature_c": maximum,
                        "precipitation_mm_month": precipitation_rate * days,
                        "potential_evapotranspiration_mm_month": thornthwaite_pet_mm_month(
                            location.latitude_deg,
                            year,
                            month,
                            annual_temperatures,
                        ),
                    }
                )
            if missing_climate_reason is not None:
                break
        if missing_climate_reason is not None:
            corrections.append(
                {
                    "location_id": location.location_id,
                    "source_record_status": "rejected",
                    "reasons": missing_climate_reason,
                }
            )
            continue
        locations.append(location_record)
        monthly.extend(location_monthly)
        corrections.append(
            {
                "location_id": location.location_id,
                "source_record_status": "accepted",
                **correction,
            }
        )
    return locations, monthly, corrections


def _archetype(record: dict[str, object]) -> str:
    if as_float(record["ph_h2o"]) < 5.5:
        return "acidic_empirical_location"
    if as_float(record["clay_percent"]) >= 30.0:
        return "high_clay_empirical_location"
    if as_float(record["soc_stock_t_c_ha_0_23cm"]) < 35.0:
        return "low_soc_empirical_location"
    return "moderate_empirical_location"


def to_empirical_dataset(
    locations: list[dict[str, object]], monthly: list[dict[str, object]]
) -> EmpiricalDataset:
    """Convert observable records to the existing generator contract.

    Available P, AMF initial stocks, drainage and management history are not
    observed by the pilot and remain explicitly labelled scenario assumptions.
    """
    by_location: dict[str, list[dict[str, object]]] = {}
    for row in monthly:
        by_location.setdefault(str(row["location_id"]), []).append(row)
    seeds: list[EmpiricalSeedRecord] = []
    weather: list[WeatherYearRecord] = []
    for record in locations:
        location_id = str(record["location_id"])
        seeds.append(
            EmpiricalSeedRecord(
                seed_id=location_id,
                region_id=location_id,
                archetype=_archetype(record),
                latitude_deg=as_float(record["latitude_deg_rounded_0_1"]),
                longitude_deg=as_float(record["longitude_deg_rounded_0_1"]),
                clay_percent=as_float(record["clay_percent"]),
                silt_percent=as_float(record["silt_percent"]),
                sand_percent=as_float(record["sand_percent"]),
                ph=as_float(record["ph_h2o"]),
                soc_t_c_ha=as_float(record["soc_stock_t_c_ha_0_23cm"]),
                bulk_density_g_cm3=as_float(record["bulk_density_g_cm3"]),
                available_p_kg_ha=20.0,
                cation_exchange_capacity_cmolc_kg=as_float(
                    record["cation_exchange_capacity_cmolc_kg"]
                ),
                total_nitrogen_percent=as_float(record["total_nitrogen_percent"]),
                amf_live_c_t_ha=0.20,
                amf_necromass_c_t_ha=0.10,
                drainage_class="not_observed_scenario_assumption",
                management_history="not_observed_scenario_assumption",
                eligible_interventions=(
                    "baseline",
                    "conventional_tillage",
                    "reduced_tillage",
                    "cover_crop",
                    "phosphorus",
                    "farmyard_manure",
                ),
                provenance=(
                    "SoilGrids 2.0 observable 0-23 cm pilot record; available P, AMF stocks, "
                    "drainage and management history are separate scenario assumptions A077-A078"
                ),
            )
        )
        rows = by_location[location_id]
        for year in range(2001, 2021):
            year_rows = sorted(
                (row for row in rows if as_int(row["year"]) == year),
                key=lambda row: as_int(row["month"]),
            )
            if len(year_rows) != 12:
                raise ValueError(f"incomplete weather year {location_id} {year}")
            weather.append(
                WeatherYearRecord(
                    weather_year_id=f"nasa-power-{location_id}-{year}",
                    region_id=location_id,
                    source_year=year,
                    temperature_c=tuple(
                        as_float(row["mean_air_temperature_c"]) for row in year_rows
                    ),
                    rainfall_mm=tuple(as_float(row["precipitation_mm_month"]) for row in year_rows),
                    evapotranspiration_mm=tuple(
                        as_float(row["potential_evapotranspiration_mm_month"]) for row in year_rows
                    ),
                    provenance=(
                        "NASA POWER v10/MERRA-2 monthly 2001-2020; precipitation rate converted "
                        "to monthly total; Thornthwaite PET from monthly mean temperature"
                    ),
                )
            )
    return EmpiricalDataset(
        dataset_name="phase96_soilgrids_power_gb_pilot",
        dataset_version="1.0.0",
        adapter_name="phase96_cached_json",
        adapter_version="1.0.0",
        source_datasets=(
            VersionedInput(name="SoilGrids", version="2.0 Q0.5", provenance="ISRIC CC BY 4.0"),
            VersionedInput(
                name="NASA POWER", version="v10; MERRA-2 2001-2020", provenance="NASA CC0"
            ),
        ),
        seeds=tuple(seeds),
        weather_years=tuple(weather),
        provenance=(
            "56 rounded GB locations paired by location with immutable SoilGrids and NASA POWER "
            "source extracts; empirical observables remain separate from latent priors"
        ),
    )
