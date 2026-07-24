"""Explicit local/cached adapters for versioned empirical seed records.

Adapters perform no network I/O. A caller must explicitly provide a local file
or a previously cached file and, for the cached adapter, its expected SHA-256.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Protocol

import yaml
from pydantic import ValidationError

from soil_simulator.domain.population import EmpiricalDataset


class DatasetAdapterError(ValueError):
    """Raised when a population dataset cannot be read or validated."""


class EmpiricalDatasetAdapter(Protocol):
    """Adapter boundary for versioned local or explicitly cached datasets."""

    def load(self, path: str | Path) -> EmpiricalDataset:
        """Load a validated adapter-neutral empirical dataset."""


class VersionedLocalYamlAdapter:
    """Load a caller-selected versioned YAML dataset without network access."""

    adapter_name = "versioned_local_yaml"
    adapter_version = "1.0.0"

    def load(self, path: str | Path) -> EmpiricalDataset:
        """Read and validate a local YAML seed/weather collection."""
        dataset_path = Path(path)
        try:
            raw: object = yaml.safe_load(dataset_path.read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError) as exc:
            raise DatasetAdapterError(
                f"could not read population dataset {dataset_path}: {exc}"
            ) from exc
        try:
            dataset = EmpiricalDataset.model_validate(raw)
        except ValidationError as exc:
            raise DatasetAdapterError(f"invalid population dataset {dataset_path}: {exc}") from exc
        if dataset.adapter_name != self.adapter_name:
            raise DatasetAdapterError(
                f"dataset declares adapter {dataset.adapter_name!r}, expected {self.adapter_name!r}"
            )
        if dataset.adapter_version != self.adapter_version:
            raise DatasetAdapterError(
                f"dataset adapter version {dataset.adapter_version!r} is not supported"
            )
        return dataset


class CachedYamlDatasetAdapter:
    """Load an explicit cached YAML file only when its expected digest matches."""

    def __init__(self, expected_sha256: str) -> None:
        if len(expected_sha256) != 64 or any(
            character not in "0123456789abcdef" for character in expected_sha256
        ):
            raise ValueError("expected_sha256 must be a lowercase SHA-256 digest")
        self.expected_sha256 = expected_sha256

    def load(self, path: str | Path) -> EmpiricalDataset:
        """Verify cache identity before applying the versioned local adapter."""
        dataset_path = Path(path)
        try:
            payload = dataset_path.read_bytes()
        except OSError as exc:
            raise DatasetAdapterError(
                f"could not read cached dataset {dataset_path}: {exc}"
            ) from exc
        observed = hashlib.sha256(payload).hexdigest()
        if observed != self.expected_sha256:
            raise DatasetAdapterError(
                "cached dataset hash mismatch: "
                f"expected {self.expected_sha256}, observed {observed}"
            )
        return VersionedLocalYamlAdapter().load(dataset_path)
