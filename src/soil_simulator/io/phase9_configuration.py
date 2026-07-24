"""Load the strict Phase 9 selection-benchmark protocol."""

from pathlib import Path

import yaml
from pydantic import ValidationError

from soil_simulator.io.configuration import ConfigLoadError
from soil_simulator.selection.schema import Phase9BenchmarkConfig


def load_phase9_benchmark_config(path: str | Path) -> Phase9BenchmarkConfig:
    """Load versioned scenario choices without network I/O."""
    config_path = Path(path)
    try:
        raw: object = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise ConfigLoadError(f"could not read Phase 9 configuration {config_path}: {exc}") from exc
    try:
        return Phase9BenchmarkConfig.model_validate(raw)
    except ValidationError as exc:
        raise ConfigLoadError(f"invalid Phase 9 configuration {config_path}: {exc}") from exc
