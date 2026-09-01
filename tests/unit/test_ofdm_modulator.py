import numpy as np
import pytest

from ofdm_linksim.ofdm_modulator import modulate_ofdm
from ofdm_linksim.core.types import MappingType, ModulationType
from ofdm_linksim.utils.random import make_stream_rngs


def test_modulate_ofdm_basic():
    rng = make_stream_rngs(42)["source"]
    bits = rng.integers(0, 2, size=192 * 4 * 2, dtype=bool)  # 4 symbols QPSK
    symbols = np.random.randn(192 * 4) + 1j * np.random.randn(192 * 4)  # dummy

    tx = modulate_ofdm(
        symbols,
        source_bits=bits,
        coded_bits=bits,
        interleaved_bits=bits,
        fft_size=256,
        oversampling=4,
        cyclic_prefix_length=16,
        n_data=192,
        n_pilots=0,
        mapping=MappingType.SYMMETRIC,
    )

    assert tx.waveform.n_symbols == 4
    assert tx.waveform.fft_size == 256
    assert tx.waveform.cyclic_prefix_length == 16
    assert tx.waveform.oversampling == 4
