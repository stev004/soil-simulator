"""Phase 8.5 synthetic intervention-outcome ML diagnostics.

This package is downstream of the Phase 6 simulator and Phase 7 population
generator.  It never changes mechanistic equations and does not select or
recommend interventions.
"""

from soil_simulator.ml.schema import DATASET_VERSION, FEATURE_SETS, TARGETS

__all__ = ["DATASET_VERSION", "FEATURE_SETS", "TARGETS"]
