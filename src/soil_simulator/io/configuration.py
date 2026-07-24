"""Load YAML configuration into strict domain objects."""

from pathlib import Path

import yaml
from pydantic import ValidationError

from soil_simulator.domain.carbon import CarbonCoreScenario
from soil_simulator.domain.management import ManagementScenarioSet
from soil_simulator.domain.models import ModelParameters
from soil_simulator.domain.plant import PlantScenario


class ConfigLoadError(ValueError):
    """Raised when model configuration cannot be read or validated."""


def load_model_parameters(path: str | Path) -> ModelParameters:
    """Load and validate a model configuration file without retaining raw mappings."""
    config_path = Path(path)
    try:
        raw: object = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise ConfigLoadError(f"could not read configuration {config_path}: {exc}") from exc
    try:
        return ModelParameters.model_validate(raw)
    except ValidationError as exc:
        raise ConfigLoadError(f"invalid configuration {config_path}: {exc}") from exc


def load_carbon_core_scenario(path: str | Path) -> CarbonCoreScenario:
    """Load and validate a predefined deterministic carbon-core scenario."""
    scenario_path = Path(path)
    try:
        raw: object = yaml.safe_load(scenario_path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise ConfigLoadError(f"could not read scenario {scenario_path}: {exc}") from exc
    try:
        return CarbonCoreScenario.model_validate(raw)
    except ValidationError as exc:
        raise ConfigLoadError(f"invalid scenario {scenario_path}: {exc}") from exc


def load_plant_scenario(path: str | Path) -> PlantScenario:
    """Load and validate a deterministic Phase 4 plant/P scenario."""
    scenario_path = Path(path)
    try:
        raw: object = yaml.safe_load(scenario_path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise ConfigLoadError(f"could not read scenario {scenario_path}: {exc}") from exc
    try:
        return PlantScenario.model_validate(raw)
    except ValidationError as exc:
        raise ConfigLoadError(f"invalid scenario {scenario_path}: {exc}") from exc


def load_management_scenarios(path: str | Path) -> ManagementScenarioSet:
    """Load and validate predefined deterministic Phase 6 policies."""
    scenario_path = Path(path)
    try:
        raw: object = yaml.safe_load(scenario_path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise ConfigLoadError(f"could not read scenario {scenario_path}: {exc}") from exc
    try:
        return ManagementScenarioSet.model_validate(raw)
    except ValidationError as exc:
        raise ConfigLoadError(f"invalid scenario {scenario_path}: {exc}") from exc
