"""Training-only deterministic preprocessing for Phase 8.x feature sets."""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from typing import cast

from soil_simulator.domain.enums import PopulationSplit
from soil_simulator.ml.schema import FEATURE_SETS, FeatureSet, MlRow


@dataclass(frozen=True)
class FittedPreprocessor:
    """Means/scales and one-hot levels fitted without validation/test rows."""

    feature_set_name: str
    numeric_features: tuple[str, ...]
    categorical_features: tuple[str, ...]
    numeric_means: tuple[float, ...]
    numeric_scales: tuple[float, ...]
    categorical_levels: tuple[tuple[str, ...], ...]
    output_feature_names: tuple[str, ...]
    fitted_row_ids_hash: str

    def transform(self, row: MlRow) -> tuple[float, ...]:
        """Transform one row; unknown validation/test categories map to all-zero indicators."""
        values: list[float] = []
        for index, name in enumerate(self.numeric_features):
            numeric_raw = float(row.features[name])
            values.append((numeric_raw - self.numeric_means[index]) / self.numeric_scales[index])
        for index, name in enumerate(self.categorical_features):
            categorical_raw = str(row.features[name])
            values.extend(
                1.0 if categorical_raw == level else 0.0 for level in self.categorical_levels[index]
            )
        return tuple(values)

    def model_dump(self) -> dict[str, object]:
        """Return a JSON-safe deterministic preprocessing artifact."""
        return {
            "artifact_type": "soil_simulator_fitted_preprocessor",
            "artifact_version": "0.8.6",
            "feature_set_name": self.feature_set_name,
            "numeric_features": list(self.numeric_features),
            "categorical_features": list(self.categorical_features),
            "numeric_means": list(self.numeric_means),
            "numeric_scales": list(self.numeric_scales),
            "categorical_levels": [list(levels) for levels in self.categorical_levels],
            "output_feature_names": list(self.output_feature_names),
            "fitted_row_ids_hash": self.fitted_row_ids_hash,
        }

    @classmethod
    def model_validate(cls, value: object) -> FittedPreprocessor:
        """Restore a strict preprocessing artifact."""
        data = cast(dict[str, object], value)
        if data.get("artifact_type") not in {
            "phase85_fitted_preprocessor",
            "soil_simulator_fitted_preprocessor",
        }:
            raise ValueError("not a supported fitted preprocessor artifact")
        return cls(
            feature_set_name=str(data["feature_set_name"]),
            numeric_features=tuple(
                str(item) for item in cast(list[object], data["numeric_features"])
            ),
            categorical_features=tuple(
                str(item) for item in cast(list[object], data["categorical_features"])
            ),
            numeric_means=tuple(
                float(cast(str | float | int, item))
                for item in cast(list[object], data["numeric_means"])
            ),
            numeric_scales=tuple(
                float(cast(str | float | int, item))
                for item in cast(list[object], data["numeric_scales"])
            ),
            categorical_levels=tuple(
                tuple(str(item) for item in cast(list[object], levels))
                for levels in cast(list[object], data["categorical_levels"])
            ),
            output_feature_names=tuple(
                str(item) for item in cast(list[object], data["output_feature_names"])
            ),
            fitted_row_ids_hash=str(data["fitted_row_ids_hash"]),
        )

    def stable_hash(self) -> str:
        """Hash the semantic preprocessing state."""
        canonical = json.dumps(
            self.model_dump(),
            allow_nan=False,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )
        return hashlib.sha256(canonical.encode()).hexdigest()


def _row_ids_hash(rows: tuple[MlRow, ...]) -> str:
    payload = json.dumps(sorted(row.row_id for row in rows), separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()


def fit_preprocessor(
    rows: tuple[MlRow, ...],
    feature_set: FeatureSet,
    *,
    require_training_split: bool = True,
) -> FittedPreprocessor:
    """Fit numeric scaling and categories on supplied rows only.

    Final benchmark fitting requires the frozen training split. Separate OOD
    experiments may explicitly disable that check while still fitting only on
    their own development subset.
    """
    if not rows:
        raise ValueError("cannot fit preprocessing without rows")
    if require_training_split and any(
        row.population_split is not PopulationSplit.TRAIN for row in rows
    ):
        raise ValueError("final preprocessing may be fitted on training rows only")
    means: list[float] = []
    scales: list[float] = []
    for name in feature_set.numeric:
        values = [float(row.features[name]) for row in rows]
        mean = math.fsum(values) / len(values)
        variance = math.fsum((value - mean) ** 2 for value in values) / len(values)
        means.append(mean)
        scales.append(math.sqrt(variance) if variance > 0.0 else 1.0)
    levels = tuple(
        tuple(sorted({str(row.features[name]) for row in rows})) for name in feature_set.categorical
    )
    output_names = list(feature_set.numeric)
    for name, categories in zip(feature_set.categorical, levels, strict=True):
        output_names.extend(f"{name}={category}" for category in categories)
    return FittedPreprocessor(
        feature_set_name=feature_set.name,
        numeric_features=feature_set.numeric,
        categorical_features=feature_set.categorical,
        numeric_means=tuple(means),
        numeric_scales=tuple(scales),
        categorical_levels=levels,
        output_feature_names=tuple(output_names),
        fitted_row_ids_hash=_row_ids_hash(rows),
    )


def preprocessor_from_dict(value: object) -> FittedPreprocessor:
    """Restore and validate feature-set identity and separation."""
    fitted = FittedPreprocessor.model_validate(value)
    expected = FEATURE_SETS.get(fitted.feature_set_name)
    if expected is None:
        raise ValueError(f"unknown feature set {fitted.feature_set_name}")
    if (
        fitted.numeric_features != expected.numeric
        or fitted.categorical_features != expected.categorical
    ):
        raise ValueError("serialized preprocessing feature registry has changed")
    return fitted
