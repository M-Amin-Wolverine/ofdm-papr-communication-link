import numpy as np
import pytest

from ofdm_linksim.ofdm_modulator import modulate_ofdm
from ofdm_linksim.papr import compute_papr
from ofdm_linksim.utils.random import make_stream_rngs
from ofdm_linksim.core.types import MappingType, ModulationType


@pytest.mark.integration
def test_papr_on_useful_samples_only():
    """
    تست PAPR: باید همیشه روی **useful samples** (بدون CP) محاسبه شود.
    """
    seed = 42
    n_blocks = 10
    n_data = 192
    fft_size = 256
    oversampling = 4
    cp_length = 16
    mod = ModulationType.QPSK

    streams = make_stream_rngs(seed)
    rng_src = streams["source"]

    # ساخت TX
    bits = rng_src.integers(0, 2, size=n_data * n_blocks * 2, dtype=bool)
    symbols = np.random.randn(n_data * n_blocks) + 1j * np.random.randn(n_data * n_blocks)

    tx = modulate_ofdm(
        symbols,
        source_bits=bits,
        coded_bits=bits,
        interleaved_bits=bits,
        fft_size=fft_size,
        oversampling=oversampling,
        cyclic_prefix_length=cp_length,
        n_data=n_data,
        n_pilots=0,
        mapping=MappingType.SYMMETRIC,
    )

    # PAPR (مرجع locked)
    papr = compute_papr(tx.waveform.samples)

    assert papr.n_samples_used < tx.waveform.samples.size  # CP حذف شده
    assert 1.0 <= papr.papr_linear
    assert papr.papr_db >= 0.0
