"""Build and export the versioned Phase 8.5 field-policy-horizon table."""

from __future__ import annotations

import csv
import hashlib
import json
import math
import statistics
from collections import Counter
from pathlib import Path
from typing import IO, Protocol, cast

from soil_simulator.domain.enums import PopulationSplit
from soil_simulator.domain.population import (
    PopulationBatchFieldResult,
    PopulationBatchResult,
    SyntheticField,
    SyntheticPopulation,
)
from soil_simulator.ml.schema import (
    BASE_TARGETS,
    DATASET_VERSION,
    FEATURE_SETS,
    HORIZON_TARGET_APPLICABILITY,
    OBSERVABLE_FEATURE_RATIONALE,
    TARGET_UNITS,
    TARGETS,
    MlDatasetManifest,
    MlRow,
)

METADATA_COLUMNS = (
    "dataset_version",
    "row_id",
    "field_id",
    "empirical_seed_id",
    "archetype",
    "population_split",
    "weather_regime",
    "phosphorus_status",
)
ALL_FEATURE_COLUMNS = FEATURE_SETS["full_simulator_state"].names
CSV_COLUMNS = METADATA_COLUMNS + ALL_FEATURE_COLUMNS + TARGETS


def load_saved_population(path: Path) -> SyntheticPopulation:
    """Load complete saved Phase 7 fields and their compact manifest."""
    payload = cast(dict[str, object], json.loads(path.read_text(encoding="utf-8")))
    manifest = payload.get("manifest", payload.get("population_manifest"))
    fields = payload.get("fields")
    if fields is None or manifest is None:
        raise ValueError("saved Phase 7 JSON must contain complete fields and a manifest")
    return SyntheticPopulation.model_validate({"fields": fields, "manifest": manifest})


def load_saved_batch(path: Path) -> PopulationBatchResult:
    """Load saved Phase 6 batch outcomes produced by the Phase 7 CLI."""
    payload = cast(dict[str, object], json.loads(path.read_text(encoding="utf-8")))
    batch = payload.get("batch", payload)
    return PopulationBatchResult.model_validate(batch)


def load_ml_dataset_csv(path: Path) -> tuple[MlRow, ...]:
    """Restore a versioned flat ML dataset for deterministic artifact replay."""
    rows: list[MlRow] = []
    with path.open(encoding="utf-8", newline="") as handle:
        for raw in csv.DictReader(handle):
            features: dict[str, float | str] = {}
            for name in FEATURE_SETS["full_simulator_state"].numeric:
                features[name] = float(raw[name])
            for name in FEATURE_SETS["full_simulator_state"].categorical:
                features[name] = raw[name]
            targets = {name: float(raw[name]) for name in TARGETS}
            rows.append(
                MlRow(
                    field_id=raw["field_id"],
                    empirical_seed_id=raw["empirical_seed_id"],
                    archetype=raw["archetype"],
                    weather_regime=raw["weather_regime"],
                    phosphorus_status=raw["phosphorus_status"],
                    population_split=PopulationSplit(raw["population_split"]),
                    policy_id=raw["policy_id"],
                    simulation_horizon_months=int(float(raw["simulation_horizon_months"])),
                    features=features,
                    targets=targets,
                )
            )
    if not rows:
        raise ValueError("saved ML dataset is empty")
    result = tuple(rows)
    assert_group_isolation(result)
    return result


class DatasetAuditConfig(Protocol):
    """Minimum configuration surface needed for dataset duplicate auditing."""

    @property
    def near_duplicate_distance(self) -> float: ...


def _weather_regime(annual_rainfall_mm: float, mean_temperature_c: float, region_id: str) -> str:
    phase86_prefix = "phase86-weather-"
    if region_id.startswith(phase86_prefix) and region_id.endswith("-ood"):
        regime = region_id[len(phase86_prefix) : -len("-ood")]
        if regime in {"dry", "hot", "wet", "cool", "hot_dry"}:
            return regime
    if region_id.startswith("phase86-region-"):
        return "temperate"
    if annual_rainfall_mm < 500.0:
        return "dry"
    if annual_rainfall_mm > 850.0:
        return "wet"
    if mean_temperature_c > 13.0:
        return "hot"
    if mean_temperature_c < 7.0:
        return "cool"
    return "temperate"


def _phosphorus_status(available_p_kg_ha: float) -> str:
    if available_p_kg_ha < 10.0:
        return "low"
    if available_p_kg_ha > 30.0:
        return "high"
    return "moderate"


def _management_indicators(history: str) -> tuple[float, float, float]:
    tillage = 2.0 if history in {"conventional_arable", "intensive_inversion_tillage"} else 1.0
    if history in {"reduced_tillage_arable", "cover_cropped_arable"}:
        tillage = 0.5
    cover = 1.0 if "cover" in history else 0.0
    high_input = 1.0 if history in {"high_input_arable", "intensive_inversion_tillage"} else 0.0
    return tillage, cover, high_input


def _field_features(field: SyntheticField, horizon_months: int) -> dict[str, float | str]:
    weather = field.weather[:horizon_months]
    if len(weather) != horizon_months:
        raise ValueError(f"field {field.field.field_id} lacks weather for horizon {horizon_months}")
    years = len(weather) / 12.0
    temperatures = [month.mean_air_temperature_c for month in weather]
    annual_rainfall = math.fsum(month.precipitation_mm for month in weather) / years
    annual_pet = math.fsum(month.potential_evapotranspiration_mm for month in weather) / years
    growing = tuple(month for month in weather if 3 <= month.month <= 9)
    winter = tuple(month for month in weather if month.month >= 10 or month.month <= 2)
    tillage, historical_cover, high_input = _management_indicators(field.management_history)
    phosphorus_status = _phosphorus_status(field.initial_state.available_p_kg_ha)
    values: dict[str, float | str] = {
        "soil_depth_cm": field.field.soil_depth_cm,
        "clay_percent": field.field.clay_percent,
        "silt_percent": field.field.silt_percent,
        "sand_percent": field.field.sand_percent,
        "bulk_density_g_cm3": field.field.bulk_density_g_cm3,
        "ph": field.field.ph,
        "cation_exchange_capacity_cmolc_kg": (field.field.cation_exchange_capacity_cmolc_kg),
        "baseline_total_nitrogen_percent": field.field.baseline_total_nitrogen_percent,
        "baseline_soc_t_c_ha": field.field.baseline_soc_t_c_ha,
        "baseline_soc_concentration_g_kg": (
            10.0
            * field.field.baseline_soc_t_c_ha
            / (field.field.bulk_density_g_cm3 * field.field.soil_depth_cm)
        ),
        "weather_mean_temperature_c": statistics.fmean(temperatures),
        "weather_temperature_sd_c": statistics.pstdev(temperatures),
        "weather_annual_rainfall_mm": annual_rainfall,
        "weather_annual_pet_mm": annual_pet,
        "growing_season_mean_temperature_c": statistics.fmean(
            month.mean_air_temperature_c for month in growing
        ),
        "growing_season_rainfall_mm_per_year": (
            math.fsum(month.precipitation_mm for month in growing) / years
        ),
        "growing_season_pet_mm_per_year": (
            math.fsum(month.potential_evapotranspiration_mm for month in growing) / years
        ),
        "winter_rainfall_mm_per_year": (
            math.fsum(month.precipitation_mm for month in winter) / years
        ),
        "climate_aridity_index": annual_rainfall / annual_pet if annual_pet > 0.0 else 0.0,
        "dry_month_fraction": (
            math.fsum(
                1.0
                for month in weather
                if month.precipitation_mm < month.potential_evapotranspiration_mm
            )
            / len(weather)
        ),
        "management_history_tillage_intensity": tillage,
        "management_history_cover_crop_indicator": historical_cover,
        "management_history_high_input_indicator": high_input,
        "simulation_horizon_months": float(horizon_months),
        "drainage_class": field.field.drainage_class,
        "management_history": field.management_history,
        "policy_id": "",  # Filled from the outcome row below.
        "initial_phosphorus_status": phosphorus_status,
        "initial_available_phosphorus_kg_p_ha": field.initial_state.available_p_kg_ha,
        "initial_plant_c_t_ha": field.initial_state.plant_c,
        "initial_root_c_t_ha": field.initial_state.root_c,
        "initial_amf_live_c_t_ha": field.initial_state.amf_live_c,
        "initial_amf_necromass_c_t_ha": field.initial_state.amf_necromass_c,
        "initial_dpm_c_t_ha": field.initial_state.dpm_c,
        "initial_rpm_c_t_ha": field.initial_state.rpm_c,
        "initial_microbial_c_t_ha": field.initial_state.microbial_c,
        "initial_protected_soc_proxy_t_c_ha": field.initial_state.protected_soc_c,
        "initial_iom_c_t_ha": field.initial_state.iom_c,
        "initial_topsoil_moisture_deficit_mm": (field.initial_state.topsoil_moisture_deficit_mm),
        "spinup_equilibrium_annual_input_t_c_ha": (field.spinup.equilibrium_annual_input_t_c_ha),
    }
    draw_names = {
        "photosynthate_allocation_fraction",
        "carbon_use_efficiency",
        "turnover_per_month",
        "necromass_stabilisation_fraction",
        "p_uptake_vmax",
        "conventional_amf_pulse_mortality",
        "cover_crop_establishment_success",
    }
    for name in draw_names:
        values[f"latent_{name}"] = field.uncertainty_value(name)
    if set(values) != set(ALL_FEATURE_COLUMNS):
        missing = sorted(set(ALL_FEATURE_COLUMNS) - set(values))
        extra = sorted(set(values) - set(ALL_FEATURE_COLUMNS))
        raise ValueError(f"feature construction mismatch; missing={missing}, extra={extra}")
    return values


def _base_targets(outcome: PopulationBatchFieldResult) -> dict[str, float]:
    return {
        "final_total_soc_t_c_ha": outcome.final_total_soc_t_c_ha,
        "final_protected_soc_proxy_t_c_ha": outcome.final_protected_soc_proxy_t_c_ha,
        "crop_yield_t_dm_ha": outcome.yield_t_dm_ha,
        "cumulative_respiration_t_c_ha": outcome.cumulative_respiration_t_c_ha,
        "final_available_phosphorus_kg_p_ha": outcome.final_available_phosphorus_kg_p_ha,
        "intervention_cost_gbp_ha": outcome.cost_gbp_ha,
        "emissions_proxy_kg_co2e_ha": outcome.emissions_proxy_kg_co2e_ha,
    }


def construct_paired_targets(
    outcomes: tuple[PopulationBatchFieldResult, ...],
) -> dict[tuple[str, str, int], dict[str, float]]:
    """Construct explicit outcomes and same-field/horizon minus-baseline effects."""
    by_key: dict[tuple[str, str, int], PopulationBatchFieldResult] = {}
    baselines: dict[tuple[str, int], PopulationBatchFieldResult] = {}
    for outcome in outcomes:
        key = (outcome.field_id, outcome.policy_id, outcome.simulation_horizon_months)
        if key in by_key:
            raise ValueError(f"duplicate batch outcome {key}")
        by_key[key] = outcome
        if outcome.policy_id == "baseline":
            baseline_key = (outcome.field_id, outcome.simulation_horizon_months)
            if baseline_key in baselines:
                raise ValueError(f"duplicate paired baseline {baseline_key}")
            baselines[baseline_key] = outcome
    targets: dict[tuple[str, str, int], dict[str, float]] = {}
    for key, outcome in by_key.items():
        baseline_key = (outcome.field_id, outcome.simulation_horizon_months)
        if baseline_key not in baselines:
            raise ValueError(f"missing paired baseline for field/horizon {baseline_key}")
        values = _base_targets(outcome)
        baseline_values = _base_targets(baselines[baseline_key])
        values.update(
            {f"delta_{name}": values[name] - baseline_values[name] for name in BASE_TARGETS}
        )
        targets[key] = values
    return targets


def assert_group_isolation(rows: tuple[MlRow, ...]) -> None:
    """Require fields and empirical seed groups to occur in exactly one frozen split."""
    field_splits: dict[str, set[PopulationSplit]] = {}
    seed_splits: dict[str, set[PopulationSplit]] = {}
    for row in rows:
        field_splits.setdefault(row.field_id, set()).add(row.population_split)
        seed_splits.setdefault(row.empirical_seed_id, set()).add(row.population_split)
    crossing_fields = sorted(key for key, splits in field_splits.items() if len(splits) != 1)
    crossing_seeds = sorted(key for key, splits in seed_splits.items() if len(splits) != 1)
    if crossing_fields or crossing_seeds:
        raise ValueError(
            f"group leakage detected; fields={crossing_fields}, empirical_seeds={crossing_seeds}"
        )


def _field_duplicate_audit(
    rows: tuple[MlRow, ...], threshold: float
) -> tuple[tuple[tuple[str, str], ...], tuple[tuple[str, str, float], ...]]:
    field_rows: dict[str, MlRow] = {}
    for row in rows:
        field_rows.setdefault(row.field_id, row)
    numeric_names = tuple(
        name
        for name in FEATURE_SETS["observable_features"].numeric
        if name != "simulation_horizon_months"
    )
    fields = sorted(field_rows)
    columns = {
        name: [float(field_rows[field].features[name]) for field in fields]
        for name in numeric_names
    }
    ranges = {name: max(values) - min(values) for name, values in columns.items()}
    exact_signatures: dict[tuple[float, ...], list[str]] = {}
    for field in fields:
        signature = tuple(
            round(float(field_rows[field].features[name]), 12) for name in numeric_names
        )
        exact_signatures.setdefault(signature, []).append(field)
    exact: list[tuple[str, str]] = []
    for duplicates in exact_signatures.values():
        for left_index, left in enumerate(duplicates):
            exact.extend((left, right) for right in duplicates[left_index + 1 :])
    near: list[tuple[str, str, float]] = []
    for left_index, left in enumerate(fields):
        for right in fields[left_index + 1 :]:
            squared = 0.0
            used = 0
            for name in numeric_names:
                scale = ranges[name]
                if scale > 0.0:
                    difference = (
                        float(field_rows[left].features[name])
                        - float(field_rows[right].features[name])
                    ) / scale
                    squared += difference * difference
                    used += 1
            distance = math.sqrt(squared / used) if used else 0.0
            if 0.0 < distance <= threshold:
                near.append((left, right, distance))
    return tuple(exact), tuple(near)


def _dataset_hash(rows: tuple[MlRow, ...]) -> str:
    payload = [
        {
            "row_id": row.row_id,
            "empirical_seed_id": row.empirical_seed_id,
            "archetype": row.archetype,
            "population_split": row.population_split.value,
            "weather_regime": row.weather_regime,
            "phosphorus_status": row.phosphorus_status,
            "features": row.features,
            "targets": row.targets,
        }
        for row in rows
    ]
    canonical = json.dumps(
        payload, allow_nan=False, ensure_ascii=True, separators=(",", ":"), sort_keys=True
    )
    return hashlib.sha256(canonical.encode()).hexdigest()


def build_ml_dataset(
    population: SyntheticPopulation,
    batch: PopulationBatchResult,
    config: DatasetAuditConfig,
    *,
    dataset_version: str = DATASET_VERSION,
) -> tuple[tuple[MlRow, ...], MlDatasetManifest]:
    """Join saved Phase 7 fields to Phase 6 outcomes without recomputing simulation state."""
    if population.manifest.population_hash != batch.population_hash:
        raise ValueError("population and batch hashes do not match")
    if batch.failures:
        raise ValueError("cannot build an ML dataset from a batch containing simulator failures")
    fields = {field.field.field_id: field for field in population.fields}
    paired = construct_paired_targets(batch.results)
    rows: list[MlRow] = []
    for outcome in sorted(
        batch.results,
        key=lambda item: (item.field_id, item.policy_id, item.simulation_horizon_months),
    ):
        if outcome.field_id not in fields:
            raise ValueError(f"batch outcome has no Phase 7 field: {outcome.field_id}")
        field = fields[outcome.field_id]
        if outcome.population_split is not field.population_split:
            raise ValueError(f"batch split changed for field {outcome.field_id}")
        features = _field_features(field, outcome.simulation_horizon_months)
        features["policy_id"] = outcome.policy_id
        key = (outcome.field_id, outcome.policy_id, outcome.simulation_horizon_months)
        rows.append(
            MlRow(
                field_id=outcome.field_id,
                empirical_seed_id=field.empirical_seed_id,
                archetype=field.archetype,
                weather_regime=_weather_regime(
                    float(features["weather_annual_rainfall_mm"]),
                    float(features["weather_mean_temperature_c"]),
                    field.region_id,
                ),
                phosphorus_status=str(features["initial_phosphorus_status"]),
                population_split=field.population_split,
                policy_id=outcome.policy_id,
                simulation_horizon_months=outcome.simulation_horizon_months,
                features=features,
                targets=paired[key],
            )
        )
    result = tuple(rows)
    assert_group_isolation(result)
    exact, near = _field_duplicate_audit(result, config.near_duplicate_distance)
    if exact:
        raise ValueError(f"exact duplicate synthetic fields detected: {exact}")
    split_counts = Counter(row.population_split.value for row in result)
    split_groups = {
        split: len({row.empirical_seed_id for row in result if row.population_split.value == split})
        for split in sorted(split_counts)
    }
    manifest = MlDatasetManifest(
        dataset_version=dataset_version,
        dataset_hash=_dataset_hash(result),
        population_hash=population.manifest.population_hash,
        population_configuration_hash=population.manifest.configuration_hash,
        model_configuration_hash=population.manifest.model_configuration_hash,
        source_dataset_name=population.manifest.dataset_name,
        source_dataset_version=population.manifest.dataset_version,
        source_batch_scenario_version=batch.scenario_version,
        row_count=len(result),
        field_count=len(fields),
        empirical_seed_group_count=len({field.empirical_seed_id for field in population.fields}),
        split_counts=dict(sorted(split_counts.items())),
        split_empirical_seed_group_counts=split_groups,
        observable_features=FEATURE_SETS["observable_features"].names,
        full_simulator_state=FEATURE_SETS["full_simulator_state"].names,
        targets=TARGETS,
        target_units=TARGET_UNITS,
        horizon_target_applicability=HORIZON_TARGET_APPLICABILITY,
        observable_feature_measurement_rationale=OBSERVABLE_FEATURE_RATIONALE,
        revised_covariance_assumptions=(
            "SOC and bulk density use separate permuted donors in the expanded synthetic "
            "seed foundation.",
            "Independent SOC log residuals and bulk-density residuals dominate a weakened "
            "shared factor.",
            "Available-P and initial AMF stocks use diverse donors with only weak negative "
            "coupling.",
            "Soil, weather, management history, and AMF combinations remain synthetic and "
            "non-representative.",
        ),
        exact_duplicate_field_pairs=exact,
        near_duplicate_field_pairs=near,
        provenance=(
            f"Phase {dataset_version} deterministic join of saved Phase 7-compatible field "
            "manifests and "
            "saved Phase 6 batch outcomes; no target-derived feature construction"
        ),
    )
    return result, manifest


def _write_rows(handle: IO[str], rows: tuple[MlRow, ...], dataset_version: str) -> None:
    writer = csv.DictWriter(handle, fieldnames=CSV_COLUMNS, lineterminator="\n")
    writer.writeheader()
    for row in rows:
        values: dict[str, str | float | int] = {
            "dataset_version": dataset_version,
            "row_id": row.row_id,
            "field_id": row.field_id,
            "empirical_seed_id": row.empirical_seed_id,
            "archetype": row.archetype,
            "population_split": row.population_split.value,
            "weather_regime": row.weather_regime,
            "phosphorus_status": row.phosphorus_status,
            "policy_id": row.policy_id,
            "simulation_horizon_months": row.simulation_horizon_months,
        }
        values.update(row.features)
        values.update(row.targets)
        writer.writerow(values)


def write_ml_dataset(
    path: Path, rows: tuple[MlRow, ...], *, dataset_version: str = DATASET_VERSION
) -> None:
    """Write stable CSV with one row per field-policy-horizon."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        _write_rows(handle, rows, dataset_version)


def write_dataset_manifest(path: Path, manifest: MlDatasetManifest) -> None:
    """Write finite, stable manifest JSON."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(manifest.model_dump(mode="json"), allow_nan=False, indent=2, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )
