"""Offline Phase 9 synthetic intervention-selection benchmark.

This package is downstream of the mechanistic simulator and frozen Phase 8.6
observable models.  It must never be imported by the simulation kernel.
"""

from soil_simulator.selection.schema import PHASE9_VERSION

__all__ = ["PHASE9_VERSION"]
