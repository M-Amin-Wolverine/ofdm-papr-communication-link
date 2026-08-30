"""
Source bit generation
=====================

Produces the original information bits that enter the communication chain.

Stage-1 contract
----------------
- Only random binary sources are required.
- The generator MUST come from ``utils.random`` (no global np.random).
- Output is always a 1-D ``BitArray`` with values in {0, 1}.
"""

from __future__ import annotations

from typing import Optional

import numpy as np

from ofdm_linksim.core.types import BitArray, validate_bits
from ofdm_linksim.utils.random import source_rng, make_master_seed


def generate_random_bits(
    n_bits: int,
    *,
    seed: int,
    rng: Optional[np.random.Generator] = None,
) -> BitArray:
    """
    Generate a vector of independent Bernoulli(1/2) bits.

    Parameters
    ----------
    n_bits :
        Number of bits to generate (must be positive).
    seed :
        Master experiment seed. Used only when ``rng`` is not supplied.
    rng :
        Optional pre-created Generator (normally the ``source`` stream).
        When provided, ``seed`` is ignored for generation.

    Returns
    -------
    BitArray
        1-D array of dtype uint8 containing only 0 and 1.
    """
    if not isinstance(n_bits, (int, np.integer)) or n_bits <= 0:
        raise ValueError(f"n_bits must be a positive integer, got {n_bits}")

    if rng is None:
        rng = source_rng(make_master_seed(seed))

    bits = rng.integers(0, 2, size=n_bits, dtype=np.uint8)
    validate_bits(bits)
    return bits


def bits_from_bytes(data: bytes) -> BitArray:
    """
    Convert an arbitrary byte string into a bit array (MSB first per byte).

    Useful later for real file sources (text / image / binary).
    """
    if not data:
        raise ValueError("Cannot convert empty bytes to bits.")

    arr = np.frombuffer(data, dtype=np.uint8)
    # unpackbits gives MSB first inside each byte
    bits = np.unpackbits(arr)
    validate_bits(bits)
    return bits


def bits_to_bytes(bits: BitArray) -> bytes:
    """
    Pack a bit array back into bytes (pads with zeros if length is not
    a multiple of 8).
    """
    validate_bits(bits)
    b = np.asarray(bits, dtype=np.uint8).ravel()

    pad = (-b.size) % 8
    if pad:
        b = np.concatenate([b, np.zeros(pad, dtype=np.uint8)])

    packed = np.packbits(b)
    return packed.tobytes()
