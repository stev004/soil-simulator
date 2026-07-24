"""Phase 9.5 pre-publication scientific-remediation interfaces.

This package is downstream of the frozen v0.9.0 implementation.  It does not
change historical model equations or artifacts.  ``protected_soc`` remains a
model proxy and is not measured MAOC.
"""

from soil_simulator.phase95.accounting import (
    AccountingSchedule,
    AccountingTotals,
    load_accounting_schedule,
)
from soil_simulator.phase95.reporting import (
    DIAGNOSTIC_ONLY_TARGETS,
    HEADLINE_EFFECT_TARGETS,
    NON_ML_IDENTITY_TARGETS,
)

PHASE95_VERSION = "0.9.5"

__all__ = [
    "DIAGNOSTIC_ONLY_TARGETS",
    "HEADLINE_EFFECT_TARGETS",
    "NON_ML_IDENTITY_TARGETS",
    "PHASE95_VERSION",
    "AccountingSchedule",
    "AccountingTotals",
    "load_accounting_schedule",
]
