"""
CRC (Cyclic Redundancy Check)
=============================

Cyclic Redundancy Check stage of OFDM-LinkSim.

Stage-1 baseline
----------------
CRC is disabled by default and therefore behaves as an identity
pass-through:

    input bits
        │
        ▼
      CRC OFF
        │
        ▼
    output bits

Optional CRC-16/CCITT and CRC-32 implementations are provided for
later experiments without changing the pipeline-facing API.

Supported CRC modes
-------------------
- Disabled / identity
- CRC-16/CCITT
- CRC-32

Design principles
-----------------
1. CRC is disabled by default.
2. Disabled CRC MUST return an exact copy of the input bits.
3. All bit arrays are validated through the project's ``validate_bits``.
4. CRC implementations operate MSB-first.
5. CRC width must explicitly be 16 or 32.
6. Encoding appends the CRC remainder to the payload.
7. Decoding verifies and strips the CRC field.
8. CRC verification never silently converts a failed CRC into success.
9. The public pipeline aliases ``crc_encode`` and ``crc_decode`` remain
   available for component injection.
10. The implementation is deterministic and requires no RNG.

CRC-16/CCITT
------------
Polynomial:

    0x1021

CRC-32
-------
Polynomial:

    0x04C11DB7

Important
---------
This module implements the bit-oriented CRC algorithm used by the
project. It is intentionally explicit and research-friendly rather
than optimized for maximum throughput.

The implementation does not silently assume reflected input/output,
XOR-out, or byte-wise lookup-table semantics. This makes the exact
algorithm easier to inspect and reproduce in research experiments.
"""

from __future__ import annotations

from typing import Tuple

import numpy as np

from ofdm_linksim.core.types import (
    BitArray,
    validate_bits,
)


# ============================================================================
# CRC configuration
# ============================================================================

CRC16_WIDTH: int = 16
CRC32_WIDTH: int = 32

CRC16_CCITT_POLY: int = 0x1021
CRC32_POLY: int = 0x04C11DB7


SUPPORTED_CRC_WIDTHS = frozenset({
    CRC16_WIDTH,
    CRC32_WIDTH,
})


# ============================================================================
# Validation helpers
# ============================================================================


def _validate_crc_width(width: int) -> None:
    """
    Validate CRC width.

    Only CRC-16 and CRC-32 are currently supported.
    """
    if not isinstance(width, (int, np.integer)):
        raise TypeError(
            "CRC width must be an integer."
        )

    if int(width) not in SUPPORTED_CRC_WIDTHS:
        raise ValueError(
            "CRC width must be either 16 or 32."
        )


def _validate_crc_polynomial(
    poly: int,
    width: int,
) -> None:
    """Validate that a polynomial fits the requested CRC width."""
    if not isinstance(poly, (int, np.integer)):
        raise TypeError(
            "CRC polynomial must be an integer."
        )

    if poly <= 0:
        raise ValueError(
            "CRC polynomial must be positive."
        )

    if poly >= (1 << width):
        raise ValueError(
            f"CRC polynomial 0x{poly:X} does not fit "
            f"inside a {width}-bit CRC."
        )


# ============================================================================
# Bit/integer conversion helpers
# ============================================================================


def _bits_to_int(
    bits: BitArray,
) -> int:
    """
    Convert an MSB-first bit array to an integer.

    Example
    -------
        [1, 0, 1, 1] -> 0b1011 -> 11
    """
    validate_bits(bits)

    value = 0

    for bit in np.asarray(
        bits,
        dtype=np.uint8,
    ).ravel():
        value = (value << 1) | int(bit)

    return int(value)


def _int_to_bits(
    value: int,
    n_bits: int,
) -> BitArray:
    """
    Convert an integer into an MSB-first bit array.
    """
    if not isinstance(
        n_bits,
        (int, np.integer),
    ):
        raise TypeError(
            "n_bits must be an integer."
        )

    if n_bits <= 0:
        raise ValueError(
            "n_bits must be positive."
        )

    if not isinstance(
        value,
        (int, np.integer),
    ):
        raise TypeError(
            "value must be an integer."
        )

    if value < 0 or value >= (1 << n_bits):
        raise ValueError(
            f"value {value} does not fit in "
            f"{n_bits} bits."
        )

    return np.array(
        [
            (value >> (n_bits - 1 - i)) & 1
            for i in range(n_bits)
        ],
        dtype=np.uint8,
    )


# ============================================================================
# Core CRC engine
# ============================================================================


def _crc_bits(
    data_bits: BitArray,
    poly: int,
    width: int,
) -> BitArray:
    """
    Compute a generic MSB-first bit-oriented CRC.

    Parameters
    ----------
    data_bits:
        Payload bits.

    poly:
        Generator polynomial without the implicit x^width term.

    width:
        CRC register width.

    Returns
    -------
    BitArray
        CRC remainder represented as MSB-first bits.

    Algorithm
    ---------
    The register is initialized to zero.

    Each input bit is shifted into the most-significant side of the
    register. Whenever the MSB is set, the generator polynomial is
    XORed after the shift.

    Finally, ``width`` zero bits are processed to obtain the remainder.
    """
    validate_bits(data_bits)

    if not isinstance(
        width,
        (int, np.integer),
    ):
        raise TypeError(
            "width must be an integer."
        )

    width = int(width)

    if width <= 0:
        raise ValueError(
            "width must be positive."
        )

    _validate_crc_polynomial(
        poly,
        width,
    )

    bits = np.asarray(
        data_bits,
        dtype=np.uint8,
    ).ravel()

    register = 0

    top_bit = 1 << (width - 1)
    mask = (1 << width) - 1

    # ---------------------------------------------------------------
    # Process payload bits
    # ---------------------------------------------------------------

    for bit in bits:
        register ^= int(bit) << (width - 1)

        if register & top_bit:
            register = (
                (register << 1) ^ poly
            ) & mask
        else:
            register = (
                register << 1
            ) & mask

    # ---------------------------------------------------------------
    # Flush CRC register
    # ---------------------------------------------------------------

    for _ in range(width):
        if register & top_bit:
            register = (
                (register << 1) ^ poly
            ) & mask
        else:
            register = (
                register << 1
            ) & mask

    return _int_to_bits(
        register,
        width,
    )


# ============================================================================
# Public CRC primitive
# ============================================================================


def compute_crc(
    bits: BitArray,
    *,
    width: int = CRC16_WIDTH,
) -> BitArray:
    """
    Compute CRC bits without appending them to the payload.

    Parameters
    ----------
    bits:
        Payload bits.

    width:
        CRC width: 16 or 32.

    Returns
    -------
    BitArray
        CRC remainder only.
    """
    validate_bits(bits)
    _validate_crc_width(width)

    if width == CRC16_WIDTH:
        polynomial = CRC16_CCITT_POLY
    elif width == CRC32_WIDTH:
        polynomial = CRC32_POLY
    else:
        # Defensive branch; validation above should make this unreachable.
        raise ValueError(
            f"Unsupported CRC width: {width}"
        )

    return _crc_bits(
        bits,
        polynomial,
        width,
    )


# ============================================================================
# Encoding
# ============================================================================


def encode_crc(
    bits: BitArray,
    *,
    enabled: bool = False,
    width: int = CRC16_WIDTH,
) -> BitArray:
    """
    Append CRC bits to the payload.

    Parameters
    ----------
    bits:
        Input payload bits.

    enabled:
        Enable or disable CRC.

        False:
            Identity pass-through.

        True:
            Append the selected CRC.

    width:
        CRC width: 16 or 32.

    Returns
    -------
    BitArray
        Payload followed by CRC bits.

    Examples
    --------
    Disabled:

        [payload] -> [payload]

    Enabled:

        [payload] -> [payload | CRC]
    """
    validate_bits(bits)

    data = np.asarray(
        bits,
        dtype=np.uint8,
    ).ravel()

    if not enabled:
        return data.copy()

    _validate_crc_width(width)

    crc = compute_crc(
        data,
        width=width,
    )

    encoded = np.concatenate(
        (
            data,
            crc,
        )
    )

    return np.asarray(
        encoded,
        dtype=np.uint8,
    )


# ============================================================================
# Decoding / verification
# ============================================================================


def check_crc(
    bits_with_crc: BitArray,
    *,
    enabled: bool = False,
    width: int = CRC16_WIDTH,
) -> Tuple[BitArray, bool]:
    """
    Verify CRC and remove the CRC field.

    Parameters
    ----------
    bits_with_crc:
        Payload + CRC bits.

    enabled:
        Enable CRC verification.

    width:
        CRC width: 16 or 32.

    Returns
    -------
    payload_bits, ok

    ``ok`` is True only when the received CRC exactly matches the
    locally calculated CRC.

    When CRC is disabled:

        input -> unchanged copy
        ok    -> True
    """
    validate_bits(bits_with_crc)

    data = np.asarray(
        bits_with_crc,
        dtype=np.uint8,
    ).ravel()

    if not enabled:
        return data.copy(), True

    _validate_crc_width(width)

    if data.size < width:
        raise ValueError(
            f"Bit vector length ({data.size}) is shorter "
            f"than the CRC width ({width})."
        )

    payload = data[:-width]
    received_crc = data[-width:]

    expected_crc = compute_crc(
        payload,
        width=width,
    )

    crc_ok = bool(
        np.array_equal(
            received_crc,
            expected_crc,
        )
    )

    return (
        payload.astype(
            np.uint8,
            copy=True,
        ),
        crc_ok,
    )


# ============================================================================
# Decode policy helpers
# ============================================================================


def crc_decode_checked(
    bits_with_crc: BitArray,
    *,
    enabled: bool = False,
    width: int = CRC16_WIDTH,
) -> tuple[BitArray, bool]:
    """
    Pipeline-friendly CRC decoder that preserves verification status.

    This is preferable to ``crc_decode`` when the simulation needs to
    distinguish:

        CRC success
        CRC failure

    rather than merely recovering the payload.
    """
    return check_crc(
        bits_with_crc,
        enabled=enabled,
        width=width,
    )


def crc_is_valid(
    bits_with_crc: BitArray,
    *,
    width: int = CRC16_WIDTH,
) -> bool:
    """
    Return only the CRC verification result.

    This helper is useful for BER/FER-style analysis where the payload
    itself is not needed.
    """
    _, ok = check_crc(
        bits_with_crc,
        enabled=True,
        width=width,
    )

    return bool(ok)


# ============================================================================
# Pipeline aliases
# ============================================================================


def crc_encode(
    bits: BitArray,
    **kwargs,
) -> BitArray:
    """
    Pipeline-compatible CRC encoder.

    Parameters are accepted through ``kwargs`` to remain compatible
    with the project's component-injection interface.
    """
    return encode_crc(
        bits,
        enabled=kwargs.get(
            "enabled",
            False,
        ),
        width=kwargs.get(
            "width",
            CRC16_WIDTH,
        ),
    )


def crc_decode(
    bits: BitArray,
    **kwargs,
) -> BitArray:
    """
    Pipeline-compatible CRC decoder.

    Note
    ----
    This function returns only the recovered payload for compatibility
    with a simple decode-stage interface.

    Use ``crc_decode_checked`` when CRC verification status is required.
    """
    payload, _ = check_crc(
        bits,
        enabled=kwargs.get(
            "enabled",
            False,
        ),
        width=kwargs.get(
            "width",
            CRC16_WIDTH,
        ),
    )

    return payload


# ============================================================================
# Public API
# ============================================================================

__all__ = [
    "CRC16_WIDTH",
    "CRC32_WIDTH",
    "CRC16_CCITT_POLY",
    "CRC32_POLY",
    "SUPPORTED_CRC_WIDTHS",
    "compute_crc",
    "encode_crc",
    "check_crc",
    "crc_decode_checked",
    "crc_is_valid",
    "crc_encode",
    "crc_decode",
]
