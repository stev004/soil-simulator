"""Load the frozen Phase 8.6 repeated-experiment protocol."""

from pathlib import Path

import yaml
from pydantic import ValidationError

from soil_simulator.io.configuration import ConfigLoadError
from soil_simulator.ml.phase86_schema import Phase86BenchmarkConfig


def load_phase86_benchmark_config(path: str | Path) -> Phase86BenchmarkConfig:
    """Load strict Phase 8.6 settings without network I/O."""
    config_path = Path(path)
    try:
        raw: object = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise ConfigLoadError(
            f"could not read Phase 8.6 configuration {config_path}: {exc}"
        ) from exc
    try:
        return Phase86BenchmarkConfig.model_validate(raw)
    except ValidationError as exc:
        raise ConfigLoadError(f"invalid Phase 8.6 configuration {config_path}: {exc}") from exc
