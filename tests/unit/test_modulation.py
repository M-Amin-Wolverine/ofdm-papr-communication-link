import pytest
import numpy as np

from ofdm_linksim.modulation import modulate, demodulate, bits_per_symbol
from ofdm_linksim.core.types import ModulationType


@pytest.mark.parametrize("mod", [ModulationType.QPSK])
def test_modulate_demodulate_roundtrip(mod):
    bits = np.array([0, 1, 0, 0, 1, 1, 0, 1], dtype=bool)
    symbols = modulate(bits, mod=mod)
    rx_bits = demodulate(symbols, mod=mod)
    assert np.array_equal(bits, rx_bits)


def test_bits_per_symbol():
    assert bits_per_symbol(ModulationType.QPSK) == 2
    assert bits_per_symbol(ModulationType._16QAM) == 4
