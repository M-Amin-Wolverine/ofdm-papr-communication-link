import numpy as np
import pytest

from ofdm_linksim.ofdm_demodulator import demodulate_ofdm
from ofdm_linksim.core.types import MappingType
from ofdm_linksim.utils.random import make_stream_rngs


def test_demodulate_ofdm_basic():
    rng = make_stream_rngs(42)["source"]
    # dummy symbols
    symbols = rng.normal(size=192) + 1j * rng.normal(size=192)
    tx = type("Tx", (), {"ofdm_grid": type("Grid", (), {"data_indices": np.arange(192), "pilot_indices": np.array([])})()})()

    rx = demodulate_ofdm(
        symbols,
        data_indices=tx.ofdm_grid.data_indices,
        pilot_indices=tx.ofdm_grid.pilot_indices,
        fft_size=256,
        oversampling=4,
        cyclic_prefix_length=16,
        n_symbols=1,
        cp_included=False,
    )

    assert hasattr(rx, "equalized_symbols")
    assert rx.equalized_symbols.shape == (192,)
