"""
OFDM Demodulator
================

Inverse of the OFDM modulator:

    received time-domain waveform
        → cyclic-prefix removal
        → FFT (with oversampling support)
        → frequency-domain OFDMGrid
        → data-subcarrier extraction

Stage-1 contract
----------------
- Does **not** construct ``ReceiveFrame`` (that happens later in the pipeline).
- Returns an object implementing ``OFDMDemodResultLike``:
      received_waveform : OFDMSignal
      ofdm_grid         : OFDMGrid
      equalized_symbols : ComplexArray   # data carriers only

- When no explicit equalizer is present, ``equalized_symbols`` is simply
  the extracted data subcarriers (identity equalisation).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Sequence

import numpy as np

from ofdm_linksim.core.types import (
    ComplexArray,
    IntArray,
    OFDMGrid,
    OFDMSignal,
    FFTNormalization,
    DEFAULT_FFT_SIZE,
    DEFAULT_OVERSAMPLING,
    DEFAULT_CP_LENGTH,
    numpy_fft_norm,
    validate_complex_signal,
    validate_fft_size,
    validate_oversampling,
    validate_positive_integer,
)


# ---------------------------------------------------------------------------
# Result container (satisfies OFDMDemodResultLike Protocol)
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class OFDMDemodResult:
    """
    Concrete result of the OFDM demodulation stage.

    Matches the structural contract expected by the pipeline.
    """

    received_waveform: OFDMSignal
    ofdm_grid: OFDMGrid
    equalized_symbols: ComplexArray


# ---------------------------------------------------------------------------
# Low-level helpers
# ---------------------------------------------------------------------------

def remove_cyclic_prefix(
    samples: ComplexArray,
    *,
    n_symbols: int,
    fft_size: int,
    oversampling: int,
    cyclic_prefix_length: int,
) -> ComplexArray:
    """
    Strip the cyclic prefix and return useful samples.

    Shape out: (n_symbols, fft_size * oversampling)
    """
    validate_oversampling(oversampling)
    validate_fft_size(fft_size)
    validate_positive_integer(n_symbols, "n_symbols")

    if cyclic_prefix_length < 0:
        raise ValueError("cyclic_prefix_length cannot be negative.")

    L = oversampling
    useful_len = fft_size * L
    cp_os = cyclic_prefix_length * L
    total_len = useful_len + cp_os

    flat = np.asarray(samples, dtype=np.complex128).ravel()
    expected = n_symbols * total_len

    if flat.size != expected:
        raise ValueError(
            f"Waveform length mismatch: expected {expected} samples "
            f"({n_symbols} symbols × {total_len} samples/symbol), "
            f"got {flat.size}."
        )

    useful = np.empty((n_symbols, useful_len), dtype=np.complex128)
    for i in range(n_symbols):
        start = i * total_len + cp_os
        useful[i] = flat[start : start + useful_len]

    return useful


def ofdm_fft(
    useful: ComplexArray,
    *,
    fft_size: int,
    oversampling: int = DEFAULT_OVERSAMPLING,
    norm: FFTNormalization = FFTNormalization.UNITARY,
) -> ComplexArray:
    """
    FFT of the useful (non-CP) oversampled waveform.

    Returns the original-rate frequency grid of shape
    (n_symbols, fft_size) by discarding the oversampling bins.
    """
    validate_fft_size(fft_size)
    validate_oversampling(oversampling)

    useful = np.asarray(useful, dtype=np.complex128)
    if useful.ndim == 1:
        useful = useful[np.newaxis, :]

    n_os = fft_size * oversampling
    if useful.shape[-1] != n_os:
        raise ValueError(
            f"Expected useful length {n_os}, got {useful.shape[-1]}."
        )

    freq_os = np.fft.fft(useful, axis=-1, norm=numpy_fft_norm(norm))

    # Extract the original-rate bins (inverse of the zero-padding done
    # in the modulator).
    half = fft_size // 2
    grid = np.zeros((useful.shape[0], fft_size), dtype=np.complex128)

    # DC + positive frequencies
    grid[:, : half + 1] = freq_os[:, : half + 1]
    # negative frequencies
    if half > 0:
        grid[:, -half:] = freq_os[:, -half:]

    return grid


def rebuild_grid(
    freq_symbols: ComplexArray,
    *,
    data_indices: IntArray,
    pilot_indices: Optional[IntArray] = None,
) -> OFDMGrid:
    """
    Rebuild an ``OFDMGrid`` from the recovered frequency-domain symbols
    using the same index sets that were used at the transmitter.
    """
    freq_symbols = np.asarray(freq_symbols, dtype=np.complex128)
    if freq_symbols.ndim == 1:
        freq_symbols = freq_symbols[np.newaxis, :]

    data_indices = np.asarray(data_indices, dtype=np.int64)
    if pilot_indices is None:
        pilot_indices = np.array([], dtype=np.int64)
    else:
        pilot_indices = np.asarray(pilot_indices, dtype=np.int64)

    active = np.sort(np.concatenate([data_indices, pilot_indices]))

    return OFDMGrid(
        symbols=freq_symbols,
        active_indices=active,
        pilot_indices=pilot_indices,
        data_indices=data_indices,
    )


# ---------------------------------------------------------------------------
# Public high-level API
# ---------------------------------------------------------------------------

def demodulate_ofdm(
    received: OFDMSignal | ComplexArray,
    *,
    data_indices: Sequence[int] | IntArray,
    pilot_indices: Optional[Sequence[int] | IntArray] = None,
    fft_size: Optional[int] = None,
    oversampling: Optional[int] = None,
    cyclic_prefix_length: Optional[int] = None,
    n_symbols: Optional[int] = None,
    fft_norm: FFTNormalization = FFTNormalization.UNITARY,
    **kwargs,
) -> OFDMDemodResult:
    """
    Complete OFDM demodulation stage.

    Parameters
    ----------
    received :
        Either a full ``OFDMSignal`` (preferred) or a raw complex
        waveform.  When a raw array is supplied the explicit OFDM
        parameters must also be provided.
    data_indices, pilot_indices :
        Subcarrier index sets used at the transmitter (must match).
    fft_size, oversampling, cyclic_prefix_length, n_symbols :
        Taken from the ``OFDMSignal`` when available; otherwise required.
    fft_norm :
        Must match the normalisation used by the modulator.

    Returns
    -------
    OFDMDemodResult
        Satisfies ``OFDMDemodResultLike``.
    """
    # ------------------------------------------------------------------
    # Normalise input to OFDMSignal
    # ------------------------------------------------------------------
    if isinstance(received, OFDMSignal):
        waveform = received
        fft_size = waveform.fft_size
        oversampling = waveform.oversampling
        cyclic_prefix_length = waveform.cyclic_prefix_length
        n_symbols = waveform.n_symbols
        samples = waveform.samples
        cp_included = waveform.cp_included
    else:
        validate_complex_signal(received)
        if any(v is None for v in (fft_size, oversampling, cyclic_prefix_length, n_symbols)):
            raise ValueError(
                "When passing a raw waveform you must supply "
                "fft_size, oversampling, cyclic_prefix_length and n_symbols."
            )
        fft_size = int(fft_size)
        oversampling = int(oversampling)
        cyclic_prefix_length = int(cyclic_prefix_length)
        n_symbols = int(n_symbols)

        samples = np.asarray(received, dtype=np.complex128)
        cp_included = True  # assume CP is present for raw input

        waveform = OFDMSignal(
            samples=samples,
            fft_size=fft_size,
            oversampling=oversampling,
            cyclic_prefix_length=cyclic_prefix_length,
            cp_included=cp_included,
            n_symbols=n_symbols,
        )

    data_indices = np.asarray(data_indices, dtype=np.int64)
    if pilot_indices is None:
        pilot_indices = np.array([], dtype=np.int64)
    else:
        pilot_indices = np.asarray(pilot_indices, dtype=np.int64)

    # ------------------------------------------------------------------
    # CP removal
    # ------------------------------------------------------------------
    if cp_included and cyclic_prefix_length > 0:
        useful = remove_cyclic_prefix(
            samples,
            n_symbols=n_symbols,
            fft_size=fft_size,
            oversampling=oversampling,
            cyclic_prefix_length=cyclic_prefix_length,
        )
    else:
        # already useful samples
        useful = np.asarray(samples, dtype=np.complex128)
        if useful.ndim == 1:
            useful_len = fft_size * oversampling
            if useful.size != n_symbols * useful_len:
                raise ValueError("Raw useful waveform has unexpected length.")
            useful = useful.reshape(n_symbols, useful_len)

    # ------------------------------------------------------------------
    # FFT → frequency grid
    # ------------------------------------------------------------------
    freq = ofdm_fft(
        useful,
        fft_size=fft_size,
        oversampling=oversampling,
        norm=fft_norm,
    )

    # ------------------------------------------------------------------
    # Rebuild OFDMGrid
    # ------------------------------------------------------------------
    grid = rebuild_grid(
        freq,
        data_indices=data_indices,
        pilot_indices=pilot_indices,
    )

    # ------------------------------------------------------------------
    # Data-subcarrier extraction (= identity equalisation for Stage-1)
    # ------------------------------------------------------------------
    equalized = grid.get_data_symbols().ravel()

    return OFDMDemodResult(
        received_waveform=waveform,
        ofdm_grid=grid,
        equalized_symbols=equalized,
    )


# Alias expected by the pipeline component injection
ofdm_demodulator = demodulate_ofdm
