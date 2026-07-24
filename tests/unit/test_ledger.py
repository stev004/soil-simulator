"""Unit tests for immutable flow-ledger accounting and clear failures."""

from __future__ import annotations

from pathlib import Path

import pytest

from soil_simulator.domain.models import FluxRecord
from soil_simulator.io.configuration import load_model_parameters
from soil_simulator.simulator.errors import MassBalanceError
from soil_simulator.simulator.ledger import FluxLedger, verify_mass_balance

CONFIG_PATH = Path(__file__).parents[2] / "config" / "model_defaults.yaml"


def _record(month: int, amount: float) -> FluxRecord:
    return FluxRecord(
        month_index=month,
        source_pool="dpm_c",
        destination_pool="atmosphere",
        amount_t_c_ha=amount,
        uncertainty_t_c_ha=None,
        process="test respiration",
        parameter_version="test",
        provenance="unit test",
    )


def test_ledger_append_returns_new_ordered_ledger() -> None:
    empty = FluxLedger()
    first = empty.appended(_record(0, 0.1))
    second = first.appended(_record(1, 0.2))
    assert empty.records == ()
    assert len(first.records) == 1
    assert len(second.records) == 2
    with pytest.raises(ValueError, match="ordered"):
        second.appended(_record(0, 0.3))


def test_mass_balance_error_reports_residual_and_terms() -> None:
    with pytest.raises(MassBalanceError, match=r"month 3: carbon mass-balance residual.*inputs="):
        verify_mass_balance(
            month_index=3,
            initial_carbon_t_c_ha=1.0,
            final_carbon_t_c_ha=0.5,
            ledger=FluxLedger(),
            numerics=load_model_parameters(CONFIG_PATH).numerics,
        )
