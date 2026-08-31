"""
Channel Coding - Transmitter Side
=================================

Forward Error Correction (FEC) / channel-coding stage of OFDM-LinkSim.

Stage-1 baseline
----------------
CodingType.NONE performs a strict identity pass-through:

    information bits
        │
        ▼
    CodingType.NONE
        │
        ▼
    coded bits

No redundancy is added in Stage-1.

Architecture
------------
The encoder is intentionally designed as a codec dispatch layer so that
future channel-coding algorithms can be introduced without changing the
pipeline-facing interface.

Planned codecs
--------------
- NONE
    Identity / uncoded transmission.

- CONVOLUTIONAL
    Future convolutional encoder.

- LDPC
    Future LDPC encoder.

- POLAR
    Future Polar encoder.

Design principles
-----------------
1. CodingType.NONE MUST return an exact copy of the input.
2. Input bits are always validated before processing.
3. The encoder never modifies the caller's input array in-place.
4. Unsupported codecs fail explicitly.
5. Randomness is not used by the Stage-1 encoder.
6. Future codec-specific configuration is passed through ``kwargs``.
7. The public aliases ``channel_encoder`` and ``encoder`` remain stable.
8. The module is transmitter-side only; decoding belongs to the receiver
   side and must not be mixed into this file.

Research-oriented design
------------------------
The encoder is kept separate from CRC.

Recommended transmitter ordering:

    Source
      │
      ▼
    CRC
      │
      ▼
    Channel Encoder
      │
      ▼
    Interleaver
      │
      ▼
    Modulation

Recommended receiver ordering:

    Demodulation
      │
      ▼
    Deinterleaver
      │
      ▼
    Channel Decoder
      │
      ▼
    CRC Check

This separation allows BER, FER, coding gain, and PAPR experiments
to be evaluated independently.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from ofdm_linksim.core.types import (
    BitArray,
    CodingType,
    validate_bits,
)


# ============================================================================
# Configuration
# ============================================================================

SUPPORTED_CODING_TYPES = frozenset(
    {
        CodingType.NONE,
    }
)

# Future codecs can be registered here when their implementations are
# introduced. Keeping the registry explicit prevents accidentally
# pretending that an unimplemented codec is available.


# ============================================================================
# Validation helpers
# ============================================================================


def _validate_coding_type(
    coding: CodingType,
) -> None:
    """
    Validate the requested channel-coding mode.

    A dedicated helper keeps the public encoder readable and gives us
    one place to extend validation when additional codecs are added.
    """
    if not isinstance(coding, CodingType):
        raise TypeError(
            "coding must be an instance of CodingType."
        )


def _normalize_bits(
    bits: BitArray,
) -> BitArray:
    """
    Validate and normalize an input bit vector.

    The returned array is always:

        dtype = uint8
        shape = (N,)
        contiguous = True

    A copy is intentionally produced so that the encoder can never
    mutate the caller's buffer.
    """
    validate_bits(bits)

    data = np.asarray(
        bits,
        dtype=np.uint8,
    ).ravel()

    if data.size == 0:
        raise ValueError(
            "Input bit sequence cannot be empty."
        )

    if not np.all(
        (data == 0) | (data == 1)
    ):
        raise ValueError(
            "Input contains values other than binary 0/1."
        )

    return np.ascontiguousarray(
        data,
        dtype=np.uint8,
    )


# ============================================================================
# Codec metadata
# ============================================================================


def coding_rate(
    coding: CodingType,
    **kwargs: Any,
) -> float:
    """
    Return the nominal code rate of the selected coding scheme.

    Stage-1
    -------
    CodingType.NONE has:

        R = 1.0

    Future codecs should return their effective rate here.

    Parameters
    ----------
    coding:
        Requested coding type.

    kwargs:
        Reserved for codec-specific configuration.
    """
    _validate_coding_type(coding)

    if coding is CodingType.NONE:
        return 1.0

    raise NotImplementedError(
        f"Coding rate for {coding} is not implemented yet."
    )


def coding_overhead(
    coding: CodingType,
    **kwargs: Any,
) -> float:
    """
    Return redundancy overhead relative to the information bits.

    Definition:

        overhead = (N - K) / K

    For uncoded transmission:

        overhead = 0.0
    """
    rate = coding_rate(
        coding,
        **kwargs,
    )

    if rate <= 0.0 or rate > 1.0:
        raise ValueError(
            f"Invalid coding rate: {rate}"
        )

    return float(
        (1.0 / rate) - 1.0
    )


# ============================================================================
# Main encoder
# ============================================================================


def encode(
    bits: BitArray,
    *,
    coding: CodingType = CodingType.NONE,
    **kwargs: Any,
) -> BitArray:
    """
    Encode information bits using the selected channel code.

    Parameters
    ----------
    bits:
        Information-bit sequence.

    coding:
        Channel coding scheme.

        Stage-1 supports only:

            CodingType.NONE

    kwargs:
        Reserved for future codec-specific configuration.

        Examples for future implementations may include:

            convolutional:
                constraint_length
                generator_polynomials
                termination

            LDPC:
                code_rate
                base_graph
                lifting_size

            Polar:
                block_length
                information_length
                frozen_bit_strategy

    Returns
    -------
    BitArray
        Encoded bit sequence.

    Raises
    ------
    TypeError
        If ``coding`` is not a CodingType.

    ValueError
        If the input bit sequence is invalid or empty.

    NotImplementedError
        If a valid CodingType exists but is not yet implemented.
    """
    _validate_coding_type(coding)

    data = _normalize_bits(bits)

    # ------------------------------------------------------------------
    # Stage-1 baseline: uncoded transmission
    # ------------------------------------------------------------------

    if coding is CodingType.NONE:
        return data.copy()

    # ------------------------------------------------------------------
    # Future coding schemes
    # ------------------------------------------------------------------

    raise NotImplementedError(
        f"Channel coding scheme {coding.name!r} "
        "is not implemented yet. "
        "Use CodingType.NONE for the Stage-1 baseline."
    )


# ============================================================================
# Pipeline metadata helper
# ============================================================================


def encoded_length(
    n_information_bits: int,
    *,
    coding: CodingType = CodingType.NONE,
    **kwargs: Any,
) -> int:
    """
    Predict the number of coded bits produced by the encoder.

    Parameters
    ----------
    n_information_bits:
        Number of information bits.

    coding:
        Channel coding scheme.

    Returns
    -------
    int
        Number of coded bits.

    Notes
    -----
    For Stage-1:

        N = K

    Future codecs can account for termination bits, puncturing,
    shortening, rate matching, etc.
    """
    if not isinstance(
        n_information_bits,
        (int, np.integer),
    ):
        raise TypeError(
            "n_information_bits must be an integer."
        )

    if n_information_bits <= 0:
        raise ValueError(
            "n_information_bits must be greater than zero."
        )

    rate = coding_rate(
        coding,
        **kwargs,
    )

    if rate <= 0.0 or rate > 1.0:
        raise ValueError(
            f"Invalid coding rate: {rate}"
        )

    length = int(
        np.ceil(
            n_information_bits / rate
        )
    )

    return length


# ============================================================================
# Pipeline aliases
# ============================================================================


def channel_encoder(
    bits: BitArray,
    **kwargs: Any,
) -> BitArray:
    """
    Pipeline-compatible channel encoder alias.
    """
    return encode(
        bits,
        **kwargs,
    )


def encoder(
    bits: BitArray,
    **kwargs: Any,
) -> BitArray:
    """
    Backward-compatible short alias for ``encode``.
    """
    return encode(
        bits,
        **kwargs,
    )


# ============================================================================
# Public API
# ============================================================================

__all__ = [
    "SUPPORTED_CODING_TYPES",
    "coding_rate",
    "coding_overhead",
    "encoded_length",
    "encode",
    "channel_encoder",
    "encoder",
]
