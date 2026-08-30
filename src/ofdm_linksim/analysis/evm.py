"""
Error Vector Magnitude (EVM) analysis
=====================================

Produces ``EVMResult`` from reference and received complex symbols.
"""

from __future__ import annotations

import numpy as np

from ofdm_linksim.core.types import (
    ComplexArray,
    EVMResult,
    validate_complex_signal,
)


def compute_evm(
    reference: ComplexArray,
    received: ComplexArray,
) -> EVMResult:
    """
    Compute RMS and Peak Error Vector Magnitude.

    Definition (linear scale):

        e[k] = received[k] - reference[k]
        rms_evm  = sqrt( mean( |e|^{2} ) / mean( |reference|^{2} ) )
        peak_evm = max( |e| ) / rms(reference)

    Parameters
    ----------
    reference :
        Ideal constellation symbols (after mapping, before channel).
    received :
        Equalized / demodulated symbols at the receiver.

    Returns
    -------
    EVMResult
    """
    validate_complex_signal(reference)
    validate_complex_signal(received)

    ref = np.asarray(reference, dtype=np.complex128).ravel()
    rx  = np.asarray(received,  dtype=np.complex128).ravel()

    if ref.size != rx.size:
        raise ValueError(
            f"reference and received length mismatch: "
            f"{ref.size} vs {rx.size}"
        )

    if ref.size == 0:
        raise ValueError("Cannot compute EVM on empty arrays.")

    error = rx - ref
    error_power = np.abs(error) ** 2
    ref_power   = np.abs(ref) ** 2

    mean_ref_power = float(np.mean(ref_power))
    if mean_ref_power <= 0.0:
        raise ValueError("Reference signal has zero average power.")

    rms_evm = float(np.sqrt(np.mean(error_power) / mean_ref_power))
    peak_evm = float(np.max(np.abs(error)) / np.sqrt(mean_ref_power))

    return EVMResult(
        rms_evm=rms_evm,
        rms_evm_percent=rms_evm * 100.0,
        peak_evm=peak_evm,
        peak_evm_percent=peak_evm * 100.0,
    )
