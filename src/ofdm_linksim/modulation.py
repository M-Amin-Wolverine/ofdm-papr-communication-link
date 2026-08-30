```python
"""
OFDM-LinkSim — Digital Modulation / Demodulation
=================================================

Provides bit-to-symbol modulation and hard-decision symbol-to-bit
demodulation for the supported digital modulation schemes.

Supported schemes
-----------------
- QPSK
- 16-QAM
- 64-QAM
- 256-QAM
- 1024-QAM

Design principles
-----------------
- All constellations use unit average symbol power.
- QPSK and QAM use Gray-coded labeling.
- Bit ordering is MSB-first.
- Modulation is deterministic and does not use random state.
- Demodulation uses minimum Euclidean distance.
- Public inputs and outputs are validated at the module boundary.
- Constellation definitions are immutable from the caller's perspective.

Stage-1 baseline
----------------
QPSK is the default modulation scheme.

Higher-order QAM schemes are implemented here so that PAPR, channel,
equalization, and BER experiments can change modulation order without
changing the modulation interface.

Bit mapping convention
----------------------
For every symbol, the input bits are interpreted MSB-first.

For square QAM, the first half of the bits controls the I-axis and the
second half controls the Q-axis.

Gray coding is applied independently on both axes.

Examples
--------
QPSK:

    00 -> (+1 + 1j) / sqrt(2)
    01 -> (+1 - 1j) / sqrt(2)
    11 -> (-1 - 1j) / sqrt(2)
    10 -> (-1 + 1j) / sqrt(2)

16-QAM uses 2 Gray-coded bits per axis:

    00 -> -3
    01 -> -1
    11 -> +1
    10 -> +3

The complete constellation is then normalized to unit average power.
"""

from __future__ import annotations

from typing import Dict

import numpy as np

from ofdm_linksim.core.types import (
    BitArray,
    ComplexArray,
    ModulationType,
    validate_bits,
    validate_complex_signal,
)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_SUPPORTED_QAM_ORDERS = (16, 64, 256, 1024)

_CONSTELLATION_DTYPE = np.complex128
_BIT_DTYPE = np.uint8


# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------

def _validate_modulation(mod: ModulationType) -> None:
    """Validate a supported modulation enum value."""
    if not isinstance(mod, ModulationType):
        raise TypeError(
            "mod must be an instance of ModulationType, "
            f"got {type(mod).__name__}."
        )


def _gray_encode(value: np.ndarray) -> np.ndarray:
    """
    Convert binary integers to Gray-coded integers.

    Gray encoding:

        g = b XOR (b >> 1)

    Parameters
    ----------
    value :
        Non-negative integer NumPy array.

    Returns
    -------
    np.ndarray
        Gray-coded integer array.
    """
    value = np.asarray(value, dtype=np.int64)
    return value ^ (value >> 1)


def _gray_decode(value: np.ndarray) -> np.ndarray:
    """
    Convert Gray-coded integers back to binary integers.

    Parameters
    ----------
    value :
        Gray-coded integer NumPy array.

    Returns
    -------
    np.ndarray
        Binary integer array.
    """
    value = np.asarray(value, dtype=np.int64)

    decoded = value.copy()
    shift = 1

    while shift < value.dtype.itemsize * 8:
        decoded ^= value >> shift
        shift <<= 1

    return decoded


def _bits_to_integers(
    bits: BitArray,
    bits_per_value: int,
) -> np.ndarray:
    """
    Convert groups of MSB-first bits into unsigned integer indices.

    Parameters
    ----------
    bits :
        1-D validated bit array.
    bits_per_value :
        Number of bits represented by each integer.

    Returns
    -------
    np.ndarray
        Integer representation of each bit group.
    """
    b = np.asarray(bits, dtype=_BIT_DTYPE).reshape(-1, bits_per_value)

    weights = (
        1 << np.arange(bits_per_value - 1, -1, -1)
    ).astype(np.int64)

    return b @ weights


def _integers_to_bits(
    values: np.ndarray,
    bits_per_value: int,
) -> BitArray:
    """
    Convert integer values to MSB-first bits.

    Parameters
    ----------
    values :
        Integer array.
    bits_per_value :
        Number of bits per integer.

    Returns
    -------
    BitArray
        Flattened MSB-first bit array.
    """
    values = np.asarray(values, dtype=np.int64).ravel()

    shifts = np.arange(
        bits_per_value - 1,
        -1,
        -1,
        dtype=np.int64,
    )

    bits = (
        (values[:, None] >> shifts) & 1
    ).astype(_BIT_DTYPE)

    return bits.ravel()


# ---------------------------------------------------------------------------
# QPSK
# ---------------------------------------------------------------------------

def _qpsk_constellation() -> ComplexArray:
    """
    Build the Gray-coded unit-power QPSK constellation.

    Mapping:

        00 -> (+1 + 1j) / sqrt(2)
        01 -> (+1 - 1j) / sqrt(2)
        11 -> (-1 - 1j) / sqrt(2)
        10 -> (-1 + 1j) / sqrt(2)

    Array index corresponds directly to the binary bit-group index:

        00 -> index 0
        01 -> index 1
        10 -> index 2
        11 -> index 3

    Therefore the physical point ordering is deliberately arranged to
    preserve the Gray-coded bit labels.
    """
    constellation = np.array(
        [
            1 + 1j,     # 00
            1 - 1j,     # 01
            -1 + 1j,    # 10
            -1 - 1j,    # 11
        ],
        dtype=_CONSTELLATION_DTYPE,
    )

    constellation /= np.sqrt(2.0)

    return constellation


# ---------------------------------------------------------------------------
# Square QAM
# ---------------------------------------------------------------------------

def _square_qam_constellation(M: int) -> ComplexArray:
    """
    Build a Gray-coded square M-QAM constellation.

    Supported orders:

        16, 64, 256, 1024

    Gray coding is applied independently to the I and Q axes.

    The resulting constellation is normalized to unit average power.
    """
    if M not in _SUPPORTED_QAM_ORDERS:
        raise ValueError(
            f"Unsupported square QAM order: {M}. "
            f"Supported orders are {_SUPPORTED_QAM_ORDERS}."
        )

    levels_per_axis = int(np.sqrt(M))
    bits_per_axis = int(np.log2(levels_per_axis))

    # Natural integer indices:
    #
    #   0, 1, 2, ..., levels_per_axis - 1
    #
    # are transformed to Gray indices before selecting physical levels.
    binary_indices = np.arange(
        levels_per_axis,
        dtype=np.int64,
    )

    gray_indices = _gray_encode(binary_indices)

    # PAM levels are ordered from negative to positive.
    levels = np.arange(
        -(levels_per_axis - 1),
        levels_per_axis,
        2,
        dtype=np.float64,
    )

    # Gray index -> physical amplitude.
    axis = levels[gray_indices]

    # Each QAM symbol is formed from one I-axis and one Q-axis value.
    #
    # The constellation index is:
    #
    #   I_index * levels_per_axis + Q_index
    #
    I, Q = np.meshgrid(
        axis,
        axis,
        indexing="ij",
    )

    constellation = (I + 1j * Q).ravel()

    # Unit average symbol power.
    average_power = np.mean(
        np.abs(constellation) ** 2
    )

    constellation /= np.sqrt(average_power)

    return constellation.astype(_CONSTELLATION_DTYPE)


# ---------------------------------------------------------------------------
# Constellation registry
# ---------------------------------------------------------------------------

_CONSTELLATIONS: Dict[ModulationType, ComplexArray] = {
    ModulationType.QPSK: _qpsk_constellation(),
    ModulationType.QAM16: _square_qam_constellation(16),
    ModulationType.QAM64: _square_qam_constellation(64),
    ModulationType.QAM256: _square_qam_constellation(256),
    ModulationType.QAM1024: _square_qam_constellation(1024),
}


_BITS_PER_SYMBOL: Dict[ModulationType, int] = {
    ModulationType.QPSK: 2,
    ModulationType.QAM16: 4,
    ModulationType.QAM64: 6,
    ModulationType.QAM256: 8,
    ModulationType.QAM1024: 10,
}


# ---------------------------------------------------------------------------
# Public information API
# ---------------------------------------------------------------------------

def bits_per_symbol(mod: ModulationType) -> int:
    """
    Return the number of information bits carried by one symbol.

    Examples
    --------
    QPSK   -> 2
    16-QAM -> 4
    64-QAM -> 6
    256-QAM -> 8
    1024-QAM -> 10
    """
    _validate_modulation(mod)

    try:
        return _BITS_PER_SYMBOL[mod]
    except KeyError as exc:
        raise ValueError(
            f"Unsupported modulation: {mod!r}."
        ) from exc


def modulation_order(mod: ModulationType) -> int:
    """
    Return the constellation size M.

    This is equivalent to:

        2 ** bits_per_symbol(mod)
    """
    return 1 << bits_per_symbol(mod)


def get_constellation(mod: ModulationType) -> ComplexArray:
    """
    Return a defensive copy of the requested constellation.

    The returned array can safely be modified by the caller without
    changing the module's internal constellation registry.
    """
    _validate_modulation(mod)

    try:
        return _CONSTELLATIONS[mod].copy()
    except KeyError as exc:
        raise ValueError(
            f"Unsupported modulation: {mod!r}."
        ) from exc


# ---------------------------------------------------------------------------
# Modulation
# ---------------------------------------------------------------------------

def modulate(
    bits: BitArray,
    mod: ModulationType = ModulationType.QPSK,
) -> ComplexArray:
    """
    Map bits to complex constellation symbols.

    Parameters
    ----------
    bits :
        1-D bit array containing only 0 and 1.

    mod :
        Modulation scheme.

    Returns
    -------
    ComplexArray
        1-D complex symbol array with unit average power.

    Raises
    ------
    ValueError
        If the bit count is not divisible by the number of bits per symbol.

    Notes
    -----
    Bit groups are interpreted MSB-first.

    QAM uses Gray-coded axis mapping.
    """
    validate_bits(bits)
    _validate_modulation(mod)

    bps = bits_per_symbol(mod)
    constellation = _CONSTELLATIONS[mod]

    bit_array = np.asarray(
        bits,
        dtype=_BIT_DTYPE,
    ).ravel()

    if bit_array.size == 0:
        raise ValueError(
            "Cannot modulate an empty bit array."
        )

    if bit_array.size % bps != 0:
        raise ValueError(
            f"Number of bits ({bit_array.size}) must be a "
            f"multiple of bits_per_symbol ({bps}) for {mod.name}."
        )

    # ------------------------------------------------------------------
    # QPSK
    # ------------------------------------------------------------------
    if mod is ModulationType.QPSK:
        indices = _bits_to_integers(
            bit_array,
            bits_per_value=2,
        )

        symbols = constellation[indices]

    # ------------------------------------------------------------------
    # Square QAM
    # ------------------------------------------------------------------
    else:
        bits_per_axis = bps // 2

        groups = bit_array.reshape(-1, bps)

        i_bits = groups[:, :bits_per_axis]
        q_bits = groups[:, bits_per_axis:]

        i_binary = _bits_to_integers(
            i_bits.ravel(),
            bits_per_axis,
        )

        q_binary = _bits_to_integers(
            q_bits.ravel(),
            bits_per_axis,
        )

        i_gray = _gray_encode(i_binary)
        q_gray = _gray_encode(q_binary)

        levels_per_axis = 1 << bits_per_axis

        indices = (
            i_gray * levels_per_axis
            + q_gray
        )

        symbols = constellation[indices]

    symbols = np.asarray(
        symbols,
        dtype=_CONSTELLATION_DTYPE,
    )

    validate_complex_signal(symbols)

    return symbols


# ---------------------------------------------------------------------------
# Demodulation
# ---------------------------------------------------------------------------

def demodulate(
    symbols: ComplexArray,
    mod: ModulationType = ModulationType.QPSK,
) -> BitArray:
    """
    Hard-decision minimum-Euclidean-distance demodulation.

    Parameters
    ----------
    symbols :
        Received complex symbols. They may contain noise and should normally
        already be equalized when a channel model is active.

    mod :
        Modulation scheme used by the transmitter.

    Returns
    -------
    BitArray
        Recovered 1-D MSB-first bit array.

    Notes
    -----
    The detector performs minimum Euclidean-distance detection against the
    complete normalized constellation.

    This is intentionally a hard-decision detector. Soft-decision LLR
    demodulation can be added later without changing the current API.
    """
    validate_complex_signal(symbols)
    _validate_modulation(mod)

    bps = bits_per_symbol(mod)
    constellation = _CONSTELLATIONS[mod]

    received = np.asarray(
        symbols,
        dtype=_CONSTELLATION_DTYPE,
    ).ravel()

    if received.size == 0:
        raise ValueError(
            "Cannot demodulate an empty symbol array."
        )

    # Vectorized minimum-distance detector.
    #
    # Shape:
    #
    #   received[:, None] -> (N, 1)
    #   constellation[None, :] -> (1, M)
    #
    # Result:
    #
    #   distances -> (N, M)
    distances = np.abs(
        received[:, None]
        - constellation[None, :]
    )

    indices = np.argmin(
        distances,
        axis=1,
    ).astype(np.int64)

    # ------------------------------------------------------------------
    # QPSK
    # ------------------------------------------------------------------
    if mod is ModulationType.QPSK:
        bits = _integers_to_bits(
            indices,
            bits_per_value=2,
        )

    # ------------------------------------------------------------------
    # Square QAM
    # ------------------------------------------------------------------
    else:
        bits_per_axis = bps // 2
        levels_per_axis = 1 << bits_per_axis

        i_gray = indices // levels_per_axis
        q_gray = indices % levels_per_axis

        i_binary = _gray_decode(i_gray)
        q_binary = _gray_decode(q_gray)

        i_bits = _integers_to_bits(
            i_binary,
            bits_per_axis,
        ).reshape(-1, bits_per_axis)

        q_bits = _integers_to_bits(
            q_binary,
            bits_per_axis,
        ).reshape(-1, bits_per_axis)

        bits = np.concatenate(
            [i_bits, q_bits],
            axis=1,
        ).ravel()

    bits = np.asarray(
        bits,
        dtype=_BIT_DTYPE,
    )

    validate_bits(bits)

    return bits
```
