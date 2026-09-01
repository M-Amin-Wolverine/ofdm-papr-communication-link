import numpy as np
import pytest

from ofdm_linksim.channel_coding import encode, decode
from ofdm_linksim.core.types import CodingType


def test_channel_coding_none():
    bits = np.array([0, 1, 0, 1], dtype=bool)
    coded, meta = encode(bits, scheme=CodingType.NONE)
    assert np.array_equal(coded, bits)
    decoded, meta = decode(coded)
    assert np.array_equal(decoded, bits)
