"""Clear failures raised by the deterministic simulation kernel."""


class CarbonCoreError(RuntimeError):
    """Base class for deterministic carbon-core failures."""


class NumericalSafetyError(CarbonCoreError):
    """Raised when a carbon calculation becomes non-finite or negative."""


class MassBalanceError(CarbonCoreError):
    """Raised when a carbon-conservation residual exceeds configured tolerance."""
