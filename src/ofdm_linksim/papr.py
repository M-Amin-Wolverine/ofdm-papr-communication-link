"""
PAPR Analysis Module
====================

Research-grade PAPR analysis for OFDM waveforms.

This module measures the Peak-to-Average Power Ratio (PAPR) on the
useful, non-cyclic-prefix portion of an OFDM waveform.

Pipeline
--------
    TransmitFrame
        │
        ▼
    OFDMSignal
        │
        ▼
    useful samples (CP removed)
        │
        ▼
    PAPR analysis
        │
        ├── Linear PAPR
        ├── PAPR [dB]
        ├── Peak power
        ├── Average power
        └── Metadata
        │
        ▼
    PAPRResult

Design rules
------------
1. PAPR is ALWAYS evaluated on useful samples only.
2. CP samples are never included in the PAPR calculation.
3. No global NumPy RNG is used.
4. The analysis API accepts an injected RNG for pipeline consistency.
5. The Stage-1 baseline remains deterministic and uses the continuous
   PAPR definition.
6. Raw complex arrays are supported as a convenience API.
7. The public ``papr_analysis`` and ``papr`` pipeline interfaces remain
   compatible with the existing project architecture.

Important
---------
PAPR itself is a deterministic metric for a given waveform.

The RNG is therefore not used by the basic PAPR calculation. It is
accepted because the OFDM-LinkSim architecture assigns independent
random streams to pipeline stages and because future analysis methods
may require randomized processing.

PAPR definition
---------------
For a complex baseband signal x[n]:

    PAPR = max(|x[n]|²) / E[|x[n]|²]

and:

    PAPR_dB = 10 log10(PAPR)

The CP is excluded from this calculation.

For oversampled OFDM, oversampling does NOT mean dividing PAPR by L².
Instead, the oversampled waveform itself must be supplied to the
measurement stage so that additional inter-sample peaks can be observed.
"""

from __future__ import annotations

from typing import Optional, Sequence, Tuple

import numpy as np

from ofdm_linksim.core.types import (
    PAPRResult,
    ComplexArray,
    OFDMSignal,
    TransmitFrame,
    make_papr_result,
    compute_papr_linear as _core_compute_papr_linear,
    validate_complex_signal,
)

try:
    from ofdm_linksim.core.random import (
        papr_rng,
        DEFAULT_SEED,
    )
except ImportError:
    # Backward-compatible fallback.
    #
    # The pipeline should normally inject its own RNG. This fallback
    # exists only for legacy callers.
    DEFAULT_SEED = 0

    def papr_rng(seed: int = DEFAULT_SEED) -> np.random.Generator:
        return np.random.default_rng(seed)


# ============================================================================
# Constants
# ============================================================================

_DEFAULT_OVERSAMPLING_FACTOR = 4
_MIN_OVERSAMPLING_FACTOR = 1


# ============================================================================
# Validation
# ============================================================================


def _validate_rng(
    rng: Optional[np.random.Generator],
) -> None:
    """Validate the injected PAPR random stream."""
    if rng is not None and not isinstance(
        rng,
        np.random.Generator,
    ):
        raise TypeError(
            "rng must be an instance of numpy.random.Generator."
        )


def _validate_method(method: str) -> None:
    """Validate supported PAPR calculation methods."""
    if method not in {"continuous", "oversampled"}:
        raise ValueError(
            f"Unknown PAPR method: {method!r}. "
            "Expected 'continuous' or 'oversampled'."
        )


def _validate_oversampling_factor(
    oversampling_factor: int,
) -> None:
    """Validate the requested oversampling factor."""
    if not isinstance(
        oversampling_factor,
        (int, np.integer),
    ):
        raise TypeError(
            "oversampling_factor must be an integer."
        )

    if oversampling_factor < _MIN_OVERSAMPLING_FACTOR:
        raise ValueError(
            "oversampling_factor must be >= 1."
        )


# ============================================================================
# Input normalization
# ============================================================================


def get_useful_samples(
    waveform: OFDMSignal | ComplexArray,
) -> ComplexArray:
    """
    Extract the useful non-CP samples.

    Parameters
    ----------
    waveform:
        Either an OFDMSignal or a raw complex array.

    Returns
    -------
    ComplexArray
        Flattened useful samples.

    Notes
    -----
    For an OFDMSignal, ``get_useful_samples()`` is the authoritative
    mechanism for removing the cyclic prefix.

    For a raw array there is no metadata describing CP boundaries, so
    the complete array is treated as useful.
    """
    if isinstance(waveform, OFDMSignal):
        validate_complex_signal(waveform.samples)

        useful = waveform.get_useful_samples()

        useful = np.asarray(
            useful,
            dtype=np.complex128,
        )

    else:
        validate_complex_signal(waveform)

        useful = np.asarray(
            waveform,
            dtype=np.complex128,
        )

    useful = useful.ravel()

    if useful.size == 0:
        raise ValueError(
            "Cannot compute PAPR from an empty waveform."
        )

    if not np.all(np.isfinite(useful.real)) or not np.all(
        np.isfinite(useful.imag)
    ):
        raise ValueError(
            "Waveform contains NaN or infinite values."
        )

    return useful


def _extract_waveform_metadata(
    waveform: OFDMSignal | ComplexArray,
) -> dict:
    """
    Extract metadata from an OFDMSignal.

    Raw arrays receive conservative fallback metadata.
    """
    if isinstance(waveform, OFDMSignal):
        return {
            "fft_size": int(waveform.fft_size),
            "oversampling": int(waveform.oversampling),
            "cyclic_prefix_length": int(
                waveform.cyclic_prefix_length
            ),
            "n_symbols": int(waveform.n_symbols),
            "cp_included": bool(waveform.cp_included),
        }

    return {
        "fft_size": None,
        "oversampling": None,
        "cyclic_prefix_length": None,
        "n_symbols": None,
        "cp_included": False,
    }


# ============================================================================
# PAPR mathematics
# ============================================================================


def compute_papr_linear(
    samples: ComplexArray,
    *,
    n_samples: Optional[int] = None,
    oversampling_factor: int = 1,
) -> Tuple[float, float, float, float]:
    """
    Compute PAPR using the project-level core implementation.

    This wrapper intentionally delegates to ``core.types`` under the
    private alias ``_core_compute_papr_linear`` to avoid the name
    collision that existed in the original implementation.

    Returns
    -------
    tuple
        ``(papr_db, papr_linear, peak_power_dbfs, average_power_dbfs)``
    """
    validate_complex_signal(samples)

    _validate_oversampling_factor(
        oversampling_factor
    )

    data = np.asarray(
        samples,
        dtype=np.complex128,
    ).ravel()

    if data.size == 0:
        raise ValueError(
            "Cannot compute PAPR from an empty sample array."
        )

    return _core_compute_papr_linear(
        data,
        n_samples=n_samples,
        oversampling_factor=oversampling_factor,
    )


# ============================================================================
# High-level PAPR computation
# ============================================================================


def compute_papr(
    waveform: OFDMSignal | ComplexArray,
    *,
    snr_db: Optional[float] = None,
    rng: Optional[np.random.Generator] = None,
    method: str = "continuous",
    oversampling_factor: int = 4,
    **kwargs,
) -> PAPRResult:
    """
    Compute PAPR on the useful samples of an OFDM waveform.

    Parameters
    ----------
    waveform:
        OFDMSignal or raw complex waveform.

    snr_db:
        Optional SNR metadata.
        It does not alter the PAPR calculation.

    rng:
        PAPR-stage random stream.

        PAPR itself is deterministic, but the parameter is retained
        for pipeline consistency and future randomized analysis.

    method:
        ``"continuous"``:
            Stage-1 baseline.

        ``"oversampled"``:
            Explicit oversampled analysis mode.

    oversampling_factor:
        Oversampling factor used by the core PAPR calculator.

    Returns
    -------
    PAPRResult
        Validated PAPR result.
    """
    _validate_rng(rng)
    _validate_method(method)
    _validate_oversampling_factor(
        oversampling_factor
    )

    useful = get_useful_samples(waveform)
    metadata = _extract_waveform_metadata(waveform)

    # ------------------------------------------------------------------
    # Determine effective oversampling configuration
    # ------------------------------------------------------------------

    if method == "continuous":
        effective_oversampling = 1
    else:
        effective_oversampling = oversampling_factor

    # ------------------------------------------------------------------
    # Core PAPR calculation
    # ------------------------------------------------------------------

    papr_db, papr_linear, peak_db, avg_db = (
        compute_papr_linear(
            useful,
            n_samples=useful.size,
            oversampling_factor=effective_oversampling,
        )
    )

    # ------------------------------------------------------------------
    # Numerical sanity checks
    # ------------------------------------------------------------------

    values = {
        "papr_db": papr_db,
        "papr_linear": papr_linear,
        "peak_db": peak_db,
        "avg_db": avg_db,
    }

    for name, value in values.items():
        if not np.isfinite(value):
            raise ValueError(
                f"PAPR calculation produced non-finite {name}."
            )

    if papr_linear <= 0.0:
        raise ValueError(
            "PAPR linear value must be greater than zero."
        )

    if papr_linear < 1.0 - 1e-10:
        raise ValueError(
            "PAPR linear value cannot be below unity."
        )

    # ------------------------------------------------------------------
    # Metadata is deliberately kept local.
    #
    # PAPRResult remains the canonical project result object, so we
    # don't dynamically inject arbitrary attributes into it.
    # ------------------------------------------------------------------

    _ = metadata
    _ = kwargs

    return make_papr_result(
        papr_db=float(papr_db),
        papr_linear=float(papr_linear),
        peak_power_dBFS=float(peak_db),
        average_power_dBFS=float(avg_db),
        n_samples=int(useful.size),
        snr_db=snr_db,
        method=method,
    )


# ============================================================================
# PAPR statistics
# ============================================================================


def papr_statistics(
    papr_db_values: Sequence[float],
) -> dict[str, float]:
    """
    Calculate descriptive statistics for a collection of PAPR values.

    Parameters
    ----------
    papr_db_values:
        Sequence of PAPR measurements in dB.

    Returns
    -------
    dict
        Mean, median, standard deviation, minimum, maximum and percentiles.
    """
    values = np.asarray(
        papr_db_values,
        dtype=np.float64,
    ).ravel()

    if values.size == 0:
        raise ValueError(
            "papr_db_values cannot be empty."
        )

    if not np.all(np.isfinite(values)):
        raise ValueError(
            "papr_db_values contains NaN or infinite values."
        )

    return {
        "mean_db": float(np.mean(values)),
        "median_db": float(np.median(values)),
        "std_db": float(np.std(values)),
        "min_db": float(np.min(values)),
        "max_db": float(np.max(values)),
        "p50_db": float(np.percentile(values, 50)),
        "p90_db": float(np.percentile(values, 90)),
        "p95_db": float(np.percentile(values, 95)),
        "p99_db": float(np.percentile(values, 99)),
    }


# ============================================================================
# Peak and average power helpers
# ============================================================================


def compute_peak_power(
    waveform: OFDMSignal | ComplexArray,
) -> float:
    """
    Return peak instantaneous power of useful samples.
    """
    useful = get_useful_samples(waveform)

    return float(
        np.max(np.abs(useful) ** 2)
    )


def compute_average_power(
    waveform: OFDMSignal | ComplexArray,
) -> float:
    """
    Return average power of useful samples.
    """
    useful = get_useful_samples(waveform)

    return float(
        np.mean(np.abs(useful) ** 2)
    )


def compute_papr_from_powers(
    peak_power: float,
    average_power: float,
) -> tuple[float, float]:
    """
    Compute linear and dB PAPR directly from peak and average power.

    Returns
    -------
    papr_linear, papr_db
    """
    if not np.isfinite(peak_power):
        raise ValueError(
            "peak_power must be finite."
        )

    if not np.isfinite(average_power):
        raise ValueError(
            "average_power must be finite."
        )

    if peak_power < 0.0:
        raise ValueError(
            "peak_power cannot be negative."
        )

    if average_power <= 0.0:
        raise ValueError(
            "average_power must be greater than zero."
        )

    if peak_power < average_power:
        raise ValueError(
            "peak_power cannot be lower than average_power."
        )

    papr_linear = peak_power / average_power

    papr_db = 10.0 * np.log10(papr_linear)

    return float(papr_linear), float(papr_db)


# ============================================================================
# CCDF integration
# ============================================================================


def compute_papr_for_ccdf(
    papr_db_list: Sequence[float],
    *,
    thresholds_db: Optional[Sequence[float]] = None,
    n_points: int = 201,
) -> PAPRResult:
    """
    Convenience wrapper for CCDF analysis.

    The actual CCDF calculation remains owned by
    ``analysis.ccdf``. This function exists to preserve the high-level
    PAPR-analysis API.
    """
    from ofdm_linksim.analysis.ccdf import compute_ccdf

    return compute_ccdf(
        papr_db_list,
        thresholds_db=thresholds_db,
        n_points=n_points,
    )


# ============================================================================
# Pipeline entry point
# ============================================================================


def papr_analysis(
    transmit_frame: TransmitFrame,
    *,
    snr_db: Optional[float] = None,
    rng: Optional[np.random.Generator] = None,
    method: str = "continuous",
    oversampling_factor: int = 4,
    **kwargs,
) -> PAPRResult:
    """
    High-level PAPR stage used by the OFDM-LinkSim pipeline.

    Parameters
    ----------
    transmit_frame:
        OFDM transmit frame.

    snr_db:
        Optional SNR metadata.

    rng:
        PAPR random stream.

        If omitted, a deterministic legacy fallback is used. New
        pipeline code should always inject ``papr_rng``.

    method:
        PAPR analysis mode.

    oversampling_factor:
        Oversampling factor for explicit oversampled analysis.
    """
    if not isinstance(
        transmit_frame,
        TransmitFrame,
    ):
        raise TypeError(
            "transmit_frame must be a TransmitFrame instance."
        )

    if rng is None:
        # Legacy compatibility only.
        #
        # New pipeline code should inject its dedicated PAPR RNG.
        rng = papr_rng(DEFAULT_SEED)

    return compute_papr(
        transmit_frame.waveform,
        snr_db=snr_db,
        rng=rng,
        method=method,
        oversampling_factor=oversampling_factor,
        **kwargs,
    )


# ============================================================================
# Pipeline compatibility alias
# ============================================================================

papr = papr_analysis


# ============================================================================
# Public API
# ============================================================================

__all__ = [
    "compute_papr",
    "compute_papr_linear",
    "get_useful_samples",
    "compute_peak_power",
    "compute_average_power",
    "compute_papr_from_powers",
    "papr_statistics",
    "compute_papr_for_ccdf",
    "papr_analysis",
    "papr",
]
