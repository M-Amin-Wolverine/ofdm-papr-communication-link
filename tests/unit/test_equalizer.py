import numpy as np
import pytest

from ofdm_linksim.equalizer import equalize
from ofdm_linksim.core.types import EqualizationMethod


def test_equalizer_none():
    symbols = np.random.randn(100) + 1j * np.random.randn(100)
    equalized, meta = equalize(symbols, method=EqualizationMethod.NONE)
    assert np.array_equal(equalized, symbols)
