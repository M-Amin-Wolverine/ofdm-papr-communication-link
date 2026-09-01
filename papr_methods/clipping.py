"""
PAPR method: Clipping
=====================

Classic amplitude clipping of the time-domain OFDM waveform.

Two modes
---------
- hard : |x| > A  →  A * exp(j·arg(x))
- soft : smooth clip with tanh (optional)

Clipping ratio CR is defined as:

    CR = A / sqrt(E[|x|²])

Stage-1 research uses hard clipping on useful samples for PAPR
statistics; the returned waveform may still include CP (same layout
as the input) with clipping applied to the entire vector, or only
to useful samples depending on ``clip_cp``.

PAPR is always reported on useful samples (project contract).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

import numpy as np

from ofdm_linksim.core.types import (
    ComplexArray,
    OFDMSignal,
    PAPRMethod,
    PAPRResult,
    TransmitFrame,
    make_papr_result,
    safe_mean_power,
    validate_complex_signal,
)
from ofdm_linksim.papr import get_useful_samples
from papr_methods.none import PAPRProcessResult


def _clip_hard(x: ComplexArray, amplitude: float) -> ComplexArray:
    mag = np.abs(x)
    scale = np.ones_like(mag, dtype=np.float64)
    mask = mag > amplitude
    scale[mask] = amplitude / mag[mask]
    return (x * scale).astype(np.complex128, copy=False)


def _clip_soft(x: ComplexArray, amplitude: float) -> ComplexArray:
    """Soft clip: amplitude * tanh(|x|/amplitude) * exp(j·phase)."""
    mag = np.abs(x)
    phase = np.exp(1j * np.angle(x))
    # avoid 0/0
    mag_safe = np.where(mag == 0.0, 1.0, mag)
    new_mag = amplitude * np.tanh(mag / amplitude)
    out = new_mag * phase
    out = np.where(mag == 0.0, 0.0 + 0.0j, out)
    return out.astype(np.complex128, copy=False)


def apply_clipping(
    waveform: OFDMSignal | ComplexArray | TransmitFrame,
    *,
    clipping_ratio: float = 1.5,
    mode: str = "hard",
    clip_cp: bool = True,
    rng: Optional[np.random.Generator] = None,
    **kwargs: Any,
) -> PAPRProcessResult:
    """
    Apply amplitude clipping and measure PAPR on useful samples.

    Parameters
    ----------
    clipping_ratio :
        CR = A / rms. Typical research values: 1.2 … 2.0.
    mode :
        ``"hard"`` or ``"soft"``.
    clip_cp :
        If True, clip the full waveform (including CP).
        PAPR is still computed on useful samples only.
    """
    if clipping_ratio <= 0.0:
        raise ValueError("clipping_ratio must be positive.")

    mode = str(mode).lower()
    if mode not in {"hard", "soft"}:
        raise ValueError("mode must be 'hard' or 'soft'.")

    ofdm_signal: Optional[OFDMSignal] = None
    if isinstance(waveform, TransmitFrame):
        ofdm_signal = waveform.waveform
        full = np.asarray(ofdm_signal.samples, dtype=np.complex128).copy()
    elif isinstance(waveform, OFDMSignal):
        ofdm_signal = waveform
        full = np.asarray(waveform.samples, dtype=np.complex128).copy()
    else:
        validate_complex_signal(waveform)
        full = np.asarray(waveform, dtype=np.complex128).copy()

    # RMS from useful samples (definition consistency)
    if ofdm_signal is not None:
        useful_ref = get_useful_samples(ofdm_signal).ravel()
    else:
        useful_ref = full.ravel()

    p_avg = safe_mean_power(useful_ref)
    if p_avg <= 0.0:
        raise ValueError("Average power is zero; cannot clip.")
    rms = float(np.sqrt(p_avg))
    amplitude = float(clipping_ratio * rms)

    if clip_cp or ofdm_signal is None:
        target = full
    else:
        # clip only useful region, keep CP untouched
        target = get_useful_samples(ofdm_signal)
        # operate on a writable copy then write back
        target = np.asarray(target, dtype=np.complex128).copy()

    clip_fn = _clip_hard if mode == "hard" else _clip_soft
    clipped_region = clip_fn(target.ravel(), amplitude).reshape(target.shape)

    if clip_cp or ofdm_signal is None:
        full = clipped_region.reshape(full.shape)
        useful = get_useful_samples(
            OFDMSignal(
                samples=full,
                fft_size=ofdm_signal.fft_size if ofdm_signal else 256,
                oversampling=ofdm_signal.oversampling if ofdm_signal else 4,
                cyclic_prefix_length=(
                    ofdm_signal.cyclic_prefix_length if ofdm_signal else 0
                ),
                cp_included=ofdm_signal.cp_included if ofdm_signal else False,
                n_symbols=ofdm_signal.n_symbols if ofdm_signal else 1,
            )
        ) if ofdm_signal is not None else full.ravel()
    else:
        # write clipped useful samples back into full layout
        full = _write_useful_back(ofdm_signal, full, clipped_region)
        useful = clipped_region.ravel()

    papr = make_papr_result(np.asarray(useful).ravel(), cp_excluded=True)

    # clipping noise / distortion metrics
    err = useful_ref.ravel() - np.asarray(useful).ravel()
    clip_noise_power = float(np.mean(np.abs(err) ** 2)) if err.size else 0.0

    return PAPRProcessResult(
        waveform=full,
        papr=papr,
        method=PAPRMethod.CLIPPING,
        meta={
            "clipping_ratio": float(clipping_ratio),
            "amplitude": amplitude,
            "rms": rms,
            "mode": mode,
            "clip_cp": bool(clip_cp),
            "clip_noise_power": clip_noise_power,
            "cp_excluded": True,
            "n_samples_used": int(np.asarray(useful).size),
            "modified": True,
        },
    )


def _write_useful_back(
    signal: OFDMSignal,
    full: ComplexArray,
    useful_clipped: ComplexArray,
) -> ComplexArray:
    """Replace useful samples inside a CP-bearing waveform."""
    full = np.asarray(full, dtype=np.complex128).copy()
    useful_clipped = np.asarray(useful_clipped, dtype=np.complex128)

    L = signal.oversampling
    n_fft = signal.fft_size * L
    n_cp = signal.cyclic_prefix_length * L
    n_total = n_fft + n_cp
    n_sym = signal.n_symbols

    u = useful_clipped.ravel()
    if signal.cp_included:
        if full.ndim == 2:
            # (n_sym, n_total)
            full[:, n_cp:] = u.reshape(n_sym, n_fft)
        else:
            for i in range(n_sym):
                start = i * n_total + n_cp
                full.ravel()[start : start + n_fft] = u[i * n_fft : (i + 1) * n_fft]
    else:
        full = u.reshape(full.shape)
    return full


def process(
    transmit_frame: TransmitFrame,
    *,
    clipping_ratio: float = 1.5,
    mode: str = "hard",
    clip_cp: bool = True,
    rng: Optional[np.random.Generator] = None,
    **kwargs: Any,
) -> PAPRResult:
    """
    Pipeline entry: returns ``PAPRResult`` after clipping.

    Note: the pipeline Stage-1 contract returns PAPRResult only.
    Call ``apply_clipping`` if you also need the clipped waveform.
    """
    result = apply_clipping(
        transmit_frame,
        clipping_ratio=clipping_ratio,
        mode=mode,
        clip_cp=clip_cp,
        rng=rng,
        **kwargs,
    )
    return result.papr


clipping = process
