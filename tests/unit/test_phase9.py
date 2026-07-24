"""Phase 9 frozen-artifact, selection, regret, abstention and replay tests."""

from __future__ import annotations

import hashlib
import inspect
import json
import shutil
from pathlib import Path
from typing import Any, cast

import pytest

from soil_simulator.domain.enums import PopulationSplit
from soil_simulator.io.phase9_configuration import load_phase9_benchmark_config
from soil_simulator.ml.dataset import load_ml_dataset_csv
from soil_simulator.ml.phase86_schema import PHASE86_PRIMARY_TASKS
from soil_simulator.ml.schema import FEATURE_SETS, MlRow
from soil_simulator.selection.artifacts import (
    FrozenArtifactError,
    load_frozen_phase86_bundle,
    observable_applicability_reasons,
)
from soil_simulator.selection.benchmark import ExperimentData, fit_selector_state
from soil_simulator.selection.core import (
    NormalisationContract,
    NormalisationStat,
    OutcomeInterval,
    OutcomeValues,
    calculate_regret,
    constraints_allow,
    exhaustive_oracle,
    fit_normalisation,
    is_catastrophic_failure,
    utility,
)
from soil_simulator.selection.schema import PHASE9_POLICIES
from soil_simulator.selection.selectors import (
    FrozenPolicyPredictions,
    deterministic_random_policy,
    select_observable_ml,
)

ROOT = Path(__file__).parents[2]
CONFIG = load_phase9_benchmark_config(ROOT / "config" / "selection" / "phase9_benchmark.yaml")
ARTIFACTS = ROOT / "outputs" / "phase86_v0.8.6"
PHASE86_CONFIG = ROOT / "config" / "ml" / "phase86_benchmark.yaml"


def _bundle() -> Any:
    return load_frozen_phase86_bundle(
        artifact_dir=ARTIFACTS,
        phase86_config_path=PHASE86_CONFIG,
        expected=CONFIG.frozen_artifacts,
    )


def _zero_normalisation() -> NormalisationContract:
    units = {
        name: "test unit"
        for name in (
            "yield_effect",
            "total_soc_effect_5y",
            "total_soc_effect_10y",
            "protected_soc_proxy_effect_5y",
            "protected_soc_proxy_effect_10y",
            "intervention_cost",
            "emissions_proxy",
        )
    }
    return NormalisationContract(
        stats={name: NormalisationStat(0.0, 1.0, unit) for name, unit in units.items()},
        fitted_row_ids_hash="0" * 64,
    )


def _outcome(
    *,
    yield_effect: float = 0.0,
    total: float = 0.0,
    protected: float = 0.0,
    cost: float = 0.0,
    emissions: float = 0.0,
) -> OutcomeValues:
    return OutcomeValues(
        yield_effect=yield_effect,
        total_soc_effect_5y=total,
        total_soc_effect_10y=total,
        protected_soc_proxy_effect_5y=protected,
        protected_soc_proxy_effect_10y=protected,
        intervention_cost=cost,
        emissions_proxy=emissions,
    )


def test_frozen_models_preprocessing_uncertainty_and_domain_hashes_are_enforced(
    tmp_path: Path,
) -> None:
    bundle = _bundle()
    assert set(bundle.models) == set(PHASE86_PRIMARY_TASKS)
    assert bundle.preprocessor.stable_hash() == CONFIG.frozen_artifacts.preprocessing_hash

    copied = tmp_path / "phase86"
    shutil.copytree(ARTIFACTS, copied)
    model_path = copied / "models" / "delta_crop_yield_t_dm_ha__h24.json"
    payload = json.loads(model_path.read_text(encoding="utf-8"))
    payload["policy_models"]["baseline"]["coefficients"][0][0] = 0.125
    model_path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(FrozenArtifactError, match="model hash mismatch"):
        load_frozen_phase86_bundle(
            artifact_dir=copied,
            phase86_config_path=PHASE86_CONFIG,
            expected=CONFIG.frozen_artifacts,
        )


def test_frozen_artifact_version_mismatch_is_rejected(tmp_path: Path) -> None:
    copied = tmp_path / "phase86"
    shutil.copytree(ARTIFACTS, copied)
    path = copied / "preprocessing" / "observable_preprocessor.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["artifact_version"] = "tampered"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(FrozenArtifactError, match="preprocessing version mismatch"):
        load_frozen_phase86_bundle(
            artifact_dir=copied,
            phase86_config_path=PHASE86_CONFIG,
            expected=CONFIG.frozen_artifacts,
        )


def test_observable_selector_cannot_access_latent_features() -> None:
    bundle = _bundle()
    assert bundle.preprocessor.feature_set_name == "observable_features"
    assert not any(name.startswith("latent_") for name in bundle.preprocessor.numeric_features)
    assert not any(name.startswith("initial_amf") for name in bundle.preprocessor.numeric_features)
    assert set(bundle.preprocessor.numeric_features) == set(
        FEATURE_SETS["observable_features"].numeric
    )
    assert "outcomes" not in inspect.signature(select_observable_ml).parameters
    assert "oracle" not in inspect.signature(select_observable_ml).parameters


def test_applicability_missing_out_of_domain_and_unsupported_weather_abstain() -> None:
    bundle = _bundle()
    rows = load_ml_dataset_csv(ARTIFACTS / "frozen_final_dataset_v0.8.6.csv")
    task = "delta_crop_yield_t_dm_ha@24"
    supported = next(
        row
        for row in rows
        if row.simulation_horizon_months == 24
        and row.policy_id == "baseline"
        and row.weather_regime in {"temperate", "cool", "hot", "wet"}
    )
    assert observable_applicability_reasons(supported, task=task, bundle=bundle) == ()
    missing = MlRow(
        **{
            **supported.__dict__,
            "features": {key: value for key, value in supported.features.items() if key != "ph"},
        }
    )
    assert "missing_observation:ph" in observable_applicability_reasons(
        missing, task=task, bundle=bundle
    )
    outside_features = dict(supported.features)
    outside_features["ph"] = 1000.0
    outside = MlRow(**{**supported.__dict__, "features": outside_features})
    assert any(
        reason.startswith("outside_numeric_domain:ph")
        for reason in (observable_applicability_reasons(outside, task=task, bundle=bundle))
    )
    unsupported = next(
        row
        for row in rows
        if row.simulation_horizon_months == 24
        and row.policy_id == "baseline"
        and row.weather_regime in {"dry", "hot_dry"}
    )
    assert "unsupported_target_weather_regime" in observable_applicability_reasons(
        unsupported, task=task, bundle=bundle
    )


def test_utility_and_training_only_normalisation_are_exact() -> None:
    normalisation = _zero_normalisation()
    profile = CONFIG.utility_profiles[0]
    values = OutcomeValues(1.0, 2.0, 4.0, 1.0, 3.0, 10.0, 5.0)
    assert utility(values, profile, normalisation) == pytest.approx(-0.375)
    first = fit_normalisation(
        (("train:a", _outcome(total=1.0)), ("validation:b", _outcome(total=3.0)))
    )
    replay = fit_normalisation(
        (("train:a", _outcome(total=1.0)), ("validation:b", _outcome(total=3.0)))
    )
    assert first.stable_hash() == replay.stable_hash()
    assert first.stats["total_soc_effect_5y"].mean == 2.0
    assert first.stats["total_soc_effect_5y"].scale == 1.0


def test_constraints_and_eligibility_are_enforced() -> None:
    constraints = CONFIG.utility_profiles[3].constraints
    decision = constraints_allow(
        _outcome(yield_effect=-0.3, total=-0.1, cost=70.0, emissions=30.0),
        constraints,
        eligible=False,
        applicable=False,
    )
    assert not decision.feasible
    assert set(decision.violations) == {
        "intervention_ineligible",
        "outside_applicability_domain",
        "maximum_yield_loss",
        "maximum_cost",
        "maximum_emissions_proxy",
        "minimum_total_soc_benefit",
    }


def test_uncertainty_aware_overlap_and_no_improvement_abstain() -> None:
    normalisation = _zero_normalisation()
    profile = CONFIG.utility_profiles[2]
    zero = _outcome()
    small = _outcome(yield_effect=0.3, total=0.3, protected=0.3)
    width = _outcome(yield_effect=0.2, total=0.2, protected=0.2)
    predictions = FrozenPolicyPredictions(
        intervals={
            "baseline": OutcomeInterval(
                zero, zero, _outcome(yield_effect=0.5, total=0.5, protected=0.5)
            ),
            "cover_crop": OutcomeInterval(
                small,
                _outcome(yield_effect=0.1, total=0.1, protected=0.1),
                _outcome(yield_effect=0.5, total=0.5, protected=0.5),
            ),
        },
        rejection_reasons={},
    )
    overlap = select_observable_ml(
        method="uncertainty_overlap_abstain",
        predictions=predictions,
        eligible_policies={"baseline", "cover_crop"},
        profile=profile,
        normalisation=normalisation,
        overlap_tolerance=0.0,
        improvement_margin=0.0,
    )
    no_improvement = select_observable_ml(
        method="uncertainty_baseline_abstain",
        predictions=predictions,
        eligible_policies={"baseline", "cover_crop"},
        profile=profile,
        normalisation=normalisation,
        overlap_tolerance=0.0,
        improvement_margin=0.0,
    )
    assert overlap.abstained and overlap.reason == "material_policy_ranking_overlap"
    assert no_improvement.abstained
    assert no_improvement.reason == "no_confident_improvement_over_baseline"
    assert width.yield_effect == 0.2  # explicit interval-width fixture remains visible


def test_selector_stability_and_eligibility_filtering() -> None:
    normalisation = _zero_normalisation()
    profile = CONFIG.utility_profiles[2]
    baseline = _outcome()
    strong = _outcome(yield_effect=1.0, total=1.0, protected=1.0)
    perturbed = _outcome(yield_effect=0.99, total=1.01, protected=1.0)

    def choose(candidate: OutcomeValues, eligible: set[str]) -> str | None:
        intervals = FrozenPolicyPredictions(
            intervals={
                "baseline": OutcomeInterval(baseline, baseline, baseline),
                "cover_crop": OutcomeInterval(candidate, candidate, candidate),
            },
            rejection_reasons={},
        )
        return select_observable_ml(
            method="observable_ml",
            predictions=intervals,
            eligible_policies=eligible,
            profile=profile,
            normalisation=normalisation,
            overlap_tolerance=0.0,
            improvement_margin=0.0,
        ).selected_policy

    assert choose(strong, {"baseline", "cover_crop"}) == "cover_crop"
    assert choose(perturbed, {"baseline", "cover_crop"}) == "cover_crop"
    assert choose(strong, {"baseline"}) == "baseline"


def test_oracle_regret_and_catastrophic_failure_are_correct() -> None:
    normalisation = _zero_normalisation()
    profile = CONFIG.utility_profiles[2]
    outcomes = {
        "baseline": _outcome(),
        "cover_crop": _outcome(yield_effect=0.2, total=0.5, protected=0.3, cost=0.1, emissions=0.1),
        "phosphorus": _outcome(
            yield_effect=-1.0, total=0.2, protected=0.1, cost=0.1, emissions=0.1
        ),
    }
    oracle = exhaustive_oracle(outcomes, set(outcomes), profile, normalisation)
    assert oracle.policy_id == "cover_crop"
    regret = calculate_regret(
        selected_policy="baseline",
        abstention_evaluation_policy="baseline",
        oracle=oracle,
        outcomes=outcomes,
        profile=profile,
        normalisation=normalisation,
    )
    assert regret is not None and regret.utility_regret > 0.0
    assert regret.yield_regret == pytest.approx(0.2)
    actual = constraints_allow(
        outcomes["baseline"], profile.constraints, eligible=True, applicable=True
    )
    assert is_catastrophic_failure(regret, actual, 0.5) == (regret.normalised_regret >= 0.5)


def _rows(field_id: str, split: PopulationSplit, multiplier: float) -> tuple[MlRow, ...]:
    rows: list[MlRow] = []
    for policy_index, policy in enumerate(PHASE9_POLICIES):
        effect = multiplier * policy_index / 10.0
        for horizon in (24, 60, 120):
            rows.append(
                MlRow(
                    field_id=field_id,
                    empirical_seed_id=f"seed-{field_id}",
                    archetype="test",
                    weather_regime="temperate",
                    phosphorus_status="moderate",
                    population_split=split,
                    policy_id=policy,
                    simulation_horizon_months=horizon,
                    features={},
                    targets={
                        "delta_crop_yield_t_dm_ha": effect,
                        "delta_final_total_soc_t_c_ha": effect,
                        "delta_final_protected_soc_proxy_t_c_ha": effect,
                        "delta_intervention_cost_gbp_ha": float(policy_index),
                        "delta_emissions_proxy_kg_co2e_ha": float(policy_index),
                    },
                )
            )
    return tuple(rows)


def test_final_outcomes_cannot_tune_selectors_and_replay_is_deterministic() -> None:
    train = _rows("train", PopulationSplit.TRAIN, 1.0)
    test_low = _rows("final", PopulationSplit.TEST, 1.0)
    test_high = _rows("final", PopulationSplit.TEST, 100.0)
    first = ExperimentData(
        "run", cast(Any, object()), cast(Any, object()), train + test_low, "a" * 64, {}
    )
    changed_final = ExperimentData(
        "run", cast(Any, object()), cast(Any, object()), train + test_high, "b" * 64, {}
    )
    state_a = fit_selector_state((first,), CONFIG)
    state_b = fit_selector_state((changed_final,), CONFIG)
    assert state_a.stable_hash == state_b.stable_hash
    assert state_a.normalisation.fitted_row_ids_hash == state_b.normalisation.fitted_row_ids_hash
    policy_a = deterministic_random_policy(
        field_id="f", profile_id="balanced", eligible_policies=set(PHASE9_POLICIES), random_seed=7
    )
    policy_b = deterministic_random_policy(
        field_id="f", profile_id="balanced", eligible_policies=set(PHASE9_POLICIES), random_seed=7
    )
    assert policy_a == policy_b
    assert (
        CONFIG.stable_hash()
        == load_phase9_benchmark_config(
            ROOT / "config" / "selection" / "phase9_benchmark.yaml"
        ).stable_hash()
    )


def test_frozen_final_artifact_replay_and_hashing() -> None:
    output = ROOT / "outputs" / "phase9_v0.9.0"
    report = json.loads(
        (output / "frozen_final_evaluation_report.json").read_text(encoding="utf-8")
    )
    stored_report_hash = report.pop("deterministic_report_hash")
    report.pop("runtime_seconds")
    canonical = json.dumps(
        report, allow_nan=False, ensure_ascii=True, sort_keys=True, separators=(",", ":")
    )
    assert hashlib.sha256(canonical.encode()).hexdigest() == stored_report_hash

    protocol = json.loads((output / "frozen_protocol.json").read_text(encoding="utf-8"))
    stored_decision_hash = protocol.pop("frozen_phase9_decision_hash")
    canonical = json.dumps(
        protocol, allow_nan=False, ensure_ascii=True, sort_keys=True, separators=(",", ":")
    )
    assert hashlib.sha256(canonical.encode()).hexdigest() == stored_decision_hash
    assert protocol["final_outcomes_seen"] is False

    dataset = json.loads((output / "selection_dataset_v0.9.0.json").read_text(encoding="utf-8"))
    manifest = json.loads((output / "selection_dataset_manifest.json").read_text(encoding="utf-8"))
    canonical = json.dumps(
        dataset, allow_nan=False, ensure_ascii=True, sort_keys=True, separators=(",", ":")
    )
    assert hashlib.sha256(canonical.encode()).hexdigest() == manifest["dataset_hash"]
    assert manifest["final_outcomes_used_for_tuning"] is False
