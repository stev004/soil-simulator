"""Strict loader and applicability guard for frozen Phase 8.6 artifacts."""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from soil_simulator.io.phase86_configuration import load_phase86_benchmark_config
from soil_simulator.ml.models import MultiTargetModel, model_from_dict
from soil_simulator.ml.phase86_schema import PHASE86_PRIMARY_TASKS
from soil_simulator.ml.preprocessing import FittedPreprocessor, preprocessor_from_dict
from soil_simulator.ml.schema import MlRow
from soil_simulator.selection.schema import FrozenArtifactExpectations


class FrozenArtifactError(RuntimeError):
    """Raised when a frozen artifact is missing, altered or incompatible."""


@dataclass(frozen=True)
class FrozenApplicability:
    """Target/regime support and training-preprocessor feature-domain contract."""

    supported: dict[tuple[str, str], bool]
    reasons: dict[tuple[str, str], str]
    maximum_absolute_standardised_feature: float


@dataclass(frozen=True)
class FrozenPhase86Bundle:
    """Verified preprocessing, models, residual widths and applicability."""

    protocol_hash: str
    frozen_decision_hash: str
    preprocessor: FittedPreprocessor
    models: dict[str, MultiTargetModel]
    half_widths: dict[str, dict[str, float]]
    applicability: FrozenApplicability
    model_hashes: dict[str, str]


def _semantic_hash(payload: object) -> str:
    canonical = json.dumps(
        payload, allow_nan=False, ensure_ascii=True, separators=(",", ":"), sort_keys=True
    )
    return hashlib.sha256(canonical.encode()).hexdigest()


def _read_json(path: Path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise FrozenArtifactError(f"could not load frozen artifact {path}: {exc}") from exc


def _model_filename(task: str) -> str:
    target, horizon = task.rsplit("@", maxsplit=1)
    return f"{target}__h{horizon}.json"


def load_frozen_phase86_bundle(
    *,
    artifact_dir: Path,
    phase86_config_path: Path,
    expected: FrozenArtifactExpectations,
) -> FrozenPhase86Bundle:
    """Load and cryptographically enforce every frozen Phase 8.6 contract."""
    raw_protocol = _read_json(artifact_dir / "frozen_protocol.json")
    if not isinstance(raw_protocol, dict):
        raise FrozenArtifactError("frozen protocol must be a JSON object")
    protocol = cast(dict[str, object], raw_protocol)
    if protocol.get("phase") != "8.6":
        raise FrozenArtifactError("frozen protocol version mismatch")
    configured_protocol_hash = load_phase86_benchmark_config(phase86_config_path).stable_hash()
    if configured_protocol_hash != expected.protocol_hash:
        raise FrozenArtifactError("Phase 8.6 configuration hash mismatch")
    if protocol.get("protocol_hash") != expected.protocol_hash:
        raise FrozenArtifactError("frozen protocol hash does not match the expected version")
    decision_payload = dict(protocol)
    stored_decision_hash = decision_payload.pop("frozen_decision_hash", None)
    computed_decision_hash = _semantic_hash(decision_payload)
    if (
        stored_decision_hash != expected.frozen_decision_hash
        or computed_decision_hash != expected.frozen_decision_hash
    ):
        raise FrozenArtifactError("frozen decision hash mismatch")

    raw_preprocessor = _read_json(artifact_dir / "preprocessing" / "observable_preprocessor.json")
    if (
        not isinstance(raw_preprocessor, dict)
        or raw_preprocessor.get("artifact_version") != "0.8.6"
    ):
        raise FrozenArtifactError("frozen preprocessing version mismatch")
    try:
        preprocessor = preprocessor_from_dict(raw_preprocessor)
    except (KeyError, TypeError, ValueError) as exc:
        raise FrozenArtifactError(f"invalid frozen preprocessing artifact: {exc}") from exc
    if preprocessor.stable_hash() != expected.preprocessing_hash:
        raise FrozenArtifactError("frozen preprocessing hash mismatch")
    if protocol.get("preprocessing_hash") != expected.preprocessing_hash:
        raise FrozenArtifactError("protocol preprocessing hash mismatch")

    protocol_model_hashes = cast(dict[str, str], protocol.get("model_hashes"))
    if protocol_model_hashes != expected.model_hashes:
        raise FrozenArtifactError("protocol model-hash registry mismatch")
    models: dict[str, MultiTargetModel] = {}
    for task in PHASE86_PRIMARY_TASKS:
        raw_model = _read_json(artifact_dir / "models" / _model_filename(task))
        if not isinstance(raw_model, dict) or raw_model.get("artifact_version") != "0.8.6":
            raise FrozenArtifactError(f"frozen model version mismatch for {task}")
        try:
            model = model_from_dict(raw_model)
        except (KeyError, TypeError, ValueError) as exc:
            raise FrozenArtifactError(f"invalid frozen model for {task}: {exc}") from exc
        if model.stable_hash() != expected.model_hashes[task]:
            raise FrozenArtifactError(f"frozen model hash mismatch for {task}")
        target, _ = task.rsplit("@", maxsplit=1)
        if model.target_names != (target,):
            raise FrozenArtifactError(f"frozen model target mismatch for {task}")
        models[task] = model

    raw_widths = protocol.get("calibration_half_widths")
    raw_domain = protocol.get("applicability_domain")
    if not isinstance(raw_widths, dict) or not isinstance(raw_domain, list):
        raise FrozenArtifactError("uncertainty calibration or applicability contract is missing")
    half_widths: dict[str, dict[str, float]] = {}
    for task in PHASE86_PRIMARY_TASKS:
        task_widths = raw_widths.get(task)
        if not isinstance(task_widths, dict):
            raise FrozenArtifactError(f"uncertainty unavailable for {task}")
        half_widths[task] = {}
        for regime, value in task_widths.items():
            width = float(cast(float | int | str, value))
            if not math.isfinite(width) or width < 0.0:
                raise FrozenArtifactError(f"unsupported uncertainty width for {task}/{regime}")
            half_widths[task][str(regime)] = width

    supported: dict[tuple[str, str], bool] = {}
    reasons: dict[tuple[str, str], str] = {}
    for raw_item in raw_domain:
        if not isinstance(raw_item, dict):
            raise FrozenArtifactError("invalid applicability-domain entry")
        item = cast(dict[str, object], raw_item)
        key = (str(item["target_task"]), str(item["regime"]))
        if key in supported:
            raise FrozenArtifactError(f"duplicate applicability entry {key}")
        supported[key] = bool(item["supported"])
        reasons[key] = str(item["reason"])
    for task in PHASE86_PRIMARY_TASKS:
        if not any(key[0] == task for key in supported):
            raise FrozenArtifactError(f"applicability unavailable for {task}")
        for task_key, regime in tuple(supported):
            if task_key == task and regime not in half_widths[task]:
                raise FrozenArtifactError(f"uncertainty unavailable for {task}/{regime}")
    return FrozenPhase86Bundle(
        protocol_hash=expected.protocol_hash,
        frozen_decision_hash=expected.frozen_decision_hash,
        preprocessor=preprocessor,
        models=models,
        half_widths=half_widths,
        applicability=FrozenApplicability(
            supported=supported,
            reasons=reasons,
            maximum_absolute_standardised_feature=(expected.maximum_absolute_standardised_feature),
        ),
        model_hashes=dict(expected.model_hashes),
    )


def observable_applicability_reasons(
    row: MlRow,
    *,
    task: str,
    bundle: FrozenPhase86Bundle,
) -> tuple[str, ...]:
    """Check only observable inputs, frozen regimes and uncertainty support."""
    reasons: list[str] = []
    regime_key = (task, row.weather_regime)
    if not bundle.applicability.supported.get(regime_key, False):
        reasons.append("unsupported_target_weather_regime")
    if row.weather_regime not in bundle.half_widths.get(task, {}):
        reasons.append("uncertainty_unavailable")
    for index, name in enumerate(bundle.preprocessor.numeric_features):
        raw = row.features.get(name)
        if raw is None:
            reasons.append(f"missing_observation:{name}")
            continue
        try:
            value = float(raw)
        except (TypeError, ValueError):
            reasons.append(f"invalid_observation:{name}")
            continue
        if not math.isfinite(value):
            reasons.append(f"invalid_observation:{name}")
            continue
        standardised = (value - bundle.preprocessor.numeric_means[index]) / (
            bundle.preprocessor.numeric_scales[index]
        )
        if abs(standardised) > bundle.applicability.maximum_absolute_standardised_feature:
            reasons.append(f"outside_numeric_domain:{name}")
    for index, name in enumerate(bundle.preprocessor.categorical_features):
        raw = row.features.get(name)
        if raw is None:
            reasons.append(f"missing_observation:{name}")
        elif str(raw) not in bundle.preprocessor.categorical_levels[index]:
            reasons.append(f"outside_categorical_domain:{name}")
    return tuple(sorted(set(reasons)))


def predict_frozen_task(
    row: MlRow,
    *,
    task: str,
    bundle: FrozenPhase86Bundle,
) -> tuple[float, float]:
    """Return one frozen point prediction and supported residual half-width."""
    reasons = observable_applicability_reasons(row, task=task, bundle=bundle)
    if reasons:
        raise FrozenArtifactError("; ".join(reasons))
    matrix = (bundle.preprocessor.transform(row),)
    prediction = bundle.models[task].predict(matrix, (row.policy_id,))[0][0]
    width = bundle.half_widths[task][row.weather_regime]
    if not math.isfinite(prediction):
        raise FrozenArtifactError("frozen model returned a non-finite prediction")
    return prediction, width
