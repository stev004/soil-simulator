"""Load strict Phase 7 population-generation configuration."""

from pathlib import Path

import yaml
from pydantic import ValidationError

from soil_simulator.domain.population import PopulationGenerationConfig
from soil_simulator.io.configuration import ConfigLoadError


def load_population_config(path: str | Path) -> PopulationGenerationConfig:
    """Load a validated versioned population configuration without network I/O."""
    config_path = Path(path)
    try:
        raw: object = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise ConfigLoadError(
            f"could not read population configuration {config_path}: {exc}"
        ) from exc
    try:
        return PopulationGenerationConfig.model_validate(raw)
    except ValidationError as exc:
        raise ConfigLoadError(f"invalid population configuration {config_path}: {exc}") from exc
