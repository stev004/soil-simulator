"""Deterministic Phase 8.5 expansion of the local synthetic seed fixture.

The expansion creates additional *synthetic* seed groups for leakage and
generalisation experiments.  It is not an empirical survey expansion and must
not be described as representative of UK arable soils.
"""

from __future__ import annotations

import hashlib
import math
import random

from soil_simulator.domain.models import VersionedInput
from soil_simulator.domain.population import (
    EmpiricalDataset,
    EmpiricalSeedRecord,
    WeatherYearRecord,
)

ARCHETYPE_OOD_NAME = "acidic-low-productivity-phase85-ood"
WEATHER_OOD_REGION = "phase85-extreme-dry-ood"
PHASE86_WEATHER_REGIMES = ("dry", "hot", "wet", "cool", "hot_dry")
PHASE86_WEATHER_OOD_REGIONS = tuple(
    f"phase86-weather-{regime}-ood" for regime in PHASE86_WEATHER_REGIMES
)
PHASE86_ARCHETYPE_OOD_NAME = "acidic-low-productivity-phase86-ood"
FOUNDATION_PROVENANCE = (
    "Phase 8.5 deterministic synthetic expansion of ten local demonstration templates; "
    "designed for software and ML stress testing, non-representative and not field validation"
)


def _derived_seed(base_seed: int, label: str, index: int) -> int:
    payload = f"{base_seed}:{label}:{index}".encode()
    return int.from_bytes(hashlib.sha256(payload).digest()[:8], "big")


def _clamp(value: float, lower: float, upper: float) -> float:
    return min(upper, max(lower, value))


def _texture(seed: EmpiricalSeedRecord, rng: random.Random) -> tuple[float, float, float]:
    clay_logratio = math.log(seed.clay_percent / seed.sand_percent) + rng.gauss(0.0, 0.28)
    silt_logratio = math.log(seed.silt_percent / seed.sand_percent) + rng.gauss(0.0, 0.24)
    clay_exp = math.exp(clay_logratio)
    silt_exp = math.exp(silt_logratio)
    denominator = clay_exp + silt_exp + 1.0
    clay = 100.0 * clay_exp / denominator
    silt = 100.0 * silt_exp / denominator
    return clay, silt, 100.0 - clay - silt


def _weather_variant(
    source: WeatherYearRecord,
    *,
    group_index: int,
    year_index: int,
    region_id: str,
    weather_ood: bool,
    random_seed: int,
) -> WeatherYearRecord:
    rng = random.Random(
        _derived_seed(random_seed, "foundation-weather", group_index * 3 + year_index)
    )
    temperature_shift = rng.gauss(0.0, 0.7) + (1.8 if weather_ood else 0.0)
    rainfall_scale = math.exp(rng.gauss(0.0, 0.13)) * (0.52 if weather_ood else 1.0)
    pet_scale = math.exp(rng.gauss(0.0, 0.08)) * (1.18 if weather_ood else 1.0)
    temperatures = tuple(
        value + temperature_shift + 0.25 * math.sin((month + 1) * math.pi / 6.0)
        for month, value in enumerate(source.temperature_c)
    )
    rainfall = tuple(max(1.0, value * rainfall_scale) for value in source.rainfall_mm)
    pet = tuple(max(1.0, value * pet_scale) for value in source.evapotranspiration_mm)
    return WeatherYearRecord(
        weather_year_id=f"phase85-weather-{group_index + 1:03d}-{year_index + 1}",
        region_id=region_id,
        source_year=2020 + year_index,
        temperature_c=temperatures,
        rainfall_mm=rainfall,
        evapotranspiration_mm=pet,
        provenance=(
            f"Synthetic coherent anomaly of {source.weather_year_id}; "
            f"weather_ood={weather_ood}; {FOUNDATION_PROVENANCE}"
        ),
    )


def expand_synthetic_foundation(
    dataset: EmpiricalDataset,
    *,
    group_count: int = 50,
    random_seed: int = 20260721,
) -> EmpiricalDataset:
    """Return at least 50 distinct, explicitly synthetic empirical-seed groups.

    Soil donors are deliberately permuted across the original joint templates,
    then supplied with independent SOC and bulk-density residuals.  This weakens
    the earlier near-deterministic SOC--bulk-density relationship while keeping
    variables inside the Phase 7 mineral-topsoil domain.
    """
    if group_count < 50:
        raise ValueError("Phase 8.5 requires at least 50 empirical-seed groups")
    templates = tuple(sorted(dataset.seeds, key=lambda item: item.seed_id))
    weather_templates = tuple(sorted(dataset.weather_years, key=lambda item: item.weather_year_id))
    if len(templates) < 2 or not weather_templates:
        raise ValueError("foundation expansion requires multiple soil and weather templates")
    seeds: list[EmpiricalSeedRecord] = []
    weather_years: list[WeatherYearRecord] = []
    archetype_ood_start = group_count - 10
    weather_ood_start = group_count - 5
    histories = (
        "conventional_arable",
        "reduced_tillage_arable",
        "low_input_arable",
        "high_input_arable",
        "mixed_arable",
        "cover_cropped_arable",
    )
    policies = (
        "baseline",
        "conventional_tillage",
        "reduced_tillage",
        "no_till",
        "cover_crop",
        "phosphorus",
        "farmyard_manure",
    )
    for index in range(group_count):
        rng = random.Random(_derived_seed(random_seed, "foundation-soil", index))
        texture_template = templates[index % len(templates)]
        soc_template = templates[(index * 7 + 3) % len(templates)]
        density_template = templates[(index * 3 + 1) % len(templates)]
        p_template = templates[(index * 9 + 4) % len(templates)]
        amf_template = templates[(index * 5 + 2) % len(templates)]
        clay, silt, sand = _texture(texture_template, rng)
        soc = _clamp(soc_template.soc_t_c_ha * math.exp(rng.gauss(0.0, 0.24)), 18.0, 155.0)
        density_residual = rng.gauss(0.0, 0.115)
        bulk_density = _clamp(
            density_template.bulk_density_g_cm3
            - 0.0007 * (soc - soc_template.soc_t_c_ha)
            - 0.0008 * (clay - texture_template.clay_percent)
            + density_residual,
            0.88,
            1.72,
        )
        phosphorus = _clamp(
            p_template.available_p_kg_ha * math.exp(rng.gauss(0.0, 0.34)), 2.0, 85.0
        )
        amf_residual = rng.gauss(0.0, 0.42)
        amf_live = _clamp(
            amf_template.amf_live_c_t_ha
            * math.exp(amf_residual - 0.05 * math.log(phosphorus / p_template.available_p_kg_ha)),
            0.012,
            0.24,
        )
        archetype_ood = index >= archetype_ood_start and index < weather_ood_start
        weather_ood = index >= weather_ood_start
        archetype = ARCHETYPE_OOD_NAME if archetype_ood else texture_template.archetype
        region_id = WEATHER_OOD_REGION if weather_ood else f"phase85-region-{index + 1:03d}"
        ph = _clamp(
            (4.55 + rng.gauss(0.0, 0.18))
            if archetype_ood
            else texture_template.ph + rng.gauss(0.0, 0.42),
            4.05,
            8.25,
        )
        cec = _clamp(3.0 + 0.42 * clay + rng.gauss(0.0, 3.2), 2.0, 38.0)
        nitrogen = _clamp(0.045 + 0.00125 * soc + rng.gauss(0.0, 0.035), 0.04, 0.34)
        seed = EmpiricalSeedRecord(
            seed_id=f"phase85-seed-{index + 1:03d}",
            region_id=region_id,
            archetype=archetype,
            latitude_deg=_clamp(texture_template.latitude_deg + rng.gauss(0.0, 0.65), 49.5, 58.5),
            longitude_deg=_clamp(texture_template.longitude_deg + rng.gauss(0.0, 0.75), -7.5, 2.0),
            clay_percent=clay,
            silt_percent=silt,
            sand_percent=sand,
            ph=ph,
            soc_t_c_ha=soc,
            bulk_density_g_cm3=bulk_density,
            available_p_kg_ha=phosphorus,
            cation_exchange_capacity_cmolc_kg=cec,
            total_nitrogen_percent=nitrogen,
            amf_live_c_t_ha=amf_live,
            amf_necromass_c_t_ha=_clamp(amf_live * math.exp(rng.gauss(-0.8, 0.22)), 0.006, 0.12),
            drainage_class=texture_template.drainage_class,
            management_history=histories[index % len(histories)],
            eligible_interventions=policies,
            provenance=(
                f"Synthetic Phase 8.5 group {index + 1}; texture donor={texture_template.seed_id}; "
                f"SOC donor={soc_template.seed_id}; density donor={density_template.seed_id}; "
                f"independent residual covariance revision; {FOUNDATION_PROVENANCE}"
            ),
        )
        seeds.append(seed)
        for year_index in range(3):
            source = weather_templates[(index * 2 + year_index * 3) % len(weather_templates)]
            weather_years.append(
                _weather_variant(
                    source,
                    group_index=index,
                    year_index=year_index,
                    region_id=region_id,
                    weather_ood=weather_ood,
                    random_seed=random_seed,
                )
            )
    return EmpiricalDataset(
        dataset_name="phase85_expanded_synthetic_foundation",
        dataset_version="0.8.5",
        adapter_name="deterministic_synthetic_foundation_expander",
        adapter_version="0.8.5",
        source_datasets=(
            *dataset.source_datasets,
            VersionedInput(
                name="phase85_covariance_and_ood_design",
                version="0.8.5",
                provenance=FOUNDATION_PROVENANCE,
            ),
        ),
        seeds=tuple(seeds),
        weather_years=tuple(weather_years),
        provenance=FOUNDATION_PROVENANCE,
    )


def soc_bulk_density_correlation(dataset: EmpiricalDataset) -> float:
    """Return the seed-level Pearson correlation used by covariance tests."""
    soc = [seed.soc_t_c_ha for seed in dataset.seeds]
    density = [seed.bulk_density_g_cm3 for seed in dataset.seeds]
    soc_mean = math.fsum(soc) / len(soc)
    density_mean = math.fsum(density) / len(density)
    numerator = math.fsum(
        (left - soc_mean) * (right - density_mean) for left, right in zip(soc, density, strict=True)
    )
    denominator = math.sqrt(
        math.fsum((value - soc_mean) ** 2 for value in soc)
        * math.fsum((value - density_mean) ** 2 for value in density)
    )
    return 0.0 if denominator == 0.0 else numerator / denominator


def _phase86_weather_variant(
    source: WeatherYearRecord,
    *,
    group_index: int,
    year_index: int,
    region_id: str,
    regime: str | None,
    random_seed: int,
) -> WeatherYearRecord:
    """Create a coherent whole-year Phase 8.6 weather stress scenario."""
    rng = random.Random(
        _derived_seed(random_seed, "phase86-foundation-weather", group_index * 3 + year_index)
    )
    temperature_delta = {
        None: 0.0,
        "dry": 0.0,
        "hot": 2.8,
        "wet": 0.0,
        "cool": -2.8,
        "hot_dry": 2.8,
    }[regime]
    rainfall_multiplier = {
        None: 1.0,
        "dry": 0.58,
        "hot": 1.0,
        "wet": 1.55,
        "cool": 1.0,
        "hot_dry": 0.50,
    }[regime]
    pet_multiplier = {
        None: 1.0,
        "dry": 1.08,
        "hot": 1.18,
        "wet": 0.96,
        "cool": 0.88,
        "hot_dry": 1.24,
    }[regime]
    temperature_shift = rng.gauss(0.0, 0.65) + temperature_delta
    rainfall_scale = math.exp(rng.gauss(0.0, 0.12)) * rainfall_multiplier
    pet_scale = math.exp(rng.gauss(0.0, 0.07)) * pet_multiplier
    return WeatherYearRecord(
        weather_year_id=f"phase86-weather-{group_index + 1:03d}-{year_index + 1}",
        region_id=region_id,
        source_year=2030 + year_index,
        temperature_c=tuple(
            value + temperature_shift + 0.2 * math.sin((month + 1) * math.pi / 6.0)
            for month, value in enumerate(source.temperature_c)
        ),
        rainfall_mm=tuple(max(1.0, value * rainfall_scale) for value in source.rainfall_mm),
        evapotranspiration_mm=tuple(
            max(1.0, value * pet_scale) for value in source.evapotranspiration_mm
        ),
        provenance=(
            f"Synthetic coherent Phase 8.6 anomaly of {source.weather_year_id}; "
            f"regime={regime or 'temperate'}; non-representative and not field validation"
        ),
    )


def expand_phase86_foundation(
    dataset: EmpiricalDataset,
    *,
    group_count: int = 75,
    random_seed: int = 20260860,
) -> EmpiricalDataset:
    """Create independent Phase 8.6 groups with five dedicated weather regimes.

    The last 25 groups comprise five groups each for dry, hot, wet, cool, and
    compound hot-dry conditions. The preceding five groups form the archetype
    holdout. All records remain synthetic and explicitly non-representative.
    """
    if group_count < 75:
        raise ValueError("Phase 8.6 requires at least 75 groups for balanced OOD support")
    templates = tuple(sorted(dataset.seeds, key=lambda item: item.seed_id))
    weather_templates = tuple(sorted(dataset.weather_years, key=lambda item: item.weather_year_id))
    if len(templates) < 2 or not weather_templates:
        raise ValueError("foundation expansion requires multiple soil and weather templates")
    weather_ood_start = group_count - 25
    archetype_ood_start = weather_ood_start - 5
    histories = (
        "conventional_arable",
        "reduced_tillage_arable",
        "low_input_arable",
        "high_input_arable",
        "mixed_arable",
        "cover_cropped_arable",
    )
    policies = (
        "baseline",
        "conventional_tillage",
        "reduced_tillage",
        "no_till",
        "cover_crop",
        "phosphorus",
        "farmyard_manure",
    )
    seeds: list[EmpiricalSeedRecord] = []
    weather_years: list[WeatherYearRecord] = []
    for index in range(group_count):
        rng = random.Random(_derived_seed(random_seed, "phase86-foundation-soil", index))
        texture_template = templates[index % len(templates)]
        soc_template = templates[(index * 7 + 3) % len(templates)]
        density_template = templates[(index * 3 + 1) % len(templates)]
        p_template = templates[(index * 9 + 4) % len(templates)]
        amf_template = templates[(index * 5 + 2) % len(templates)]
        clay, silt, sand = _texture(texture_template, rng)
        soc = _clamp(soc_template.soc_t_c_ha * math.exp(rng.gauss(0.0, 0.26)), 18.0, 155.0)
        bulk_density = _clamp(
            density_template.bulk_density_g_cm3
            - 0.0005 * (soc - soc_template.soc_t_c_ha)
            - 0.0006 * (clay - texture_template.clay_percent)
            + rng.gauss(0.0, 0.12),
            0.88,
            1.72,
        )
        phosphorus = _clamp(
            p_template.available_p_kg_ha * math.exp(rng.gauss(0.0, 0.36)), 2.0, 85.0
        )
        amf_live = _clamp(
            amf_template.amf_live_c_t_ha
            * math.exp(
                rng.gauss(0.0, 0.44) - 0.04 * math.log(phosphorus / p_template.available_p_kg_ha)
            ),
            0.012,
            0.24,
        )
        archetype_ood = archetype_ood_start <= index < weather_ood_start
        regime: str | None = None
        if index >= weather_ood_start:
            regime = PHASE86_WEATHER_REGIMES[(index - weather_ood_start) // 5]
        archetype = PHASE86_ARCHETYPE_OOD_NAME if archetype_ood else texture_template.archetype
        region_id = (
            f"phase86-weather-{regime}-ood"
            if regime is not None
            else f"phase86-region-{index + 1:03d}"
        )
        ph = _clamp(
            4.55 + rng.gauss(0.0, 0.18)
            if archetype_ood
            else texture_template.ph + rng.gauss(0.0, 0.44),
            4.05,
            8.25,
        )
        seed = EmpiricalSeedRecord(
            seed_id=f"phase86-seed-{index + 1:03d}",
            region_id=region_id,
            archetype=archetype,
            latitude_deg=_clamp(texture_template.latitude_deg + rng.gauss(0.0, 0.7), 49.5, 58.5),
            longitude_deg=_clamp(texture_template.longitude_deg + rng.gauss(0.0, 0.8), -7.5, 2.0),
            clay_percent=clay,
            silt_percent=silt,
            sand_percent=sand,
            ph=ph,
            soc_t_c_ha=soc,
            bulk_density_g_cm3=bulk_density,
            available_p_kg_ha=phosphorus,
            cation_exchange_capacity_cmolc_kg=_clamp(
                3.0 + 0.42 * clay + rng.gauss(0.0, 3.4), 2.0, 38.0
            ),
            total_nitrogen_percent=_clamp(
                0.045 + 0.00125 * soc + rng.gauss(0.0, 0.038), 0.04, 0.34
            ),
            amf_live_c_t_ha=amf_live,
            amf_necromass_c_t_ha=_clamp(amf_live * math.exp(rng.gauss(-0.8, 0.24)), 0.006, 0.12),
            drainage_class=texture_template.drainage_class,
            management_history=histories[index % len(histories)],
            eligible_interventions=policies,
            provenance=(
                f"Synthetic Phase 8.6 group {index + 1}; separate texture/SOC/density/P/AMF "
                "donors with dominant independent residuals; non-representative"
            ),
        )
        seeds.append(seed)
        for year_index in range(3):
            source = weather_templates[(index * 2 + year_index * 3) % len(weather_templates)]
            weather_years.append(
                _phase86_weather_variant(
                    source,
                    group_index=index,
                    year_index=year_index,
                    region_id=region_id,
                    regime=regime,
                    random_seed=random_seed,
                )
            )
    provenance = (
        "Phase 8.6 repeated-experiment synthetic foundation with revised covariance and "
        "five dedicated weather stress regimes; non-representative and not field validation"
    )
    return EmpiricalDataset(
        dataset_name="phase86_repeated_synthetic_foundation",
        dataset_version="0.8.6",
        adapter_name="deterministic_phase86_foundation_expander",
        adapter_version="0.8.6",
        source_datasets=(
            *dataset.source_datasets,
            VersionedInput(
                name="phase86_repeated_population_and_weather_ood_design",
                version="0.8.6",
                provenance=provenance,
            ),
        ),
        seeds=tuple(seeds),
        weather_years=tuple(weather_years),
        provenance=provenance,
    )
