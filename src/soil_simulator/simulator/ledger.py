"""Append-only carbon-flow ledger and mass-balance verification.

The ledger uses explicit named system boundaries: ``external_inputs`` for
carbon entering the soil core and ``atmosphere`` for respiration losses. All
amounts use ``t C ha-1``.
"""

from __future__ import annotations

import math
from collections.abc import Iterable
from dataclasses import dataclass
from itertools import pairwise

from soil_simulator.domain.carbon import MassBalanceDiagnostic
from soil_simulator.domain.enums import CarbonBoundary
from soil_simulator.domain.models import FluxRecord, NumericalParameters
from soil_simulator.simulator.errors import MassBalanceError


@dataclass(frozen=True, slots=True, init=False)
class FluxLedger:
    """Immutable view of carbon records assembled only by appending records."""

    _records: tuple[FluxRecord, ...]

    def __init__(self, records: Iterable[FluxRecord] = ()) -> None:
        collected = tuple(records)
        if any(later.month_index < earlier.month_index for earlier, later in pairwise(collected)):
            raise ValueError("flux records must be ordered by non-decreasing month_index")
        object.__setattr__(self, "_records", collected)

    @property
    def records(self) -> tuple[FluxRecord, ...]:
        """Return records as an immutable tuple."""
        return self._records

    def appended(self, record: FluxRecord) -> FluxLedger:
        """Return a new ledger with one record appended; existing records never change."""
        return FluxLedger((*self._records, record))

    def extended(self, records: Iterable[FluxRecord]) -> FluxLedger:
        """Return a new ledger with records appended in chronological order."""
        return FluxLedger((*self._records, *records))

    def total_from(self, source: str) -> float:
        """Sum carbon leaving a named source [t C ha-1]."""
        return math.fsum(
            record.amount_t_c_ha for record in self._records if record.source_pool == source
        )

    def total_to(self, destination: str) -> float:
        """Sum carbon entering a named destination [t C ha-1]."""
        return math.fsum(
            record.amount_t_c_ha
            for record in self._records
            if record.destination_pool == destination
        )


def verify_mass_balance(
    *,
    month_index: int,
    initial_carbon_t_c_ha: float,
    final_carbon_t_c_ha: float,
    ledger: FluxLedger,
    numerics: NumericalParameters,
) -> MassBalanceDiagnostic:
    """Verify one ledger against carbon conservation and raise on failure.

    The verified equation is ``initial + external inputs - respiration = final``.
    Internal transfers cancel because every record has an explicit source and
    destination. The residual is equivalently ``left side - right side`` when
    respiration is moved to the right side.
    """
    external_inputs = ledger.total_from(CarbonBoundary.EXTERNAL_INPUTS)
    respiration = ledger.total_to(CarbonBoundary.ATMOSPHERE)
    left_side = initial_carbon_t_c_ha + external_inputs
    right_side = final_carbon_t_c_ha + respiration
    values = (initial_carbon_t_c_ha, final_carbon_t_c_ha, left_side, right_side)
    if any(not math.isfinite(value) or value < 0.0 for value in values):
        raise MassBalanceError(
            f"month {month_index}: mass-balance inputs must be finite and non-negative"
        )

    residual = left_side - right_side
    scale = max(abs(left_side), abs(right_side))
    relative_residual = abs(residual) / scale if scale > 0.0 else 0.0
    tolerance = max(
        numerics.absolute_mass_balance_tolerance,
        numerics.relative_mass_balance_tolerance * scale,
    )
    within_tolerance = abs(residual) <= tolerance
    diagnostic = MassBalanceDiagnostic(
        month_index=month_index,
        initial_carbon_t_c_ha=initial_carbon_t_c_ha,
        external_inputs_t_c_ha=external_inputs,
        respiration_losses_t_c_ha=respiration,
        final_carbon_t_c_ha=final_carbon_t_c_ha,
        residual_t_c_ha=residual,
        relative_residual=relative_residual,
        tolerance_t_c_ha=tolerance,
        within_tolerance=within_tolerance,
    )
    if not within_tolerance:
        raise MassBalanceError(
            f"month {month_index}: carbon mass-balance residual {residual:.17g} t C ha-1 "
            f"exceeds tolerance {tolerance:.17g} t C ha-1 "
            f"(initial={initial_carbon_t_c_ha:.17g}, inputs={external_inputs:.17g}, "
            f"respiration={respiration:.17g}, final={final_carbon_t_c_ha:.17g})"
        )
    return diagnostic
