import numpy as np
import pytest

from ofdm_linksim.channel import apply_channel
from ofdm_linksim.core.types import ChannelType
from ofdm_linksim.utils.random import make_stream_rngs


def test_apply_channel_awgn():
    rng = make_stream_rngs(42)["channel"]
    tx = type("Tx", (), {"waveform": type("WF", (), {"samples": np.random.randn(256) + 1j * np.random.randn(256)})()})()

    out = apply_channel(
        tx,
        snr_db=20.0,
        rng=rng,
        channel_type=ChannelType.AWGN,
    )

    assert hasattr(out, "signal")
    assert out.signal.samples.shape == tx.waveform.samples.shape
