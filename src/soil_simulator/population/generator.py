"""Deterministic coherent Phase 7 synthetic-field population generator."""

from __future__ import annotations

import hashlib
import json
import math
import random

from soil_simulator.domain.enums import ParameterSource, PopulationSplit
from soil_simulator.domain.models import FieldProperties, ModelParameters, WeatherMonth
from soil_simulator.domain.population import (
    EmpiricalDataset,
    EmpiricalSeedRecord,
    FieldManifestEntry,
    PopulationGenerationConfig,
    PopulationManifest,
    RejectionRecord,
    SyntheticField,
    SyntheticPopulation,
    UncertaintyDraw,
)
from soil_simulator.population.quality import SimulatorProbe, quality_control
from soil_simulator.population.spinup import spin_up_carbon_pools

POPULATION_PROVENANCE = (
    "soil_simulator Phase 7 synthetic population v0.7.0; empirical seed plus "
    "bounded correlated perturbation; synthetic success is not field validation"
)


def _derived_seed(base_seed: int, label: str, index: int) -> int:
    payload = f"{base_seed}:{label}:{index}".encode()
    return int.from_bytes(hashlib.sha256(payload).digest()[:8], "big")


def _clamp(value: float, lower: float, upper: float) -> float:
    return min(upper, max(lower, value))


def _bounded_seed_relative(value: float, seed_value: float, relative_limit: float) -> float:
    return _clamp(value, seed_value * (1.0 - relative_limit), seed_value * (1.0 + relative_limit))


def _compositional_texture(
    seed: EmpiricalSeedRecord, rng: random.Random, logratio_sd: float
) -> tuple[float, float, float]:
    """Perturb texture in additive-log-ratio space and return an exact composition."""
    clay_logratio = math.log(seed.clay_percent / seed.sand_percent) + rng.gauss(0.0, logratio_sd)
    silt_logratio = math.log(seed.silt_percent / seed.sand_percent) + rng.gauss(0.0, logratio_sd)
    clay_exp = math.exp(clay_logratio)
    silt_exp = math.exp(silt_logratio)
    denominator = clay_exp + silt_exp + 1.0
    clay = 100.0 * clay_exp / denominator
    silt = 100.0 * silt_exp / denominator
    sand = 100.0 - clay - silt
    return clay, silt, sand


def _draw(
    *,
    name: str,
    value: float,
    unit: str,
    distribution: str,
    distribution_parameters: str,
    classification: ParameterSource,
    random_seed: int,
    provenance: str,
) -> UncertaintyDraw:
    return UncertaintyDraw(
        name=name,
        value=value,
        unit=unit,
        distribution=distribution,
        distribution_parameters=distribution_parameters,
        classification=classification,
        random_seed=random_seed,
        provenance=provenance,
    )


def _latent_draws(
    rng: random.Random, biological_seed: int, parameters: ModelParameters
) -> tuple[UncertaintyDraw, ...]:
    allocation = 0.02 + rng.betavariate(2.0, 8.0) * 0.18
    cue = rng.triangular(0.30, 0.65, 0.45)
    turnover = math.exp(rng.uniform(math.log(0.1), math.log(6.0)))
    stabilisation = 0.02 + rng.betavariate(2.0, 5.0) * 0.48
    p_vmax = rng.triangular(0.2, 3.0, 1.0)
    tillage_mortality = rng.triangular(0.0, 0.60, 0.25)
    cover_success = rng.betavariate(8.0, 2.0)
    return (
        _draw(
            name="photosynthate_allocation_fraction",
            value=allocation,
            unit="fraction",
            distribution="beta_scaled",
            distribution_parameters="alpha=2,beta=8,min=0.02,max=0.20",
            classification=parameters.amf.photosynthate_allocation_fraction.classification,
            random_seed=biological_seed,
            provenance="A003-A004 literature-informed broad prior",
        ),
        _draw(
            name="carbon_use_efficiency",
            value=cue,
            unit="fraction",
            distribution="triangular",
            distribution_parameters="min=0.30,mode=0.45,max=0.65",
            classification=parameters.amf.carbon_use_efficiency.classification,
            random_seed=biological_seed,
            provenance="A006 provisional AMF CUE prior",
        ),
        _draw(
            name="turnover_per_month",
            value=turnover,
            unit="month^-1",
            distribution="log_uniform",
            distribution_parameters="min=0.1,max=6.0",
            classification=parameters.amf.turnover_per_month.classification,
            random_seed=biological_seed,
            provenance="A005 broad literature-informed turnover prior",
        ),
        _draw(
            name="necromass_stabilisation_fraction",
            value=stabilisation,
            unit="fraction",
            distribution="beta_scaled",
            distribution_parameters="alpha=2,beta=5,min=0.02,max=0.50",
            classification=parameters.amf.necromass_stabilisation_fraction.classification,
            random_seed=biological_seed,
            provenance="A007/A021 protected-SOC proxy routing hypothesis",
        ),
        _draw(
            name="p_uptake_vmax",
            value=p_vmax,
            unit="kg_P_t_AMF_C^-1_month^-1",
            distribution="triangular",
            distribution_parameters="min=0.2,mode=1.0,max=3.0",
            classification=parameters.amf.p_uptake_vmax.classification,
            random_seed=biological_seed,
            provenance="A023 provisional AMF P-acquisition scale",
        ),
        _draw(
            name="conventional_amf_pulse_mortality",
            value=tillage_mortality,
            unit="fraction",
            distribution="triangular",
            distribution_parameters="min=0.0,mode=0.25,max=0.60",
            classification=(
                parameters.management.tillage.conventional.amf_pulse_mortality.classification
            ),
            random_seed=biological_seed,
            provenance="A009/A027 provisional tillage disturbance magnitude",
        ),
        _draw(
            name="cover_crop_establishment_success",
            value=cover_success,
            unit="probability",
            distribution="beta",
            distribution_parameters="alpha=8,beta=2",
            classification=ParameterSource.SCENARIO_ASSUMPTION,
            random_seed=biological_seed,
            provenance=(
                "A037 provisional latent cover-establishment draw; Phase 6 remains deterministic"
            ),
        ),
    )


def _split_by_seed(
    dataset: EmpiricalDataset, config: PopulationGenerationConfig, generation_seed: int
) -> dict[str, PopulationSplit]:
    archetype_ood = {
        seed.seed_id
        for seed in dataset.seeds
        if seed.archetype in set(config.archetype_ood_archetypes)
    }
    weather_ood = {
        seed.seed_id for seed in dataset.seeds if seed.region_id in set(config.weather_ood_regions)
    }
    if archetype_ood & weather_ood:
        raise ValueError("one empirical seed cannot belong to both OOD partitions")
    seed_ids = sorted(
        seed.seed_id for seed in dataset.seeds if seed.seed_id not in archetype_ood | weather_ood
    )
    random.Random(_derived_seed(generation_seed, "population-splits", 0)).shuffle(seed_ids)
    count = len(seed_ids)
    train_end = round(count * config.split_train_fraction)
    validation_end = train_end + round(count * config.split_validation_fraction)
    splits = {
        seed_id: (
            PopulationSplit.TRAIN
            if index < train_end
            else PopulationSplit.VALIDATION
            if index < validation_end
            else PopulationSplit.TEST
        )
        for index, seed_id in enumerate(seed_ids)
    }
    splits.update({seed_id: PopulationSplit.ARCHETYPE_OOD for seed_id in archetype_ood})
    splits.update({seed_id: PopulationSplit.WEATHER_OOD for seed_id in weather_ood})
    return splits


def _sample_weather(
    *,
    dataset: EmpiricalDataset,
    seed: EmpiricalSeedRecord,
    weather_seed: int,
    years_per_field: int,
) -> tuple[tuple[WeatherMonth, ...], tuple[str, ...]]:
    rng = random.Random(weather_seed)
    candidates = tuple(year for year in dataset.weather_years if year.region_id == seed.region_id)
    sampled = tuple(rng.choice(candidates) for _ in range(years_per_field))
    months: list[WeatherMonth] = []
    for block_index, weather_year in enumerate(sampled):
        for month_index in range(12):
            months.append(
                WeatherMonth(
                    year=2026 + block_index,
                    month=month_index + 1,
                    mean_air_temperature_c=weather_year.temperature_c[month_index],
                    precipitation_mm=weather_year.rainfall_mm[month_index],
                    potential_evapotranspiration_mm=(
                        weather_year.evapotranspiration_mm[month_index]
                    ),
                    source_id=weather_year.weather_year_id,
                    provenance=(
                        f"complete weather-year resample from {weather_year.provenance}; "
                        f"source_year={weather_year.source_year}"
                    ),
                )
            )
    return tuple(months), tuple(year.weather_year_id for year in sampled)


def _candidate(
    *,
    candidate_index: int,
    accepted_index: int,
    empirical_seed: EmpiricalSeedRecord,
    split: PopulationSplit,
    dataset: EmpiricalDataset,
    parameters: ModelParameters,
    config: PopulationGenerationConfig,
    generation_seed: int,
    weather_resampling_seed: int,
    biological_parameter_seed: int,
) -> SyntheticField:
    field_seed = _derived_seed(generation_seed, "field", candidate_index)
    weather_seed = _derived_seed(weather_resampling_seed, "weather", candidate_index)
    biological_seed = _derived_seed(biological_parameter_seed, "biology", candidate_index)
    rng = random.Random(field_seed)
    shared = rng.gauss(0.0, config.soil_shared_factor_sd.default)
    clay, silt, sand = _compositional_texture(
        empirical_seed, rng, config.texture_logratio_sd.default
    )
    relative_limit = config.soc_relative_limit.default
    independent_soc = (
        0.0
        if config.soc_independent_log_sd is None
        else rng.gauss(0.0, config.soc_independent_log_sd.default)
    )
    soc = _bounded_seed_relative(
        empirical_seed.soc_t_c_ha * math.exp(shared + independent_soc),
        empirical_seed.soc_t_c_ha,
        relative_limit,
    )
    soc = _clamp(
        soc,
        config.minimum_soc_t_c_ha.default,
        config.maximum_soc_t_c_ha.default,
    )
    clay_shift = clay - empirical_seed.clay_percent
    bulk_shared_coefficient = (
        0.55
        if config.bulk_density_shared_factor_coefficient is None
        else config.bulk_density_shared_factor_coefficient.default
    )
    bulk_residual = (
        0.0
        if config.bulk_density_independent_sd is None
        else rng.gauss(0.0, config.bulk_density_independent_sd.default)
    )
    bulk_density = (
        empirical_seed.bulk_density_g_cm3
        - bulk_shared_coefficient * shared
        - 0.002 * clay_shift
        + bulk_residual
    )
    bulk_density = _bounded_seed_relative(bulk_density, empirical_seed.bulk_density_g_cm3, 0.12)
    bulk_density = _clamp(
        bulk_density,
        config.minimum_bulk_density_g_cm3.default,
        config.maximum_bulk_density_g_cm3.default,
    )
    ph = _clamp(
        empirical_seed.ph + rng.gauss(0.0, config.ph_absolute_sd.default) + 0.003 * clay_shift,
        config.minimum_ph.default,
        config.maximum_ph.default,
    )
    phosphorus = empirical_seed.available_p_kg_ha * math.exp(
        rng.gauss(0.0, config.phosphorus_log_sd.default) + 0.20 * shared
    )
    phosphorus = _bounded_seed_relative(
        phosphorus, empirical_seed.available_p_kg_ha, relative_limit
    )
    phosphorus = _clamp(
        phosphorus,
        config.minimum_available_p_kg_ha.default,
        config.maximum_available_p_kg_ha.default,
    )
    cec = max(
        0.1,
        empirical_seed.cation_exchange_capacity_cmolc_kg
        * math.exp(0.45 * shared + 0.012 * clay_shift),
    )
    nitrogen = max(
        0.01,
        empirical_seed.total_nitrogen_percent * (soc / empirical_seed.soc_t_c_ha) ** 0.8,
    )
    amf_noise = rng.gauss(0.0, config.amf_log_sd.default)
    phosphorus_pressure = math.log(phosphorus / empirical_seed.available_p_kg_ha)
    amf_live = empirical_seed.amf_live_c_t_ha * math.exp(amf_noise - 0.25 * phosphorus_pressure)
    amf_necromass = empirical_seed.amf_necromass_c_t_ha * math.exp(0.6 * amf_noise)
    weather, weather_year_ids = _sample_weather(
        dataset=dataset,
        seed=empirical_seed,
        weather_seed=weather_seed,
        years_per_field=config.weather_years_per_field,
    )
    draws = _latent_draws(random.Random(biological_seed), biological_seed, parameters)
    spinup = spin_up_carbon_pools(
        baseline_soc_t_c_ha=soc,
        clay_percent=clay,
        available_p_kg_ha=phosphorus,
        amf_live_c_t_ha=amf_live,
        amf_necromass_c_t_ha=amf_necromass,
        weather=weather,
        parameters=parameters,
        config=config,
    )
    field_id = f"phase7-field-{accepted_index + 1:06d}"
    properties = FieldProperties(
        field_id=field_id,
        latitude_deg=_clamp(empirical_seed.latitude_deg + rng.gauss(0.0, 0.02), -90.0, 90.0),
        longitude_deg=_clamp(empirical_seed.longitude_deg + rng.gauss(0.0, 0.02), -180.0, 180.0),
        synthetic_archetype=empirical_seed.archetype,
        soil_depth_cm=parameters.model.soil_depth_cm,
        clay_percent=clay,
        silt_percent=silt,
        sand_percent=sand,
        bulk_density_g_cm3=bulk_density,
        ph=ph,
        cation_exchange_capacity_cmolc_kg=cec,
        baseline_total_nitrogen_percent=nitrogen,
        baseline_soc_t_c_ha=soc,
        drainage_class=empirical_seed.drainage_class,
        climate_normal_id=f"{dataset.dataset_name}:{empirical_seed.region_id}",
        provenance=(
            f"bounded correlated perturbation of empirical seed {empirical_seed.seed_id}; "
            f"dataset={dataset.dataset_name}@{dataset.dataset_version}"
        ),
    )
    return SyntheticField(
        field=properties,
        empirical_seed_id=empirical_seed.seed_id,
        region_id=empirical_seed.region_id,
        archetype=empirical_seed.archetype,
        population_split=split,
        management_history=empirical_seed.management_history,
        intervention_eligibility=empirical_seed.eligible_interventions,
        initial_state=spinup.state,
        weather=weather,
        weather_year_ids=weather_year_ids,
        uncertainty_draws=draws,
        spinup=spinup.diagnostic,
        generation_seed=field_seed,
        weather_seed=weather_seed,
        biological_parameter_seed=biological_seed,
        qc_passed=False,
        provenance=POPULATION_PROVENANCE,
    )


def _population_hash(
    fields: tuple[SyntheticField, ...],
    config_hash: str,
    dataset: EmpiricalDataset,
) -> str:
    payload = {
        "configuration_hash": config_hash,
        "dataset_name": dataset.dataset_name,
        "dataset_version": dataset.dataset_version,
        "fields": [field.model_dump(mode="json") for field in fields],
    }
    canonical = json.dumps(
        payload,
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )
    return hashlib.sha256(canonical.encode()).hexdigest()


def generate_population(
    *,
    dataset: EmpiricalDataset,
    config: PopulationGenerationConfig,
    parameters: ModelParameters,
    population_size: int | None = None,
    generation_seed: int | None = None,
    weather_resampling_seed: int | None = None,
    biological_parameter_seed: int | None = None,
    simulator_probe: SimulatorProbe | None = None,
) -> SyntheticPopulation:
    """Generate accepted fields with independently controlled deterministic seeds."""
    count = config.default_population_size if population_size is None else population_size
    if count < 1:
        raise ValueError("population_size must be positive")
    resolved_seed = config.generation_seed if generation_seed is None else generation_seed
    resolved_weather_seed = (
        resolved_seed if weather_resampling_seed is None else weather_resampling_seed
    )
    resolved_biological_seed = (
        resolved_seed if biological_parameter_seed is None else biological_parameter_seed
    )
    if min(resolved_seed, resolved_weather_seed, resolved_biological_seed) < 0:
        raise ValueError("population, weather, and biological seeds must be non-negative")
    if simulator_probe is None:
        from soil_simulator.population.batch import probe_field

        def default_probe(field: SyntheticField) -> None:
            probe_field(field, parameters, config)

        simulator_probe = default_probe
    splits = _split_by_seed(dataset, config, resolved_seed)
    empirical_seeds = tuple(sorted(dataset.seeds, key=lambda item: item.seed_id))
    accepted: list[SyntheticField] = []
    accepted_seed_ids: set[str] = set()
    rejections: list[RejectionRecord] = []
    maximum_attempts = count * config.max_generation_attempt_multiplier
    for candidate_index in range(maximum_attempts):
        missing_seeds = (
            tuple(seed for seed in empirical_seeds if seed.seed_id not in accepted_seed_ids)
            if count >= len(empirical_seeds)
            else ()
        )
        empirical_seed = (
            missing_seeds[0]
            if missing_seeds
            else empirical_seeds[candidate_index % len(empirical_seeds)]
        )
        candidate_id = f"candidate-{candidate_index + 1:06d}"
        try:
            field = _candidate(
                candidate_index=candidate_index,
                accepted_index=len(accepted),
                empirical_seed=empirical_seed,
                split=splits[empirical_seed.seed_id],
                dataset=dataset,
                parameters=parameters,
                config=config,
                generation_seed=resolved_seed,
                weather_resampling_seed=resolved_weather_seed,
                biological_parameter_seed=resolved_biological_seed,
            )
            qc = quality_control(field, config, simulator_probe=simulator_probe)
        except (ArithmeticError, RuntimeError, ValueError) as exc:
            rejections.append(
                RejectionRecord(
                    candidate_id=candidate_id,
                    empirical_seed_id=empirical_seed.seed_id,
                    reasons=(f"generation_failure:{type(exc).__name__}",),
                )
            )
            continue
        if qc.passed:
            accepted.append(field.model_copy(update={"qc_passed": True}))
            accepted_seed_ids.add(empirical_seed.seed_id)
            if len(accepted) == count:
                break
        else:
            rejections.append(
                RejectionRecord(
                    candidate_id=candidate_id,
                    empirical_seed_id=empirical_seed.seed_id,
                    reasons=qc.reasons,
                )
            )
    if len(accepted) != count:
        raise RuntimeError(
            f"population generation accepted {len(accepted)} of {count} requested fields "
            f"after {maximum_attempts} attempts"
        )
    fields = tuple(accepted)
    config_hash = config.stable_hash()
    population_hash = _population_hash(fields, config_hash, dataset)
    manifest_entries = tuple(
        FieldManifestEntry(
            field_id=field.field.field_id,
            empirical_seed_id=field.empirical_seed_id,
            region_id=field.region_id,
            archetype=field.archetype,
            population_split=field.population_split,
            weather_year_ids=field.weather_year_ids,
            uncertainty_draws=field.uncertainty_draws,
        )
        for field in fields
    )
    manifest = PopulationManifest(
        model_version=parameters.model.version,
        generation_seed=resolved_seed,
        weather_resampling_seed=resolved_weather_seed,
        biological_parameter_seed=resolved_biological_seed,
        configuration_hash=config_hash,
        model_configuration_hash=parameters.stable_hash(),
        dataset_name=dataset.dataset_name,
        dataset_version=dataset.dataset_version,
        adapter_name=dataset.adapter_name,
        adapter_version=dataset.adapter_version,
        source_datasets=dataset.source_datasets,
        fields=manifest_entries,
        rejections=tuple(rejections),
        accepted_count=len(fields),
        rejected_count=len(rejections),
        population_hash=population_hash,
        provenance=POPULATION_PROVENANCE,
    )
    return SyntheticPopulation(fields=fields, manifest=manifest)
