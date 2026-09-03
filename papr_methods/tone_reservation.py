"""
PAPR Method: Tone Reservation (TR)
==================================

Iterative Tone Reservation for OFDM PAPR reduction.

Algorithm (classic gradient / clipping-based TR)
------------------------------------------------
1. Reserve a set of subcarriers (tones) that carry no data.
2. In the time domain, identify samples that exceed a target threshold.
3. Generate a cancellation signal whose frequency support lies only
   on the reserved tones (least-squares / filtered clip residual).
4. Add a scaled version of the cancellation signal to the waveform.
5. Repeat for a fixed number of iterations.

The data-bearing subcarriers are never modified → zero BER impact
from the PAPR reduction itself (only power / spectral efficiency cost).

Reserved tones
--------------
If ``reserved_indices`` is not supplied, the highest-frequency data
tones (or a symmetric pair near the band edges) are reserved.

PAPR is measured on useful samples only.
"""

from __future__ import annotations

from typing import Any, Optional, Sequence

import numpy as np

from ofdm_linksim.core.types import (
    ComplexArray,
    FFTNormalization,
    OFDMGrid,
    OFDMSignal,
    PAPRMethod,
    PAPRResult,
    TransmitFrame,
    make_papr_result,
    numpy_fft_norm,
    safe_mean_power,
    validate_positive_integer,
)
from ofdm_linksim.ofdm_modulator import ofdm_ifft, add_cyclic_prefix
from ofdm_linksim.papr import get_useful_samples
from papr_methods.none import PAPRProcessResult


METHOD = PAPRMethod.TONE_RESERVATION
METHOD_NAME = METHOD.value
IMPLEMENTED = True
STAGE = "Phase-2"


def _default_reserved(
    data_indices: np.ndarray,
    n_reserved: int,
) -> np.ndarray:
    """Pick n_reserved tones from the ends of the data set (band edges)."""
    if n_reserved <= 0:
        return np.array([], dtype=np.int64)
    if n_reserved >= len(data_indices):
        raise ValueError("n_reserved must be smaller than number of data tones.")
    # take from both ends
    half = n_reserved // 2
    left = data_indices[: n_reserved - half]
    right = data_indices[-(half):] if half else np.array([], dtype=np.int64)
    return np.unique(np.concatenate([left, right]))


def _ifft_reserved(
    C_freq: ComplexArray,
    fft_size: int,
    oversampling: int,
    fft_norm: FFTNormalization,
) -> ComplexArray:
    """IFFT of a frequency vector that is non-zero only on reserved tones."""
    if C_freq.ndim == 1:
        C_freq = C_freq[np.newaxis, :]
    grid = OFDMGrid(
        symbols=C_freq,
        active_indices=np.where(np.any(np.abs(C_freq) > 0, axis=0))[0],
        pilot_indices=np.array([], dtype=np.int64),
        data_indices=np.where(np.any(np.abs(C_freq) > 0, axis=0))[0],
    )
    # active may be empty on first call – handle
    if grid.active_indices.size == 0:
        n_sym = C_freq.shape[0]
        return np.zeros((n_sym, fft_size * oversampling), dtype=np.complex128)
    # Rebuild with valid indices
    active = np.where(np.any(np.abs(C_freq) > 0, axis=0))[0].astype(np.int64)
    if active.size == 0:
        return np.zeros((C_freq.shape[0], fft_size * oversampling), dtype=np.complex128)
    grid = OFDMGrid(
        symbols=C_freq,
        active_indices=active,
        pilot_indices=np.array([], dtype=np.int64),
        data_indices=active,
    )
    return ofdm_ifft(grid, oversampling=oversampling, norm=fft_norm)


def apply_tone_reservation(
    waveform: TransmitFrame | OFDMSignal | ComplexArray,
    *,
    n_reserved: int = 8,
    reserved_indices: Optional[Sequence[int]] = None,
    clipping_ratio: float = 1.5,
    n_iterations: int = 10,
    step_size: float = 1.0,
    rng: Optional[np.random.Generator] = None,
    fft_norm: FFTNormalization = FFTNormalization.UNITARY,
    **kwargs: Any,
) -> PAPRProcessResult:
    """
    Apply iterative Tone Reservation.

    Parameters
    ----------
    n_reserved :
        Number of reserved tones (used only when reserved_indices is None).
    reserved_indices :
        Explicit FFT-bin indices to reserve. Must be subset of data tones
        or unused bins; they will be zeroed for data and used for cancellation.
    clipping_ratio :
        Target peak threshold = CR · rms.
    n_iterations :
        Number of TR iterations.
    step_size :
        Scale applied to the cancellation signal each iteration (μ).
    """
    validate_positive_integer(n_iterations, "n_iterations")
    if clipping_ratio <= 0.0:
        raise ValueError("clipping_ratio must be positive.")
    if step_size <= 0.0:
        raise ValueError("step_size must be positive.")

    if not isinstance(waveform, TransmitFrame):
        raise TypeError(
            "Tone Reservation requires a TransmitFrame (frequency-domain grid)."
        )

    frame: TransmitFrame = waveform
    ofdm_signal = frame.waveform
    grid = frame.ofdm_grid
    X = np.asarray(grid.symbols, dtype=np.complex128).copy()
    if X.ndim == 1:
        X = X[np.newaxis, :]

    data_idx = np.asarray(grid.data_indices, dtype=np.int64)
    pilot_idx = np.asarray(grid.pilot_indices, dtype=np.int64)
    active_idx = np.asarray(grid.active_indices, dtype=np.int64)
    fft_size = grid.fft_size
    L = ofdm_signal.oversampling
    n_sym = X.shape[0]

    if reserved_indices is not None:
        reserved = np.asarray(reserved_indices, dtype=np.int64)
    else:
        reserved = _default_reserved(data_idx, n_reserved)

    if reserved.size == 0:
        raise ValueError("At least one reserved tone is required.")

    # Data tones that remain for information
    data_kept = np.setdiff1d(data_idx, reserved)
    if data_kept.size == 0:
        raise ValueError("Tone reservation would remove all data tones.")

    # Zero reserved tones in the data grid (they will carry cancellation only)
    X[:, reserved] = 0.0

    # Initial time-domain
    useful = ofdm_ifft(
        OFDMGrid(
            symbols=X,
            active_indices=np.union1d(data_kept, pilot_idx),
            pilot_indices=pilot_idx,
            data_indices=data_kept,
        ),
        oversampling=L,
        norm=fft_norm,
    )

    p_avg = safe_mean_power(useful.ravel())
    if p_avg <= 0.0:
        raise ValueError("Average power is zero.")
    rms = float(np.sqrt(p_avg))
    threshold = float(clipping_ratio * rms)

    # Kernel: impulse response of reserved-tone subspace (for filtering residual)
    # Use a single-symbol prototype
    e = np.zeros((1, fft_size), dtype=np.complex128)
    e[0, reserved] = 1.0
    # For projection we work in frequency domain directly

    for _ in range(n_iterations):
        mag = np.abs(useful)
        # Clip residual: peaks above threshold
        peak_mask = mag > threshold
        if not np.any(peak_mask):
            break
        residual = np.zeros_like(useful)
        residual[peak_mask] = useful[peak_mask] * (
            1.0 - threshold / mag[peak_mask]
        )

        # Project residual onto reserved tones via FFT
        # residual is oversampled → take every L-th sample approx via FFT of size n_os
        n_os = fft_size * L
        R = np.fft.fft(residual, axis=-1, norm=numpy_fft_norm(fft_norm))
        # Map oversampled bins back to original FFT bins (DC + pos + neg)
        C = np.zeros((n_sym, fft_size), dtype=np.complex128)
        half = fft_size // 2
        # positive incl DC
        C[:, : half + 1] = R[:, : half + 1]
        if half > 0:
            C[:, -half:] = R[:, -half:]
        # Keep only reserved tones
        mask = np.ones(fft_size, dtype=bool)
        mask[reserved] = False
        C[:, mask] = 0.0

        # IFFT cancellation signal
        c_time = ofdm_ifft(
            OFDMGrid(
                symbols=C,
                active_indices=reserved,
                pilot_indices=np.array([], dtype=np.int64),
                data_indices=reserved,
            ),
            oversampling=L,
            norm=fft_norm,
        )
        useful = useful - step_size * c_time
        # Also accumulate cancellation into frequency domain for final waveform
        X[:, reserved] = X[:, reserved] - step_size * C[:, reserved]

    # Final full waveform
    if ofdm_signal.cp_included and ofdm_signal.cyclic_prefix_length > 0:
        full = add_cyclic_prefix(
            useful,
            cp_length=ofdm_signal.cyclic_prefix_length,
            oversampling=L,
        )
    else:
        full = useful

    papr = make_papr_result(useful.ravel(), cp_excluded=True)

    meta = {
        "n_reserved": int(reserved.size),
        "reserved_indices": reserved.tolist(),
        "clipping_ratio": float(clipping_ratio),
        "n_iterations": int(n_iterations),
        "step_size": float(step_size),
        "threshold": threshold,
        "cp_excluded": True,
        "n_samples_used": int(useful.size),
        "modified": True,
        "spectral_efficiency_loss": float(reserved.size / max(len(data_idx), 1)),
    }

    return PAPRProcessResult(
        waveform=full,
        papr=papr,
        method=PAPRMethod.TONE_RESERVATION,
        meta=meta,
    )


def process(
    transmit_frame: TransmitFrame,
    *,
    n_reserved: int = 8,
    reserved_indices: Optional[Sequence[int]] = None,
    clipping_ratio: float = 1.5,
    n_iterations: int = 10,
    step_size: float = 1.0,
    rng: Optional[np.random.Generator] = None,
    **kwargs: Any,
) -> PAPRResult:
    result = apply_tone_reservation(
        transmit_frame,
        n_reserved=n_reserved,
        reserved_indices=reserved_indices,
        clipping_ratio=clipping_ratio,
        n_iterations=n_iterations,
        step_size=step_size,
        rng=rng,
        **kwargs,
    )
    return result.papr


def method_name() -> str:
    return METHOD_NAME


def is_implemented() -> bool:
    return IMPLEMENTED


def stage() -> str:
    return STAGE


def description() -> str:
    return (
        "Tone Reservation (TR): reserve subcarriers and iteratively "
        "build a cancellation signal to reduce peaks."
    )


def metadata() -> dict[str, Any]:
    return {
        "method": METHOD_NAME,
        "implemented": IMPLEMENTED,
        "stage": STAGE,
        "parameters": {
            "n_reserved": "int (default 8)",
            "reserved_indices": "optional explicit bins",
            "clipping_ratio": "float (default 1.5)",
            "n_iterations": "int (default 10)",
            "step_size": "float (default 1.0)",
        },
    }


tone_reservation = apply_tone_reservation

__all__ = [
    "apply_tone_reservation",
    "process",
    "method_name",
    "is_implemented",
    "stage",
    "description",
    "metadata",
    "tone_reservation",
    "METHOD",
    "IMPLEMENTED",
]
