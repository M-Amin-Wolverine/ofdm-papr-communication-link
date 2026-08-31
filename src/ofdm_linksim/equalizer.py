```python
"""
Frequency-domain equalization
=============================

Receiver-side frequency-domain equalizers for OFDM-LinkSim.

This module applies one-tap equalization to received frequency-domain
symbols. It is designed to support the baseline AWGN link as well as
future fading-channel experiments such as Rayleigh and Rician channels.

Supported equalizers
--------------------
EqualizerType.NONE
    Identity/pass-through operation.

EqualizerType.ZF
    Zero-Forcing equalization:

        X_hat = Y / H

EqualizerType.MMSE
    Minimum Mean-Square Error equalization:

        X_hat = Y * H* / (|H|² + N0/Es)

    where ``N0`` is represented by ``noise_power`` and ``Es`` is
    normalized to one unless otherwise specified.

Design goals
------------
- Strict complex-signal validation.
- Explicit equalizer dispatch.
- Numerically stable ZF operation.
- Standard one-tap MMSE formulation.
- Flexible channel-gain broadcasting.
- Defensive output copies.
- Clear error messages.
- Easy extension toward pilot-based channel estimation and MIMO.

Notes
-----
The equalizer operates on already demodulated frequency-domain
symbols. It does not estimate the channel itself.

Channel estimation should therefore be handled by the synchronization,
pilot, or channel-estimation layer in the receiver pipeline and the
resulting channel response should be passed through ``channel_gain``.
"""

from __future__ import annotations

from typing import Any, Optional

import numpy as np

from ofdm_linksim.core.types import (
    ComplexArray,
    EqualizerType,
    validate_complex_signal,
)


# ----------------------------------------------------------------------
# Numerical configuration
# ----------------------------------------------------------------------

_DEFAULT_EPSILON = 1e-12


def _prepare_channel_gain(
    symbols: ComplexArray,
    channel_gain: ComplexArray,
) -> np.ndarray:
    """
    Validate and prepare the channel response.

    The channel response may have:
    - exactly the same shape as ``symbols``;
    - a broadcast-compatible shape;
    - a flattened representation with the same number of elements.

    Parameters
    ----------
    symbols:
        Received complex symbols.

    channel_gain:
        Estimated channel frequency response.

    Returns
    -------
    np.ndarray
        Complex channel response broadcast to the symbol shape.

    Raises
    ------
    ValueError
        If the channel response cannot be aligned with the symbols.
    """
    h = np.asarray(channel_gain, dtype=np.complex128)

    if h.shape == symbols.shape:
        return h

    # Direct NumPy broadcasting.
    try:
        return np.broadcast_to(h, symbols.shape).astype(
            np.complex128,
            copy=False,
        )
    except ValueError:
        pass

    # If the total number of elements matches, allow a flattened
    # representation to be reshaped onto the received symbol grid.
    if h.size == symbols.size:
        return h.reshape(symbols.shape)

    raise ValueError(
        "channel_gain shape is incompatible with symbols: "
        f"channel_gain={h.shape}, symbols={symbols.shape}."
    )


def _validate_noise_power(noise_power: float) -> float:
    """
    Validate and normalize noise power.

    Negative noise power is physically meaningless and therefore
    rejected instead of silently clamping it to zero.
    """
    if isinstance(noise_power, bool):
        raise TypeError("noise_power must be a real non-negative number.")

    try:
        value = float(noise_power)
    except (TypeError, ValueError) as exc:
        raise TypeError(
            "noise_power must be a real non-negative number."
        ) from exc

    if not np.isfinite(value):
        raise ValueError("noise_power must be finite.")

    if value < 0.0:
        raise ValueError("noise_power cannot be negative.")

    return value


def _equalize_zf(
    y: np.ndarray,
    h: np.ndarray,
    *,
    epsilon: float = _DEFAULT_EPSILON,
) -> np.ndarray:
    """
    Apply numerically stable one-tap Zero-Forcing equalization.

    The ideal ZF operation is:

        X_hat = Y / H

    When ``|H|`` approaches zero, direct inversion becomes numerically
    unstable and can amplify noise catastrophically.

    Such channel taps are therefore detected and replaced by zero in
    the equalized output.
    """
    if epsilon <= 0.0:
        raise ValueError("epsilon must be greater than zero.")

    magnitude = np.abs(h)

    result = np.zeros_like(y, dtype=np.complex128)

    valid = magnitude > epsilon

    np.divide(
        y,
        h,
        out=result,
        where=valid,
    )

    return result


def _equalize_mmse(
    y: np.ndarray,
    h: np.ndarray,
    *,
    noise_power: float,
    signal_power: float = 1.0,
    epsilon: float = _DEFAULT_EPSILON,
) -> np.ndarray:
    """
    Apply one-tap MMSE equalization.

    The equalizer coefficient is

        W = H* / (|H|² + N0/Es)

    and the equalized symbol is

        X_hat = W Y.

    ``signal_power`` represents the average transmitted symbol energy
    ``Es``. For normalized constellations, the default value of 1.0 is
    appropriate.

    A small numerical epsilon is included in the denominator to avoid
    pathological division-by-zero cases when both the channel and
    noise term are zero.
    """
    if signal_power <= 0.0:
        raise ValueError("signal_power must be greater than zero.")

    if epsilon <= 0.0:
        raise ValueError("epsilon must be greater than zero.")

    regularization = noise_power / signal_power

    denominator = (
        np.abs(h) ** 2
        + regularization
        + epsilon
    )

    return (
        y
        * np.conj(h)
        / denominator
    )


def equalize(
    symbols: ComplexArray,
    *,
    channel_gain: Optional[ComplexArray] = None,
    equalizer: EqualizerType = EqualizerType.NONE,
    noise_power: float = 0.0,
    signal_power: float = 1.0,
    epsilon: float = _DEFAULT_EPSILON,
    **kwargs: Any,
) -> ComplexArray:
    """
    Equalize received frequency-domain symbols.

    Parameters
    ----------
    symbols:
        Received complex-valued frequency-domain symbols.

    channel_gain:
        Estimated complex channel frequency response ``H``.

        Required for:
            - Zero-Forcing (ZF)
            - Minimum Mean-Square Error (MMSE)

        The channel response may be:
            - identical in shape to ``symbols``;
            - broadcast-compatible with ``symbols``;
            - flattened with the same total number of elements.

    equalizer:
        Equalization strategy.

        ``EqualizerType.NONE``
            Return the received symbols unchanged.

        ``EqualizerType.ZF``
            Apply Zero-Forcing equalization.

        ``EqualizerType.MMSE``
            Apply one-tap MMSE equalization.

    noise_power:
        Noise power ``N0`` used by the MMSE equalizer.

        Must be finite and non-negative.

    signal_power:
        Average transmitted symbol power ``Es``.

        The default value of 1.0 assumes normalized constellation
        energy.

    epsilon:
        Numerical stability threshold.

        For ZF, channel taps with ``|H| <= epsilon`` are treated as
        non-invertible and their equalized output is set to zero.

        For MMSE, ``epsilon`` prevents pathological zero denominators.

    **kwargs:
        Reserved for future equalizer-specific parameters.

        Possible future parameters include:
            - channel_estimation_mode
            - pilot_spacing
            - regularization
            - MIMO channel matrices
            - spatial stream index
            - soft-output equalization options

    Returns
    -------
    ComplexArray
        Equalized complex-valued symbols.

    Raises
    ------
    ValueError
        If a required channel response is missing, dimensions are
        incompatible, numerical parameters are invalid, or the
        equalizer type is unsupported.

    TypeError
        If numerical parameters have invalid types.

    Notes
    -----
    For ``EqualizerType.NONE``, ``channel_gain`` is not required and
    ``noise_power`` is ignored.

    The input symbol array is never modified in-place.

    Examples
    --------
    Baseline AWGN:

        equalized = equalize(
            received,
            equalizer=EqualizerType.NONE,
        )

    Zero-Forcing:

        equalized = equalize(
            received,
            channel_gain=H,
            equalizer=EqualizerType.ZF,
        )

    MMSE:

        equalized = equalize(
            received,
            channel_gain=H,
            equalizer=EqualizerType.MMSE,
            noise_power=noise_power,
        )
    """
    # ------------------------------------------------------------------
    # Input validation
    # ------------------------------------------------------------------
    validate_complex_signal(symbols)

    y = np.asarray(
        symbols,
        dtype=np.complex128,
    )

    # ------------------------------------------------------------------
    # Identity / bypass mode
    # ------------------------------------------------------------------
    if equalizer is EqualizerType.NONE:
        return y.copy()

    # ------------------------------------------------------------------
    # Channel response is mandatory for adaptive equalization
    # ------------------------------------------------------------------
    if channel_gain is None:
        raise ValueError(
            f"channel_gain is required for {equalizer.value!r} "
            "equalization."
        )

    h = _prepare_channel_gain(
        y,
        channel_gain,
    )

    # ------------------------------------------------------------------
    # Zero-Forcing
    # ------------------------------------------------------------------
    if equalizer is EqualizerType.ZF:
        return _equalize_zf(
            y,
            h,
            epsilon=epsilon,
        )

    # ------------------------------------------------------------------
    # Minimum Mean-Square Error
    # ------------------------------------------------------------------
    if equalizer is EqualizerType.MMSE:
        validated_noise_power = _validate_noise_power(
            noise_power,
        )

        return _equalize_mmse(
            y,
            h,
            noise_power=validated_noise_power,
            signal_power=signal_power,
            epsilon=epsilon,
        )

    # ------------------------------------------------------------------
    # Unsupported mode
    # ------------------------------------------------------------------
    raise NotImplementedError(
        f"Equalizer type {equalizer!r} is not implemented."
    )


# ----------------------------------------------------------------------
# Backward-compatible public alias
# ----------------------------------------------------------------------

equalizer = equalize


__all__ = [
    "equalize",
    "equalizer",
]
