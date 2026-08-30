"""
Complementary Cumulative Distribution Function (CCDF) of PAPR
=============================================================

Empirical CCDF from a collection of per-block PAPR values.
"""

from __future__ import annotations

from typing import Sequence

import numpy as np

from ofdm_linksim.core.types import (
    RealArray,
    CCDFResult,
    CCDF_REPORT_PROBABILITIES,
)


def compute_ccdf(
    papr_db_values: Sequence[float] | RealArray,
    *,
    thresholds_db: RealArray | None = None,
    n_points: int = 201,
) -> CCDFResult:
    """
    Compute empirical CCDF of PAPR.

        CCDF(γ) = Pr(PAPR_dB > γ)

    Parameters
    ----------
    papr_db_values :
        1-D array of PAPR values in dB (one value per OFDM block).
    thresholds_db :
        Optional grid of thresholds. If None, a linear grid covering
        the observed range is generated.
    n_points :
        Number of points when generating the automatic grid.

    Returns
    -------
    CCDFResult
    """
    values = np.asarray(papr_db_values, dtype=np.float64).ravel()

    if values.size == 0:
        raise ValueError("Cannot compute CCDF from empty PAPR list.")

    if not np.all(np.isfinite(values)):
        raise ValueError("papr_db_values contain non-finite numbers.")

    if thresholds_db is None:
        lo = float(np.min(values))
        hi = float(np.max(values))
        # small margin so the CCDF starts at 1.0 and ends near 0
        span = max(hi - lo, 1.0)
        thresholds = np.linspace(lo - 0.5, hi + 0.5 * span, n_points)
    else:
        thresholds = np.asarray(thresholds_db, dtype=np.float64).ravel()

    # empirical survival function
    # for each threshold γ: fraction of samples strictly greater than γ
    probs = np.array(
        [np.mean(values > γ) for γ in thresholds],
        dtype=np.float64,
    )

    return CCDFResult(
        thresholds_db=thresholds,
        probabilities=probs,
        n_blocks=int(values.size),
        method="empirical",
    )


def ccdf_at_probabilities(
    papr_db_values: Sequence[float] | RealArray,
    probabilities: Sequence[float] = CCDF_REPORT_PROBABILITIES,
) -> dict[float, float]:
    """
    Convenience helper: return the PAPR threshold (dB) that is exceeded
    with each given probability.

    Example
    -------
    >>> ccdf_at_probabilities(papr_list, (1e-2, 1e-3))
    {0.01: 9.87, 0.001: 11.23}
    """
    values = np.sort(np.asarray(papr_db_values, dtype=np.float64).ravel())[::-1]
    n = values.size
    if n == 0:
        raise ValueError("Empty PAPR list.")

    result = {}
    for p in probabilities:
        if not (0.0 < p <= 1.0):
            raise ValueError(f"Probability {p} out of (0, 1].")
        idx = min(int(np.ceil(p * n)) - 1, n - 1)
        result[float(p)] = float(values[idx])
    return result
