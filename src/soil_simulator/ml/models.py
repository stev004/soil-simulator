"""Transparent deterministic baselines and nonlinear models for Phase 8.x."""

from __future__ import annotations

import hashlib
import json
import math
import random
from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol, cast


class MultiTargetModel(Protocol):
    """Minimal serializable multi-target regression interface."""

    @property
    def model_type(self) -> str: ...

    @property
    def target_names(self) -> tuple[str, ...]: ...

    def predict(
        self, matrix: tuple[tuple[float, ...], ...], policies: tuple[str, ...]
    ) -> tuple[tuple[float, ...], ...]: ...

    def model_dump(self) -> dict[str, object]: ...

    def stable_hash(self) -> str: ...


def _semantic_hash(payload: dict[str, object]) -> str:
    canonical = json.dumps(
        payload, allow_nan=False, ensure_ascii=True, separators=(",", ":"), sort_keys=True
    )
    return hashlib.sha256(canonical.encode()).hexdigest()


@dataclass(frozen=True)
class GlobalMeanModel:
    """Training-target mean baseline."""

    target_names: tuple[str, ...]
    means: tuple[float, ...]
    model_type: str = "global_target_mean"

    def predict(
        self, matrix: tuple[tuple[float, ...], ...], policies: tuple[str, ...]
    ) -> tuple[tuple[float, ...], ...]:
        del policies
        return tuple(self.means for _ in matrix)

    def model_dump(self) -> dict[str, object]:
        return {
            "artifact_version": "0.8.6",
            "model_type": self.model_type,
            "target_names": list(self.target_names),
            "means": list(self.means),
        }

    def stable_hash(self) -> str:
        return _semantic_hash(self.model_dump())


@dataclass(frozen=True)
class PolicyMeanModel:
    """Training-only policy-specific target mean with a global fallback."""

    target_names: tuple[str, ...]
    global_means: tuple[float, ...]
    policy_means: dict[str, tuple[float, ...]]
    model_type: str = "policy_specific_target_mean"

    def predict(
        self, matrix: tuple[tuple[float, ...], ...], policies: tuple[str, ...]
    ) -> tuple[tuple[float, ...], ...]:
        if len(matrix) != len(policies):
            raise ValueError("matrix and policy lengths differ")
        return tuple(self.policy_means.get(policy, self.global_means) for policy in policies)

    def model_dump(self) -> dict[str, object]:
        return {
            "artifact_version": "0.8.6",
            "model_type": self.model_type,
            "target_names": list(self.target_names),
            "global_means": list(self.global_means),
            "policy_means": {
                policy: list(values) for policy, values in sorted(self.policy_means.items())
            },
        }

    def stable_hash(self) -> str:
        return _semantic_hash(self.model_dump())


def fit_global_mean(
    targets: tuple[tuple[float, ...], ...], target_names: tuple[str, ...]
) -> GlobalMeanModel:
    """Fit honest means from the supplied training outcomes only."""
    if not targets:
        raise ValueError("cannot fit a mean without targets")
    width = len(target_names)
    means = tuple(math.fsum(row[index] for row in targets) / len(targets) for index in range(width))
    return GlobalMeanModel(target_names=target_names, means=means)


def fit_policy_mean(
    targets: tuple[tuple[float, ...], ...],
    policies: tuple[str, ...],
    target_names: tuple[str, ...],
) -> PolicyMeanModel:
    """Fit policy means using only rows explicitly supplied by the caller."""
    if len(targets) != len(policies) or not targets:
        raise ValueError("policy mean inputs are empty or misaligned")
    global_model = fit_global_mean(targets, target_names)
    grouped: dict[str, list[tuple[float, ...]]] = {}
    for policy, row in zip(policies, targets, strict=True):
        grouped.setdefault(policy, []).append(row)
    policy_means = {
        policy: tuple(
            math.fsum(row[index] for row in values) / len(values)
            for index in range(len(target_names))
        )
        for policy, values in grouped.items()
    }
    return PolicyMeanModel(
        target_names=target_names,
        global_means=global_model.means,
        policy_means=policy_means,
    )


def _solve_linear_system(matrix: list[list[float]], vector: list[float]) -> tuple[float, ...]:
    """Solve a positive-definite ridge system with deterministic pivoting."""
    size = len(vector)
    augmented = [[*row, vector[index]] for index, row in enumerate(matrix)]
    for column in range(size):
        pivot = max(range(column, size), key=lambda row: abs(augmented[row][column]))
        if abs(augmented[pivot][column]) <= 1.0e-15:
            raise ValueError("singular regularised linear system")
        augmented[column], augmented[pivot] = augmented[pivot], augmented[column]
        divisor = augmented[column][column]
        augmented[column] = [value / divisor for value in augmented[column]]
        for row in range(size):
            if row == column:
                continue
            factor = augmented[row][column]
            if factor != 0.0:
                augmented[row] = [
                    left - factor * right
                    for left, right in zip(augmented[row], augmented[column], strict=True)
                ]
    return tuple(augmented[index][-1] for index in range(size))


@dataclass(frozen=True)
class RidgeModel:
    """Multi-target L2-regularised linear regression with an explicit intercept."""

    target_names: tuple[str, ...]
    feature_names: tuple[str, ...]
    alpha: float
    coefficients: tuple[tuple[float, ...], ...]
    model_type: str = "regularised_linear_regression"

    def predict(
        self, matrix: tuple[tuple[float, ...], ...], policies: tuple[str, ...]
    ) -> tuple[tuple[float, ...], ...]:
        del policies
        predictions: list[tuple[float, ...]] = []
        for row in matrix:
            design = (1.0, *row)
            predictions.append(
                tuple(
                    math.fsum(weight * value for weight, value in zip(weights, design, strict=True))
                    for weights in self.coefficients
                )
            )
        return tuple(predictions)

    def model_dump(self) -> dict[str, object]:
        return {
            "artifact_version": "0.8.6",
            "model_type": self.model_type,
            "target_names": list(self.target_names),
            "feature_names": list(self.feature_names),
            "alpha": self.alpha,
            "coefficients": [list(row) for row in self.coefficients],
        }

    def stable_hash(self) -> str:
        return _semantic_hash(self.model_dump())


def fit_ridge(
    matrix: tuple[tuple[float, ...], ...],
    targets: tuple[tuple[float, ...], ...],
    target_names: tuple[str, ...],
    feature_names: tuple[str, ...],
    alpha: float,
) -> RidgeModel:
    """Fit deterministic ridge normal equations."""
    if not matrix or len(matrix) != len(targets) or alpha <= 0.0:
        raise ValueError("invalid ridge training inputs")
    design = tuple((1.0, *row) for row in matrix)
    width = len(design[0])
    gram = [
        [math.fsum(row[left] * row[right] for row in design) for right in range(width)]
        for left in range(width)
    ]
    for index in range(1, width):
        gram[index][index] += alpha
    coefficients: list[tuple[float, ...]] = []
    for target_index in range(len(target_names)):
        rhs = [
            math.fsum(
                row[column] * target[target_index]
                for row, target in zip(design, targets, strict=True)
            )
            for column in range(width)
        ]
        coefficients.append(_solve_linear_system(gram, rhs))
    return RidgeModel(
        target_names=target_names,
        feature_names=feature_names,
        alpha=alpha,
        coefficients=tuple(coefficients),
    )


@dataclass(frozen=True)
class ForestNode:
    """One deterministic multi-output regression-tree node."""

    prediction: tuple[float, ...]
    feature_index: int | None = None
    threshold: float | None = None
    left: ForestNode | None = None
    right: ForestNode | None = None
    gain: float = 0.0

    @property
    def is_leaf(self) -> bool:
        return self.feature_index is None

    def predict(self, row: tuple[float, ...]) -> tuple[float, ...]:
        node = self
        while not node.is_leaf:
            if node.feature_index is None or node.threshold is None:
                raise RuntimeError("invalid tree node")
            child = node.left if row[node.feature_index] <= node.threshold else node.right
            if child is None:
                raise RuntimeError("tree branch is missing")
            node = child
        return node.prediction

    def model_dump(self) -> dict[str, object]:
        return {
            "prediction": list(self.prediction),
            "feature_index": self.feature_index,
            "threshold": self.threshold,
            "gain": self.gain,
            "left": None if self.left is None else self.left.model_dump(),
            "right": None if self.right is None else self.right.model_dump(),
        }

    @classmethod
    def model_validate(cls, value: object) -> ForestNode:
        data = cast(dict[str, object], value)
        return cls(
            prediction=tuple(
                float(cast(str | float | int, item))
                for item in cast(list[object], data["prediction"])
            ),
            feature_index=(
                None if data.get("feature_index") is None else int(cast(int, data["feature_index"]))
            ),
            threshold=None
            if data.get("threshold") is None
            else float(cast(str | float | int, data["threshold"])),
            gain=float(cast(str | float | int, data.get("gain", 0.0))),
            left=None if data.get("left") is None else cls.model_validate(data["left"]),
            right=None if data.get("right") is None else cls.model_validate(data["right"]),
        )


@dataclass(frozen=True)
class RandomForestModel:
    """Deterministic bagged multi-output regression trees."""

    target_names: tuple[str, ...]
    feature_names: tuple[str, ...]
    trees: tuple[ForestNode, ...]
    max_depth: int
    min_leaf: int
    feature_fraction: float
    random_seed: int
    feature_importances: tuple[float, ...]
    model_type: str = "deterministic_random_forest"

    def predict(
        self, matrix: tuple[tuple[float, ...], ...], policies: tuple[str, ...]
    ) -> tuple[tuple[float, ...], ...]:
        del policies
        predictions: list[tuple[float, ...]] = []
        for row in matrix:
            tree_predictions = [tree.predict(row) for tree in self.trees]
            predictions.append(
                tuple(
                    math.fsum(values[index] for values in tree_predictions) / len(self.trees)
                    for index in range(len(self.target_names))
                )
            )
        return tuple(predictions)

    def model_dump(self) -> dict[str, object]:
        return {
            "artifact_version": "0.8.6",
            "model_type": self.model_type,
            "target_names": list(self.target_names),
            "feature_names": list(self.feature_names),
            "trees": [tree.model_dump() for tree in self.trees],
            "max_depth": self.max_depth,
            "min_leaf": self.min_leaf,
            "feature_fraction": self.feature_fraction,
            "random_seed": self.random_seed,
            "feature_importances": list(self.feature_importances),
        }

    def stable_hash(self) -> str:
        return _semantic_hash(self.model_dump())


def _target_means(targets: tuple[tuple[float, ...], ...], indices: list[int]) -> tuple[float, ...]:
    return tuple(
        math.fsum(targets[index][column] for index in indices) / len(indices)
        for column in range(len(targets[0]))
    )


def _normalised_sse(
    targets: tuple[tuple[float, ...], ...],
    indices: list[int],
    variances: tuple[float, ...],
) -> float:
    means = _target_means(targets, indices)
    return math.fsum(
        (targets[index][column] - means[column]) ** 2 / variances[column]
        for index in indices
        for column in range(len(means))
    )


def _build_tree(
    matrix: tuple[tuple[float, ...], ...],
    targets: tuple[tuple[float, ...], ...],
    indices: list[int],
    *,
    depth: int,
    max_depth: int,
    min_leaf: int,
    feature_count: int,
    rng: random.Random,
    variances: tuple[float, ...],
    importance: list[float],
) -> ForestNode:
    prediction = _target_means(targets, indices)
    if depth >= max_depth or len(indices) < 2 * min_leaf:
        return ForestNode(prediction=prediction)
    selected = sorted(rng.sample(range(len(matrix[0])), min(feature_count, len(matrix[0]))))
    best: tuple[float, int, float, list[int], list[int]] | None = None
    for feature_index in selected:
        unique = sorted({matrix[index][feature_index] for index in indices})
        if len(unique) < 2:
            continue
        positions = sorted({len(unique) // 4, len(unique) // 2, (3 * len(unique)) // 4})
        for position in positions:
            if position <= 0 or position >= len(unique):
                continue
            threshold = (unique[position - 1] + unique[position]) / 2.0
            left = [index for index in indices if matrix[index][feature_index] <= threshold]
            right = [index for index in indices if matrix[index][feature_index] > threshold]
            if len(left) < min_leaf or len(right) < min_leaf:
                continue
            left_means = _target_means(targets, left)
            right_means = _target_means(targets, right)
            gain = (len(left) * len(right) / len(indices)) * math.fsum(
                (left_means[column] - right_means[column]) ** 2 / variances[column]
                for column in range(len(variances))
            )
            candidate = (gain, feature_index, threshold, left, right)
            if best is None or candidate[:3] > best[:3]:
                best = candidate
    if best is None or best[0] <= 1.0e-12:
        return ForestNode(prediction=prediction)
    gain, feature_index, threshold, left_indices, right_indices = best
    importance[feature_index] += gain
    left_node = _build_tree(
        matrix,
        targets,
        left_indices,
        depth=depth + 1,
        max_depth=max_depth,
        min_leaf=min_leaf,
        feature_count=feature_count,
        rng=rng,
        variances=variances,
        importance=importance,
    )
    right_node = _build_tree(
        matrix,
        targets,
        right_indices,
        depth=depth + 1,
        max_depth=max_depth,
        min_leaf=min_leaf,
        feature_count=feature_count,
        rng=rng,
        variances=variances,
        importance=importance,
    )
    return ForestNode(
        prediction=prediction,
        feature_index=feature_index,
        threshold=threshold,
        left=left_node,
        right=right_node,
        gain=gain,
    )


def fit_random_forest(
    matrix: tuple[tuple[float, ...], ...],
    targets: tuple[tuple[float, ...], ...],
    target_names: tuple[str, ...],
    feature_names: tuple[str, ...],
    *,
    tree_count: int,
    max_depth: int,
    min_leaf: int,
    feature_fraction: float,
    random_seed: int,
) -> RandomForestModel:
    """Fit a deterministic bagged nonlinear model using normalised multi-target splits."""
    if not matrix or len(matrix) != len(targets):
        raise ValueError("invalid forest training inputs")
    rng = random.Random(random_seed)
    target_width = len(target_names)
    target_means = tuple(
        math.fsum(row[column] for row in targets) / len(targets) for column in range(target_width)
    )
    variances = tuple(
        max(
            math.fsum((row[column] - target_means[column]) ** 2 for row in targets) / len(targets),
            1.0e-12,
        )
        for column in range(target_width)
    )
    feature_count = max(1, math.ceil(len(matrix[0]) * feature_fraction))
    importance = [0.0] * len(matrix[0])
    trees: list[ForestNode] = []
    for _ in range(tree_count):
        bootstrap = [rng.randrange(len(matrix)) for _ in range(len(matrix))]
        trees.append(
            _build_tree(
                matrix,
                targets,
                bootstrap,
                depth=0,
                max_depth=max_depth,
                min_leaf=min_leaf,
                feature_count=feature_count,
                rng=rng,
                variances=variances,
                importance=importance,
            )
        )
    total_importance = math.fsum(importance)
    normalised = tuple(
        value / total_importance if total_importance > 0.0 else 0.0 for value in importance
    )
    return RandomForestModel(
        target_names=target_names,
        feature_names=feature_names,
        trees=tuple(trees),
        max_depth=max_depth,
        min_leaf=min_leaf,
        feature_fraction=feature_fraction,
        random_seed=random_seed,
        feature_importances=normalised,
    )


@dataclass(frozen=True)
class PerPolicyModel:
    """One separately fitted outcome model per intervention policy."""

    target_names: tuple[str, ...]
    policy_models: dict[str, MultiTargetModel]
    model_type: str = "separate_per_policy_models"

    def predict(
        self, matrix: tuple[tuple[float, ...], ...], policies: tuple[str, ...]
    ) -> tuple[tuple[float, ...], ...]:
        if len(matrix) != len(policies):
            raise ValueError("matrix and policy lengths differ")
        predictions: list[tuple[float, ...]] = []
        for row, policy in zip(matrix, policies, strict=True):
            model = self.policy_models.get(policy)
            if model is None:
                raise ValueError(f"no separately fitted model for policy {policy!r}")
            predictions.append(model.predict((row,), (policy,))[0])
        return tuple(predictions)

    def model_dump(self) -> dict[str, object]:
        return {
            "artifact_version": "0.8.6",
            "model_type": self.model_type,
            "target_names": list(self.target_names),
            "policy_models": {
                policy: model.model_dump() for policy, model in sorted(self.policy_models.items())
            },
        }

    def stable_hash(self) -> str:
        return _semantic_hash(self.model_dump())


def fit_per_policy(
    matrix: tuple[tuple[float, ...], ...],
    targets: tuple[tuple[float, ...], ...],
    policies: tuple[str, ...],
    fitter: Callable[
        [tuple[tuple[float, ...], ...], tuple[tuple[float, ...], ...], str],
        MultiTargetModel,
    ],
) -> PerPolicyModel:
    """Fit a supplied deterministic model factory independently by policy."""
    if not matrix or len(matrix) != len(targets) or len(matrix) != len(policies):
        raise ValueError("invalid per-policy training inputs")
    models: dict[str, MultiTargetModel] = {}
    for policy in sorted(set(policies)):
        indices = [index for index, value in enumerate(policies) if value == policy]
        models[policy] = fitter(
            tuple(matrix[index] for index in indices),
            tuple(targets[index] for index in indices),
            policy,
        )
    first = next(iter(models.values()))
    return PerPolicyModel(target_names=first.target_names, policy_models=models)


def model_from_dict(value: object) -> MultiTargetModel:
    """Restore any Phase 8.5 model artifact for serialization/replay tests."""
    data = cast(dict[str, object], value)
    target_names = tuple(str(item) for item in cast(list[object], data["target_names"]))
    model_type = data.get("model_type")
    if model_type == "separate_per_policy_models":
        raw_models = cast(dict[str, object], data["policy_models"])
        return PerPolicyModel(
            target_names=target_names,
            policy_models={policy: model_from_dict(model) for policy, model in raw_models.items()},
        )
    if model_type == "global_target_mean":
        return GlobalMeanModel(
            target_names=target_names,
            means=tuple(
                float(cast(str | float | int, item)) for item in cast(list[object], data["means"])
            ),
        )
    if model_type == "policy_specific_target_mean":
        raw_means = cast(dict[str, object], data["policy_means"])
        return PolicyMeanModel(
            target_names=target_names,
            global_means=tuple(
                float(cast(str | float | int, item))
                for item in cast(list[object], data["global_means"])
            ),
            policy_means={
                policy: tuple(
                    float(cast(str | float | int, item)) for item in cast(list[object], values)
                )
                for policy, values in raw_means.items()
            },
        )
    if model_type == "regularised_linear_regression":
        return RidgeModel(
            target_names=target_names,
            feature_names=tuple(str(item) for item in cast(list[object], data["feature_names"])),
            alpha=float(cast(str | float | int, data["alpha"])),
            coefficients=tuple(
                tuple(float(cast(str | float | int, item)) for item in cast(list[object], row))
                for row in cast(list[object], data["coefficients"])
            ),
        )
    if model_type == "deterministic_random_forest":
        return RandomForestModel(
            target_names=target_names,
            feature_names=tuple(str(item) for item in cast(list[object], data["feature_names"])),
            trees=tuple(
                ForestNode.model_validate(item) for item in cast(list[object], data["trees"])
            ),
            max_depth=int(cast(int, data["max_depth"])),
            min_leaf=int(cast(int, data["min_leaf"])),
            feature_fraction=float(cast(str | float | int, data["feature_fraction"])),
            random_seed=int(cast(int, data["random_seed"])),
            feature_importances=tuple(
                float(cast(str | float | int, item))
                for item in cast(list[object], data["feature_importances"])
            ),
        )
    raise ValueError(f"unknown Phase 8.5 model type: {model_type}")
