"""
Channel decoding (receiver side)
================================

Stage-1 baseline: CodingType.NONE → pure identity.
"""

from __future__ import annotations

import numpy as np

from ofdm_linksim.core.types import BitArray, CodingType, validate_bits


def decode(
    bits: BitArray,
    *,
    coding: CodingType = CodingType.NONE,
    **kwargs,
) -> BitArray:
    """
    Decode coded bits back to information bits.

    Stage-1: returns an exact copy of the input.
    """
    validate_bits(bits)
    data = np.asarray(bits, dtype=np.uint8).ravel()

    if coding is CodingType.NONE:
        return data.copy()

    raise NotImplementedError(
        f"Coding scheme {coding} is not implemented in Stage-1. "
        "Use CodingType.NONE."
    )


channel_decoder = decode
decoder = decode
