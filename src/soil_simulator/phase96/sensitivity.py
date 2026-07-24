"""Population-aware Morris/Sobol sensitivity for the empirical Phase 9.6 pilot."""

from __future__ import annotations

import math
import random
from collections import Counter
from collections.abc import Mapping
from pathlib import Path
from typing import Any, cast

import yaml

from soil_simulator.domain.management import ManagementScenarioSet
from soil_simulator.domain.models import ModelParameters
from soil_simulator.domain.population import (
    PopulationGenerationConfig,
    SyntheticField,
    SyntheticPopulation,
)
from soil_simulator.phase95.analysis import sensitivity_evaluator
from soil_simulator.phase95.sensitivity import (
    SensitivityParameter,
    morris_screen,
    rank_stability,
    sobol_indices,
)
from soil_simulator.phase96.values import as_float


def _load_specification(
    path: str | Path,
) -> tuple[dict[str, int], tuple[SensitivityParameter, ...]]:
    raw = cast(dict[str, Any], yaml.safe_load(Path(path).read_text(encoding="utf-8")))
    if raw.get("version") != "0.9.6":
        raise ValueError("Phase 9.6 sensitivity specification must be version 0.9.6")
    parameters = tuple(
        SensitivityParameter(
            name=str(item["name"]),
            minimum=as_float(item["minimum"]),
            maximum=as_float(item["maximum"]),
            distribution=str(item["distribution"]),
            classification=str(item["classification"]),
            source=str(item["source"]),
        )
        for item in cast(list[dict[str, object]], raw["parameters"])
    )
    settings = {
        name: int(raw[name])
        for name in (
            "seed",
            "morris_trajectories",
            "morris_levels",
            "sobol_base_sample_size",
            "sobol_parameter_count",
        )
    }
    return settings, parameters


def _with_weather_and_spinup(field: SyntheticField, values: Mapping[str, float]) -> SyntheticField:
    blocks = tuple(
        field.weather[offset : offset + 12] for offset in range(0, len(field.weather), 12)
    )
    weather_index = min(len(blocks) - 1, max(0, round(values.get("weather_resample_index", 0.0))))
    selected = blocks[weather_index]
    weather = tuple(month for _ in blocks for month in selected)
    weather_ids = tuple(field.weather_year_ids[weather_index] for _ in blocks)
    blend = min(1.0, max(0.0, values.get("spinup_pool_blend", 0.0)))
    state = field.initial_state
    active_total = math.fsum((state.dpm_c, state.rpm_c, state.microbial_c, state.protected_soc_c))
    ratios = (0.1533, 4.4852, 0.6671, 25.8576)
    ratio_total = math.fsum(ratios)
    alternative = tuple(active_total * value / ratio_total for value in ratios)
    current = (state.dpm_c, state.rpm_c, state.microbial_c, state.protected_soc_c)
    blended = tuple(
        (1.0 - blend) * left + blend * right
        for left, right in zip(current, alternative, strict=True)
    )
    initial_state = state.model_copy(
        update={
            "dpm_c": blended[0],
            "rpm_c": blended[1],
            "microbial_c": blended[2],
            "protected_soc_c": blended[3],
        }
    )
    return field.model_copy(
        update={"weather": weather, "weather_year_ids": weather_ids, "initial_state": initial_state}
    )


def _aggregate_scores(
    screen: Mapping[str, Mapping[str, Mapping[str, float]]],
    parameters: tuple[SensitivityParameter, ...],
) -> dict[str, float]:
    scores = {parameter.name: 0.0 for parameter in parameters}
    count = 0
    for by_parameter in screen.values():
        maximum = max(metric["mu_star"] for metric in by_parameter.values())
        if maximum == 0.0:
            continue
        count += 1
        for name, metric in by_parameter.items():
            scores[name] += metric["mu_star"] / maximum
    return {name: value / max(count, 1) for name, value in scores.items()}


def _sobol_rank_agreement(full: Mapping[str, object], half: Mapping[str, object]) -> float:
    full_outputs = cast(dict[str, dict[str, object]], full["outputs"])
    half_outputs = cast(dict[str, dict[str, object]], half["outputs"])
    agreements: list[float] = []
    for output, payload in full_outputs.items():
        full_indices = cast(dict[str, dict[str, float | None]], payload["indices"])
        half_indices = cast(dict[str, dict[str, float | None]], half_outputs[output]["indices"])
        full_rank = sorted(
            full_indices,
            key=lambda name: float(full_indices[name]["total_order"] or 0.0),
            reverse=True,
        )
        half_rank = sorted(
            half_indices,
            key=lambda name: float(half_indices[name]["total_order"] or 0.0),
            reverse=True,
        )
        agreements.append(
            math.fsum(left == right for left, right in zip(full_rank, half_rank, strict=True))
            / len(full_rank)
        )
    return math.fsum(agreements) / len(agreements)


def _ranking_stability(
    evaluator: Any, parameters: tuple[SensitivityParameter, ...], seed: int, draws: int = 64
) -> dict[str, object]:
    rng = random.Random(seed)
    winners: dict[str, Counter[str]] = {}
    reversal_examples: list[dict[str, object]] = []
    for draw in range(draws):
        values = {parameter.name: parameter.transform(rng.random()) for parameter in parameters}
        outcomes = evaluator(values)
        for target, horizon in (
            ("yield_t_dm_ha", 24),
            ("total_soc_t_c_ha", 60),
            ("protected_soc_proxy_t_c_ha", 60),
            ("total_soc_t_c_ha", 120),
            ("protected_soc_proxy_t_c_ha", 120),
        ):
            eligible = {
                key.split("|", 1)[0]: value
                for key, value in outcomes.items()
                if key.endswith(f"|{target}|{horizon}") and not key.startswith("phosphorus|")
            }
            winner = max(eligible, key=eligible.__getitem__)
            label = f"{target}|{horizon}"
            winners.setdefault(label, Counter())[winner] += 1
            if draw < 12:
                reversal_examples.append(
                    {
                        "target_horizon": label,
                        "winner": winner,
                        "empirical_location_index": values["empirical_location_index"],
                        "weather_resample_index": values["weather_resample_index"],
                        "schedule_interval_months": values["schedule_interval_months"],
                    }
                )
    return {
        "draws": draws,
        "phosphorus_excluded_from_headline_ranking": True,
        "winner_proportions": {
            label: {policy: count / draws for policy, count in sorted(counter.items())}
            for label, counter in sorted(winners.items())
        },
        "ranking_reversal_conditions_sample": reversal_examples,
    }


def run_population_sensitivity(
    population: SyntheticPopulation,
    template: ManagementScenarioSet,
    model_parameters: ModelParameters,
    population_config: PopulationGenerationConfig,
    specification_path: str | Path,
) -> dict[str, object]:
    """Run global sensitivity with empirical location, weather and spin-up factors."""
    settings, parameters = _load_specification(specification_path)
    by_location: dict[str, list[SyntheticField]] = {}
    for field in population.fields:
        by_location.setdefault(field.empirical_seed_id, []).append(field)
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
        return sensitivity_evaluator(field, template, model_parameters, population_config, values)

    morris = morris_screen(
        parameters,
        evaluator,
        trajectories=settings["morris_trajectories"],
        levels=settings["morris_levels"],
        seed=settings["seed"],
    )
    half_morris = morris_screen(
        parameters,
        evaluator,
        trajectories=max(2, settings["morris_trajectories"] // 2),
        levels=settings["morris_levels"],
        seed=settings["seed"],
    )
    aggregate = _aggregate_scores(morris, parameters)
    selected_names = tuple(
        name
        for name, _ in sorted(aggregate.items(), key=lambda item: item[1], reverse=True)[
            : settings["sobol_parameter_count"]
        ]
    )
    selected = tuple(parameter for parameter in parameters if parameter.name in selected_names)
    sobol = sobol_indices(
        selected,
        evaluator,
        sample_size=settings["sobol_base_sample_size"],
        seed=settings["seed"] + 1,
    )
    half_sobol = sobol_indices(
        selected,
        evaluator,
        sample_size=max(16, settings["sobol_base_sample_size"] // 2),
        seed=settings["seed"] + 1,
    )
    morris_stability = {
        output: rank_stability(payload, half_morris[output]) for output, payload in morris.items()
    }
    return {
        "version": "0.9.6",
        "population_hash": population.manifest.population_hash,
        "empirical_location_count": len(locations),
        "generated_field_count": len(population.fields),
        "parameters": [parameter.__dict__ for parameter in parameters],
        "morris": morris,
        "morris_aggregate_scores": aggregate,
        "sobol_selected_parameters": selected_names,
        "sobol": sobol,
        "convergence": {
            "morris_mean_rank_agreement": math.fsum(morris_stability.values())
            / len(morris_stability),
            "morris_by_output": morris_stability,
            "sobol_mean_rank_agreement": _sobol_rank_agreement(sobol, half_sobol),
        },
        "location_specific_sensitivity": {
            "method": (
                "empirical location is an explicit global factor; output-level Morris effects "
                "retained"
            ),
            "location_factor": {
                output: payload["empirical_location_index"] for output, payload in morris.items()
            },
        },
        "target_horizon_policy_ranking_stability": _ranking_stability(
            evaluator, parameters, settings["seed"] + 2
        ),
        "calibrated_parameters_included": False,
        "calibration_exclusion_reason": (
            "Hoosfield input-reconstruction calibration is optional evidence and is not retained "
            "as a general simulator parameter."
        ),
        "primary_outputs": "paired intervention-minus-baseline effects only",
    }
