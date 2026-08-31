"""
Bit interleaving / de-interleaving
==================================

Receiver/transmitter-side bit permutation utilities for OFDM-LinkSim.

Interleaving is used to redistribute adjacent coded bits across a
different time/frequency structure. This can improve robustness against
burst errors and frequency-selective fading by preventing consecutive
information bits from being affected by the same local channel event.

Design goals
------------
- Strict bit validation.
- Deterministic and exactly reversible transforms.
- Explicit interleaving-mode dispatch.
- Defensive copies for identity operation.
- Clear validation of block dimensions.
- Easy extension for future interleaving schemes.
- No hidden modification of caller-owned arrays.

Currently supported
--------------------
InterleavingType.NONE
    Identity transformation.

Other modes
-----------
A simple deterministic block interleaver is supported through the
``rows`` and ``cols`` parameters. This implementation is intentionally
kept generic so that more advanced schemes can be introduced later.

Future candidates include
-------------------------
- Random permutation interleaver
- S-random interleaver
- Convolutional interleaver
- Matrix/block interleaver
- Frequency-domain interleaver
- Time-frequency interleaver
- Standard-specific LTE/5G NR interleavers

Public API
----------
interleave(bits, ...)
    Apply the selected bit interleaving transform.

deinterleave(bits, ...)
    Apply the exact inverse transform.

Aliases
-------
interleaver
    Alias for ``interleave``.

deinterleaver
    Alias for ``deinterleave``.
"""

from __future__ import annotations

from typing import Any, Optional

import numpy as np

from ofdm_linksim.core.types import (
    BitArray,
    InterleavingType,
    validate_bits,
)


def _validate_block_dimensions(
    rows: Optional[int],
    cols: Optional[int],
) -> tuple[int, int]:
    """
    Validate and normalize block-interleaver dimensions.

    Parameters
    ----------
    rows:
        Number of rows in the interleaver matrix.

    cols:
        Number of columns in the interleaver matrix.

    Returns
    -------
    tuple[int, int]
        Validated ``(rows, cols)``.

    Raises
    ------
    ValueError
        If either dimension is missing or non-positive.

    TypeError
        If either dimension is not an integer.
    """
    if rows is None or cols is None:
        raise ValueError(
            "rows and cols are required for block interleaving."
        )

    if isinstance(rows, bool) or not isinstance(rows, (int, np.integer)):
        raise TypeError("rows must be a positive integer.")

    if isinstance(cols, bool) or not isinstance(cols, (int, np.integer)):
        raise TypeError("cols must be a positive integer.")

    rows = int(rows)
    cols = int(cols)

    if rows <= 0:
        raise ValueError("rows must be greater than zero.")

    if cols <= 0:
        raise ValueError("cols must be greater than zero.")

    return rows, cols


def _validate_block_length(
    data: BitArray,
    rows: int,
    cols: int,
) -> None:
    """
    Validate that the bit sequence exactly fills the interleaver block.
    """
    expected = rows * cols

    if data.size != expected:
        raise ValueError(
            "Bit sequence length is incompatible with the requested "
            f"interleaver block: got {data.size}, expected {expected} "
            f"({rows} × {cols})."
        )


def _interleave_block(
    data: BitArray,
    rows: int,
    cols: int,
) -> BitArray:
    """
    Apply a deterministic matrix-transpose block interleaver.

    The input sequence is written row-wise into an ``rows × cols``
    matrix and read column-wise.

    Mathematically:

        X = reshape(bits, rows, cols)
        Y = X.T

    The flattened output is therefore:

        interleaved = X.T.ravel()

    This operation is fully reversible when the same ``rows`` and
    ``cols`` values are supplied to ``deinterleave``.
    """
    return (
        np.asarray(data, dtype=np.uint8)
        .reshape(rows, cols)
        .T
        .ravel()
        .copy()
    )


def _deinterleave_block(
    data: BitArray,
    rows: int,
    cols: int,
) -> BitArray:
    """
    Reverse the deterministic matrix-transpose block interleaver.

    The interleaved stream is interpreted as a ``cols × rows`` matrix
    and transposed back to the original ``rows × cols`` arrangement.
    """
    return (
        np.asarray(data, dtype=np.uint8)
        .reshape(cols, rows)
        .T
        .ravel()
        .copy()
    )


def interleave(
    bits: BitArray,
    *,
    interleaving: InterleavingType = InterleavingType.NONE,
    rows: Optional[int] = None,
    cols: Optional[int] = None,
    **kwargs: Any,
) -> BitArray:
    """
    Interleave a sequence of bits.

    Parameters
    ----------
    bits:
        Input bit sequence.

    interleaving:
        Interleaving scheme to use.

        ``InterleavingType.NONE``
            Identity transformation.

        Other values
            Currently interpreted as the generic block-interleaver
            mode when ``rows`` and ``cols`` are supplied.

    rows:
        Number of rows for block interleaving.

    cols:
        Number of columns for block interleaving.

    **kwargs:
        Reserved for future interleaver-specific parameters.

    Returns
    -------
    BitArray
        Interleaved bit sequence.

    Raises
    ------
    TypeError
        If ``bits`` or block dimensions are invalid.

    ValueError
        If the block dimensions are invalid or the input length does
        not exactly match the requested block size.

    Notes
    -----
    ``interleave()`` never modifies the caller-owned input array.
    """
    validate_bits(bits)

    data = np.asarray(bits, dtype=np.uint8).ravel()

    # --------------------------------------------------------------
    # Identity mode
    # --------------------------------------------------------------
    if interleaving is InterleavingType.NONE:
        return data.copy()

    # --------------------------------------------------------------
    # Generic block interleaver
    # --------------------------------------------------------------
    rows, cols = _validate_block_dimensions(rows, cols)
    _validate_block_length(data, rows, cols)

    return _interleave_block(data, rows, cols)


def deinterleave(
    bits: BitArray,
    *,
    interleaving: InterleavingType = InterleavingType.NONE,
    rows: Optional[int] = None,
    cols: Optional[int] = None,
    **kwargs: Any,
) -> BitArray:
    """
    De-interleave a sequence of bits.

    This function implements the exact inverse of ``interleave()``.

    Parameters
    ----------
    bits:
        Interleaved bit sequence.

    interleaving:
        Interleaving scheme that was used at the transmitter.

    rows:
        Number of rows used by the original block interleaver.

    cols:
        Number of columns used by the original block interleaver.

    **kwargs:
        Reserved for future de-interleaver-specific parameters.

    Returns
    -------
    BitArray
        Reconstructed bit sequence.

    Raises
    ------
    TypeError
        If ``bits`` or block dimensions are invalid.

    ValueError
        If the block dimensions are invalid or the input length does
        not match the expected block size.

    Notes
    -----
    For a valid configuration:

        deinterleave(interleave(bits)) == bits

    The returned array is independent from the input array.
    """
    validate_bits(bits)

    data = np.asarray(bits, dtype=np.uint8).ravel()

    # --------------------------------------------------------------
    # Identity mode
    # --------------------------------------------------------------
    if interleaving is InterleavingType.NONE:
        return data.copy()

    # --------------------------------------------------------------
    # Generic block de-interleaver
    # --------------------------------------------------------------
    rows, cols = _validate_block_dimensions(rows, cols)
    _validate_block_length(data, rows, cols)

    return _deinterleave_block(data, rows, cols)


# ----------------------------------------------------------------------
# Backward-compatible public aliases
# ----------------------------------------------------------------------

interleaver = interleave
deinterleaver = deinterleave


__all__ = [
    "interleave",
    "deinterleave",
    "interleaver",
    "deinterleaver",
]
