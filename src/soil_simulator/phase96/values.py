"""Strict scalar conversion helpers for heterogeneous artifact rows."""

from __future__ import annotations

import math


def as_float(value: object) -> float:
    """Convert an artifact scalar to a finite float or fail explicitly."""
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        raise TypeError(f"expected a numeric artifact scalar, got {type(value).__name__}")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError("artifact scalar must be finite")
    return result


def as_int(value: object) -> int:
    """Convert an integer artifact scalar without silently truncating floats."""
    if isinstance(value, bool) or not isinstance(value, (int, str)):
        raise TypeError(f"expected an integer artifact scalar, got {type(value).__name__}")
    return int(value)
