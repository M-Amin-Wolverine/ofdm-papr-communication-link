"""
Power Spectral Density (PSD) analysis
=====================================

Welch-method PSD estimate that produces ``PSDResult``.
"""

from __future__ import annotations

from typing import Optional

import numpy as np
from scipy import signal

from ofdm_linksim.core.types import (
    ComplexArray,
    RealArray,
    PSDResult,
    validate_complex_signal,
)


def compute_psd(
    waveform: ComplexArray,
    *,
    fs: float = 1.0,
    nperseg: int = 1024,
    noverlap: Optional[int] = None,
    window: str = "hann",
    scaling: str = "density",
) -> PSDResult:
    """
    Estimate one-sided power spectral density using Welch's method.

    Parameters
    ----------
    waveform :
        Complex baseband time-domain signal (can contain multiple
        OFDM symbols concatenated).
    fs :
        Sampling frequency (Hz). Used only for the frequency axis.
    nperseg, noverlap, window :
        Standard Welch parameters.
    scaling :
        'density' → V²/Hz   or   'spectrum' → V²

    Returns
    -------
    PSDResult
        frequencies in Hz, psd in dB (10·log10).
    """
    validate_complex_signal(waveform)

    x = np.asarray(waveform, dtype=np.complex128).ravel()

    if x.size < 8:
        raise ValueError("Waveform too short for reliable PSD estimation.")

    if noverlap is None:
        noverlap = nperseg // 2

    freqs, psd = signal.welch(
        x,
        fs=fs,
        window=window,
        nperseg=nperseg,
        noverlap=noverlap,
        return_onesided=True,
        scaling=scaling,
        average="mean",
    )

    # convert to dB (avoid log of zero)
    psd_db = 10.0 * np.log10(np.maximum(psd, 1e-20))

    return PSDResult(
        frequencies=freqs.astype(np.float64),
        psd_db=psd_db.astype(np.float64),
        method="welch",
        nperseg=nperseg,
        noverlap=noverlap,
        window=window,
    )
