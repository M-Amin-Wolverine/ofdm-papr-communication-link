import numpy as np
import pytest

from ofdm_linksim.source import generate_random_bits
from ofdm_linksim.modulation import modulate, demodulate, bits_per_symbol
from ofdm_linksim.ofdm_modulator import modulate_ofdm
from ofdm_linksim.ofdm_demodulator import demodulate_ofdm
from ofdm_linksim.channel import apply_channel
from ofdm_linksim.analysis.ber import compute_ber
from ofdm_linksim.core.types import (
    ChannelType,
    MappingType,
    ModulationType,
)
from ofdm_linksim.utils.random import make_stream_rngs


@pytest.mark.integration
def test_end_to_end_baseline_link():
    """
    تست کامل Stage-1 baseline: TX -> OFDM -> AWGN -> RX -> BER
    """
    seed = 42
    n_blocks = 4          # کوچک برای تست سریع
    n_data = 192
    fft_size = 256
    oversampling = 4
    cp_length = 16
    snr_db = 20.0
    mod = ModulationType.QPSK

    streams = make_stream_rngs(seed)
    rng_src = streams["source"]
    rng_ch = streams["channel"]

    # --- TX ---
    bps = bits_per_symbol(mod)
    n_mod_symbols = n_data * n_blocks
    n_bits = n_mod_symbols * bps
    bits = generate_random_bits(n_bits, rng=rng_src)

    symbols = modulate(bits, mod=mod)

    tx_frame = modulate_ofdm(
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

    # --- Channel (AWGN) ---
    ch_out = apply_channel(
        tx_frame,
        snr_db=snr_db,
        rng=rng_ch,
        channel_type=ChannelType.AWGN,
    )

    # --- RX ---
    demod = demodulate_ofdm(
        ch_out.signal,
        data_indices=tx_frame.ofdm_grid.data_indices,
        pilot_indices=tx_frame.ofdm_grid.pilot_indices,
        fft_size=fft_size,
        oversampling=oversampling,
        cyclic_prefix_length=cp_length,
        n_symbols=tx_frame.waveform.n_symbols,
        cp_included=tx_frame.waveform.cp_included,
    )

    rx_symbols = np.asarray(demod.equalized_symbols, dtype=np.complex128)
    rx_bits = demodulate(rx_symbols, mod=mod)

    # BER
    ber = compute_ber(bits[: len(rx_bits)], rx_bits, snr_db=snr_db)

    # Assertions
    assert ber.ber < 0.05          # QPSK @ 20dB باید خیلی پایین باشد
    assert ber.bit_errors < 5      # چون نویز کم داریم
    assert len(rx_bits) == len(bits)  # round-trip کامل
