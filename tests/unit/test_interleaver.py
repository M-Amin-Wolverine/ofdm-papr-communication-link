import numpy as np
import pytest

from ofdm_linksim.interleaver import interleave, deinterleave
from ofdm_linksim.core.types import InterleavingType


def test_interleaver_none():
    bits = np.array([0, 1, 0, 1, 1, 0, 1, 0], dtype=bool)
    inter, meta = interleave(bits, scheme=InterleavingType.NONE)
    assert np.array_equal(inter, bits)
    de, meta = deinterleave(inter)
    assert np.array_equal(de, bits)
