"""
PAPR Method: Active Constellation Extension (ACE)
=================================================

Iterative ACE for OFDM PAPR reduction.

Algorithm
---------
1. Convert current frequency-domain data symbols to time domain.
2. Soft-clip (or hard-clip) peaks that exceed a target threshold.
3. FFT the clip residual back to frequency domain.
4. For each data tone, keep only the component of the residual that
   moves the constellation point *outward* (away from the origin /
   outside the nominal constellation boundary). Discard inward moves.
5. Add a scaled version of the allowed extension to the data symbols.
6. Repeat for a fixed number of iterations.

ACE does not need side information at the receiver (constellation
points remain in decision regions for sufficiently moderate extension).

PAPR is measured on useful samples only.
"""

from __future__ import annotations

from typing import Any, Optional

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
from papr_methods.none import PAPRProcessResult


METHOD = PAPRMethod.ACE
METHOD_NAME = METHOD.value
IMPLEMENTED = True
STAGE = "Phase-2"


def _os_fft_to_grid(
    time: ComplexArray,
    fft_size: int,
    oversampling: int,
    fft_norm: FFTNormalization,
) -> ComplexArray:
    """
    FFT oversampled time signal and fold back to original FFT bins.
    time: (n_sym, fft_size * L)
    returns: (n_sym, fft_size)
    """
    R = np.fft.fft(time, axis=-1, norm=numpy_fft_norm(fft_norm))
    half = fft_size // 2
    C = np.zeros((time.shape[0], fft_size), dtype=np.complex128)
    C[:, : half + 1] = R[:, : half + 1]
    if half > 0:
        C[:, -half:] = R[:, -half:]
    return C


def apply_ace(
    waveform: TransmitFrame | OFDMSignal | ComplexArray,
    *,
    clipping_ratio: float = 1.5,
    n_iterations: int = 8,
    step_size: float = 0.8,
    max_extension: Optional[float] = None,
    rng: Optional[np.random.Generator] = None,
    fft_norm: FFTNormalization = FFTNormalization.UNITARY,
    **kwargs: Any,
) -> PAPRProcessResult:
    """
    Apply iterative Active Constellation Extension.

    Parameters
    ----------
    clipping_ratio :
        Target peak = CR · rms of the original useful signal.
    n_iterations :
        Number of ACE iterations.
    step_size :
        Scale μ applied to the allowed extension each iteration.
    max_extension :
        Optional hard limit on |extension| relative to original
        symbol magnitude (None = unlimited).
    """
    validate_positive_integer(n_iterations, "n_iterations")
    if clipping_ratio <= 0.0:
        raise ValueError("clipping_ratio must be positive.")
    if step_size <= 0.0:
        raise ValueError("step_size must be positive.")

    if not isinstance(waveform, TransmitFrame):
        raise TypeError(
            "ACE requires a TransmitFrame (frequency-domain grid)."
        )

    frame: TransmitFrame = waveform
    ofdm_signal = frame.waveform
    grid = frame.ofdm_grid
    X0 = np.asarray(grid.symbols, dtype=np.complex128).copy()
    if X0.ndim == 1:
        X0 = X0[np.newaxis, :]
    X = X0.copy()

    data_idx = np.asarray(grid.data_indices, dtype=np.int64)
    pilot_idx = np.asarray(grid.pilot_indices, dtype=np.int64)
    active_idx = np.asarray(grid.active_indices, dtype=np.int64)
    fft_size = grid.fft_size
    L = ofdm_signal.oversampling
    n_sym = X.shape[0]

    # Original data symbols (for outward test)
    X_data0 = X0[:, data_idx].copy()

    useful = ofdm_ifft(
        OFDMGrid(
            symbols=X,
            active_indices=active_idx,
            pilot_indices=pilot_idx,
            data_indices=data_idx,
        ),
        oversampling=L,
        norm=fft_norm,
    )
    p_avg = safe_mean_power(useful.ravel())
    if p_avg <= 0.0:
        raise ValueError("Average power is zero.")
    rms = float(np.sqrt(p_avg))
    threshold = float(clipping_ratio * rms)

    for _ in range(n_iterations):
        mag = np.abs(useful)
        peak_mask = mag > threshold
        if not np.any(peak_mask):
            break

        # Soft clip residual
        residual = np.zeros_like(useful)
        residual[peak_mask] = useful[peak_mask] * (
            1.0 - threshold / mag[peak_mask]
        )

        # Frequency-domain residual
        R = _os_fft_to_grid(residual, fft_size, L, fft_norm)

        # Allowed extension: only components that increase |X| (outward)
        ext = np.zeros_like(X)
        Xd = X[:, data_idx]
        Rd = R[:, data_idx]
        # Projection of residual onto the radial direction of current symbol
        # Keep only the part that points away from origin relative to original
        # Classic ACE: extend outside the constellation boundary.
        # Practical rule: keep Re{ R * conj(X0) / |X0| } > 0 component.
        X0d = X_data0
        mag0 = np.abs(X0d)
        mag0_safe = np.where(mag0 < 1e-12, 1.0, mag0)
        unit = X0d / mag0_safe
        radial = np.real(Rd * np.conj(unit))
        radial = np.maximum(radial, 0.0)  # outward only
        extension = radial * unit

        if max_extension is not None:
            ext_mag = np.abs(extension)
            cap = max_extension * mag0_safe
            scale = np.ones_like(ext_mag)
            over = ext_mag > cap
            scale[over] = cap[over] / ext_mag[over]
            extension = extension * scale

        ext[:, data_idx] = extension
        X = X - step_size * ext  # subtract residual contribution ≈ add extension opposite to peak

        # Rebuild time signal
        useful = ofdm_ifft(
            OFDMGrid(
                symbols=X,
                active_indices=active_idx,
                pilot_indices=pilot_idx,
                data_indices=data_idx,
            ),
            oversampling=L,
            norm=fft_norm,
        )

    if ofdm_signal.cp_included and ofdm_signal.cyclic_prefix_length > 0:
        full = add_cyclic_prefix(
            useful,
            cp_length=ofdm_signal.cyclic_prefix_length,
            oversampling=L,
        )
    else:
        full = useful

    papr = make_papr_result(useful.ravel(), cp_excluded=True)

    # Extension energy metric
    dX = X[:, data_idx] - X_data0
    ext_power = float(np.mean(np.abs(dX) ** 2)) if dX.size else 0.0

    meta = {
        "clipping_ratio": float(clipping_ratio),
        "n_iterations": int(n_iterations),
        "step_size": float(step_size),
        "max_extension": max_extension,
        "threshold": threshold,
        "extension_power": ext_power,
        "cp_excluded": True,
        "n_samples_used": int(useful.size),
        "modified": True,
    }

    return PAPRProcessResult(
        waveform=full,
        papr=papr,
        method=PAPRMethod.ACE,
        meta=meta,
    )


def process(
    transmit_frame: TransmitFrame,
    *,
    clipping_ratio: float = 1.5,
    n_iterations: int = 8,
    step_size: float = 0.8,
    max_extension: Optional[float] = None,
    rng: Optional[np.random.Generator] = None,
    **kwargs: Any,
) -> PAPRResult:
    result = apply_ace(
        transmit_frame,
        clipping_ratio=clipping_ratio,
        n_iterations=n_iterations,
        step_size=step_size,
        max_extension=max_extension,
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
        "Active Constellation Extension (ACE): iteratively extend "
        "constellation points outward to reduce time-domain peaks."
    )


def metadata() -> dict[str, Any]:
    return {
        "method": METHOD_NAME,
        "implemented": IMPLEMENTED,
        "stage": STAGE,
        "parameters": {
            "clipping_ratio": "float (default 1.5)",
            "n_iterations": "int (default 8)",
            "step_size": "float (default 0.8)",
            "max_extension": "optional float",
        },
    }


ace = apply_ace

__all__ = [
    "apply_ace",
    "process",
    "method_name",
    "is_implemented",
    "stage",
    "description",
    "metadata",
    "ace",
    "METHOD",
    "IMPLEMENTED",
]
