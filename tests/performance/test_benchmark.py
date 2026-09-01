"""
Performance / scale smoke tests
===============================

These are **not** strict latency SLOs. They verify that core Stage-1 paths
scale to a moderate number of OFDM symbols without pathological slowdowns
and that timing is measurable and finite.

Run::

    pytest tests/performance -q
    pytest tests/performance -q -m performance

Skip in fast CI if desired::

    pytest tests/ -q -m "not performance"
"""

from __future__ import annotations

import time

import numpy as np
import pytest

from ofdm_linksim.channel import apply_channel
from ofdm_linksim.core.types import (
    ChannelType,
    MappingType,
    ModulationType,
)
from ofdm_linksim.modulation import bits_per_symbol, demodulate, modulate
from ofdm_linksim.ofdm_demodulator import demodulate_ofdm
from ofdm_linksim.ofdm_modulator import modulate_ofdm
from ofdm_linksim.papr import compute_papr
from ofdm_linksim.source import generate_random_bits
from ofdm_linksim.utils.random import make_stream_rngs


# Moderate size: enough to exercise FFT/oversampling, small enough for CI
N_BLOCKS = 64
N_DATA = 192
FFT_SIZE = 256
OVERSAMPLING = 4
CP_LENGTH = 16
SEED = 42
SNR_DB = 20.0
MOD = ModulationType.QPSK

# Soft ceiling (seconds). Machines vary; this only catches catastrophic regressions.
MAX_TX_SEC = 8.0
MAX_FULL_LINK_SEC = 15.0
MAX_PAPR_SEC = 5.0


def _build_tx(n_blocks: int = N_BLOCKS):
    streams = make_stream_rngs(SEED)
    bps = bits_per_symbol(MOD)
    n_bits = N_DATA * n_blocks * bps
    bits = generate_random_bits(n_bits, rng=streams["source"])
    symbols = modulate(bits, mod=MOD)
    tx = modulate_ofdm(
        symbols,
        source_bits=bits,
        coded_bits=bits,
        interleaved_bits=bits,
        fft_size=FFT_SIZE,
        oversampling=OVERSAMPLING,
        cyclic_prefix_length=CP_LENGTH,
        n_data=N_DATA,
        n_pilots=0,
        mapping=MappingType.SYMMETRIC,
    )
    return tx, bits, streams


@pytest.mark.performance
def test_ofdm_modulator_throughput():
    """OFDM TX for N_BLOCKS symbols should finish in a reasonable wall time."""
    t0 = time.perf_counter()
    tx, _bits, _streams = _build_tx(N_BLOCKS)
    elapsed = time.perf_counter() - t0

    assert tx.waveform.n_symbols == N_BLOCKS
    assert elapsed < MAX_TX_SEC, f"modulate_ofdm too slow: {elapsed:.3f}s"


@pytest.mark.performance
def test_papr_on_moderate_waveform():
    """PAPR measurement on useful samples stays bounded in time."""
    tx, _bits, _streams = _build_tx(N_BLOCKS)

    t0 = time.perf_counter()
    pr = compute_papr(tx.waveform)
    elapsed = time.perf_counter() - t0

    assert pr.papr_linear >= 1.0
    assert np.isfinite(pr.papr_db)
    assert elapsed < MAX_PAPR_SEC, f"compute_papr too slow: {elapsed:.3f}s"


@pytest.mark.performance
def test_full_link_moderate_scale():
    """
    TX → AWGN → RX → demod for N_BLOCKS symbols.
    Soft wall-clock bound only.
    """
    t0 = time.perf_counter()

    tx, bits, streams = _build_tx(N_BLOCKS)
    ch = apply_channel(
        tx,
        snr_db=SNR_DB,
        rng=streams["channel"],
        channel_type=ChannelType.AWGN,
    )
    demod = demodulate_ofdm(
        ch.signal,
        data_indices=tx.ofdm_grid.data_indices,
        pilot_indices=tx.ofdm_grid.pilot_indices,
        fft_size=FFT_SIZE,
        oversampling=OVERSAMPLING,
        cyclic_prefix_length=CP_LENGTH,
        n_symbols=tx.waveform.n_symbols,
        cp_included=tx.waveform.cp_included,
    )
    rx_bits = demodulate(
        np.asarray(demod.equalized_symbols).ravel(),
        mod=MOD,
    )
    elapsed = time.perf_counter() - t0

    assert rx_bits.size > 0
    assert bits.size >= rx_bits.size
    assert elapsed < MAX_FULL_LINK_SEC, f"full link too slow: {elapsed:.3f}s"


@pytest.mark.performance
def test_scaling_is_roughly_linear():
    """
    Doubling block count should not explode runtime super-linearly.
    Allow a generous factor for noise and JIT/cache effects.
    """
    t1_0 = time.perf_counter()
    _build_tx(32)
    t1 = time.perf_counter() - t1_0

    t2_0 = time.perf_counter()
    _build_tx(64)
    t2 = time.perf_counter() - t2_0

    # Avoid division by zero on very fast machines
    t1 = max(t1, 1e-6)
    ratio = t2 / t1
    assert ratio < 6.0, f"unexpected super-linear scaling: ratio={ratio:.2f}"
