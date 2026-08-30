"""
General-purpose validation helpers
==================================

Domain-specific validators live in ``core.types``.
This module contains only lightweight, reusable checks
that are useful across multiple packages.
"""

from __future__ import annotations

from typing import Any, Sequence

import numpy as np


def require_1d(array: np.ndarray, name: str = "array") -> None:
    """Raise if the array is not strictly 1-dimensional."""
    if np.asarray(array).ndim != 1:
        raise ValueError(f"{name} must be 1-D, got shape {np.asarray(array).shape}")


def require_same_length(
    a: Sequence[Any] | np.ndarray,
    b: Sequence[Any] | np.ndarray,
    name_a: str = "a",
    name_b: str = "b",
) -> None:
    """Raise if two sequences / arrays have different lengths."""
    la = len(a) if not hasattr(a, "size") else int(a.size)
    lb = len(b) if not hasattr(b, "size") else int(b.size)
    if la != lb:
        raise ValueError(
            f"{name_a} and {name_b} length mismatch: {la} vs {lb}"
        )


def require_finite(array: np.ndarray, name: str = "array") -> None:
    """Raise if any element is NaN or Inf."""
    arr = np.asarray(array)
    if not np.all(np.isfinite(arr)):
        raise ValueError(f"{name} contains non-finite values")


def require_power_of_two(n: int, name: str = "value") -> None:
    """Raise if n is not a positive power of two."""
    if not isinstance(n, (int, np.integer)) or n <= 0 or (n & (n - 1)) != 0:
        raise ValueError(f"{name} must be a positive power of two, got {n}")


def require_in_range(
    value: float,
    low: float,
    high: float,
    name: str = "value",
    *,
    inclusive: bool = True,
) -> None:
    """Raise if value is outside [low, high] (or (low, high))."""
    if inclusive:
        ok = low <= value <= high
        msg = f"[{low}, {high}]"
    else:
        ok = low < value < high
        msg = f"({low}, {high})"
    if not ok:
        raise ValueError(f"{name}={value} is outside the allowed range {msg}")
