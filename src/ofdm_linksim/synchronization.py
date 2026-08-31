"""
Synchronization impairments / recovery
======================================

Synchronization-related impairments and receiver-side recovery helpers
for OFDM-LinkSim.

This module provides a controlled interface for introducing and
eventually compensating for synchronization errors in the simulated
OFDM link.

Supported impairments
---------------------
Timing Offset
    A sample-domain timing displacement.

Carrier Frequency Offset (CFO)
    A normalized frequency mismatch represented by a complex rotating
    phasor:

        y[n] = x[n] exp(j 2π ε n)

    where ``ε`` is the normalized CFO relative to the sampling rate.

Stage-1 behavior
----------------
With ``enabled=False`` the synchronization stage behaves as a strict
pass-through. A new ``ChannelOutput`` object is returned and all
numerical arrays are copied.

Design goals
------------
- Preserve the ``ChannelOutput`` contract.
- Never modify caller-owned arrays in-place.
- Keep impairment models deterministic unless randomness is explicitly
  introduced later.
- Separate timing and CFO transformations.
- Validate synchronization parameters.
- Preserve channel metadata.
- Provide clean extension points for SFO and synchronization recovery.
- Avoid silently hiding unsupported synchronization features.

Future extensions
------------------
Possible additions include:

- Fractional timing offset
- Sampling Frequency Offset (SFO)
- CFO estimation
- CFO compensation
- Preamble-based synchronization
- Schmidl-Cox synchronization
- Minn synchronization
- Park synchronization
- Pilot-aided phase tracking
- Common Phase Error (CPE) correction
- Joint timing/frequency synchronization
"""

from __future__ import annotations

from typing import Any, Optional

import numpy as np

from ofdm_linksim.core.types import (
    ChannelOutput,
    validate_complex_signal,
)


# ----------------------------------------------------------------------
# Numerical configuration
# ----------------------------------------------------------------------

_CFO_TOLERANCE = 1e-15


def _copy_channel_output(
    channel_output: ChannelOutput,
    signal: np.ndarray,
) -> ChannelOutput:
    """
    Create an independent ChannelOutput while preserving metadata.

    Parameters
    ----------
    channel_output:
        Original channel output.

    signal:
        New complex-valued signal.

    Returns
    -------
    ChannelOutput
        New object with copied channel metadata.
    """
    return ChannelOutput(
        signal=np.asarray(signal, dtype=np.complex128).copy(),
        snr_db=channel_output.snr_db,
        channel_type=channel_output.channel_type,
        noise_power=channel_output.noise_power,
        channel_gain=(
            None
            if channel_output.channel_gain is None
            else np.asarray(
                channel_output.channel_gain,
                dtype=np.complex128,
            ).copy()
        ),
    )


def _validate_timing_offset(
    timing_offset_samples: int,
) -> int:
    """
    Validate and normalize integer timing offset.
    """
    if isinstance(timing_offset_samples, bool):
        raise TypeError(
            "timing_offset_samples must be an integer."
        )

    if not isinstance(
        timing_offset_samples,
        (int, np.integer),
    ):
        raise TypeError(
            "timing_offset_samples must be an integer."
        )

    return int(timing_offset_samples)


def _validate_cfo(
    cfo_normalized: float,
) -> float:
    """
    Validate and normalize normalized CFO.

    ``cfo_normalized`` is expressed in cycles per sample.

    Examples
    --------
    ``0.01`` means a phase rotation of

        2π × 0.01

    radians per sample.
    """
    if isinstance(cfo_normalized, bool):
        raise TypeError(
            "cfo_normalized must be a finite real number."
        )

    try:
        value = float(cfo_normalized)
    except (TypeError, ValueError) as exc:
        raise TypeError(
            "cfo_normalized must be a finite real number."
        ) from exc

    if not np.isfinite(value):
        raise ValueError(
            "cfo_normalized must be finite."
        )

    return value


def _apply_timing_offset(
    signal: np.ndarray,
    timing_offset_samples: int,
) -> np.ndarray:
    """
    Apply a deterministic sample timing displacement.

    For the current simulator abstraction, timing offset is represented
    as a circular sample displacement. This keeps the output length
    unchanged and avoids introducing artificial zero-padding or signal
    truncation.

    Notes
    -----
    This is a simplified impairment model.

    It should not be interpreted as a complete physical model of OFDM
    symbol timing error, especially when the offset crosses the cyclic
    prefix boundary.

    A future receiver-level synchronization model can replace this with
    CP-aware symbol-window selection.
    """
    if timing_offset_samples == 0:
        return signal.copy()

    flat = np.asarray(
        signal,
        dtype=np.complex128,
    ).ravel()

    shifted = np.roll(
        flat,
        timing_offset_samples,
    )

    return shifted.reshape(signal.shape)


def _apply_cfo(
    signal: np.ndarray,
    cfo_normalized: float,
) -> np.ndarray:
    """
    Apply normalized carrier-frequency offset.

    The impairment is modeled as:

        y[n] = x[n] exp(j 2π ε n)

    where:
        ε = normalized CFO
        n = sample index
    """
    if abs(cfo_normalized) <= _CFO_TOLERANCE:
        return signal.copy()

    flat = np.asarray(
        signal,
        dtype=np.complex128,
    ).ravel()

    sample_index = np.arange(
        flat.size,
        dtype=np.float64,
    )

    phase_rotation = np.exp(
        1j
        * 2.0
        * np.pi
        * cfo_normalized
        * sample_index
    )

    impaired = flat * phase_rotation

    return impaired.reshape(signal.shape)


def apply_synchronization(
    channel_output: ChannelOutput,
    *,
    enabled: bool = False,
    cfo_normalized: float = 0.0,
    timing_offset_samples: int = 0,
    rng: Optional[np.random.Generator] = None,
    **kwargs: Any,
) -> ChannelOutput:
    """
    Apply synchronization-related impairments.

    Parameters
    ----------
    channel_output:
        Output of the channel model.

    enabled:
        Enable or bypass synchronization impairments.

        When ``False``, the function returns a new ``ChannelOutput``
        containing numerically identical data.

    cfo_normalized:
        Normalized carrier-frequency offset in cycles per sample.

        The resulting phase rotation is:

            exp(j 2π ε n)

        where ``ε = cfo_normalized``.

    timing_offset_samples:
        Integer timing displacement in samples.

        Positive values shift the signal toward later sample indices;
        negative values shift it toward earlier indices.

        The current implementation uses circular shifting to preserve
        signal length.

    rng:
        Reserved for future stochastic synchronization models.

        It is currently unused because CFO and timing offset are
        deterministic impairments.

    **kwargs:
        Reserved for future synchronization parameters.

        Possible examples:

            - sfo_normalized
            - cfo_estimate
            - timing_estimate
            - use_cp
            - pilot_based_tracking
            - phase_tracking

    Returns
    -------
    ChannelOutput
        A new channel-output object containing the impaired signal and
        preserved channel metadata.

    Raises
    ------
    TypeError
        If ``channel_output`` or synchronization parameters have
        invalid types.

    ValueError
        If a numerical synchronization parameter is invalid.

    Notes
    -----
    The function applies timing offset before CFO.

    Therefore:

        x
        ↓
        timing offset
        ↓
        CFO
        ↓
        output

    This ordering is explicit and deterministic.
    """
    # ------------------------------------------------------------------
    # Validate ChannelOutput
    # ------------------------------------------------------------------
    if not isinstance(
        channel_output,
        ChannelOutput,
    ):
        raise TypeError(
            "channel_output must be a ChannelOutput instance."
        )

    # ------------------------------------------------------------------
    # Validate signal
    # ------------------------------------------------------------------
    validate_complex_signal(
        channel_output.signal,
    )

    signal = np.asarray(
        channel_output.signal,
        dtype=np.complex128,
    )

    # ------------------------------------------------------------------
    # Validate parameters even when enabled=False.
    #
    # This prevents invalid configurations from silently passing
    # through the pipeline and failing much later.
    # ------------------------------------------------------------------
    timing_offset_samples = _validate_timing_offset(
        timing_offset_samples,
    )

    cfo_normalized = _validate_cfo(
        cfo_normalized,
    )

    # ``rng`` is intentionally accepted for API compatibility with
    # future stochastic synchronization models.
    if rng is not None and not isinstance(
        rng,
        np.random.Generator,
    ):
        raise TypeError(
            "rng must be a numpy.random.Generator or None."
        )

    # ------------------------------------------------------------------
    # Strict Stage-1 bypass
    # ------------------------------------------------------------------
    if not enabled:
        return _copy_channel_output(
            channel_output,
            signal,
        )

    # ------------------------------------------------------------------
    # Synchronization impairment chain
    # ------------------------------------------------------------------
    out = signal.copy()

    # 1. Timing displacement
    if timing_offset_samples != 0:
        out = _apply_timing_offset(
            out,
            timing_offset_samples,
        )

    # 2. Carrier-frequency offset
    if abs(cfo_normalized) > _CFO_TOLERANCE:
        out = _apply_cfo(
            out,
            cfo_normalized,
        )

    # ------------------------------------------------------------------
    # Preserve channel metadata while returning an independent object.
    # ------------------------------------------------------------------
    return _copy_channel_output(
        channel_output,
        out,
    )


# ----------------------------------------------------------------------
# Backward-compatible public aliases
# ----------------------------------------------------------------------

synchronizer = apply_synchronization
synchronize = apply_synchronization


__all__ = [
    "apply_synchronization",
    "synchronizer",
    "synchronize",
]
