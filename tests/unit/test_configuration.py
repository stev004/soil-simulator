"""Configuration loading and deterministic hash tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from soil_simulator.domain.enums import ParameterSource
from soil_simulator.io.configuration import ConfigLoadError, load_model_parameters

CONFIG_PATH = Path(__file__).parents[2] / "config" / "model_defaults.yaml"
EXPECTED_DEFAULT_CONFIG_HASH = "d9864cf8f17956ee313abbec6937f508d3de98c24fb25931e74759a975c65efb"


def test_default_configuration_loads_to_typed_contracts() -> None:
    parameters = load_model_parameters(CONFIG_PATH)
    assert parameters.model.name == "soil_simulator"
    assert parameters.rothc.classification is ParameterSource.ESTABLISHED_MODEL
    assert "10.5281/zenodo.10732265" in parameters.rothc.source_citation
    assert (
        parameters.amf.photosynthate_allocation_fraction.classification
        is ParameterSource.LITERATURE_INFORMED_PRIOR
    )
    assert (
        parameters.plant.monthly_npp_profile_classification is ParameterSource.SCENARIO_ASSUMPTION
    )


def test_configuration_loading_and_hash_are_deterministic() -> None:
    first = load_model_parameters(CONFIG_PATH)
    second = load_model_parameters(CONFIG_PATH)
    assert first == second
    assert first.canonical_json() == second.canonical_json()
    assert first.stable_hash() == second.stable_hash()
    assert first.stable_hash() == EXPECTED_DEFAULT_CONFIG_HASH
    assert json.loads(first.canonical_json())["model"]["version"] == "0.9.0"


def test_configuration_rejects_invalid_yaml(tmp_path: Path) -> None:
    invalid = tmp_path / "invalid.yaml"
    invalid.write_text("model: [", encoding="utf-8")
    with pytest.raises(ConfigLoadError, match="could not read configuration"):
        load_model_parameters(invalid)


def test_configuration_rejects_untyped_or_incomplete_data(tmp_path: Path) -> None:
    invalid = tmp_path / "invalid.yaml"
    invalid.write_text("model:\n  name: soil_simulator\n", encoding="utf-8")
    with pytest.raises(ConfigLoadError, match="invalid configuration"):
        load_model_parameters(invalid)


def test_configuration_rejects_non_finite_yaml_value(tmp_path: Path) -> None:
    raw = CONFIG_PATH.read_text(encoding="utf-8")
    invalid = tmp_path / "invalid.yaml"
    invalid.write_text(raw.replace("k_dpm_year: 10.0", "k_dpm_year: .inf"), encoding="utf-8")
    with pytest.raises(ConfigLoadError, match="invalid configuration"):
        load_model_parameters(invalid)


def test_configuration_rejects_partition_that_loses_carbon(tmp_path: Path) -> None:
    raw = CONFIG_PATH.read_text(encoding="utf-8")
    invalid = tmp_path / "invalid.yaml"
    invalid.write_text(
        raw.replace("retained_to_protected_fraction: 0.54", "retained_to_protected_fraction: 0.50"),
        encoding="utf-8",
    )
    with pytest.raises(ConfigLoadError, match="fractions must sum to 1"):
        load_model_parameters(invalid)


def test_configuration_rejects_manure_partition_that_creates_carbon(tmp_path: Path) -> None:
    raw = CONFIG_PATH.read_text(encoding="utf-8")
    invalid = tmp_path / "invalid.yaml"
    invalid.write_text(
        raw.replace("manure_protected_fraction: 0.02", "manure_protected_fraction: 0.03"),
        encoding="utf-8",
    )
    with pytest.raises(ConfigLoadError, match="manure carbon fractions must sum to 1"):
        load_model_parameters(invalid)


def test_configuration_rejects_amf_necromass_partition_that_creates_carbon(
    tmp_path: Path,
) -> None:
    raw = CONFIG_PATH.read_text(encoding="utf-8")
    invalid = tmp_path / "invalid.yaml"
    invalid.write_text(
        raw.replace("default: 0.3483606557377049", "default: 0.40"),
        encoding="utf-8",
    )
    with pytest.raises(ConfigLoadError, match="AMF necromass routing fractions must sum to 1"):
        load_model_parameters(invalid)


def test_configuration_rejects_invalid_monthly_profile(tmp_path: Path) -> None:
    raw = CONFIG_PATH.read_text(encoding="utf-8")
    invalid = tmp_path / "invalid.yaml"
    invalid.write_text(raw.replace("0.27, 0.25", "0.26, 0.25"), encoding="utf-8")
    with pytest.raises(ConfigLoadError, match="monthly_npp_profile must sum to 1"):
        load_model_parameters(invalid)


def test_configuration_rejects_monthly_profile_without_twelve_values(tmp_path: Path) -> None:
    raw = CONFIG_PATH.read_text(encoding="utf-8")
    invalid = tmp_path / "invalid.yaml"
    twelve_month_profile = (
        "monthly_npp_profile: [0.0, 0.0, 0.03, 0.10, 0.20, 0.27, 0.25, 0.12, 0.03, 0.0, 0.0, 0.0]"
    )
    eleven_month_profile = (
        "monthly_npp_profile: [0.0, 0.0, 0.03, 0.10, 0.20, 0.27, 0.25, 0.12, 0.03, 0.0, 0.13]"
    )
    invalid.write_text(
        raw.replace(twelve_month_profile, eleven_month_profile),
        encoding="utf-8",
    )
    with pytest.raises(ConfigLoadError, match="exactly 12 values"):
        load_model_parameters(invalid)


def test_configuration_accepts_zero_decay_boundary(tmp_path: Path) -> None:
    raw = CONFIG_PATH.read_text(encoding="utf-8")
    zero_decay = tmp_path / "zero-decay.yaml"
    zero_decay.write_text(raw.replace("k_dpm_year: 10.0", "k_dpm_year: 0.0"), encoding="utf-8")
    assert load_model_parameters(zero_decay).rothc.k_dpm_year == 0.0


def test_configuration_rejects_negative_decay_rate(tmp_path: Path) -> None:
    raw = CONFIG_PATH.read_text(encoding="utf-8")
    invalid = tmp_path / "negative-decay.yaml"
    invalid.write_text(raw.replace("k_dpm_year: 10.0", "k_dpm_year: -0.1"), encoding="utf-8")
    with pytest.raises(ConfigLoadError, match="invalid configuration"):
        load_model_parameters(invalid)


def test_configuration_rejects_non_monthly_timestep(tmp_path: Path) -> None:
    raw = CONFIG_PATH.read_text(encoding="utf-8")
    invalid = tmp_path / "two-month-step.yaml"
    invalid.write_text(raw.replace("timestep_months: 1", "timestep_months: 2"), encoding="utf-8")
    with pytest.raises(ConfigLoadError, match="invalid configuration"):
        load_model_parameters(invalid)


@pytest.mark.parametrize("safeguard", ["prohibit_negative_pools", "fail_on_non_finite"])
def test_configuration_cannot_disable_numerical_safeguards(tmp_path: Path, safeguard: str) -> None:
    raw = CONFIG_PATH.read_text(encoding="utf-8")
    invalid = tmp_path / f"disabled-{safeguard}.yaml"
    invalid.write_text(raw.replace(f"{safeguard}: true", f"{safeguard}: false"), encoding="utf-8")
    with pytest.raises(ConfigLoadError, match="invalid configuration"):
        load_model_parameters(invalid)
