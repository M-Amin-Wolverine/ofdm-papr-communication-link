import pytest
import numpy as np

from ofdm_linksim.source import generate_random_bits, bits_from_bytes
from ofdm_linksim.utils.random import make_stream_rngs


def test_generate_random_bits():
    rng = make_stream_rngs(42)["source"]
    bits = generate_random_bits(100, rng=rng)
    assert bits.dtype == np.bool_
    assert bits.size == 100
    assert np.all(np.logical_or(bits == 0, bits == 1))


def test_bits_from_bytes():
    bytes_data = b"hello world"
    bits = bits_from_bytes(bytes_data)
    assert len(bits) == len(bytes_data) * 8
    assert bits.dtype == np.bool_


def test_randomness_is_deterministic():
    """آزمون reproducibility با seed ثابت"""
    rng = make_stream_rngs(42)["source"]
    bits1 = generate_random_bits(20, rng=rng)
    bits2 = generate_random_bits(20, rng=rng)
    assert np.array_equal(bits1, bits2)
