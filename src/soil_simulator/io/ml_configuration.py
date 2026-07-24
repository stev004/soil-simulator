"""Load strict Phase 8.5 ML diagnostic configuration."""

from pathlib import Path

import yaml
from pydantic import ValidationError

from soil_simulator.io.configuration import ConfigLoadError
from soil_simulator.ml.schema import Phase8BenchmarkConfig


def load_ml_benchmark_config(path: str | Path) -> Phase8BenchmarkConfig:
    """Load deterministic Phase 8.5 settings without network I/O."""
    config_path = Path(path)
    try:
        raw: object = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise ConfigLoadError(f"could not read ML configuration {config_path}: {exc}") from exc
    try:
        return Phase8BenchmarkConfig.model_validate(raw)
    except ValidationError as exc:
        raise ConfigLoadError(f"invalid ML configuration {config_path}: {exc}") from exc
